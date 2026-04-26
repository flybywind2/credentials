import { fetchJson } from "./api.js?v=20260426-mock-cookie";
import { renderClassificationDonut } from "./classificationChart.js?v=20260426-classification-donut";
import { formatDday } from "./deadlineAdmin.js?v=20260421-p1b";
import { loadReadablePartMembers } from "./partMembers.js?v=20260426-mock-cookie";
import {
  editableOrganizationsForUser,
  orgPathOfOrganization,
  selectedEditableOrganization,
  shouldShowOrganizationSelector,
} from "./spreadsheet.js?v=20260426-part-selector";

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function statusRows(counts) {
  return Object.entries(counts || {}).map(([status, count]) => `
    <div class="metric"><span>${escapeHtml(status)}</span><strong>${count}</strong></div>
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

function renderStatusOrganizationSelector(user, organizations, selectedOrganization) {
  if (!shouldShowOrganizationSelector(user, organizations)) {
    return "";
  }
  return `
    <label class="work-org-selector">하위파트
      <select data-action="select-status-org" aria-label="하위파트 선택">
        ${organizations.map((organization) => `
          <option value="${organization.id}" ${Number(organization.id) === Number(selectedOrganization.id) ? "selected" : ""}>
            ${escapeHtml(orgPathOfOrganization(organization))}
          </option>
        `).join("")}
      </select>
    </label>
  `;
}

export async function renderPartStatus(container, options = {}) {
  const currentUser = await fetchJson("/api/auth/me");
  const organizations = ["APPROVER", "ADMIN"].includes(currentUser.role)
    ? await fetchJson("/api/organizations")
    : [currentUser.organization].filter(Boolean);
  const editableOrganizations = editableOrganizationsForUser(currentUser, organizations);
  const selectedOrganization = selectedEditableOrganization(
    currentUser,
    organizations,
    options.selectedOrgId,
  );
  const orgId = Number(selectedOrganization.id || currentUser.organization_id || currentUser.organization?.id || 1);
  const [deadline, status, rejection, members] = await Promise.all([
    fetchJson("/api/settings/deadline"),
    fetchJson(`/api/tasks/status?org_id=${orgId}`),
    fetchJson(`/api/tasks/rejection?org_id=${orgId}`),
    loadReadablePartMembers(fetchJson, orgId),
  ]);
  container.innerHTML = `
    <section class="workspace">
      <div class="section-header">
        <div>
          <h2>진행 현황</h2>
          <p>${escapeHtml(orgPathOfOrganization(selectedOrganization))}</p>
        </div>
        <div class="toolbar">
          ${renderStatusOrganizationSelector(currentUser, editableOrganizations, selectedOrganization)}
          <span class="badge ${deadline.is_closed ? "danger" : "status"}">${formatDday(deadline)}</span>
        </div>
      </div>
      ${deadline.description ? `<div class="alert-banner"><strong>마감 안내</strong><span>${escapeHtml(deadline.description)}</span></div>` : ""}
      ${rejection.has_rejection ? `<div class="alert-banner danger"><strong>반려 사유</strong><span>${escapeHtml(rejection.reject_reason)}</span></div>` : ""}
      ${renderClassificationDonut(status.classification_summary)}
      <div class="metric-grid status-metric-grid">
        <div class="metric"><span>전체</span><strong>${status.total_tasks}</strong></div>
        ${statusRows(status.status_counts)}
      </div>
      <section class="part-member-section">
        <div class="section-header part-member-header">
          <div>
            <h3>파트원 명단</h3>
            <p>관리자가 등록한 현재 파트의 인력 목록입니다.</p>
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
            <tbody>${memberRows(members)}</tbody>
          </table>
        </div>
      </section>
    </section>
  `;
  container.querySelector("[data-action='select-status-org']")?.addEventListener("change", async (event) => {
    await renderPartStatus(container, { ...options, selectedOrgId: Number(event.target.value) });
  });
}
