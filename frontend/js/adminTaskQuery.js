import { fetchJson } from "./api.js?v=20260426-mock-session";
import { paginateItems, renderPaginationControls } from "./pagination.js?v=20260425-admin-scroll";

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

export function buildTaskFilterQuery(filters) {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== "" && value !== null && value !== undefined) {
      params.set(key, value);
    }
  });
  return params.toString();
}

export function formatLatestReview(review) {
  if (!review) {
    return { decision: "-", comment: "-", reviewer: "-" };
  }
  return {
    decision: review.decision === "REJECTED" ? "반려" : "승인",
    comment: review.comment || "-",
    reviewer: review.reviewer_employee_id || "-",
  };
}

function uniqueSorted(values) {
  return [...new Set(values.filter(Boolean))].sort((a, b) => String(a).localeCompare(String(b), "ko"));
}

export function deriveHierarchyOptions(organizations, filters = {}) {
  const matches = (org, key, value) => !value || org[`${key}_name`] === value;
  const divisionFiltered = organizations.filter((org) => matches(org, "division", filters.division));
  const teamFiltered = divisionFiltered.filter((org) => matches(org, "team", filters.team));
  const groupFiltered = teamFiltered.filter((org) => matches(org, "group", filters.group));
  return {
    divisions: uniqueSorted(organizations.map((org) => org.division_name)),
    teams: uniqueSorted(divisionFiltered.map((org) => org.team_name)),
    groups: uniqueSorted(teamFiltered.map((org) => org.group_name)),
    parts: uniqueSorted(groupFiltered.map((org) => org.part_name)),
  };
}

function options(values, selectedValue, label) {
  return `<option value="">${label}</option>${values.map((value) => `
    <option value="${escapeHtml(value)}" ${value === selectedValue ? "selected" : ""}>${escapeHtml(value)}</option>
  `).join("")}`;
}

function renderRows(items) {
  if (!items.length) {
    return `<tr><td colspan="13">조회된 데이터가 없습니다.</td></tr>`;
  }
  return items.map((task) => `
    ${(() => {
      const review = formatLatestReview(task.latest_review);
      return `
    <tr>
      <td>${escapeHtml(task.division_name || "-")}</td>
      <td>${escapeHtml(task.team_name || "-")}</td>
      <td>${escapeHtml(task.group_name || "-")}</td>
      <td>${escapeHtml(task.part_name || "-")}</td>
      <td>${escapeHtml(task.major_task)}</td>
      <td>${escapeHtml(task.detail_task)}</td>
      <td>${task.is_confidential ? "기밀" : "비기밀"}</td>
      <td>${task.is_national_tech ? "해당" : "비해당"}</td>
      <td>${task.is_compliance ? "해당" : "비해당"}</td>
      <td><span class="badge status-${String(task.status).toLowerCase()}">${escapeHtml(task.status)}</span></td>
      <td>${escapeHtml(review.decision)}</td>
      <td>${escapeHtml(review.comment)}</td>
      <td>${escapeHtml(review.reviewer)}</td>
    </tr>
      `;
    })()}
  `).join("");
}

