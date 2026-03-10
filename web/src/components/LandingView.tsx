import { ChatInput } from "./ChatInput";
import { OnboardingBanner } from "./OnboardingBanner";
import { QuickActions } from "./QuickActions";

interface Props {
  onSend: (text: string) => void;
  disabled?: boolean;
  slackConnected: boolean;
  notionConnected: boolean;
  connecting: string | null;
  onConnect: (service: "slack" | "notion") => void;
}

export function LandingView({
  onSend,
  disabled,
  slackConnected,
  notionConnected,
  connecting,
  onConnect,
}: Props) {
  const hasAny = slackConnected || notionConnected;

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

        {!hasAny && (
          <OnboardingBanner
            slackConnected={slackConnected}
            notionConnected={notionConnected}
            connecting={connecting}
            onConnect={onConnect}
          />
        )}

        <ChatInput
          onSend={onSend}
          disabled={disabled}
          placeholder={hasAny ? "무엇이든 물어보세요..." : "서비스를 연결하거나 바로 대화를 시작해보세요..."}
          autoFocus
        />

        {hasAny && <QuickActions onSelect={onSend} />}
      </div>
    </div>
  );
}
