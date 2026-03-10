import { useCallback, useRef, useState } from "react";

export type MessageRole = "user" | "assistant";

export interface ToolEvent {
  tool: string;
  input?: Record<string, unknown>;
  result?: Record<string, unknown>;
  status: "running" | "done";
}

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  tools?: ToolEvent[];
}

interface UseChatReturn {
  messages: ChatMessage[];
  conversationId: string | null;
  isStreaming: boolean;
  error: string | null;
  send: (text: string) => void;
  reset: () => void;
}

let msgCounter = 0;
const uid = () => `msg-${++msgCounter}-${Date.now()}`;

export function useChat(): UseChatReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const send = useCallback(
    async (text: string) => {
      if (!text.trim() || isStreaming) return;

      setError(null);

      // Add user message
      const userMsg: ChatMessage = { id: uid(), role: "user", content: text };
      setMessages((prev) => [...prev, userMsg]);

      // Prepare assistant placeholder
      const assistantId = uid();
      const assistantMsg: ChatMessage = {
        id: assistantId,
        role: "assistant",
        content: "",
        tools: [],
      };
      setMessages((prev) => [...prev, assistantMsg]);
      setIsStreaming(true);

      const controller = new AbortController();
      abortRef.current = controller;

      try {
        const res = await fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: text, conversation_id: conversationId }),
          signal: controller.signal,
        });

        if (!res.ok || !res.body) {
          throw new Error(`Server error: ${res.status}`);
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          let eventType = "";
          for (const line of lines) {
            if (line.startsWith("event: ")) {
              eventType = line.slice(7).trim();
            } else if (line.startsWith("data: ")) {
              const data = JSON.parse(line.slice(6));
              handleEvent(eventType, data, assistantId);
            }
          }
        }
      } catch (err: unknown) {
        if (err instanceof Error && err.name !== "AbortError") {
          setError(err.message);
        }
      } finally {
        setIsStreaming(false);
        abortRef.current = null;
      }
    },
    [conversationId, isStreaming],
  );

  function handleEvent(event: string, data: Record<string, unknown>, assistantId: string) {
    if (event === "meta") {
      setConversationId(data.conversation_id as string);
      return;
    }

    if (event === "error") {
      setError(data.message as string);
      return;
    }

    if (event === "done") return;

    if (event === "message") {
      const type = data.type as string;

      if (type === "text") {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? { ...m, content: m.content + (data.content as string) }
              : m,
          ),
        );
      } else if (type === "tool_start") {
        const tool: ToolEvent = {
          tool: data.tool as string,
          input: data.input as Record<string, unknown>,
          status: "running",
        };
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? { ...m, tools: [...(m.tools || []), tool] }
              : m,
          ),
        );
      } else if (type === "tool_result") {
        setMessages((prev) =>
          prev.map((m) => {
            if (m.id !== assistantId) return m;
            const tools = (m.tools || []).map((t) =>
              t.tool === data.tool && t.status === "running"
                ? { ...t, result: data.result as Record<string, unknown>, status: "done" as const }
                : t,
            );
            return { ...m, tools };
          }),
        );
      }
    }
  }

  const reset = useCallback(() => {
    abortRef.current?.abort();
    setMessages([]);
    setConversationId(null);
    setIsStreaming(false);
    setError(null);
  }, []);

  return { messages, conversationId, isStreaming, error, send, reset };
}