export async function renderAdminTaskQuery(container) {
  const organizations = await fetchJson("/api/organizations");
  let currentItems = [];
  let currentTotalCount = 0;
  let currentPage = 1;

  function updatePagedRows() {
    const page = paginateItems(currentItems, currentPage);
    currentPage = page.page;
    container.querySelector("[data-admin-task-results]").innerHTML = renderRows(page.items);
    container.querySelector("[data-admin-task-pagination]").innerHTML = renderPaginationControls(page, "admin-tasks");
    container.querySelector("[data-admin-task-count]").textContent = `${currentTotalCount}건`;
  }

  async function load(filters = {}) {
    const query = buildTaskFilterQuery(filters);
    const data = await fetchJson(`/api/admin/tasks${query ? `?${query}` : ""}`);
    currentItems = data.items;
    currentTotalCount = data.total_count;
    currentPage = 1;
    updatePagedRows();
  }

  container.innerHTML = `
    <section class="admin-query-section">
      <div class="section-header admin-query-header">
        <div>
          <h2>전체 데이터 조회</h2>
          <p>조직, 승인 상태, 판정 결과 기준으로 전체 업무를 조회합니다.</p>
        </div>
        <div class="toolbar">
          <span class="badge neutral" data-admin-task-count>0건</span>
          <button type="button" class="secondary-button" data-action="admin-export">Excel</button>
        </div>
      </div>
      <form class="admin-query-form">
        <select class="toolbar-input" name="division" data-hierarchy-select="division"></select>
        <select class="toolbar-input" name="team" data-hierarchy-select="team"></select>
        <select class="toolbar-input" name="group" data-hierarchy-select="group"></select>
        <select class="toolbar-input" name="part" data-hierarchy-select="part"></select>
        <select class="toolbar-input" name="status">
          <option value="">전체 상태</option>
          <option value="UPLOADED">UPLOADED</option>
          <option value="DRAFT">DRAFT</option>
          <option value="SUBMITTED">SUBMITTED</option>
          <option value="APPROVED">APPROVED</option>
          <option value="REJECTED">REJECTED</option>
        </select>
        <select class="toolbar-input" name="is_confidential">
          <option value="">기밀 전체</option>
          <option value="true">기밀</option>
          <option value="false">비기밀</option>
        </select>
        <select class="toolbar-input" name="is_national_tech">
          <option value="">국가핵심 전체</option>
          <option value="true">해당</option>
          <option value="false">비해당</option>
        </select>
        <select class="toolbar-input" name="is_compliance">
          <option value="">Compliance 전체</option>
          <option value="true">해당</option>
          <option value="false">비해당</option>
        </select>
        <button type="submit" class="primary-button">조회</button>
      </form>
      <div class="table-wrap compact-table-wrap">
        <table class="compact-table admin-query-table">
          <thead>
            <tr>
              <th>실</th><th>팀</th><th>그룹</th><th>파트</th>
              <th>대업무</th><th>세부업무</th><th>기밀</th><th>국가핵심</th><th>Compliance</th><th>상태</th>
              <th>검토결과</th><th>검토의견</th><th>검토자</th>
            </tr>
          </thead>
          <tbody data-admin-task-results></tbody>
        </table>
      </div>
      <div data-admin-task-pagination></div>
    </section>
  `;

  const form = container.querySelector(".admin-query-form");
  function currentFilters() {
    return Object.fromEntries(new FormData(form).entries());
  }

  function renderHierarchySelects() {
    const filters = currentFilters();
    const hierarchy = deriveHierarchyOptions(organizations, filters);
    form.elements.division.innerHTML = options(hierarchy.divisions, filters.division, "전체 실");
    form.elements.team.innerHTML = options(hierarchy.teams, filters.team, "전체 팀");
    form.elements.group.innerHTML = options(hierarchy.groups, filters.group, "전체 그룹");
    form.elements.part.innerHTML = options(hierarchy.parts, filters.part, "전체 파트");
  }

  renderHierarchySelects();
  form.querySelectorAll("[data-hierarchy-select]").forEach((select) => {
    select.addEventListener("change", () => {
      const level = select.dataset.hierarchySelect;
      if (level === "division") {
        form.elements.team.value = "";
        form.elements.group.value = "";
        form.elements.part.value = "";
      }
      if (level === "team") {
        form.elements.group.value = "";
        form.elements.part.value = "";
      }
      if (level === "group") {
        form.elements.part.value = "";
      }
      renderHierarchySelects();
    });
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    await load(currentFilters());
  });
  container.addEventListener("click", (event) => {
    const button = event.target.closest("[data-page-action]");
    if (!button || !button.closest("[data-pagination-target='admin-tasks']")) {
      return;
    }
    currentPage += button.dataset.pageAction === "next" ? 1 : -1;
    updatePagedRows();
  });
  container.querySelector("[data-action='admin-export']").addEventListener("click", () => {
    const query = buildTaskFilterQuery(currentFilters());
    window.location.href = `/api/export/excel${query ? `?${query}` : ""}`;
  });
  await load();
}
