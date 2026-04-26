export const EXAMPLE_DATA_STORAGE_KEY = "credential_example_data_visible";

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function badge(label, tone) {
  return `<span class="badge ${tone}">${label}</span>`;
}

export function isExampleDataVisible(storage = globalThis.localStorage) {
  try {
    return storage?.getItem(EXAMPLE_DATA_STORAGE_KEY) === "true";
  } catch {
    return false;
  }
}

export function setExampleDataVisible(visible, storage = globalThis.localStorage) {
  try {
    storage?.setItem(EXAMPLE_DATA_STORAGE_KEY, visible ? "true" : "false");
  } catch {
    // localStorage can be unavailable in strict browser environments.
  }
}

export function renderInputExamplePanel(rows = []) {
  return `
    <section class="input-example-panel" aria-label="예시 데이터">
      <div class="input-example-header">
        <div>
          <h3>예시 데이터</h3>
          <p>실제 저장 데이터가 아닌 입력 참고용 예시입니다.</p>
        </div>
      </div>
      <div class="table-wrap compact-table-wrap">
        <table class="compact-table input-example-table">
          <thead>
            <tr>
              <th>No</th>
              <th>소파트</th>
              <th>대업무</th>
              <th>세부업무</th>
              <th>기밀</th>
              <th>국가핵심기술</th>
              <th>Compliance</th>
              <th>보관 장소</th>
              <th>관련 메뉴</th>
              <th>공유 범위</th>
            </tr>
          </thead>
          <tbody>
            ${rows.length ? rows.map((row, index) => `
              <tr>
                <td>${index + 1}</td>
                <td>${escapeHtml(row.sub_part || "-")}</td>
                <td>${escapeHtml(row.major_task || "-")}</td>
                <td>${escapeHtml(row.detail_task || "-")}</td>
                <td>${badge(row.is_confidential ? "기밀" : "비기밀", row.is_confidential ? "danger" : "neutral")}</td>
                <td>${badge(row.is_national_tech ? "해당" : "비해당", row.is_national_tech ? "danger" : "neutral")}</td>
                <td>${badge(row.is_compliance ? "Compliance" : "비해당", row.is_compliance ? "warning" : "neutral")}</td>
                <td>${escapeHtml(row.storage_location || "-")}</td>
                <td>${escapeHtml(row.related_menu || "-")}</td>
                <td>${escapeHtml(row.share_scope || "-")}</td>
              </tr>
            `).join("") : `<tr><td colspan="10">관리자가 등록한 예시 데이터가 없습니다.</td></tr>`}
          </tbody>
        </table>
      </div>
    </section>
  `;
}
