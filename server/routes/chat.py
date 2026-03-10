"""Chat endpoint with SSE streaming."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from server.state import create_conversation, get_conversation, list_conversations
from server.stream import stream_response

router = APIRouter(prefix="/api")


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None


@router.post("/chat")
async def chat(req: ChatRequest):
    """Send a message and receive SSE stream of agent responses."""
    # Get or create conversation
    if req.conversation_id:
        conv = get_conversation(req.conversation_id)
        if not conv:
            raise HTTPException(404, "Conversation not found")
    else:
        conv = create_conversation()

    # Append user message
    conv.messages.append({"role": "user", "content": req.message})

    # Stream response
    async def generate():
        # Send conversation ID first
        import json

        yield f"event: meta\ndata: {json.dumps({'conversation_id': conv.id})}\n\n"

        async for event in stream_response(conv):
            yield event

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/conversations")
async def get_conversations():
    """List all conversations."""
    return list_conversations()
