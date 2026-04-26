import { fetchJson } from "./api.js?v=20260426-validation-errors";

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

const TEXT_FIELDS = [
  "sub_part",
  "major_task",
  "detail_task",
  "storage_location",
  "related_menu",
  "share_scope",
];

const BOOLEAN_FIELDS = [
  "is_confidential",
  "is_national_tech",
  "is_compliance",
];

const FIELD_LABELS = {
  sub_part: "소파트",
  major_task: "대업무",
  detail_task: "세부업무",
  is_confidential: "기밀",
  is_national_tech: "국가핵심기술",
  is_compliance: "Compliance",
  storage_location: "보관 장소",
  related_menu: "관련 메뉴",
  share_scope: "공유 범위",
};

function blankExampleRow() {
  return {
    sub_part: "",
    major_task: "",
    detail_task: "",
    is_confidential: false,
    is_national_tech: false,
    is_compliance: false,
    storage_location: "",
    related_menu: "",
    share_scope: "",
  };
}

export function normalizeInputExampleRows(rows = []) {
  return rows.map((row) => ({
    ...blankExampleRow(),
    ...Object.fromEntries(TEXT_FIELDS.map((field) => [field, String(row[field] || "").trim()])),
    ...Object.fromEntries(BOOLEAN_FIELDS.map((field) => [field, Boolean(row[field])])),
  })).filter((row) => (
    row.sub_part
    || row.major_task
    || row.detail_task
    || row.storage_location
    || row.related_menu
    || row.share_scope
  ));
}

function renderExampleRows(rows) {
  return rows.map((row, index) => `
    <tr data-example-row="${index}">
      <td>${index + 1}</td>
      ${TEXT_FIELDS.slice(0, 3).map((field) => `
        <td>
          <input class="table-input" data-example-field="${field}" value="${escapeHtml(row[field] || "")}" aria-label="${escapeHtml(FIELD_LABELS[field])}">
        </td>
      `).join("")}
      ${BOOLEAN_FIELDS.map((field) => `
        <td class="checkbox-cell">
          <input type="checkbox" data-example-field="${field}" ${row[field] ? "checked" : ""} aria-label="${escapeHtml(FIELD_LABELS[field])}">
        </td>
      `).join("")}
      ${TEXT_FIELDS.slice(3).map((field) => `
        <td>
          <input class="table-input" data-example-field="${field}" value="${escapeHtml(row[field] || "")}" aria-label="${escapeHtml(FIELD_LABELS[field])}">
        </td>
      `).join("")}
      <td>
        <button type="button" class="secondary-button" data-action="remove-example-row" data-row-index="${index}">삭제</button>
      </td>
    </tr>
  `).join("");
}

function readRows(container) {
  return [...container.querySelectorAll("[data-example-row]")].map((rowElement) => {
    const row = blankExampleRow();
    TEXT_FIELDS.forEach((field) => {
      row[field] = rowElement.querySelector(`[data-example-field="${field}"]`)?.value || "";
    });
    BOOLEAN_FIELDS.forEach((field) => {
      row[field] = Boolean(rowElement.querySelector(`[data-example-field="${field}"]`)?.checked);
    });
    return row;
  });
}

function renderManager(container, rows, statusMessage = "") {
  const editableRows = rows.length ? rows : [blankExampleRow()];
  container.innerHTML = `
    <section class="input-example-admin-section">
      <div class="section-header input-example-admin-header">
        <div>
          <h2>입력 예시 데이터</h2>
          <p>입력 화면에서 사용자가 켜고 끌 수 있는 예시 행을 관리합니다.</p>
        </div>
        <div class="toolbar">
          <button type="button" class="secondary-button" data-action="add-example-row">행 추가</button>
          <button type="button" class="primary-button" data-action="save-example-rows">저장</button>
        </div>
      </div>
      ${statusMessage ? `<div class="validation-panel success-panel" role="status"><strong>${escapeHtml(statusMessage)}</strong></div>` : ""}
      <div class="table-wrap compact-table-wrap">
        <table class="compact-table input-example-admin-table">
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
              <th>작업</th>
            </tr>
          </thead>
          <tbody>${renderExampleRows(editableRows)}</tbody>
        </table>
      </div>
    </section>
  `;
}

export async function renderInputExampleManager(container) {
  let rows = normalizeInputExampleRows(await fetchJson("/api/admin/input-examples"));
  renderManager(container, rows);

  container.addEventListener("click", async (event) => {
    const removeButton = event.target.closest("[data-action='remove-example-row']");
    if (removeButton) {
      rows = readRows(container);
      rows.splice(Number(removeButton.dataset.rowIndex), 1);
      renderManager(container, normalizeInputExampleRows(rows));
      return;
    }
    if (event.target.closest("[data-action='add-example-row']")) {
      rows = [...readRows(container), blankExampleRow()];
      renderManager(container, rows);
      return;
    }
    if (event.target.closest("[data-action='save-example-rows']")) {
      rows = normalizeInputExampleRows(readRows(container));
      rows = await fetchJson("/api/admin/input-examples", {
        method: "PUT",
        body: JSON.stringify({ rows }),
      });
      renderManager(container, rows, "예시 데이터가 저장되었습니다.");
    }
  });
}
