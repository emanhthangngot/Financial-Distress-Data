/**
 * The typed context the analysis assistant is allowed to know about the page it
 * is opened from.
 *
 * The allowlist is the point of this file. The assistant sees what the analyst
 * is looking at — route, company, period, filters — and nothing else: no
 * session token, no email, no raw query string, no arbitrary page scrape. A
 * field that is not declared here cannot reach the assistant service.
 */

/**
 * Analyst surfaces only. The platform shells have no assistant scope because
 * `analyst.run_ai_request` is not a platform-role action — mounting a launcher
 * there would offer an operator a control that can only ever deny.
 */
export const ASSISTANT_SCOPES = ["portfolio", "company", "comparison", "report"] as const;
export type AssistantScope = (typeof ASSISTANT_SCOPES)[number];

export interface AssistantContext {
  /** Which product surface the analyst is on. Selects the quick actions. */
  scope: AssistantScope;
  /** Current route path, without the query string. */
  route: string;
  /** Human title of the surface, shown in the assistant header. */
  surfaceLabel: string;
  /** Ticker in focus on a company surface, null elsewhere. */
  ticker: string | null;
  /** Tickers the analyst selected in a table, empty when none. */
  selectedTickers: readonly string[];
  /** Selected period label, e.g. "30 ngày". Null when the surface has no range. */
  periodLabel: string | null;
  /** Active filter labels, e.g. ["Nguy cơ cao"]. */
  filters: readonly string[];
  /** Data version and model version the visible numbers came from. */
  dataVersion: string;
  modelVersion: string | null;
}

/**
 * Every context shares one conversation thread per scope key: switching from
 * HPG to NVL opens NVL's own thread rather than continuing a conversation about
 * a different company, and coming back to HPG restores what was asked there.
 */
export function assistantThreadKey(context: AssistantContext): string {
  return context.ticker === null ? context.scope : `${context.scope}:${context.ticker}`;
}

export interface AssistantQuickAction {
  id: string;
  label: string;
  /** The question sent when the action is chosen. */
  prompt: string;
}

const PORTFOLIO_ACTIONS: readonly AssistantQuickAction[] = [
  {
    id: "summarise-portfolio",
    label: "Tóm tắt rủi ro danh mục",
    prompt: "Tóm tắt rủi ro của danh mục trong kỳ dữ liệu đang hiển thị.",
  },
  {
    id: "explain-highest",
    label: "Giải thích nhóm nguy cơ cao",
    prompt: "Vì sao các doanh nghiệp trong nhóm nguy cơ cao được xếp vào nhóm này?",
  },
  {
    id: "sector-signals",
    label: "Ngành nào đang xấu đi",
    prompt: "Ngành nào có mức rủi ro trung bình tăng nhanh nhất trong 7 ngày qua?",
  },
  {
    id: "explain-score",
    label: "Cách tính điểm rủi ro",
    prompt: "Điểm xác suất distress được tính từ những chỉ tiêu nào?",
  },
];

const COMPANY_ACTIONS: readonly AssistantQuickAction[] = [
  {
    id: "explain-company",
    label: "Giải thích điểm rủi ro",
    prompt: "Những yếu tố nào đẩy xác suất distress của doanh nghiệp này lên cao nhất?",
  },
  {
    id: "recent-change",
    label: "Thay đổi so với kỳ trước",
    prompt: "Điểm rủi ro đã thay đổi thế nào so với kỳ dữ liệu trước và vì sao?",
  },
  {
    id: "compare-peers",
    label: "So sánh với cùng ngành",
    prompt: "Doanh nghiệp này đứng ở đâu so với trung bình ngành?",
  },
  {
    id: "draft-report",
    label: "Soạn nội dung báo cáo",
    prompt: "Soạn phần nhận định rủi ro cho báo cáo về doanh nghiệp này.",
  },
];

const COMPARISON_ACTIONS: readonly AssistantQuickAction[] = [
  {
    id: "version-delta",
    label: "Khác biệt giữa hai phiên bản",
    prompt: "Hai phiên bản mô hình khác nhau ở những yếu tố nào?",
  },
  {
    id: "which-version",
    label: "Phiên bản nào đáng tin hơn",
    prompt: "Phiên bản nào có độ tin cậy cao hơn trên doanh nghiệp đang xem và vì sao?",
  },
];

const QUICK_ACTIONS: Record<AssistantScope, readonly AssistantQuickAction[]> = {
  portfolio: PORTFOLIO_ACTIONS,
  company: COMPANY_ACTIONS,
  comparison: COMPARISON_ACTIONS,
  report: COMPANY_ACTIONS,
};

/**
 * The assistant never opens on an empty chat box. It opens on the questions
 * this surface can actually answer, which is also what keeps the analyst from
 * having to guess what the assistant is for.
 */
export function quickActionsFor(context: AssistantContext): readonly AssistantQuickAction[] {
  return QUICK_ACTIONS[context.scope];
}
