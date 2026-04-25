import { clearEmployeeId, loginWithEmployeeId, loadCurrentUser, savedEmployeeId } from "./auth.js?v=20260422-sso-token";
import { renderApproval } from "./approval.js?v=20260425-review-complete";
import { renderDashboard } from "./dashboard.js?v=20260425-admin-scroll";
import { renderGroupReadonly } from "./groupReadonly.js?v=20260425-group-pagination";
import { renderPartStatus } from "./partStatus.js?v=20260425-part-member-admin";
import { renderSpreadsheet } from "./spreadsheet.js?v=20260425-paste-grid";

const routes = {
  inputter: renderSpreadsheet,
  status: renderPartStatus,
  group: renderGroupReadonly,
  approver: renderApproval,
  admin: renderDashboard,
};

const routeItems = [
  { key: "inputter", label: "업무 입력", path: "/inputter", roles: ["INPUTTER", "APPROVER", "ADMIN"] },
  { key: "status", label: "진행 현황", path: "/status", roles: ["INPUTTER", "APPROVER", "ADMIN"] },
  { key: "group", label: "그룹 업무 조회", path: "/group", roles: ["INPUTTER", "APPROVER", "ADMIN"] },
  { key: "approver", label: "승인 검토", path: "/approver", roles: ["APPROVER", "ADMIN"] },
  { key: "admin", label: "시스템 관리", path: "/admin", roles: ["ADMIN"] },
];

let activePopstateHandler = null;

export function availableRoutesForRole(role) {
  return routeItems.filter((item) => item.roles.includes(role));
}

export function routePathForKey(key, params = {}) {
  if (key === "approver" && params.approvalId) {
    return `/approver/approvals/${encodeURIComponent(params.approvalId)}`;
  }
  return routeItems.find((item) => item.key === key)?.path || "/inputter";
}

export function routeFromPath(pathname = "/") {
  const path = String(pathname || "/").replace(/\/+$/, "") || "/";
  const approvalDetailMatch = path.match(/^\/approver\/approvals\/([^/]+)$/);
  if (approvalDetailMatch) {
    return {
      key: "approver",
      params: { approvalId: decodeURIComponent(approvalDetailMatch[1]) },
    };
  }
  const route = routeItems.find((item) => item.path === path);
  return { key: route?.key || "inputter", params: {} };
}

function renderNav(activeKey, userRole) {
  const visibleRoutes = availableRoutesForRole(userRole);
  return `
    <nav class="role-nav" aria-label="주요 작업">
      ${visibleRoutes.map(({ key, label }) => `
        <button type="button" data-route="${key}" class="${key === activeKey ? "active" : ""}">
          ${label}
        </button>
      `).join("")}
    </nav>
  `;
}

function syncBrowserPath(path, replace = false) {
  if (typeof window === "undefined" || window.location.pathname === path) {
    return;
  }
  const method = replace ? "replaceState" : "pushState";
  window.history[method]({}, "", path);
}

async function navigate(routeKey, userRole, view, options = {}) {
  const params = options.params || {};
  const allowedRoutes = availableRoutesForRole(userRole);
  const activeRouteKey = allowedRoutes.some((item) => item.key === routeKey)
    ? routeKey
    : allowedRoutes[0]?.key || "inputter";
  const activeParams = activeRouteKey === routeKey ? params : {};
  const route = routes[activeRouteKey] || routes.inputter;
  syncBrowserPath(routePathForKey(activeRouteKey, activeParams), options.replace);
  view.innerHTML = `${renderNav(activeRouteKey, userRole)}<div id="workspace-root"></div>`;
  view.querySelectorAll("[data-route]").forEach((button) => {
    button.addEventListener("click", () => navigate(button.dataset.route, userRole, view));
  });
  await route(view.querySelector("#workspace-root"), {
    params: activeParams,
    navigateTo: (nextRouteKey, nextParams = {}) => navigate(nextRouteKey, userRole, view, { params: nextParams }),
  });
}

function bindPopstate(userRole, view) {
  if (typeof window === "undefined") {
    return;
  }
  if (activePopstateHandler) {
    window.removeEventListener("popstate", activePopstateHandler);
  }
  activePopstateHandler = () => {
    const route = routeFromPath(window.location.pathname);
    navigate(route.key, userRole, view, { params: route.params, replace: true });
  };
  window.addEventListener("popstate", activePopstateHandler);
}

function unbindPopstate() {
  if (typeof window !== "undefined" && activePopstateHandler) {
    window.removeEventListener("popstate", activePopstateHandler);
  }
  activePopstateHandler = null;
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
  bindPopstate(user.role, view);
  const initialRoute = routeFromPath(window.location.pathname);
  await navigate(initialRoute.key, user.role, view, { params: initialRoute.params, replace: true });
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
    unbindPopstate();
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
      bindPopstate(user.role, view);
      const nextRoute = routeFromPath(window.location.pathname);
      await navigate(nextRoute.key, user.role, view, { params: nextRoute.params, replace: true });
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
