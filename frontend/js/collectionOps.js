import { fetchJson } from "./api.js?v=20260426-validation-errors";

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatDateTime(value) {
  if (!value) {
    return "-";
  }
  return String(value).replace("T", " ").slice(0, 19);
}

function renderAuditRows(logs) {
  if (!logs.length) {
    return `<tr><td colspan="5">감사 로그가 없습니다.</td></tr>`;
  }
  return logs.map((log) => `
    <tr>
      <td>${formatDateTime(log.created_at)}</td>
      <td>${escapeHtml(log.action)}</td>
      <td>${escapeHtml(log.employee_id || "-")}</td>
      <td>${escapeHtml(log.status)}</td>
      <td>${escapeHtml(log.message || "-")}</td>
    </tr>
  `).join("");
}

function renderMailFailures(failures) {
  if (!failures.length) {
    return `<p class="empty-note">메일 발송 실패 건이 없습니다.</p>`;
  }
  return `
    <ul class="compact-list">
      ${failures.map((failure) => `
        <li>
          <strong>${formatDateTime(failure.created_at)}</strong>
          <span>${escapeHtml(failure.message || "메일 발송 실패")}</span>
        </li>
      `).join("")}
    </ul>
  `;
}

export async function renderCollectionOpsManager(container) {
  const [status, auditLogs] = await Promise.all([
    fetchJson("/api/admin/collection/status"),
    fetchJson("/api/admin/audit-logs?limit=8"),
  ]);
  const locked = Boolean(status.collection_locked);

  container.innerHTML = `
    <div class="ops-grid">
      <section class="ops-block">
        <h3>취합 상태</h3>
        <div class="metric">
          <span>현재 상태</span>
          <strong>${locked ? "종료됨" : "진행 중"}</strong>
        </div>
        <label class="field-group">종료 사유
          <input name="collection_lock_reason" data-collection-lock-reason value="${escapeHtml(status.lock_reason || "")}" placeholder="예: 최종 취합 종료">
        </label>
        <div class="toolbar">
          <button type="button" class="${locked ? "secondary-button" : "primary-button"}" data-action="toggle-collection-lock">
            ${locked ? "재오픈" : "취합 종료"}
          </button>
        </div>
      </section>
      <section class="ops-block">
        <h3>최종 Export</h3>
        <p>마지막 산출물: ${escapeHtml(status.last_export?.filename || "-")}</p>
        <p>실행자: ${escapeHtml(status.last_export?.employee_id || "-")}</p>
        <p>실행일: ${formatDateTime(status.last_export?.exported_at)}</p>
      </section>
      <section class="ops-block">
        <h3>메일 발송 실패</h3>
        ${renderMailFailures(status.mail_failures || [])}
      </section>
    </div>
    <section class="ops-block">
      <h3>감사 로그</h3>
      <div class="table-wrap compact-table-wrap">
        <table class="compact-table">
          <thead>
            <tr><th>일시</th><th>이벤트</th><th>사용자</th><th>상태</th><th>내용</th></tr>
          </thead>
          <tbody>${renderAuditRows(auditLogs.items || [])}</tbody>
        </table>
      </div>
    </section>
  `;

  container.querySelector("[data-action='toggle-collection-lock']").addEventListener("click", async () => {
    await fetchJson("/api/admin/collection/status", {
      method: "PUT",
      body: JSON.stringify({
        collection_locked: !locked,
        lock_reason: container.querySelector("[data-collection-lock-reason]").value,
      }),
    });
    await renderCollectionOpsManager(container);
  });
}
