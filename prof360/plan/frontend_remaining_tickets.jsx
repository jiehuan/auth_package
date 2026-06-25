import { useState } from "react";

const engineers = [
  { id: "A", color: { bg: "#E6F1FB", text: "#0C447C" } },
  { id: "B", color: { bg: "#E1F5EE", text: "#085041" } },
  { id: "C", color: { bg: "#EEEDFE", text: "#3C3489" } },
];

const tagStyle = {
  setup:  { background: "#E6F1FB", color: "#0C447C" },
  feat:   { background: "#EAF3DE", color: "#27500A" },
  chart:  { background: "#EEEDFE", color: "#3C3489" },
  api:    { background: "#FAEEDA", color: "#633806" },
  ux:     { background: "#FBEAF0", color: "#72243E" },
};

const sprints = [
  {
    id: "S2", label: "Sprint 2 残留", note: "先做 FE-003，FE-007 和 FE-026 依赖它", pts: 14,
    columns: [
      {
        eng: "A", tickets: []
      },
      {
        eng: "B", tickets: [
          { id: "FE-003", title: "API client & BFF layer", desc: "axios 封装，error handling，interceptor，base URL 配置，先接 mock", pts: 3, tag: "api" },
          { id: "FE-026", title: "React Query setup & caching", desc: "TanStack Query，staleTime，refetch 策略，prefetch on hover", pts: 4, tag: "setup" },
        ]
      },
      {
        eng: "C", tickets: [
          { id: "FE-007", title: "Global search typeahead", desc: "防抖，接 mock /companies/search，下拉结果，键盘导航，跳转 detail", pts: 5, tag: "feat", dep: "dep: FE-003" },
          { id: "FE-025", title: "Responsive layout", desc: "Landing 卡片网格，Detail 双栏，响应式断点适配", pts: 3, tag: "ux" },
        ]
      },
    ]
  },
  {
    id: "S3", label: "Sprint 3 — Detail page", note: "依赖 FE-003 API client 完成", pts: 27,
    columns: [
      {
        eng: "A", tickets: [
          { id: "FE-012", title: "Detail page layout & header", desc: "Back 按钮，公司 header，SAVE PREFERENCES，EXPORT TO EMAIL，浮动 favorite 按钮", pts: 3, tag: "feat" },
          { id: "FE-013", title: "Key Insights Summary", desc: "6张 insight 卡片，red/yellow/green severity，GET /insights", pts: 4, tag: "feat" },
          { id: "FE-017", title: "Recent Activity timeline", desc: "右侧时间线，事件 icon + 颜色，日期排序，GET /activity", pts: 3, tag: "feat" },
          { id: "FE-027", title: "User Activity Tracking", desc: "useActivityTracker hook，fire-and-forget POST /activity，触发：view_company / click_risk_flags / click_followup / update_metrics", pts: 3, tag: "api" },
        ]
      },
      {
        eng: "B", tickets: [
          { id: "FE-014", title: "Collapsible metrics sections", desc: "4个折叠区块（Capital / Profitability / Credit Risk / Exposure），SELECT METRICS 按钮，展开动画", pts: 4, tag: "ux" },
          { id: "FE-015", title: "Loan Portfolio table", desc: "5列表格，YoY 正负颜色区分，GET /loan-portfolio", pts: 3, tag: "feat" },
          { id: "FE-018", title: "Follow-Up Questions", desc: "问题列表，category filter，ENTER QUESTIONS 交互，GET /follow-up-questions", pts: 3, tag: "feat" },
        ]
      },
      {
        eng: "C", tickets: [
          { id: "FE-016", title: "Strategic & Risk Insights", desc: "4个分类（Risk & Legal / Event Signals / Qualitative / Governance），severity badge，展开全文，GET /risk-insights", pts: 5, tag: "feat" },
          { id: "FE-019", title: "Save Preferences & Export to Email", desc: "PUT /preferences，POST /export-email，loading / success toast", pts: 3, tag: "ux" },
          { id: "FE-024", title: "Global loading & error states", desc: "统一 loading spinner，skeleton cards，error boundary，API 失败 toast", pts: 3, tag: "ux" },
        ]
      },
    ]
  },
  {
    id: "S4", label: "Sprint 4 — ECharts", note: "依赖 FE-005 ECharts wrapper（已完成）+ FE-014 collapsible sections", pts: 17,
    columns: [
      {
        eng: "A", tickets: [
          { id: "FE-022", title: "Chart skeleton & empty states", desc: "所有图表统一 loading skeleton，无数据 empty state，ECharts error boundary", pts: 2, tag: "ux" },
          { id: "FE-023", title: "SELECT METRICS modal", desc: "勾选想显示的 metrics，PUT /preferences 保存，下次进入页面自动还原，同时触发 activity tracking", pts: 3, tag: "ux" },
        ]
      },
      {
        eng: "B", tickets: [
          { id: "FE-021", title: "Metrics section charts", desc: "SELECT METRICS 展开后 ECharts bar/line，图表类型由 metric 配置决定，复用 EChartsWrapper", pts: 8, tag: "chart", dep: "dep: FE-014" },
        ]
      },
      {
        eng: "C", tickets: [
          { id: "FE-020", title: "Performance Trends (3x line charts)", desc: "Net Interest Margin / Non-Performing Loans / 第三指标，ECharts line，GET /trends，tooltip + zoom", pts: 5, tag: "chart" },
        ]
      },
    ]
  },
];

