import { fetchJson } from "./api.js";
import { paginateItems, renderPaginationControls } from "./pagination.js?v=20260425-admin-scroll";

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

export function renderGroupRows(tasks, startIndex = 0) {
  if (!tasks.length) {
    return `<tr><td colspan="9">동일 그룹 내 조회 가능한 업무가 없습니다.</td></tr>`;
  }
  return tasks.map((task, index) => `
    <tr>
      <td>${startIndex + index + 1}</td>
      <td>${escapeHtml(task.part_name || "-")}</td>
      <td>${escapeHtml(task.sub_part || "-")}</td>
      <td>${escapeHtml(task.major_task)}</td>
      <td>${escapeHtml(task.detail_task)}</td>
      <td>${task.is_confidential ? "기밀" : "비기밀"}</td>
      <td>${task.is_national_tech ? "해당" : "비해당"}</td>
      <td>${task.is_compliance ? "해당" : "비해당"}</td>
      <td><span class="badge status-${String(task.status).toLowerCase()}">${escapeHtml(task.status)}</span></td>
    </tr>
  `).join("");
}

export async function renderGroupReadonly(container) {
  const tasks = await fetchJson("/api/tasks/group");
  let currentPage = 1;

  function updateRows() {
    const page = paginateItems(tasks, currentPage);
    currentPage = page.page;
    container.querySelector("[data-group-readonly-body]").innerHTML = renderGroupRows(
      page.items,
      (page.page - 1) * page.pageSize,
    );
    container.querySelector("[data-group-pagination]").innerHTML = renderPaginationControls(page, "group-readonly");
  }

  container.innerHTML = `
    <section class="workspace readonly-section">
      <div class="section-header">
        <div>
          <h2>동일 그룹 조회</h2>
          <p>같은 그룹의 파트 업무를 읽기 전용으로 확인합니다.</p>
        </div>
      </div>
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>No</th><th>파트</th><th>소파트</th><th>대업무</th><th>세부업무</th>
              <th>기밀</th><th>국가핵심기술</th><th>Compliance</th><th>상태</th>
            </tr>
          </thead>
          <tbody data-group-readonly-body></tbody>
        </table>
      </div>
      <div data-group-pagination></div>
    </section>
  `;
  container.querySelector("[data-group-pagination]").addEventListener("click", (event) => {
    const button = event.target.closest("[data-page-action]");
    if (!button) {
      return;
    }
    currentPage += button.dataset.pageAction === "next" ? 1 : -1;
    updateRows();
  });
  updateRows();
}
