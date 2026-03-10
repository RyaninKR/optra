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

function AssistantMessage({ msg }: { msg: ChatMessage }) {
  return (
    <div className="flex justify-start">
      <div className="max-w-[80%]">
        {msg.tools?.map((tool, i) => (
          <ToolIndicator key={i} tool={tool} />
        ))}
        {msg.content && (
          <div className="assistant-markdown text-sm leading-relaxed">
            <ReactMarkdown>{msg.content}</ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  );
}

export function MessageList({ messages }: { messages: ChatMessage[] }) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="flex-1 overflow-y-auto px-6 py-6 space-y-5">
      {messages.map((msg) =>
        msg.role === "user" ? (
          <UserMessage key={msg.id} msg={msg} />
        ) : (
          <AssistantMessage key={msg.id} msg={msg} />
        ),
      )}
      <div ref={bottomRef} />
    </div>
  );
}
