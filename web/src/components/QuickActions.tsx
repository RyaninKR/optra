import { BarChart3, CalendarDays, Search } from "lucide-react";

interface Props {
  onSelect: (text: string) => void;
}

const ACTIONS = [
  {
    icon: CalendarDays,
    label: "이번 주 업무 요약",
    prompt: "이번 주 업무를 요약해줘",
  },
  {
    icon: Search,
    label: "최근 활동 검색",
    prompt: "최근 활동 중에서 중요한 것들을 보여줘",
  },
  {
    icon: BarChart3,
    label: "업무 인사이트",
    prompt: "지난 30일간 업무 인사이트를 분석해줘",
  },
];

export function QuickActions({ onSelect }: Props) {
  return (
    <div className="space-y-3 mt-8">
      <p className="text-xs text-text-secondary tracking-wide uppercase">
        추천 질문
      </p>
      <div className="flex flex-wrap gap-3">
        {ACTIONS.map((action) => (
          <button
            key={action.label}
            onClick={() => onSelect(action.prompt)}
            className="group flex items-center gap-3 bg-bg-secondary border border-border rounded-xl px-4 py-3 text-left hover:border-accent/30 hover:bg-bg-hover transition-all"
          >
            <action.icon
              size={18}
              className="text-text-secondary group-hover:text-accent transition-colors shrink-0"
            />
            <span className="text-sm text-text-primary">{action.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
