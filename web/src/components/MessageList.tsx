import { useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import type { ChatMessage } from "../hooks/useChat";
import { ToolIndicator } from "./ToolIndicator";

function UserMessage({ msg }: { msg: ChatMessage }) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[70%] bg-bg-hover rounded-2xl rounded-br-sm px-4 py-2.5 text-sm leading-relaxed">
        {msg.content}
      </div>
    </div>
  );
}

function AssistantMessage({ msg, isLast, isStreaming }: { msg: ChatMessage; isLast: boolean; isStreaming: boolean }) {
  const showCursor = isLast && isStreaming;
  const hasContent = msg.content.length > 0;
  const hasRunningTool = msg.tools?.some((t) => t.status === "running");

  return (
    <div className="flex justify-start">
      <div className="max-w-[80%]">
        {msg.tools?.map((tool, i) => (
          <ToolIndicator key={i} tool={tool} />
        ))}
        {hasContent && (
          <div className="assistant-markdown text-sm leading-relaxed">
            <ReactMarkdown>{msg.content}</ReactMarkdown>
            {showCursor && (
              <span className="inline-block w-[5px] h-[14px] bg-accent/70 ml-0.5 align-middle animate-pulse" />
            )}
          </div>
        )}
        {!hasContent && showCursor && !hasRunningTool && (
          <div className="flex items-center gap-1.5 py-1">
            <span className="w-1.5 h-1.5 rounded-full bg-accent/60 animate-pulse" />
            <span className="w-1.5 h-1.5 rounded-full bg-accent/60 animate-pulse [animation-delay:150ms]" />
            <span className="w-1.5 h-1.5 rounded-full bg-accent/60 animate-pulse [animation-delay:300ms]" />
          </div>
        )}
      </div>
    </div>
  );
}

export function MessageList({ messages, isStreaming }: { messages: ChatMessage[]; isStreaming: boolean }) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="flex-1 overflow-y-auto px-6 py-6 space-y-5">
      {messages.map((msg, i) =>
        msg.role === "user" ? (
          <UserMessage key={msg.id} msg={msg} />
        ) : (
          <AssistantMessage
            key={msg.id}
            msg={msg}
            isLast={i === messages.length - 1}
            isStreaming={isStreaming}
          />
        ),
      )}
      <div ref={bottomRef} />
    </div>
  );
}
