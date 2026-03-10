import { Check, Loader2 } from "lucide-react";
import type { ToolEvent } from "../hooks/useChat";

const TOOL_LABELS: Record<string, string> = {
  check_auth_status: "연결 상태 확인",
  connect_slack: "Slack 연결",
  connect_notion: "Notion 연결",
  collect_items: "데이터 수집",
  generate_summary: "요약 생성",
  search_items: "검색",
  get_insights: "인사이트 분석",
  get_recent_items: "최근 항목 조회",
  get_stats: "통계 조회",
  categorize_items: "카테고리 분류",
};

export function ToolIndicator({ tool }: { tool: ToolEvent }) {
  const label = TOOL_LABELS[tool.tool] || tool.tool;
  const isRunning = tool.status === "running";

  return (
    <div className="flex items-center gap-2 text-xs text-text-secondary py-1">
      {isRunning ? (
        <Loader2 size={12} className="animate-spin text-accent" />
      ) : (
        <Check size={12} className="text-slack" />
      )}
      <span>{label}</span>
      {!isRunning && tool.result && "fetched" in tool.result && (
        <span className="text-text-secondary/60">
          ({String(tool.result.fetched)}개 항목)
        </span>
      )}
    </div>
  );
}
