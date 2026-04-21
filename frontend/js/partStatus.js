import { fetchJson } from "./api.js";
import { formatDday } from "./deadlineAdmin.js?v=20260421-p1b";

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function statusRows(counts) {
  return Object.entries(counts || {}).map(([status, count]) => `
    <div class="metric"><span>${escapeHtml(status)}</span><strong>${count}</strong></div>
  `).join("");
}

export async function renderPartStatus(container) {
  const [currentUser, deadline, status, rejection] = await Promise.all([
    fetchJson("/api/auth/me"),
    fetchJson("/api/settings/deadline"),
    fetchJson("/api/tasks/status"),
    fetchJson("/api/tasks/rejection"),
  ]);
  const org = currentUser.organization || {};
  container.innerHTML = `
    <section class="workspace">
      <div class="section-header">
        <div>
          <h2>내 파트 현황</h2>
          <p>${escapeHtml([org.division_name, org.team_name, org.group_name, org.part_name].filter(Boolean).join(" > "))}</p>
        </div>
        <span class="badge ${deadline.is_closed ? "danger" : "status"}">${formatDday(deadline)}</span>
      </div>
      ${deadline.description ? `<div class="alert-banner"><strong>마감 안내</strong><span>${escapeHtml(deadline.description)}</span></div>` : ""}
      ${rejection.has_rejection ? `<div class="alert-banner danger"><strong>반려 사유</strong><span>${escapeHtml(rejection.reject_reason)}</span></div>` : ""}
      <div class="metric-grid status-metric-grid">
        <div class="metric"><span>전체</span><strong>${status.total_tasks}</strong></div>
        ${statusRows(status.status_counts)}
      </div>
    </section>
  `;
}
