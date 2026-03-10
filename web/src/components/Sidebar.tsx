import { Hash, Loader2, MessageSquarePlus, Settings, X } from "lucide-react";

interface ConversationItem {
  id: string;
  title: string;
}

interface ServiceStatus {
  connected: boolean;
  team?: string;
  workspace?: string;
}

interface Props {
  slackStatus: ServiceStatus;
  notionStatus: ServiceStatus;
  connecting: string | null;
  currentConversation: ConversationItem | null;
  onNewChat: () => void;
  onConnect: (service: "slack" | "notion") => void;
  onDisconnect: (service: "slack" | "notion") => void;
}

export function Sidebar({
  slackStatus,
  notionStatus,
  connecting,
  currentConversation,
  onNewChat,
  onConnect,
  onDisconnect,
}: Props) {
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

      {/* Conversation list */}
      <div className="flex-1 px-4 overflow-y-auto">
        <p className="text-[11px] text-text-secondary uppercase tracking-wide mt-4 mb-2 px-3">
          최근 대화
        </p>
        {currentConversation ? (
          <div className="text-sm text-text-primary bg-bg-hover rounded-lg px-3 py-2 truncate">
            {currentConversation.title}
          </div>
        ) : (
          <p className="text-xs text-text-secondary/50 px-3">
            대화를 시작해보세요
          </p>
        )}
      </div>

      {/* Bottom: connected services */}
      <div className="border-t border-border p-4 space-y-3">
        <ServiceRow
          icon={<Hash size={13} />}
          name="Slack"
          status={slackStatus}
          accentClass="text-slack bg-slack"
          isConnecting={connecting === "slack"}
          onConnect={() => onConnect("slack")}
          onDisconnect={() => onDisconnect("slack")}
        />
        <ServiceRow
          icon={<Settings size={13} />}
          name="Notion"
          status={notionStatus}
          accentClass="text-notion bg-notion"
          isConnecting={connecting === "notion"}
          onConnect={() => onConnect("notion")}
          onDisconnect={() => onDisconnect("notion")}
        />
      </div>
    </aside>
  );
}

function ServiceRow({
  icon,
  name,
  status,
  accentClass,
  isConnecting,
  onConnect,
  onDisconnect,
}: {
  icon: React.ReactNode;
  name: string;
  status: { connected: boolean; team?: string; workspace?: string };
  accentClass: string;
  isConnecting: boolean;
  onConnect: () => void;
  onDisconnect: () => void;
}) {
  const dotColor = status.connected ? accentClass.split(" ")[1] : "bg-border";
  const detail = status.team || status.workspace;

  if (isConnecting) {
    return (
      <div className="flex items-center gap-2.5 text-xs text-text-secondary">
        <Loader2 size={13} className="animate-spin text-accent" />
        <span>{name} 연결 중...</span>
      </div>
    );
  }

  return (
    <div className="group flex items-center gap-2.5 text-xs text-text-secondary">
      <span className={`w-2 h-2 rounded-full shrink-0 ${dotColor}`} />
      {icon}
      <span>{name}</span>
      {status.connected ? (
        <>
          {detail && <span className="text-[10px] text-text-secondary/60 truncate">{detail}</span>}
          <button
            onClick={onDisconnect}
            className="ml-auto opacity-0 group-hover:opacity-100 text-text-secondary hover:text-red-400 transition-all"
            title="연결 해제"
          >
            <X size={12} />
          </button>
        </>
      ) : (
        <button
          onClick={onConnect}
          className="ml-auto text-[10px] text-accent hover:text-accent-hover transition-colors"
        >
          연결
        </button>
      )}
    </div>
  );
}
