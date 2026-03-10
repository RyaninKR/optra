"""Claude tool_use loop → SSE event generator."""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import AsyncGenerator

import anthropic

from optra.agent import TOOLS, TOOL_HANDLERS, SYSTEM_PROMPT
from optra.config import settings
from server.state import Conversation, update_title


def _execute_tool_sync(name: str, input_args: dict) -> str:
    handler = TOOL_HANDLERS.get(name)
    if not handler:
        return json.dumps({"error": f"Unknown tool: {name}"})
    try:
        return handler(**input_args)
    except Exception as e:
        return json.dumps({"error": str(e)})


def _sse_event(event_type: str, data: dict) -> str:
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event_type}\ndata: {payload}\n\n"


async def stream_response(conv: Conversation) -> AsyncGenerator[str, None]:
    """Run the Claude tool_use loop and yield SSE events.

    Yields SSE-formatted strings for:
      - message: text chunks, tool starts, tool results
      - title: conversation title update
      - done: stream end
      - error: on failure
    """
    if not settings.anthropic_api_key:
        yield _sse_event("error", {"message": "ANTHROPIC_API_KEY가 설정되지 않았습니다."})
        yield _sse_event("done", {})
        return

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    system = SYSTEM_PROMPT.format(today=today)

    max_turns = 10  # Safety limit for tool_use loops

    for _ in range(max_turns):
        try:
            response = await asyncio.to_thread(
                client.messages.create,
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                system=system,
                tools=TOOLS,
                messages=conv.messages,
            )
        except anthropic.APIError as e:
            yield _sse_event("error", {"message": str(e)})
            return

        assistant_content = response.content
        conv.messages.append({"role": "assistant", "content": assistant_content})

        # Process each content block
        if response.stop_reason == "tool_use":
            tool_results = []

            for block in assistant_content:
                if block.type == "text" and block.text.strip():
                    yield _sse_event("message", {"type": "text", "content": block.text})
                elif block.type == "tool_use":
                    # Signal tool start
                    yield _sse_event("message", {
                        "type": "tool_start",
                        "tool": block.name,
                        "input": block.input,
                    })

                    # Execute tool in thread pool
                    result = await asyncio.to_thread(
                        _execute_tool_sync, block.name, block.input
                    )

                    # Signal tool result
                    try:
                        parsed = json.loads(result)
                    except json.JSONDecodeError:
                        parsed = {"raw": result}

                    yield _sse_event("message", {
                        "type": "tool_result",
                        "tool": block.name,
                        "result": parsed,
                    })

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            # Feed tool results back to Claude
            conv.messages.append({"role": "user", "content": tool_results})
            continue  # Next iteration of the loop

        # end_turn: stream final text
        for block in assistant_content:
            if block.type == "text" and block.text.strip():
                yield _sse_event("message", {"type": "text", "content": block.text})

        break  # Done

    # Auto-title from first user message
    if conv.title == "새 대화":
        first_user = next(
            (m["content"] for m in conv.messages if m.get("role") == "user" and isinstance(m["content"], str)),
            None,
        )
        if first_user:
            title = first_user[:30].replace("\n", " ")
            if len(first_user) > 30:
                title += "..."
            update_title(conv.id, title)
            yield _sse_event("title", {"title": title})

    yield _sse_event("done", {})
