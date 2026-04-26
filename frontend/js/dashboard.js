import { fetchJson } from "./api.js?v=20260426-mock-session";
import { renderAdminTaskQuery } from "./adminTaskQuery.js?v=20260421-review2";
import { renderCollectionOpsManager } from "./collectionOps.js?v=20260425-one-time-ops";
import { formatDday, renderDeadlineManager } from "./deadlineAdmin.js?v=20260421-p1b";
import { renderOrganizationManager } from "./organizationAdmin.js?v=20260425-optional-division-head";
import { renderPartMemberManager } from "./partMemberAdmin.js?v=20260425-part-member-admin";
import { paginateItems, renderPaginationControls } from "./pagination.js?v=20260425-admin-scroll";
import { renderQuestionManager } from "./questionAdmin.js?v=20260421-p1b";
import { renderTooltipManager } from "./tooltipAdmin.js?v=20260421-p1b";
import { renderUserManager } from "./userAdmin.js?v=20260422-user-permissions-a11y";

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function statusMetricRows(statusCounts) {
  return Object.entries(statusCounts).map(([status, count]) => `
    <div class="metric"><span>${escapeHtml(status)}</span><strong>${count}</strong></div>
  `).join("");
}

export function filterDepartmentItems(items, keyword) {
  const query = String(keyword || "").trim().toLowerCase();
  if (!query) {
    return [...items];
  }
  return items.filter((item) => [
    item.division_name,
    item.team_name,
    item.group_name,
    item.part_name,
  ].some((value) => String(value || "").toLowerCase().includes(query)));
}

export function sortDepartmentItems(items, sortKey) {
  const next = [...items];
  if (sortKey === "completion_desc") {
    return next.sort((a, b) => Number(b.completion_rate) - Number(a.completion_rate));
  }
  if (sortKey === "completion_asc") {
    return next.sort((a, b) => Number(a.completion_rate) - Number(b.completion_rate));
  }
  return next.sort((a, b) => String(a.part_name || "").localeCompare(String(b.part_name || ""), "ko"));
}

export function approvalDonutStyle(statusCounts) {
  const values = [
    ["PENDING", "#8f6be8"],
    ["IN_PROGRESS", "#5d3bb6"],
    ["APPROVED", "#1b7f4c"],
    ["REJECTED", "#c62828"],
  ];
  const total = values.reduce((sum, [key]) => sum + Number(statusCounts[key] || 0), 0);
  if (!total) {
    return "background: #eee8f8";
  }
  let cursor = 0;
  const stops = values.map(([key, color]) => {
    const start = cursor;
    cursor += (Number(statusCounts[key] || 0) / total) * 360;
    return `${color} ${start}deg ${cursor}deg`;
  });
  return `background: conic-gradient(${stops.join(", ")})`;
}

function departmentRows(items) {
  if (!items.length) {
    return `<tr><td colspan="7">부서별 요약 데이터가 없습니다.</td></tr>`;
  }
  return items.map((item) => `
    <tr>
      <td>${escapeHtml(item.division_name || "-")}</td>
      <td>${escapeHtml(item.team_name || "-")}</td>
      <td>${escapeHtml(item.group_name || "-")}</td>
      <td>${escapeHtml(item.part_name || "-")}</td>
      <td>${item.total_tasks}</td>
      <td>${item.approved_tasks}</td>
      <td>${item.completion_rate}%</td>
    </tr>
  `).join("");
}

function renderApprovalDonut(statusCounts) {
  return `
    <section class="dashboard-chart-section">
      <div class="approval-donut" style="${approvalDonutStyle(statusCounts)}" aria-label="승인 진행 현황"></div>
      <div class="donut-legend">
        ${Object.entries(statusCounts).map(([status, count]) => `
          <span><i class="legend-dot status-${status.toLowerCase()}"></i>${escapeHtml(status)} ${count}</span>
        `).join("")}
      </div>
    </section>
  `;
}

function renderAdminPanel({ id, title, description = "", open = false, bodyId }) {
  return `
    <section class="admin-panel" data-admin-panel="${id}">
      <div class="admin-panel-header">
        <div>
          <h2>${escapeHtml(title)}</h2>
          ${description ? `<p>${escapeHtml(description)}</p>` : ""}
        </div>
        <button
          type="button"
          class="secondary-button compact-filter-button"
          aria-expanded="${open}"
          aria-controls="${bodyId}"
          data-admin-toggle="${id}"
        >${open ? "접기" : "펴기"}</button>
      </div>
      <div id="${bodyId}" class="admin-panel-body" ${open ? "" : "hidden"}></div>
    </section>
  `;
}

function bindAdminPanels(container) {
  container.querySelectorAll("[data-admin-toggle]").forEach((button) => {
    button.addEventListener("click", () => {
      const body = container.querySelector(`#${button.getAttribute("aria-controls")}`);
      const nextOpen = button.getAttribute("aria-expanded") !== "true";
      button.setAttribute("aria-expanded", String(nextOpen));
      button.textContent = nextOpen ? "접기" : "펴기";
      body.hidden = !nextOpen;
    });
  });
}

