import { fetchJson } from "./api.js?v=20260426-mock-cookie";
import { paginateItems, renderPaginationControls } from "./pagination.js?v=20260425-admin-scroll";

const CSV_HEADERS = [
  "실명",
  "실장명",
  "실장ID",
  "팀명",
  "팀장명",
  "팀장ID",
  "그룹명",
  "그룹장명",
  "그룹장ID",
  "파트명",
  "파트장명",
  "파트장ID",
];

const CSV_FIELD_MAP = {
  실명: "division_name",
  실장명: "division_head_name",
  실장ID: "division_head_id",
  팀명: "team_name",
  팀장명: "team_head_name",
  팀장ID: "team_head_id",
  그룹명: "group_name",
  그룹장명: "group_head_name",
  그룹장ID: "group_head_id",
  파트명: "part_name",
  파트장명: "part_head_name",
  파트장ID: "part_head_id",
};

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function parseCsvRows(text) {
  const rows = [[]];
  let cell = "";
  let inQuotes = false;
  for (let index = 0; index < text.length; index += 1) {
    const char = text[index];
    const next = text[index + 1];
    if (inQuotes) {
      if (char === '"' && next === '"') {
        cell += '"';
        index += 1;
      } else if (char === '"') {
        inQuotes = false;
      } else {
        cell += char;
      }
      continue;
    }
    if (char === '"') {
      inQuotes = true;
    } else if (char === ",") {
      rows.at(-1).push(cell);
      cell = "";
    } else if (char === "\n" || char === "\r") {
      rows.at(-1).push(cell);
      cell = "";
      if (char === "\r" && next === "\n") {
        index += 1;
      }
      rows.push([]);
    } else {
      cell += char;
    }
  }
  rows.at(-1).push(cell);
  return rows.filter((row) => row.some((value) => value.trim()));
}

function orgTypeFromRow(row) {
  if (!row["팀명"] && !row["그룹명"]) {
    return "DIV_DIRECT";
  }
  if (!row["그룹명"]) {
    return "TEAM_DIRECT";
  }
  return "NORMAL";
}

export function parseOrganizationCsvPreview(text) {
  const rows = parseCsvRows(text);
  const headers = rows.shift()?.map((header) => header.trim()) || [];
  const missing = CSV_HEADERS.filter((header) => !headers.includes(header));
  if (missing.length) {
    throw new Error(`필수 헤더 누락: ${missing.join(", ")}`);
  }

  return rows.map((values) => {
    const source = Object.fromEntries(headers.map((header, index) => [header, values[index]?.trim() || ""]));
    const mapped = {};
    Object.entries(CSV_FIELD_MAP).forEach(([sourceKey, targetKey]) => {
      mapped[targetKey] = source[sourceKey] || "";
    });
    mapped.org_type = orgTypeFromRow(source);
    mapped.division_head_email = mapped.division_head_id ? `${mapped.division_head_id}@samsung.com` : "";
    mapped.part_head_email = `${mapped.part_head_id}@samsung.com`;
    return mapped;
  });
}

function organizationPayload(form) {
  return {
    division_name: form.elements.division_name.value.trim(),
    division_head_name: form.elements.division_head_name.value.trim(),
    division_head_id: form.elements.division_head_id.value.trim(),
    team_name: form.elements.team_name.value.trim() || null,
    team_head_name: form.elements.team_head_name.value.trim() || null,
    team_head_id: form.elements.team_head_id.value.trim() || null,
    group_name: form.elements.group_name.value.trim() || null,
    group_head_name: form.elements.group_head_name.value.trim() || null,
    group_head_id: form.elements.group_head_id.value.trim() || null,
    part_name: form.elements.part_name.value.trim(),
    part_head_name: form.elements.part_head_name.value.trim(),
    part_head_id: form.elements.part_head_id.value.trim(),
    org_type: form.elements.org_type.value,
  };
}

