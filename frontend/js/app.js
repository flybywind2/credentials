import { loadCurrentUser } from "./auth.js?v=20260421-p1b";
import { renderApproval } from "./approval.js?v=20260421-rejected-pin";
import { renderDashboard } from "./dashboard.js?v=20260421-rejected-pin";
import { renderGroupReadonly } from "./groupReadonly.js?v=20260421-p1b";
import { renderSpreadsheet } from "./spreadsheet.js?v=20260421-rejected-pin";

const routes = {
  inputter: renderSpreadsheet,
  group: renderGroupReadonly,
  approver: renderApproval,
  admin: renderDashboard,
};

const routeItems = [
  { key: "inputter", label: "입력자", roles: ["INPUTTER", "ADMIN"] },
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
  userSummary.textContent = `${user.name} · ${user.role}`;
  await navigate(availableRoutesForRole(user.role)[0]?.key || "inputter", user.role, view);
}

if (typeof document !== "undefined") {
  init().catch((error) => {
    document.querySelector("#view").innerHTML = `<p class="error">${error.message}</p>`;
  });
}
