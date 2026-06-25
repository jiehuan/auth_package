import { useState } from "react";

const epics = [
  {
    id: "E1", label: "Epic 1", title: "Setup & infrastructure", pts: 14,
    color: { badge: "#E6F1FB", badgeText: "#0C447C" },
    tickets: [
      { id: "BFF-001", title: "FastAPI project scaffold", desc: "项目初始化，目录结构，uvicorn，.env 配置，health check endpoint", pts: 2, tag: "setup", endpoints: [{ m: "GET", p: "/health" }] },
      { id: "BFF-002", title: "Azure SQL connection & session", desc: "pyodbc / SQLAlchemy 连接池，Azure AD Service Principal 认证，connection retry logic", pts: 4, tag: "setup", endpoints: [] },
      { id: "BFF-003", title: "Auth middleware (Azure AD)", desc: "JWT token 验证，从 token 提取 user_id / email，注入 request context，401 处理", pts: 4, tag: "auth", endpoints: [] },
      { id: "BFF-004", title: "Global error handling & response schema", desc: "统一 response envelope {data, error, meta}，exception handler，logging 配置", pts: 2, tag: "setup", endpoints: [] },
      { id: "BFF-005", title: "CORS & OpenShift deployment config", desc: "CORS origins 白名单，Dockerfile，OpenShift deployment yaml，Harness pipeline 接入", pts: 2, tag: "setup", endpoints: [] },
    ]
  },
  {
    id: "E2", label: "Epic 2", title: "Landing page APIs", pts: 16,
    color: { badge: "#EAF3DE", badgeText: "#27500A" },
    tickets: [
      { id: "BFF-006", title: "Company search endpoint", desc: "全文搜索 company name，支持 limit / offset，返回 id / name / industry / location", pts: 3, tag: "read", fe: "FE-007", endpoints: [{ m: "GET", p: "/api/companies/search?q=&limit=&offset=" }] },
      { id: "BFF-007", title: "Favorites CRUD", desc: "获取当前用户收藏列表（含卡片所需字段），添加/删除收藏，pin 状态更新", pts: 4, tag: "write", fe: "FE-009, FE-011", endpoints: [{ m: "GET", p: "/api/companies/favorites" }, { m: "POST", p: "/api/favorites/{company_id}" }, { m: "DEL", p: "/api/favorites/{company_id}" }] },
      { id: "BFF-008", title: "Recently Viewed endpoints", desc: "获取最近30天浏览记录（表格字段），记录浏览事件（同时写 user_activity）", pts: 3, tag: "write", fe: "FE-010", endpoints: [{ m: "GET", p: "/api/companies/recent" }, { m: "POST", p: "/api/companies/recent/{company_id}" }] },
      { id: "BFF-009", title: "User activity tracking endpoint", desc: "接收前端 activity 事件写入 user_activity 表，fire-and-forget，异步写入不阻塞响应", pts: 3, tag: "write", fe: "FE-027", endpoints: [{ m: "POST", p: "/api/activity" }] },
      { id: "BFF-010", title: "User metric preferences", desc: "获取 / 保存用户对某公司的 SELECT METRICS 偏好，JSON 存储", pts: 3, tag: "write", fe: "FE-023, FE-019", endpoints: [{ m: "GET", p: "/api/users/preferences/{company_id}" }, { m: "PUT", p: "/api/users/preferences/{company_id}" }] },
    ]
  },
  {
    id: "E3", label: "Epic 3", title: "Company detail page APIs", pts: 24,
    color: { badge: "#EEEDFE", badgeText: "#3C3489" },
    tickets: [
      { id: "BFF-011", title: "Company profile endpoint", desc: "公司基础信息，header 所需字段，batch_date，favorite 状态（per user）", pts: 2, tag: "read", fe: "FE-012", endpoints: [{ m: "GET", p: "/api/companies/{id}" }] },
      { id: "BFF-012", title: "Key Insights endpoint", desc: "返回6个 insight 卡片，severity + title + summary，按最新 batch_date", pts: 2, tag: "read", fe: "FE-013", endpoints: [{ m: "GET", p: "/api/companies/{id}/insights" }] },
      { id: "BFF-013", title: "Metrics endpoints", desc: "4类指标（capital / profitability / credit_risk / exposure），支持 category filter，返回 metric_name / value / unit", pts: 4, tag: "read", fe: "FE-014, FE-021", endpoints: [{ m: "GET", p: "/api/companies/{id}/metrics?category=" }] },
      { id: "BFF-014", title: "Performance Trends endpoint", desc: "时序数据，返回 [[date, value], ...] 格式供 ECharts 直接消费，支持 trend_name filter", pts: 3, tag: "read", fe: "FE-020", endpoints: [{ m: "GET", p: "/api/companies/{id}/trends?name=" }] },
      { id: "BFF-015", title: "Loan Portfolio endpoint", desc: "按最新 period_date 返回 loan type 明细，含 balance / pct / yoy_growth / npl_ratio", pts: 2, tag: "read", fe: "FE-015", endpoints: [{ m: "GET", p: "/api/companies/{id}/loan-portfolio" }] },
      { id: "BFF-016", title: "Strategic & Risk Insights endpoint", desc: "4个分类，severity + title + body，支持 category filter", pts: 3, tag: "read", fe: "FE-016", endpoints: [{ m: "GET", p: "/api/companies/{id}/risk-insights?category=" }] },
      { id: "BFF-017", title: "Recent Activity & Follow-Up Questions", desc: "Activity 时间线事件列表；AI 生成的 broker 问题列表，支持 category filter", pts: 3, tag: "read", fe: "FE-017, FE-018", endpoints: [{ m: "GET", p: "/api/companies/{id}/activity" }, { m: "GET", p: "/api/companies/{id}/follow-up-questions?category=" }] },
      { id: "BFF-018", title: "Export to Email endpoint", desc: "聚合公司所有数据，生成 HTML 邮件内容，调 Azure Communication Services 或 SMTP 发送", pts: 5, tag: "write", fe: "FE-019", endpoints: [{ m: "POST", p: "/api/companies/{id}/export-email" }] },
    ]
  },
  {
    id: "E4", label: "Epic 4", title: "API contract & type alignment", pts: 8,
    color: { badge: "#FAEEDA", badgeText: "#633806" },
    tickets: [
      { id: "BFF-019", title: "Shared TypeScript interfaces", desc: "输出所有 endpoint 的 request / response TS interface，放 src/types/api.ts，前后端共用，BFF 改接口必须先改这里", pts: 3, tag: "setup", endpoints: [] },
      { id: "BFF-020", title: "Mock data alignment with API contract", desc: "前端 mock data 按 BFF-019 定义的 interface 更新，确保换真实 API 时零改动", pts: 2, tag: "setup", endpoints: [] },
      { id: "BFF-021", title: "Pydantic response models", desc: "所有 endpoint 的 FastAPI Pydantic model，与 BFF-019 TS interface 一一对应，自动生成 OpenAPI docs", pts: 3, tag: "setup", endpoints: [] },
    ]
  },
];