function renderOrganizationRows(organizations) {
  if (!organizations.length) {
    return `<tr><td colspan="7">조회된 조직이 없습니다.</td></tr>`;
  }
  return organizations.map((org) => `
    <tr data-organization-id="${org.id}">
      <td>${escapeHtml(org.division_name)}</td>
      <td>${escapeHtml(org.team_name || "-")}</td>
      <td>${escapeHtml(org.group_name || "-")}</td>
      <td>${escapeHtml(org.part_name)}</td>
      <td>${escapeHtml(org.part_head_id)}</td>
      <td>${escapeHtml(org.org_type)}</td>
      <td>
        <button type="button" class="secondary-button" data-action="edit-organization">수정</button>
        <button type="button" class="secondary-button" data-action="delete-organization">삭제</button>
      </td>
    </tr>
  `).join("");
}

function fillOrganizationForm(form, org = {}) {
  form.dataset.editId = org.id || "";
  [
    "division_name",
    "division_head_name",
    "division_head_id",
    "team_name",
    "team_head_name",
    "team_head_id",
    "group_name",
    "group_head_name",
    "group_head_id",
    "part_name",
    "part_head_name",
    "part_head_id",
  ].forEach((key) => {
    form.elements[key].value = org[key] || "";
  });
  form.elements.org_type.value = org.org_type || "NORMAL";
  form.querySelector("[data-form-title]").textContent = org.id ? "조직 수정" : "조직 추가";
}

