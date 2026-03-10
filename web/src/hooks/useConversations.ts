import { useCallback, useState } from "react";

export interface ConversationSummary {
  id: string;
  title: string;
  created_at: string;
  message_count: number;
}

export function useConversations() {
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);

  const refresh = useCallback(async () => {
    try {
      const res = await fetch("/api/conversations");
      if (res.ok) {
        setConversations(await res.json());
      }
    } catch {
      // ignore
    }
  }, []);

  const remove = useCallback(
    async (id: string) => {
      try {
        await fetch(`/api/conversations/${id}`, { method: "DELETE" });
        setConversations((prev) => prev.filter((c) => c.id !== id));
      } catch {
        // ignore
      }
    },
    [],
  );

  return { conversations, refresh, remove };
}
