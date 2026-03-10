import { ChatInput } from "./ChatInput";
import { QuickActions } from "./QuickActions";

interface Props {
  onSend: (text: string) => void;
  disabled?: boolean;
}

export function LandingView({ onSend, disabled }: Props) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center px-6 pb-20">
      <div className="w-full max-w-xl space-y-6">
        <div className="space-y-2">
          <h1 className="text-2xl font-semibold tracking-tight text-text-primary">
            업무 히스토리를 정리해 볼까요?
          </h1>
          <p className="text-sm text-text-secondary">
            Slack, Notion의 업무 기록을 수집하고 요약해드립니다.
          </p>
        </div>

        <ChatInput
          onSend={onSend}
          disabled={disabled}
          placeholder="무엇이든 물어보세요..."
          autoFocus
        />

        <QuickActions onSelect={onSend} />
      </div>
    </div>
  );
}
