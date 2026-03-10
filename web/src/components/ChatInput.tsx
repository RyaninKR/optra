import { ArrowRight } from "lucide-react";
import { useRef, type KeyboardEvent } from "react";

interface Props {
  onSend: (text: string) => void;
  disabled?: boolean;
  placeholder?: string;
  autoFocus?: boolean;
}

export function ChatInput({ onSend, disabled, placeholder, autoFocus }: Props) {
  const ref = useRef<HTMLTextAreaElement>(null);

  function handleKeyDown(e: KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  function submit() {
    const text = ref.current?.value.trim();
    if (!text || disabled) return;
    onSend(text);
    if (ref.current) ref.current.value = "";
  }

  return (
    <div className="border border-border rounded-xl bg-bg-secondary overflow-hidden transition-colors focus-within:border-accent/40">
      <textarea
        ref={ref}
        rows={2}
        placeholder={placeholder || "메시지를 입력하세요..."}
        onKeyDown={handleKeyDown}
        disabled={disabled}
        autoFocus={autoFocus}
        className="w-full bg-transparent px-4 pt-3.5 pb-2 text-sm text-text-primary placeholder:text-text-secondary/60 resize-none outline-none"
      />
      <div className="flex items-center justify-between px-3 pb-2.5">
        <div className="flex items-center gap-3 text-xs text-text-secondary">
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-slack" />
            Slack
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-notion" />
            Notion
          </span>
        </div>
        <button
          onClick={submit}
          disabled={disabled}
          className="flex items-center gap-1.5 bg-accent text-white text-xs font-medium px-4 py-1.5 rounded-lg hover:bg-accent-hover transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
        >
          전송
          <ArrowRight size={14} />
        </button>
      </div>
    </div>
  );
}
