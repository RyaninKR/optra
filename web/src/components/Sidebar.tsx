import { Hash, MessageSquarePlus, Settings } from "lucide-react";

interface Props {
  slackConnected: boolean;
  notionConnected: boolean;
  onNewChat: () => void;
}

export function Sidebar({ slackConnected, notionConnected, onNewChat }: Props) {
  return (
    <aside className="w-[260px] bg-bg-secondary border-r border-border flex flex-col h-screen shrink-0">
      {/* Top nav */}
      <div className="p-4 space-y-1">
        <button
          onClick={onNewChat}
          className="w-full flex items-center gap-2.5 text-sm text-text-primary hover:bg-bg-hover rounded-lg px-3 py-2 transition-colors"
        >
          <MessageSquarePlus size={16} />
          새 대화
        </button>
      </div>

      {/* Spacer */}
      <div className="flex-1 px-4 overflow-y-auto">
        <p className="text-[11px] text-text-secondary uppercase tracking-wide mt-4 mb-2 px-3">
          최근 대화
        </p>
        <p className="text-xs text-text-secondary/50 px-3">
          대화를 시작해보세요
        </p>
      </div>

      {/* Bottom: connected services */}
      <div className="border-t border-border p-4 space-y-2">
        <div className="flex items-center gap-2.5 text-xs text-text-secondary">
          <span
            className={`w-2 h-2 rounded-full ${slackConnected ? "bg-slack" : "bg-border"}`}
          />
          <Hash size={13} />
          <span>Slack</span>
          {slackConnected && (
            <span className="ml-auto text-[10px] text-slack">연결됨</span>
          )}
        </div>
        <div className="flex items-center gap-2.5 text-xs text-text-secondary">
          <span
            className={`w-2 h-2 rounded-full ${notionConnected ? "bg-notion" : "bg-border"}`}
          />
          <Settings size={13} />
          <span>Notion</span>
          {notionConnected && (
            <span className="ml-auto text-[10px] text-notion">연결됨</span>
          )}
        </div>
      </div>
    </aside>
  );
}