export async function renderDashboard(container) {
  const [summary, deadline, approvalStatus, completion, classification] = await Promise.all([
    fetchJson("/api/dashboard/summary"),
    fetchJson("/api/settings/deadline"),
    fetchJson("/api/dashboard/approval-status"),
    fetchJson("/api/dashboard/completion-rate"),
    fetchJson("/api/dashboard/classification-ratio"),
  ]);
  let visibleCompletion = sortDepartmentItems(completion.items, "part_asc");
  let departmentPage = 1;

  function updateDepartmentRows() {
    const keyword = container.querySelector("[data-summary-filter]")?.value || "";
    const sortKey = container.querySelector("[data-summary-sort]")?.value || "part_asc";
    visibleCompletion = sortDepartmentItems(filterDepartmentItems(completion.items, keyword), sortKey);
    const page = paginateItems(visibleCompletion, departmentPage);
    departmentPage = page.page;
    container.querySelector("[data-department-summary-body]").innerHTML = departmentRows(page.items);
    container.querySelector("[data-department-pagination]").innerHTML = renderPaginationControls(page, "department-summary");
  }

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
        <div class="metric"><span>통합 비율</span><strong>${summary.integrated_classification_ratio}%</strong></div>
        <div class="metric"><span>국가핵심기술</span><strong>${summary.national_tech_count}</strong></div>
        <div class="metric"><span>Compliance</span><strong>${summary.compliance_count}</strong></div>
      </div>
      <div class="metric-grid status-metric-grid">
        ${statusMetricRows(approvalStatus)}
        <div class="metric"><span>기밀</span><strong>${classification.confidential}</strong></div>
        <div class="metric"><span>국가핵심</span><strong>${classification.national_tech}</strong></div>
        <div class="metric"><span>Compliance</span><strong>${classification.compliance}</strong></div>
        <div class="metric"><span>통합</span><strong>${classification.integrated}</strong></div>
      </div>
      ${renderApprovalDonut(approvalStatus)}
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
          <div class="toolbar">
            <input id="department-summary-filter" name="department_summary_filter" class="toolbar-input" data-summary-filter placeholder="조직 검색" autocomplete="off">
            <select id="department-summary-sort" name="department_summary_sort" class="toolbar-input" data-summary-sort autocomplete="off">
              <option value="part_asc">파트명</option>
              <option value="completion_desc">완료율 높은순</option>
              <option value="completion_asc">완료율 낮은순</option>
            </select>
          </div>
        </div>
        <div class="table-wrap compact-table-wrap">
          <table class="compact-table">
            <thead>
              <tr><th>실</th><th>팀</th><th>그룹</th><th>파트</th><th>전체</th><th>승인</th><th>완료율</th></tr>
            </thead>
            <tbody data-department-summary-body>${departmentRows(visibleCompletion)}</tbody>
          </table>
        </div>
        <div data-department-pagination></div>
      </section>
      ${renderAdminPanel({
        id: "deadline",
        title: "마감 관리",
        description: "입력 마감일과 안내 문구를 관리합니다.",
        open: true,
        bodyId: "deadline-manager-root",
      })}
      ${renderAdminPanel({
        id: "collection-ops",
        title: "일회성 운영",
        description: "취합 종료, 최종 Export, 메일 실패, 감사 로그를 확인합니다.",
        open: true,
        bodyId: "collection-ops-root",
      })}
      ${renderAdminPanel({
        id: "task-query",
        title: "전체 데이터 조회",
        description: "조직, 승인 상태, 판정 결과 기준으로 업무를 조회합니다.",
        bodyId: "admin-task-query-root",
      })}
      ${renderAdminPanel({
        id: "users",
        title: "사용자 권한 관리",
        description: "사용자 권한과 담당 조직을 관리합니다.",
        bodyId: "user-manager-root",
      })}
      ${renderAdminPanel({
        id: "part-members",
        title: "파트원 명단 관리",
        description: "파트원 명단 CSV를 업로드하고 확인합니다.",
        bodyId: "part-member-manager-root",
      })}
      ${renderAdminPanel({
        id: "organizations",
        title: "조직 관리",
        description: "조직 정보를 CSV 또는 수동 입력으로 관리합니다.",
        bodyId: "organization-manager-root",
      })}
      ${renderAdminPanel({
        id: "questions",
        title: "판정 문항 관리",
        description: "기밀 및 국가핵심기술 판단 문항을 관리합니다.",
        bodyId: "question-manager-root",
      })}
      ${renderAdminPanel({
        id: "tooltips",
        title: "컬럼 예시 관리",
        description: "입력 화면 컬럼 도움말 문구를 관리합니다.",
        bodyId: "tooltip-manager-root",
      })}
    </section>
  `;
  container.querySelector("[data-action='dashboard-export']").addEventListener("click", () => {
    window.location.href = "/api/export/excel";
  });
  container.querySelector("[data-summary-filter]").addEventListener("input", () => {
    departmentPage = 1;
    updateDepartmentRows();
  });
  container.querySelector("[data-summary-sort]").addEventListener("change", () => {
    departmentPage = 1;
    updateDepartmentRows();
  });
  container.addEventListener("click", (event) => {
    const button = event.target.closest("[data-pagination-target='department-summary'] [data-page-action]");
    if (!button) {
      return;
    }
    departmentPage += button.dataset.pageAction === "next" ? 1 : -1;
    updateDepartmentRows();
  });
  bindAdminPanels(container);
  updateDepartmentRows();
  await renderDeadlineManager(container.querySelector("#deadline-manager-root"));
  await renderCollectionOpsManager(container.querySelector("#collection-ops-root"));
  await renderAdminTaskQuery(container.querySelector("#admin-task-query-root"));
  await renderUserManager(container.querySelector("#user-manager-root"));
  await renderPartMemberManager(container.querySelector("#part-member-manager-root"));
  await renderOrganizationManager(container.querySelector("#organization-manager-root"));
  await renderQuestionManager(container.querySelector("#question-manager-root"));
  await renderTooltipManager(container.querySelector("#tooltip-manager-root"));
}
