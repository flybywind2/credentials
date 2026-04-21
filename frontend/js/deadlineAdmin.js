import { fetchJson } from "./api.js";

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

export function formatDday(deadline) {
  if (!deadline?.input_deadline || deadline.d_day === null || deadline.d_day === undefined) {
    return "마감일 미설정";
  }
  if (deadline.d_day === 0) {
    return "D-Day";
  }
  return deadline.d_day > 0 ? `D-${deadline.d_day}` : `D+${Math.abs(deadline.d_day)}`;
}

export async function renderDeadlineManager(container) {
  const deadline = await fetchJson("/api/admin/settings/deadline");
  container.innerHTML = `
    <section class="deadline-admin-section">
      <div class="section-header deadline-admin-header">
        <div>
          <h2>입력 마감일 관리</h2>
          <p>입력 화면과 관리자 대시보드의 D-day 표시에 사용됩니다.</p>
        </div>
        <span class="badge ${deadline.is_closed ? "danger" : "status"}">${formatDday(deadline)}</span>
      </div>
      <form class="deadline-form">
        <label for="input-deadline">입력 마감일
          <input id="input-deadline" name="input_deadline" type="date" value="${escapeHtml(deadline.input_deadline || "")}">
        </label>
        <label class="wide-deadline-field" for="input-deadline-description">설명
          <input id="input-deadline-description" name="description" value="${escapeHtml(deadline.description || "")}">
        </label>
        <button type="submit" class="primary-button">저장</button>
      </form>
    </section>
  `;

  container.querySelector(".deadline-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const inputDeadline = event.currentTarget.elements.input_deadline.value || null;
    const description = event.currentTarget.elements.description.value.trim() || null;
    await fetchJson("/api/admin/settings/deadline", {
      method: "PUT",
      body: JSON.stringify({ input_deadline: inputDeadline, description: description }),
    });
    await renderDeadlineManager(container);
  });
}
