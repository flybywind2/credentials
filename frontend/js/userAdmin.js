import { fetchJson } from "./api.js";

const ROLE_OPTIONS = [
  ["ADMIN", "관리자"],
  ["INPUTTER", "입력자"],
  ["APPROVER", "승인자"],
];

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

export function roleLabel(role) {
  return ROLE_OPTIONS.find(([value]) => value === role)?.[1] || role || "-";
}

export function filterUserRows(users, keyword) {
  const query = String(keyword || "").trim().toLowerCase();
  if (!query) {
    return [...users];
  }
  return users.filter((user) => [
    user.employee_id,
    user.name,
    roleLabel(user.role),
    user.role,
    user.organization_path,
    user.source,
  ].some((value) => String(value || "").toLowerCase().includes(query)));
}

function organizationLabel(org) {
  return [
    org.division_name,
    org.team_name,
    org.group_name,
    org.part_name,
  ].filter(Boolean).join(" / ");
}

function renderOrganizationOptions(organizations, selectedId = "") {
  return [
    `<option value="">조직 없음</option>`,
    ...organizations.map((org) => `
      <option value="${org.id}" ${Number(selectedId) === Number(org.id) ? "selected" : ""}>
        ${escapeHtml(organizationLabel(org))}
      </option>
    `),
  ].join("");
}

function renderUserRows(users) {
  if (!users.length) {
    return `<tr><td colspan="6">조회된 사용자가 없습니다.</td></tr>`;
  }
  return users.map((user) => `
    <tr data-user-id="${escapeHtml(user.employee_id)}">
      <td>${escapeHtml(user.employee_id)}</td>
      <td>${escapeHtml(user.name)}</td>
      <td>${escapeHtml(roleLabel(user.role))}</td>
      <td>${escapeHtml(user.organization_path || "-")}</td>
      <td>${escapeHtml(user.source)}${user.managed ? "" : " · 미등록"}</td>
      <td>
        <button type="button" class="secondary-button" data-action="edit-user">${user.managed ? "수정" : "등록"}</button>
        ${user.managed
          ? `<button type="button" class="secondary-button" data-action="delete-user">삭제</button>`
          : `<span class="muted-text">-</span>`}
      </td>
    </tr>
  `).join("");
}

function userPayload(form) {
  return {
    employee_id: form.elements.employee_id.value.trim(),
    name: form.elements.name.value.trim(),
    role: form.elements.role.value,
    organization_id: form.elements.organization_id.value
      ? Number(form.elements.organization_id.value)
      : null,
  };
}

function fillUserForm(form, user = {}, organizations = []) {
  form.dataset.editId = user.employee_id || "";
  form.dataset.managed = String(Boolean(user.managed));
  form.elements.employee_id.value = user.employee_id || "";
  form.elements.employee_id.readOnly = Boolean(user.employee_id);
  form.elements.name.value = user.name || "";
  form.elements.role.value = user.role || "INPUTTER";
  form.elements.organization_id.innerHTML = renderOrganizationOptions(organizations, user.organization_id || "");
  form.querySelector("[data-form-title]").textContent = user.employee_id
    ? (user.managed ? "사용자 권한 수정" : "조직장 권한 등록")
    : "사용자 권한 추가";
}

function showError(container, message) {
  container.querySelector("[data-user-error]").textContent = message;
}