const tagStyle = {
  setup:  { background: "#E6F1FB", color: "#0C447C" },
  read:   { background: "#EAF3DE", color: "#27500A" },
  write:  { background: "#FAEEDA", color: "#633806" },
  auth:   { background: "#EEEDFE", color: "#3C3489" },
};

const methodStyle = {
  GET:  { background: "#EAF3DE", color: "#27500A" },
  POST: { background: "#FAEEDA", color: "#633806" },
  PUT:  { background: "#EEEDFE", color: "#3C3489" },
  DEL:  { background: "#FCEBEB", color: "#791F1F" },
};

export default function BffTickets() {
  const [expanded, setExpanded] = useState({});
  const toggle = (id) => setExpanded(e => ({ ...e, [id]: !e[id] }));

  const totalPts = epics.reduce((s, e) => s + e.pts, 0);
  const totalTickets = epics.reduce((s, e) => s + e.tickets.length, 0);

  return (
    <div style={{ fontFamily: "var(--font-sans)", padding: "1rem 0" }}>
      {/* Summary */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10, marginBottom: "2rem" }}>
        {[
          { label: "Total tickets", val: totalTickets },
          { label: "Story points", val: totalPts },
          { label: "Epics", val: epics.length },
          { label: "Sprints est.", val: "3–4" },
        ].map(s => (
          <div key={s.label} style={{ background: "var(--color-background-secondary)", borderRadius: "var(--border-radius-md)", padding: "0.75rem 1rem" }}>
            <div style={{ fontSize: 12, color: "var(--color-text-secondary)", marginBottom: 4 }}>{s.label}</div>
            <div style={{ fontSize: 22, fontWeight: 500, color: "var(--color-text-primary)" }}>{s.val}</div>
          </div>
        ))}
      </div>

      {epics.map(epic => (
        <div key={epic.id} style={{ marginBottom: "2rem" }}>
          {/* Epic header */}
          <div style={{ display: "flex", alignItems: "center", gap: 10, paddingBottom: "0.5rem", marginBottom: "0.75rem", borderBottom: "0.5px solid var(--color-border-tertiary)" }}>
            <span style={{ fontSize: 11, fontWeight: 500, padding: "3px 10px", borderRadius: "var(--border-radius-md)", background: epic.color.badge, color: epic.color.badgeText }}>{epic.label}</span>
            <span style={{ fontSize: 15, fontWeight: 500, color: "var(--color-text-primary)" }}>{epic.title}</span>
            <span style={{ fontSize: 12, color: "var(--color-text-secondary)", marginLeft: "auto" }}>{epic.pts} pts</span>
          </div>

          {/* Tickets */}
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {epic.tickets.map(t => (
              <div key={t.id}
                onClick={() => toggle(t.id)}
                style={{ background: "var(--color-background-primary)", border: "0.5px solid var(--color-border-tertiary)", borderRadius: "var(--border-radius-md)", padding: "10px 14px", cursor: "pointer" }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12 }}>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 10, color: "var(--color-text-tertiary)", fontFamily: "var(--font-mono)", marginBottom: 3 }}>{t.id}</div>
                    <div style={{ fontSize: 13, fontWeight: 500, color: "var(--color-text-primary)", marginBottom: 3 }}>{t.title}</div>
                    <div style={{ fontSize: 12, color: "var(--color-text-secondary)", lineHeight: 1.5 }}>{t.desc}</div>

                    {expanded[t.id] && t.endpoints.length > 0 && (
                      <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, background: "var(--color-background-secondary)", borderRadius: "var(--border-radius-md)", padding: "6px 10px", marginTop: 8, lineHeight: 1.8 }}>
                        {t.endpoints.map((ep, i) => (
                          <div key={i}>
                            <span style={{ fontSize: 10, fontWeight: 500, padding: "1px 5px", borderRadius: 3, marginRight: 6, ...methodStyle[ep.m] }}>{ep.m}</span>
                            {ep.p}
                          </div>
                        ))}
                      </div>
                    )}

                    {t.fe && (
                      <span style={{ fontSize: 10, background: "#E6F1FB", color: "#0C447C", padding: "1px 6px", borderRadius: "var(--border-radius-md)", display: "inline-block", marginTop: 6 }}>
                        unblocks {t.fe}
                      </span>
                    )}
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 6, flexShrink: 0 }}>
                    <span style={{ fontSize: 11, fontWeight: 500, padding: "2px 8px", borderRadius: "var(--border-radius-md)", background: "var(--color-background-secondary)", color: "var(--color-text-secondary)" }}>{t.pts} pts</span>
                    <span style={{ fontSize: 10, padding: "2px 7px", borderRadius: "var(--border-radius-md)", ...tagStyle[t.tag] }}>{t.tag}</span>
                    {t.endpoints.length > 0 && (
                      <span style={{ fontSize: 10, color: "var(--color-text-tertiary)" }}>{expanded[t.id] ? "▲ hide" : "▼ endpoints"}</span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