function renderPreview(rows) {
  if (!rows.length) {
    return `<p class="empty-note">CSV 미리보기 행이 없습니다.</p>`;
  }
  return `
    <div class="table-wrap compact-table-wrap">
      <table class="compact-table">
        <thead><tr><th>실</th><th>팀</th><th>그룹</th><th>파트</th><th>파트장 이메일</th><th>유형</th></tr></thead>
        <tbody>
          ${rows.slice(0, 20).map((row) => `
            <tr>
              <td>${escapeHtml(row.division_name)}</td>
              <td>${escapeHtml(row.team_name || "-")}</td>
              <td>${escapeHtml(row.group_name || "-")}</td>
              <td>${escapeHtml(row.part_name)}</td>
              <td>${escapeHtml(row.part_head_email)}</td>
              <td>${escapeHtml(row.org_type)}</td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    </div>
  `;
}

export async function renderOrganizationManager(container) {
  const organizations = await fetchJson("/api/organizations");
  container.innerHTML = `
    <section class="organization-admin-section">
      <div class="section-header organization-admin-main-header">
        <div>
          <h2>조직 관리</h2>
          <p>조직을 검색하고 CSV 또는 수동 입력으로 추가·수정·삭제합니다.</p>
        </div>
        <div class="toolbar">
          <input class="toolbar-input" name="organization_search" placeholder="파트 검색">
          <button type="button" class="secondary-button" data-action="search-organizations">검색</button>
        </div>
      </div>
      <div class="admin-two-column">
        <form class="admin-edit-form" data-organization-form novalidate>
          <h3 data-form-title>조직 추가</h3>
          <div class="admin-form-grid">
            <label>실명 <input name="division_name" required></label>
            <label>실장명 <input name="division_head_name"></label>
            <label>실장ID <input name="division_head_id"></label>
            <label>팀명 <input name="team_name"></label>
            <label>팀장명 <input name="team_head_name"></label>
            <label>팀장ID <input name="team_head_id"></label>
            <label>그룹명 <input name="group_name"></label>
            <label>그룹장명 <input name="group_head_name"></label>
            <label>그룹장ID <input name="group_head_id"></label>
            <label>파트명 <input name="part_name" required></label>
            <label>파트장명 <input name="part_head_name" required></label>
            <label>파트장ID <input name="part_head_id" required></label>
            <label>조직 유형
              <select name="org_type">
                <option value="NORMAL">NORMAL</option>
                <option value="TEAM_DIRECT">TEAM_DIRECT</option>
                <option value="DIV_DIRECT">DIV_DIRECT</option>
              </select>
            </label>
          </div>
          <p class="field-error" data-organization-error></p>
          <div class="question-admin-actions">
            <button type="button" class="secondary-button" data-action="reset-organization-form">초기화</button>
            <button type="submit" class="primary-button">저장</button>
          </div>
        </form>
        <div class="admin-import-box">
          <h3>CSV 업로드</h3>
          <input type="file" name="organization_csv" accept=".csv,text/csv">
          <p class="field-error" data-import-error></p>
          <div data-import-preview>${renderPreview([])}</div>
          <button type="button" class="primary-button" data-action="import-organizations" disabled>CSV 저장</button>
        </div>
      </div>
      <div class="table-wrap compact-table-wrap">
        <table class="compact-table">
          <thead><tr><th>실</th><th>팀</th><th>그룹</th><th>파트</th><th>파트장ID</th><th>유형</th><th>작업</th></tr></thead>
          <tbody data-organization-table-body></tbody>
        </table>
        <div data-organization-pagination></div>
      </div>
    </section>
  `;

  const form = container.querySelector("[data-organization-form]");
  let currentOrganizations = organizations;
  let currentPage = 1;
  let selectedCsvFile = null;

  function updateOrganizationRows() {
    const page = paginateItems(currentOrganizations, currentPage);
    currentPage = page.page;
    container.querySelector("[data-organization-table-body]").innerHTML = renderOrganizationRows(page.items);
    container.querySelector("[data-organization-pagination]").innerHTML = renderPaginationControls(page, "organizations");
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const payload = organizationPayload(form);
    if (!payload.division_name || !payload.part_name || !payload.part_head_name || !payload.part_head_id) {
      container.querySelector("[data-organization-error]").textContent = "필수 조직 정보를 입력하세요.";
      return;
    }
    if (form.dataset.editId) {
      await fetchJson(`/api/admin/organizations/${form.dataset.editId}`, {
        method: "PUT",
        body: JSON.stringify(payload),
      });
    } else {
      await fetchJson("/api/admin/organizations", {
        method: "POST",
        body: JSON.stringify(payload),
      });
    }
    await renderOrganizationManager(container);
  });

  container.querySelector("[data-action='reset-organization-form']").addEventListener("click", () => {
    fillOrganizationForm(form);
  });

  container.querySelector("[data-action='search-organizations']").addEventListener("click", async () => {
    const search = container.querySelector("[name='organization_search']").value.trim();
    currentOrganizations = await fetchJson(`/api/organizations${search ? `?part=${encodeURIComponent(search)}` : ""}`);
    currentPage = 1;
    updateOrganizationRows();
  });

  container.querySelector("[data-organization-table-body]").addEventListener("click", async (event) => {
    const row = event.target.closest("[data-organization-id]");
    if (!row) {
      return;
    }
    const org = currentOrganizations.find((item) => String(item.id) === row.dataset.organizationId);
    if (event.target.closest("[data-action='edit-organization']")) {
      fillOrganizationForm(form, org);
    }
    if (event.target.closest("[data-action='delete-organization']")) {
      await fetchJson(`/api/admin/organizations/${org.id}`, { method: "DELETE" });
      await renderOrganizationManager(container);
    }
  });

  container.addEventListener("click", (event) => {
    const button = event.target.closest("[data-page-action]");
    if (!button || !button.closest("[data-pagination-target='organizations']")) {
      return;
    }
    currentPage += button.dataset.pageAction === "next" ? 1 : -1;
    updateOrganizationRows();
  });

  container.querySelector("[name='organization_csv']").addEventListener("change", async (event) => {
    selectedCsvFile = event.target.files[0] || null;
    const error = container.querySelector("[data-import-error]");
    const preview = container.querySelector("[data-import-preview]");
    const importButton = container.querySelector("[data-action='import-organizations']");
    error.textContent = "";
    importButton.disabled = true;
    if (!selectedCsvFile) {
      preview.innerHTML = renderPreview([]);
      return;
    }
    try {
      const rows = parseOrganizationCsvPreview(await selectedCsvFile.text());
      preview.innerHTML = renderPreview(rows);
      importButton.disabled = rows.length === 0;
    } catch (err) {
      error.textContent = err.message;
      preview.innerHTML = renderPreview([]);
    }
  });

  container.querySelector("[data-action='import-organizations']").addEventListener("click", async () => {
    if (!selectedCsvFile) {
      return;
    }
    const formData = new FormData();
    formData.append("file", selectedCsvFile);
    const response = await fetch("/api/admin/organizations/import", {
      method: "POST",
      headers: { "X-Employee-Id": "admin001" },
      body: formData,
    });
    if (!response.ok) {
      container.querySelector("[data-import-error]").textContent = `CSV 저장 실패: ${response.status}`;
      return;
    }
    await renderOrganizationManager(container);
  });

  updateOrganizationRows();
}
