import { Square } from "lucide-react";
import type { ChatMessage } from "../hooks/useChat";
import { ChatInput } from "./ChatInput";
import { MessageList } from "./MessageList";

interface Props {
  messages: ChatMessage[];
  onSend: (text: string) => void;
  isStreaming: boolean;
  error: string | null;
  onStop: () => void;
}

export function ChatView({ messages, onSend, isStreaming, error, onStop }: Props) {
  return (
    <div className="flex-1 flex flex-col h-screen">
      <MessageList messages={messages} isStreaming={isStreaming} />

      {error && (
        <div className="mx-6 mb-2 text-xs text-red-400 bg-red-400/10 border border-red-400/20 rounded-lg px-3 py-2">
          {error}
        </div>
      )}

      <div className="px-6 pb-5 pt-2">
        {isStreaming && (
          <div className="flex justify-center mb-3">
            <button
              onClick={onStop}
              className="flex items-center gap-1.5 text-xs text-text-secondary hover:text-text-primary border border-border rounded-lg px-3 py-1.5 transition-colors"
            >
              <Square size={10} className="fill-current" />
              생성 중지
            </button>
          </div>
        )}
        <ChatInput onSend={onSend} disabled={isStreaming} />
      </div>
    </div>
  );
}
