import { clearEmployeeId, loginWithEmployeeId, loadCurrentUser, savedEmployeeId } from "./auth.js?v=20260422-sso-token";
import { renderApproval } from "./approval.js?v=20260421-rejected-pin";
import { renderDashboard } from "./dashboard.js?v=20260421-rejected-pin";
import { renderGroupReadonly } from "./groupReadonly.js?v=20260421-p1b";
import { renderPartStatus } from "./partStatus.js?v=20260421-spec-complete";
import { renderSpreadsheet } from "./spreadsheet.js?v=20260422-none-bulk";

const routes = {
  inputter: renderSpreadsheet,
  status: renderPartStatus,
  group: renderGroupReadonly,
  approver: renderApproval,
  admin: renderDashboard,
};

const routeItems = [
  { key: "inputter", label: "입력자", roles: ["INPUTTER", "ADMIN"] },
  { key: "status", label: "내 파트 현황", roles: ["INPUTTER", "ADMIN"] },
  { key: "group", label: "그룹 조회", roles: ["INPUTTER", "ADMIN"] },
  { key: "approver", label: "승인자", roles: ["APPROVER", "ADMIN"] },
  { key: "admin", label: "관리자", roles: ["ADMIN"] },
];

export function availableRoutesForRole(role) {
  return routeItems.filter((item) => item.roles.includes(role));
}

function renderNav(activeKey, userRole) {
  const visibleRoutes = availableRoutesForRole(userRole);
  return `
    <nav class="role-nav" aria-label="역할 화면">
      ${visibleRoutes.map(({ key, label }) => `
        <button type="button" data-route="${key}" class="${key === activeKey ? "active" : ""}">
          ${label}
        </button>
      `).join("")}
    </nav>
  `;
}

async function navigate(routeKey, userRole, view) {
  const allowedRoutes = availableRoutesForRole(userRole);
  const activeRouteKey = allowedRoutes.some((item) => item.key === routeKey)
    ? routeKey
    : allowedRoutes[0]?.key || "inputter";
  const route = routes[activeRouteKey] || routes.inputter;
  view.innerHTML = `${renderNav(activeRouteKey, userRole)}<div id="workspace-root"></div>`;
  view.querySelectorAll("[data-route]").forEach((button) => {
    button.addEventListener("click", () => navigate(button.dataset.route, userRole, view));
  });
  await route(view.querySelector("#workspace-root"));
}

async function init() {
  const userSummary = document.querySelector("#user-summary");
  const view = document.querySelector("#view");
  const user = await loadCurrentUser();
  if (!user) {
    renderLogin(view, userSummary);
    return;
  }
  renderAuthenticatedSummary(userSummary, user, view);
  await navigate(availableRoutesForRole(user.role)[0]?.key || "inputter", user.role, view);
}

function renderAuthenticatedSummary(userSummary, user, view) {
  const label = document.createElement("span");
  label.textContent = `${user.name} · ${user.role}`;

  const logoutButton = document.createElement("button");
  logoutButton.type = "button";
  logoutButton.className = "secondary-button compact-filter-button";
  logoutButton.setAttribute("data-action", "logout");
  logoutButton.textContent = "로그아웃";
  logoutButton.addEventListener("click", () => {
    clearEmployeeId();
    renderLogin(view, userSummary);
  });

  userSummary.replaceChildren(label, logoutButton);
}

function renderLogin(view, userSummary) {
  userSummary.textContent = "로그인 필요";
  view.innerHTML = `
    <section class="login-screen">
      <form class="login-form" data-login-form>
        <h2>로그인</h2>
        <label for="employee-id">사번 ID
          <input id="employee-id" name="employee_id" value="${savedEmployeeId()}" autocomplete="username" data-storage-key="credential_employee_id" required>
        </label>
        <label for="employee-password">비밀번호
          <input id="employee-password" name="password" type="password" autocomplete="current-password">
        </label>
        <p class="field-error" data-login-error></p>
        <button type="submit" class="primary-button">SSO 인증</button>
      </form>
    </section>
  `;
  view.querySelector("[data-login-form]").addEventListener("submit", async (event) => {
    event.preventDefault();
    const employeeId = event.currentTarget.elements.employee_id.value.trim();
    const password = event.currentTarget.elements.password.value;
    const error = view.querySelector("[data-login-error]");
    error.textContent = "";
    try {
      const user = await loginWithEmployeeId(employeeId, password);
      renderAuthenticatedSummary(userSummary, user, view);
      await navigate(availableRoutesForRole(user.role)[0]?.key || "inputter", user.role, view);
    } catch (loginError) {
      clearEmployeeId();
      error.textContent = loginError.message;
    }
  });
}

if (typeof document !== "undefined") {
  init().catch((error) => {
    document.querySelector("#view").innerHTML = `<p class="error">${error.message}</p>`;
  });
}