export default function RemainingTickets() {
  const [expanded, setExpanded] = useState({});
  const toggle = (id) => setExpanded(e => ({ ...e, [id]: !e[id] }));

  const engPts = { A: 0, B: 0, C: 0 };
  const engCount = { A: 0, B: 0, C: 0 };
  sprints.forEach(s => s.columns.forEach(col => {
    col.tickets.forEach(t => {
      engPts[col.eng] += t.pts;
      engCount[col.eng]++;
    });
  }));

  const totalPts = Object.values(engPts).reduce((a, b) => a + b, 0);

  return (
    <div style={{ fontFamily: "var(--font-sans)", padding: "1rem 0" }}>

      {/* Summary */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10, marginBottom: "2rem" }}>
        {[
          { label: "Remaining tickets", val: 18 },
          { label: "Story points", val: totalPts },
          { label: "Sprints", val: 3 },
          { label: "Engineers", val: 3 },
        ].map(s => (
          <div key={s.label} style={{ background: "var(--color-background-secondary)", borderRadius: "var(--border-radius-md)", padding: "0.75rem 1rem" }}>
            <div style={{ fontSize: 12, color: "var(--color-text-secondary)", marginBottom: 4 }}>{s.label}</div>
            <div style={{ fontSize: 22, fontWeight: 500, color: "var(--color-text-primary)" }}>{s.val}</div>
          </div>
        ))}
      </div>

      {/* Engineer load */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 10, marginBottom: "2rem" }}>
        {engineers.map(eng => (
          <div key={eng.id} style={{ background: "var(--color-background-primary)", border: "0.5px solid var(--color-border-tertiary)", borderRadius: "var(--border-radius-lg)", padding: "1rem" }}>
            <div style={{ fontSize: 14, fontWeight: 500, color: "var(--color-text-primary)", marginBottom: 6 }}>Engineer {eng.id}</div>
            <div style={{ display: "flex", gap: 16 }}>
              <div>
                <div style={{ fontSize: 20, fontWeight: 500, color: eng.color.text }}>{engCount[eng.id]}</div>
                <div style={{ fontSize: 10, color: "var(--color-text-secondary)" }}>tickets</div>
              </div>
              <div>
                <div style={{ fontSize: 20, fontWeight: 500, color: eng.color.text }}>{engPts[eng.id]}</div>
                <div style={{ fontSize: 10, color: "var(--color-text-secondary)" }}>pts</div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Sprints */}
      {sprints.map(sprint => (
        <div key={sprint.id} style={{ marginBottom: "2.5rem" }}>
          {/* Sprint header */}
          <div style={{ display: "flex", alignItems: "center", gap: 10, paddingBottom: "0.5rem", marginBottom: "0.75rem", borderBottom: "0.5px solid var(--color-border-tertiary)" }}>
            <span style={{ fontSize: 15, fontWeight: 500, color: "var(--color-text-primary)" }}>{sprint.label}</span>
            <span style={{ fontSize: 11, color: "var(--color-text-secondary)", fontStyle: "italic" }}>{sprint.note}</span>
            <span style={{ fontSize: 12, color: "var(--color-text-secondary)", marginLeft: "auto" }}>{sprint.pts} pts</span>
          </div>

          {/* 3 columns */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 10 }}>
            {sprint.columns.map(col => {
              const eng = engineers.find(e => e.id === col.eng);
              return (
                <div key={col.eng}>
                  <div style={{ fontSize: 11, fontWeight: 500, padding: "3px 10px", borderRadius: "var(--border-radius-md)", marginBottom: 8, textAlign: "center", background: eng.color.bg, color: eng.color.text }}>
                    Engineer {col.eng}
                  </div>
                  {col.tickets.length === 0 && (
                    <div style={{ fontSize: 12, color: "var(--color-text-tertiary)", padding: "8px 10px", textAlign: "center" }}>—</div>
                  )}
                  {col.tickets.map(t => (
                    <div key={t.id}
                      onClick={() => toggle(t.id)}
                      style={{ background: "var(--color-background-primary)", border: "0.5px solid var(--color-border-tertiary)", borderRadius: "var(--border-radius-md)", padding: "8px 10px", marginBottom: 6, cursor: "pointer" }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 6 }}>
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ fontSize: 10, color: "var(--color-text-tertiary)", fontFamily: "var(--font-mono)", marginBottom: 2 }}>{t.id}</div>
                          <div style={{ fontSize: 12, fontWeight: 500, color: "var(--color-text-primary)", lineHeight: 1.4, marginBottom: expanded[t.id] ? 4 : 0 }}>{t.title}</div>
                          {expanded[t.id] && (
                            <div style={{ fontSize: 11, color: "var(--color-text-secondary)", lineHeight: 1.5, marginBottom: 4 }}>{t.desc}</div>
                          )}
                          {t.dep && (
                            <span style={{ fontSize: 10, background: "#FAEEDA", color: "#633806", padding: "1px 6px", borderRadius: "var(--border-radius-md)", display: "inline-block", marginTop: 3 }}>{t.dep}</span>
                          )}
                        </div>
                        <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 4, flexShrink: 0 }}>
                          <span style={{ fontSize: 10, fontWeight: 500, padding: "1px 6px", borderRadius: "var(--border-radius-md)", background: "var(--color-background-secondary)", color: "var(--color-text-secondary)" }}>{t.pts} pts</span>
                          <span style={{ fontSize: 10, padding: "1px 6px", borderRadius: "var(--border-radius-md)", ...tagStyle[t.tag] }}>{t.tag}</span>
                          <span style={{ fontSize: 10, color: "var(--color-text-tertiary)" }}>{expanded[t.id] ? "▲" : "▼"}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
