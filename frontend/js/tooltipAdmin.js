import { fetchJson } from "./api.js?v=20260426-mock-session";

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

export function tooltipMap(tooltips) {
  return Object.fromEntries(
    tooltips.map((tooltip) => [tooltip.column_key, tooltip.example_text || ""]),
  );
}

function renderTooltipRows(tooltips) {
  return tooltips.map((tooltip) => `
    <tr>
      <td>${escapeHtml(tooltip.label)}</td>
      <td>${escapeHtml(tooltip.column_key)}</td>
      <td>
        <input
          class="table-input"
          name="tooltip_${tooltip.column_key}"
          value="${escapeHtml(tooltip.example_text)}"
          data-tooltip-key="${tooltip.column_key}"
        >
      </td>
      <td><button type="button" class="secondary-button" data-save-tooltip="${tooltip.column_key}">저장</button></td>
    </tr>
  `).join("");
}

export async function renderTooltipManager(container) {
  const tooltips = await fetchJson("/api/admin/tooltips");
  container.innerHTML = `
    <section class="tooltip-admin-section">
      <div class="section-header tooltip-admin-main-header">
        <div>
          <h2>컬럼 예시 관리</h2>
          <p>입력 화면 컬럼 헤더의 도움말 문구를 관리합니다.</p>
        </div>
      </div>
      <div class="table-wrap compact-table-wrap">
        <table class="compact-table">
          <thead><tr><th>컬럼</th><th>키</th><th>예시 문구</th><th>작업</th></tr></thead>
          <tbody>${renderTooltipRows(tooltips)}</tbody>
        </table>
      </div>
    </section>
  `;

  container.querySelectorAll("[data-save-tooltip]").forEach((button) => {
    button.addEventListener("click", async () => {
      const key = button.dataset.saveTooltip;
      const input = container.querySelector(`[data-tooltip-key="${key}"]`);
      await fetchJson(`/api/admin/tooltips/${key}`, {
        method: "PUT",
        body: JSON.stringify({ example_text: input.value.trim() }),
      });
      await renderTooltipManager(container);
    });
  });
}
