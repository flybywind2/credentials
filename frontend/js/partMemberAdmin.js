import { currentAccessToken, currentEmployeeId, fetchJson } from "./api.js";
import { paginateItems, renderPaginationControls } from "./pagination.js?v=20260425-admin-scroll";

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function authHeaders() {
  const employeeId = currentEmployeeId();
  const accessToken = currentAccessToken();
  return {
    ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
    ...(employeeId ? { "X-Employee-Id": employeeId } : {}),
  };
}

function organizationLabel(org) {
  return [org.division_name, org.team_name, org.group_name, org.part_name].filter(Boolean).join(" > ");
}

function organizationOptions(organizations) {
  return organizations.map((org) => `
    <option value="${org.id}">${escapeHtml(organizationLabel(org))}</option>
  `).join("");
}

function memberRows(members) {
  if (!members.length) {
    return `<tr><td colspan="3" class="muted-text">등록된 파트원이 없습니다.</td></tr>`;
  }
  return members.map((member) => `
    <tr>
      <td>${escapeHtml(member.part_name)}</td>
      <td>${escapeHtml(member.name)}</td>
      <td>${escapeHtml(member.knox_id)}</td>
    </tr>
  `).join("");
}

async function importPartMembers(orgId, file) {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch(`/api/part-members/import?org_id=${encodeURIComponent(orgId)}`, {
    method: "POST",
    headers: authHeaders(),
    body: formData,
  });
  if (!response.ok) {
    throw new Error(`파트원 CSV 업로드 실패: ${response.status}`);
  }
  return response.json();
}

async function loadMembers(container, orgId) {
  return fetchJson(`/api/part-members?org_id=${encodeURIComponent(orgId)}`);
}

export async function renderPartMemberManager(container) {
  const organizations = await fetchJson("/api/organizations");
  container.innerHTML = `
    <section class="part-member-section">
      <div class="section-header part-member-header">
        <div>
          <h2>파트원 명단 CSV 업로드</h2>
          <p>선택한 조직의 파트원 명단을 CSV로 교체합니다. CSV 헤더: 파트명, 이름, knox_id</p>
        </div>
      </div>
      <div class="admin-import-box part-member-import-box">
        <label>대상 조직
          <select class="toolbar-input" name="organization_id">${organizationOptions(organizations)}</select>
        </label>
        <label>CSV 파일
          <input type="file" name="part_member_csv" accept=".csv,text/csv">
        </label>
        <p class="field-error" data-part-member-error></p>
        <div class="question-admin-actions">
          <button type="button" class="primary-button" data-action="import-part-members">CSV 업로드</button>
        </div>
      </div>
      <div class="table-wrap part-member-table-wrap">
        <table class="data-table part-member-table">
          <thead>
            <tr>
              <th>파트명</th>
              <th>이름</th>
              <th>knox_id</th>
            </tr>
          </thead>
          <tbody data-part-member-body>${memberRows([])}</tbody>
        </table>
        <div data-part-member-pagination></div>
      </div>
    </section>
  `;

  const organizationSelect = container.querySelector("[name='organization_id']");
  const fileInput = container.querySelector("[name='part_member_csv']");
  const errorPanel = container.querySelector("[data-part-member-error]");
  let currentMembers = [];
  let currentPage = 1;

  function updateMemberRows() {
    const page = paginateItems(currentMembers, currentPage);
    currentPage = page.page;
    container.querySelector("[data-part-member-body]").innerHTML = memberRows(page.items);
    container.querySelector("[data-part-member-pagination]").innerHTML = renderPaginationControls(page, "part-members");
  }

  async function refreshMembers() {
    if (!organizationSelect.value) {
      currentMembers = [];
      updateMemberRows();
      return;
    }
    errorPanel.textContent = "";
    currentMembers = await loadMembers(container, organizationSelect.value);
    updateMemberRows();
  }

  organizationSelect.addEventListener("change", async () => {
    currentPage = 1;
    await refreshMembers();
  });
  container.addEventListener("click", (event) => {
    const button = event.target.closest("[data-page-action]");
    if (!button || !button.closest("[data-pagination-target='part-members']")) {
      return;
    }
    currentPage += button.dataset.pageAction === "next" ? 1 : -1;
    updateMemberRows();
  });
  container.querySelector("[data-action='import-part-members']").addEventListener("click", async () => {
    const file = fileInput.files?.[0];
    if (!organizationSelect.value || !file) {
      errorPanel.textContent = "대상 조직과 CSV 파일을 선택하세요.";
      return;
    }
    try {
      const result = await importPartMembers(organizationSelect.value, file);
      errorPanel.textContent = `${result.imported_count}명을 반영했습니다.`;
      fileInput.value = "";
      currentPage = 1;
      await refreshMembers();
    } catch (error) {
      errorPanel.textContent = error.message;
    }
  });

  await refreshMembers();
}
