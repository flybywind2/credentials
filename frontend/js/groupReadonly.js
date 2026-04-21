import { fetchJson } from "./api.js";

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function rows(tasks) {
  if (!tasks.length) {
    return `<tr><td colspan="9">동일 그룹 내 조회 가능한 업무가 없습니다.</td></tr>`;
  }
  return tasks.map((task, index) => `
    <tr>
      <td>${index + 1}</td>
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
          <tbody>${rows(tasks)}</tbody>
        </table>
      </div>
    </section>
  `;
}
