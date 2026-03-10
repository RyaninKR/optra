"""Chat endpoint with SSE streaming."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from server.state import (
    create_conversation,
    delete_conversation,
    get_conversation,
    get_display_messages,
    list_conversations,
)
from server.stream import stream_response

router = APIRouter(prefix="/api")


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None


@router.post("/chat")
async def chat(req: ChatRequest):
    """Send a message and receive SSE stream of agent responses."""
    if req.conversation_id:
        conv = get_conversation(req.conversation_id)
        if not conv:
            raise HTTPException(404, "Conversation not found")
    else:
        conv = create_conversation()

    conv.messages.append({"role": "user", "content": req.message})

    async def generate():
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


@router.get("/conversations/{conv_id}")
async def get_conversation_detail(conv_id: str):
    """Get a conversation with its display messages."""
    conv = get_conversation(conv_id)
    if not conv:
        raise HTTPException(404, "Conversation not found")

    messages = get_display_messages(conv_id)
    return {
        "id": conv.id,
        "title": conv.title,
        "created_at": conv.created_at.isoformat(),
        "messages": messages,
    }


@router.delete("/conversations/{conv_id}")
async def delete_conv(conv_id: str):
    """Delete a conversation."""
    if not delete_conversation(conv_id):
        raise HTTPException(404, "Conversation not found")
    return {"success": True}
