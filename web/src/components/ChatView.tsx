import type { ChatMessage } from "../hooks/useChat";
import { ChatInput } from "./ChatInput";
import { MessageList } from "./MessageList";

interface Props {
  messages: ChatMessage[];
  onSend: (text: string) => void;
  isStreaming: boolean;
  error: string | null;
}

export function ChatView({ messages, onSend, isStreaming, error }: Props) {
  return (
    <div className="flex-1 flex flex-col h-screen">
      <MessageList messages={messages} />

      {error && (
        <div className="mx-6 mb-2 text-xs text-red-400 bg-red-400/10 border border-red-400/20 rounded-lg px-3 py-2">
          {error}
        </div>
      )}

      <div className="px-6 pb-5 pt-2">
        <ChatInput onSend={onSend} disabled={isStreaming} />
      </div>
    </div>
  );
}
