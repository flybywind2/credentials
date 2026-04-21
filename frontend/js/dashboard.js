import { fetchJson } from "./api.js";
import { renderAdminTaskQuery } from "./adminTaskQuery.js?v=20260421-review2";
import { formatDday, renderDeadlineManager } from "./deadlineAdmin.js?v=20260421-p1b";
import { renderOrganizationManager } from "./organizationAdmin.js?v=20260421-p1b";
import { renderQuestionManager } from "./questionAdmin.js?v=20260421-p1b";
import { renderTooltipManager } from "./tooltipAdmin.js?v=20260421-p1b";

function statusMetricRows(statusCounts) {
  return Object.entries(statusCounts).map(([status, count]) => `
    <div class="metric"><span>${status}</span><strong>${count}</strong></div>
  `).join("");
}

function departmentRows(items) {
  if (!items.length) {
    return `<tr><td colspan="7">부서별 요약 데이터가 없습니다.</td></tr>`;
  }
  return items.map((item) => `
    <tr>
      <td>${item.division_name || "-"}</td>
      <td>${item.team_name || "-"}</td>
      <td>${item.group_name || "-"}</td>
      <td>${item.part_name || "-"}</td>
      <td>${item.total_tasks}</td>
      <td>${item.approved_tasks}</td>
      <td>${item.completion_rate}%</td>
    </tr>
  `).join("");
}

export async function renderDashboard(container) {
  const [summary, deadline, approvalStatus, completion, classification] = await Promise.all([
    fetchJson("/api/dashboard/summary"),
    fetchJson("/api/settings/deadline"),
    fetchJson("/api/dashboard/approval-status"),
    fetchJson("/api/dashboard/completion-rate"),
    fetchJson("/api/dashboard/classification-ratio"),
  ]);
  container.innerHTML = `
    <section class="workspace">
      <div class="section-header">
        <div>
          <h2>관리자 대시보드</h2>
          <p>전체 파트 입력률과 승인 진행 상태를 확인합니다.</p>
        </div>
        <button type="button" class="primary-button" data-action="dashboard-export">Excel 다운로드</button>
      </div>
      <div class="metric-grid">
        <div class="metric"><span>입력 마감</span><strong>${formatDday(deadline)}</strong></div>
        <div class="metric"><span>전체 파트</span><strong>${summary.total_parts}</strong></div>
        <div class="metric"><span>완료 파트</span><strong>${summary.completed_parts}</strong></div>
        <div class="metric"><span>입력 완료율</span><strong>${summary.completion_rate}%</strong></div>
        <div class="metric"><span>기밀 업무 비율</span><strong>${summary.confidential_task_ratio}%</strong></div>
        <div class="metric"><span>국가핵심기술</span><strong>${summary.national_tech_count}</strong></div>
        <div class="metric"><span>Compliance</span><strong>${summary.compliance_count}</strong></div>
      </div>
      <div class="metric-grid status-metric-grid">
        ${statusMetricRows(approvalStatus)}
        <div class="metric"><span>기밀</span><strong>${classification.confidential}</strong></div>
        <div class="metric"><span>국가핵심</span><strong>${classification.national_tech}</strong></div>
        <div class="metric"><span>Compliance</span><strong>${classification.compliance}</strong></div>
      </div>
      <div class="progress-block">
        <div class="progress-label">
          <span>입력 완료율</span>
          <strong>${summary.completion_rate}%</strong>
        </div>
        <div class="progress-track">
          <div class="progress-fill" style="width: ${summary.completion_rate}%"></div>
        </div>
      </div>
      <section class="department-summary-section">
        <div class="section-header department-summary-header">
          <div>
            <h2>부서별 요약</h2>
            <p>파트별 업무 수와 승인 완료율입니다.</p>
          </div>
        </div>
        <div class="table-wrap compact-table-wrap">
          <table class="compact-table">
            <thead>
              <tr><th>실</th><th>팀</th><th>그룹</th><th>파트</th><th>전체</th><th>승인</th><th>완료율</th></tr>
            </thead>
            <tbody>${departmentRows(completion.items)}</tbody>
          </table>
        </div>
      </section>
      <div id="deadline-manager-root"></div>
      <div id="admin-task-query-root"></div>
      <div id="organization-manager-root"></div>
      <div id="question-manager-root"></div>
      <div id="tooltip-manager-root"></div>
    </section>
  `;
  container.querySelector("[data-action='dashboard-export']").addEventListener("click", () => {
    window.location.href = "/api/export/excel";
  });
  await renderDeadlineManager(container.querySelector("#deadline-manager-root"));
  await renderAdminTaskQuery(container.querySelector("#admin-task-query-root"));
  await renderOrganizationManager(container.querySelector("#organization-manager-root"));
  await renderQuestionManager(container.querySelector("#question-manager-root"));
  await renderTooltipManager(container.querySelector("#tooltip-manager-root"));
}