export async function renderUserManager(container) {
  const [users, organizations] = await Promise.all([
    fetchJson("/api/admin/users"),
    fetchJson("/api/organizations"),
  ]);
  let currentUsers = users;

  function updateRows() {
    const keyword = container.querySelector("[name='user_search']")?.value || "";
    currentUsers = filterUserRows(users, keyword);
    container.querySelector("[data-user-table-body]").innerHTML = renderUserRows(currentUsers);
  }

  container.innerHTML = `
    <section class="user-admin-section">
      <div class="section-header user-admin-header">
        <div>
          <h2>사용자 권한 관리</h2>
          <p>SSO 사번별 관리자, 입력자, 승인자 권한과 담당 조직을 관리합니다.</p>
        </div>
        <div class="toolbar">
          <input id="user-search" class="toolbar-input" name="user_search" placeholder="사용자 검색" autocomplete="off">
        </div>
      </div>
      <div class="admin-two-column user-admin-layout">
        <form class="admin-edit-form" data-user-form novalidate>
          <h3 data-form-title>사용자 권한 추가</h3>
          <div class="admin-form-grid user-form-grid">
            <label for="user-employee-id">사번 ID <input id="user-employee-id" name="employee_id" autocomplete="username" required></label>
            <label for="user-name">이름 <input id="user-name" name="name" autocomplete="name" required></label>
            <label for="user-role">권한
              <select id="user-role" name="role" autocomplete="off">
                ${ROLE_OPTIONS.map(([value, label]) => `<option value="${value}">${label}</option>`).join("")}
              </select>
            </label>
            <label class="wide-field" for="user-organization-id">담당 조직
              <select id="user-organization-id" name="organization_id" autocomplete="off">${renderOrganizationOptions(organizations)}</select>
            </label>
          </div>
          <p class="field-error" data-user-error></p>
          <div class="question-admin-actions">
            <button type="button" class="secondary-button" data-action="reset-user-form">초기화</button>
            <button type="submit" class="primary-button">저장</button>
          </div>
        </form>
        <div class="table-wrap compact-table-wrap user-table-wrap">
          <table class="compact-table user-admin-table">
            <thead>
              <tr><th>사번</th><th>이름</th><th>권한</th><th>담당 조직</th><th>소스</th><th>작업</th></tr>
            </thead>
            <tbody data-user-table-body>${renderUserRows(currentUsers)}</tbody>
          </table>
        </div>
      </div>
    </section>
  `;

  const form = container.querySelector("[data-user-form]");
  fillUserForm(form, {}, organizations);

  container.querySelector("[name='user_search']").addEventListener("input", updateRows);
  container.querySelector("[data-action='reset-user-form']").addEventListener("click", () => {
    showError(container, "");
    fillUserForm(form, {}, organizations);
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    showError(container, "");
    const payload = userPayload(form);
    if (!payload.employee_id || !payload.name) {
      showError(container, "사번 ID와 이름을 입력하세요.");
      return;
    }
    if (payload.role !== "ADMIN" && !payload.organization_id) {
      showError(container, "입력자와 승인자는 담당 조직을 선택하세요.");
      return;
    }
    try {
      if (form.dataset.editId && form.dataset.managed === "true") {
        await fetchJson(`/api/admin/users/${encodeURIComponent(form.dataset.editId)}`, {
          method: "PUT",
          body: JSON.stringify({
            name: payload.name,
            role: payload.role,
            organization_id: payload.organization_id,
          }),
        });
      } else {
        await fetchJson("/api/admin/users", {
          method: "POST",
          body: JSON.stringify(payload),
        });
      }
      await renderUserManager(container);
    } catch (error) {
      showError(container, error.message);
    }
  });

  container.querySelector("[data-user-table-body]").addEventListener("click", async (event) => {
    const row = event.target.closest("[data-user-id]");
    if (!row) {
      return;
    }
    const selectedUser = users.find((item) => item.employee_id === row.dataset.userId);
    if (event.target.closest("[data-action='edit-user']")) {
      showError(container, "");
      fillUserForm(form, selectedUser, organizations);
      form.scrollIntoView({ block: "center" });
    }
    if (event.target.closest("[data-action='delete-user']")) {
      if (!globalThis.confirm?.(`${selectedUser.employee_id} 권한을 삭제하시겠습니까?`)) {
        return;
      }
      try {
        await fetchJson(`/api/admin/users/${encodeURIComponent(selectedUser.employee_id)}`, { method: "DELETE" });
        await renderUserManager(container);
      } catch (error) {
        showError(container, error.message);
      }
    }
  });
}
