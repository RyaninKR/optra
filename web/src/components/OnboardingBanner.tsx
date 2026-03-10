import { Hash, Loader2, Settings } from "lucide-react";

interface Props {
  slackConnected: boolean;
  notionConnected: boolean;
  connecting: string | null;
  onConnect: (service: "slack" | "notion") => void;
}

export function OnboardingBanner({ slackConnected, notionConnected, connecting, onConnect }: Props) {
  if (slackConnected && notionConnected) return null;

  return (
    <div className="border border-border rounded-xl bg-bg-secondary p-5 space-y-4">
      <div>
        <p className="text-sm font-medium text-text-primary">서비스를 연결하세요</p>
        <p className="text-xs text-text-secondary mt-1">
          업무 기록을 수집하려면 최소 하나의 서비스를 연결해주세요.
        </p>
      </div>

      <div className="flex gap-3">
        {!slackConnected && (
          <button
            onClick={() => onConnect("slack")}
            disabled={connecting === "slack"}
            className="flex items-center gap-2 text-sm border border-border rounded-lg px-4 py-2.5 hover:border-slack/40 hover:bg-bg-hover transition-all disabled:opacity-60"
          >
            {connecting === "slack" ? (
              <Loader2 size={15} className="animate-spin text-slack" />
            ) : (
              <Hash size={15} className="text-slack" />
            )}
            <span className="text-text-primary">
              {connecting === "slack" ? "연결 중..." : "Slack 연결"}
            </span>
          </button>
        )}

        {!notionConnected && (
          <button
            onClick={() => onConnect("notion")}
            disabled={connecting === "notion"}
            className="flex items-center gap-2 text-sm border border-border rounded-lg px-4 py-2.5 hover:border-notion/40 hover:bg-bg-hover transition-all disabled:opacity-60"
          >
            {connecting === "notion" ? (
              <Loader2 size={15} className="animate-spin text-notion" />
            ) : (
              <Settings size={15} className="text-notion" />
            )}
            <span className="text-text-primary">
              {connecting === "notion" ? "연결 중..." : "Notion 연결"}
            </span>
          </button>
        )}
      </div>

      {(slackConnected || notionConnected) && (
        <p className="text-[11px] text-text-secondary">
          {slackConnected ? "Slack" : "Notion"} 연결됨 — 대화를 시작해보세요.
        </p>
      )}
    </div>
  );
}
