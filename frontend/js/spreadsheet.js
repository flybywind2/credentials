import { currentEmployeeId, fetchJson } from "./api.js";
import { parseClipboardToTasks } from "./clipboard.js?v=20260425-paste-grid";
import { formatDday } from "./deadlineAdmin.js?v=20260421-p1b";
import { bindModalAccessibility } from "./modalAccessibility.js?v=20260421-p1b";
import { openTaskModal } from "./form.js?v=20260425-form-comments";
import { tooltipMap } from "./tooltipAdmin.js?v=20260421-p1b";

function badge(label, tone) {
  return `<span class="badge ${tone}">${label}</span>`;
}

function statusTone(status) {
  return `status-${String(status || "draft").toLowerCase()}`;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

export function deleteConfirmationMessage(task) {
  const label = task?.major_task ? `"${task.major_task}" 항목` : "선택한 항목";
  return `${label}을 삭제하시겠습니까?`;
}

export function renderActionError(title, message) {
  return `
    <div class="validation-panel" role="alert">
      <div>
        <strong>${escapeHtml(title)}</strong>
        <span>${escapeHtml(message)}</span>
      </div>
    </div>
  `;
}

function closePastePreview() {
  document.querySelector("#paste-preview-modal")?.remove();
}

function closeApprovalConfirm() {
  document.querySelector("#approval-confirm-modal")?.remove();
}

function orgIdOf(user) {
  return Number(user?.organization_id || user?.organization?.id || 1);
}

function orgPathOf(user) {
  return orgPathOfOrganization(user?.organization);
}

function orgPathOfOrganization(organization = {}) {
  return [
    organization.division_name,
    organization.team_name,
    organization.group_name,
    organization.part_name,
  ].filter(Boolean).join(" / ") || "조직 정보 없음";
}

function isApproverForOrganization(user, organization) {
  const employeeId = user?.employee_id;
  return Boolean(employeeId && organization && [
    organization.group_head_id,
    organization.team_head_id,
    organization.division_head_id,
    organization.part_head_id,
  ].includes(employeeId));
}

export function editableOrganizationsForUser(user, organizations = []) {
  const currentOrgId = orgIdOf(user);
  const source = Array.isArray(organizations) ? organizations : [];
  if (user?.role === "ADMIN") {
    return source.length ? source : [user.organization].filter(Boolean);
  }
  if (user?.role === "APPROVER") {
    const editable = source.filter((organization) => (
      Number(organization.id) === currentOrgId || isApproverForOrganization(user, organization)
    ));
    return editable.length ? editable : [user.organization].filter(Boolean);
  }
  const currentOrganization = source.find((organization) => Number(organization.id) === currentOrgId);
  return [currentOrganization || user?.organization].filter(Boolean);
}

export function selectedEditableOrganization(user, organizations = [], selectedOrgId = null) {
  const editable = editableOrganizationsForUser(user, organizations);
  const selectedId = Number(selectedOrgId);
  const currentOrgId = orgIdOf(user);
  return (
    editable.find((organization) => Number(organization.id) === selectedId)
    || editable.find((organization) => Number(organization.id) === currentOrgId)
    || editable[0]
    || user?.organization
    || { id: currentOrgId }
  );
}

function renderOrganizationSelector(organizations, selectedOrganization) {
  if (organizations.length <= 1) {
    return "";
  }
  return `
    <label class="work-org-selector">하위파트
      <select data-action="select-work-org" aria-label="하위파트 선택">
        ${organizations.map((organization) => `
          <option value="${organization.id}" ${Number(organization.id) === Number(selectedOrganization.id) ? "selected" : ""}>
            ${escapeHtml(orgPathOfOrganization(organization))}
          </option>
        `).join("")}
      </select>
    </label>
  `;
}

function classificationSummary(rows) {
  return rows.reduce((summary, row) => {
    const isConfidential = Boolean(row.is_confidential);
    const isNationalTech = Boolean(row.is_national_tech);
    const isCompliance = Boolean(row.is_compliance);
    return {
      total: summary.total + 1,
      confidential: summary.confidential + (isConfidential ? 1 : 0),
      nationalTech: summary.nationalTech + (isNationalTech ? 1 : 0),
      compliance: summary.compliance + (isCompliance ? 1 : 0),
      integrated: summary.integrated + (isConfidential || isNationalTech || isCompliance ? 1 : 0),
    };
  }, {
    total: 0,
    confidential: 0,
    nationalTech: 0,
    compliance: 0,
    integrated: 0,
  });
}

function assigneeSummary(task) {
  const names = (task.assignees || []).map((assignee) => assignee.name || assignee.knox_id).filter(Boolean);
  return names.length ? names.join(", ") : "-";
}

function formDataHeaders() {
  const employeeId = currentEmployeeId();
  return employeeId ? { "X-Employee-Id": employeeId } : {};
}

export function groupValidationErrors(errors) {
  const grouped = new Map();
  errors.forEach((error) => {
    const rowErrors = grouped.get(error.row_index) || [];
    rowErrors.push(error);
    grouped.set(error.row_index, rowErrors);
  });
  return grouped;
}

export function firstErrorRow(errors) {
  return errors.length ? Math.min(...errors.map((error) => error.row_index)) : null;
}

function validPreviewIndexes(rows, groupedErrors) {
  return new Set(rows.map((_, index) => index).filter((index) => !groupedErrors.has(index)));
}

export function previewSelectionSummary(rows, groupedErrors, selectedIndexes = new Set()) {
  const validIndexes = validPreviewIndexes(rows, groupedErrors);
  return {
    total: rows.length,
    valid: validIndexes.size,
    errorRows: groupedErrors.size,
    selectedValid: [...selectedIndexes].filter((index) => validIndexes.has(index)).length,
  };
}

export function selectedPreviewRows(rows, groupedErrors, selectedIndexes = new Set()) {
  const validIndexes = validPreviewIndexes(rows, groupedErrors);
  return rows.filter((_, index) => validIndexes.has(index) && selectedIndexes.has(index));
}

function allValidPreviewRows(rows, groupedErrors) {
  const validIndexes = validPreviewIndexes(rows, groupedErrors);
  return rows.filter((_, index) => validIndexes.has(index));
}

function renderPreviewSummary(rows, groupedErrors, selectedIndexes) {
  const summary = previewSelectionSummary(rows, groupedErrors, selectedIndexes);
  return `
    <span>전체 ${summary.total}행</span>
    <span>정상 ${summary.valid}행</span>
    <span>오류 ${summary.errorRows}행</span>
    <span>선택 ${summary.selectedValid}행</span>
  `;
}

function updatePreviewActions(overlay, rows, groupedErrors, selectedIndexes) {
  const summary = previewSelectionSummary(rows, groupedErrors, selectedIndexes);
  overlay.querySelector("[data-preview-summary]").innerHTML = renderPreviewSummary(
    rows,
    groupedErrors,
    selectedIndexes,
  );
  overlay.querySelector("[data-action='preview-save-selected']").disabled = summary.selectedValid === 0;
  overlay.querySelector("[data-action='preview-save-all']").disabled = summary.valid === 0;
}

function renderPreviewRows(rows, groupedErrors, selectedIndexes = new Set()) {
  if (!rows.length) {
    return `<p class="empty-note">미리보기할 행이 없습니다.</p>`;
  }

  return `
    <div class="table-wrap preview-table-wrap">
      <table class="data-table preview-table">
        <thead>
          <tr>
            <th>선택</th>
            <th>No</th>
            <th>상태</th>
            <th>소파트</th>
            <th>대업무</th>
            <th>세부업무</th>
            <th>오류</th>
          </tr>
        </thead>
        <tbody>
          ${rows.map((row, index) => {
            const errors = groupedErrors.get(index) || [];
            const isValid = errors.length === 0;
            return `
              <tr class="${isValid ? "" : "invalid-row"}">
                <td>
                  <input
                    type="checkbox"
                    data-preview-row-select="${index}"
                    ${isValid ? "" : "disabled"}
                    ${isValid && selectedIndexes.has(index) ? "checked" : ""}
                    aria-label="${index + 1}행 선택"
                  >
                </td>
                <td>${index + 1}</td>
                <td>${badge(isValid ? "정상" : "오류", isValid ? "neutral" : "danger")}</td>
                <td>${escapeHtml(row.sub_part || "-")}</td>
                <td>${escapeHtml(row.major_task || "-")}</td>
                <td>${escapeHtml(row.detail_task || "-")}</td>
                <td>${errors.map((error) => escapeHtml(error.message)).join("<br>") || "-"}</td>
              </tr>
            `;
          }).join("")}
        </tbody>
      </table>
    </div>
  `;
}

function normalizeClipboardPayload(payload = {}) {
  if (typeof payload === "string") {
    return { text: payload, html: "" };
  }
  return {
    text: payload.text || "",
    html: payload.html || "",
  };
}

function openPastePreviewModal(initialPayload, questions, organizationId, onSaveRows) {
  closePastePreview();
  let currentClipboardPayload = normalizeClipboardPayload(initialPayload);
  const overlay = document.createElement("div");
  overlay.className = "modal-overlay";
  overlay.id = "paste-preview-modal";
  overlay.innerHTML = `
    <section class="modal wide-modal" role="dialog" aria-modal="true" aria-labelledby="paste-preview-title">
      <header class="modal-header">
        <div>
          <h2 id="paste-preview-title">Excel 붙여넣기 미리보기</h2>
          <p>소파트, 대업무, 세부업무만 검증하고 정상 행만 업로드합니다.</p>
        </div>
        <button class="icon-button" type="button" aria-label="닫기" title="닫기">×</button>
      </header>
      <div class="paste-preview-body">
        <div class="excel-paste-grid" data-paste-dropzone tabindex="0" role="textbox" aria-label="Excel 붙여넣기 영역">
          <div class="excel-paste-grid-header">
            <span>소파트</span>
            <span>대업무</span>
            <span>세부업무</span>
          </div>
          <div class="excel-paste-grid-row">
            <span></span>
            <span></span>
            <span></span>
          </div>
          <div class="excel-paste-grid-row">
            <span></span>
            <span></span>
            <span></span>
          </div>
        </div>
        <div class="preview-summary" data-preview-summary>
          <span>전체 0행</span>
          <span>정상 0행</span>
          <span>오류 0행</span>
          <span>선택 0행</span>
        </div>
        <div data-preview-result>${renderPreviewRows([], new Map())}</div>
      </div>
      <div class="modal-actions">
        <button type="button" class="secondary-button" data-action="cancel">취소</button>
        <button type="button" class="secondary-button" data-action="preview-validate">미리보기</button>
        <button type="button" class="secondary-button" data-action="preview-save-selected" disabled>선택 행 저장</button>
        <button type="button" class="primary-button" data-action="preview-save-all" disabled>전체 정상 행 저장</button>
      </div>
    </section>
  `;

  let currentRows = [];
  let currentGroupedErrors = new Map();
  let selectedIndexes = new Set();

  async function validatePreview() {
    currentRows = parseClipboardToTasks(currentClipboardPayload, questions, { organizationId });
    const result = currentRows.length
      ? await fetchJson("/api/tasks/validate", {
        method: "POST",
        body: JSON.stringify({ rows: currentRows }),
      })
      : { errors: [] };
    currentGroupedErrors = groupValidationErrors(result.errors || []);
    selectedIndexes = validPreviewIndexes(currentRows, currentGroupedErrors);
    overlay.querySelector("[data-preview-result]").innerHTML = renderPreviewRows(
      currentRows,
      currentGroupedErrors,
      selectedIndexes,
    );
    updatePreviewActions(overlay, currentRows, currentGroupedErrors, selectedIndexes);
  }

  overlay.addEventListener("click", async (event) => {
    if (event.target === overlay || event.target.closest(".icon-button, [data-action='cancel']")) {
      closePastePreview();
      return;
    }
    if (event.target.closest("[data-action='preview-validate']")) {
      await validatePreview();
      return;
    }
    if (event.target.closest("[data-action='preview-save-selected']")) {
      const validRows = selectedPreviewRows(currentRows, currentGroupedErrors, selectedIndexes);
      await onSaveRows(validRows);
      closePastePreview();
      return;
    }
    if (event.target.closest("[data-action='preview-save-all']")) {
      const validRows = allValidPreviewRows(currentRows, currentGroupedErrors);
      await onSaveRows(validRows);
      closePastePreview();
    }
  });
  overlay.addEventListener("change", (event) => {
    const checkbox = event.target.closest("[data-preview-row-select]");
    if (!checkbox) {
      return;
    }
    const rowIndex = Number(checkbox.dataset.previewRowSelect);
    if (checkbox.checked) {
      selectedIndexes.add(rowIndex);
    } else {
      selectedIndexes.delete(rowIndex);
    }
    updatePreviewActions(overlay, currentRows, currentGroupedErrors, selectedIndexes);
  });
  overlay.querySelector("[data-paste-dropzone]").addEventListener("paste", async (event) => {
    const html = event.clipboardData?.getData("text/html") || "";
    const text = event.clipboardData?.getData("text/plain") || "";
    if (!html && !text) {
      return;
    }
    event.preventDefault();
    currentClipboardPayload = { html, text };
    await validatePreview();
  });
  bindModalAccessibility(overlay, closePastePreview);

  document.body.append(overlay);
  if (currentClipboardPayload.html.trim() || currentClipboardPayload.text.trim()) {
    validatePreview();
  } else {
    overlay.querySelector("[data-paste-dropzone]").focus();
  }
}

function openApprovalConfirmModal(rows, onConfirm) {
  closeApprovalConfirm();
  const summary = classificationSummary(rows);
  const overlay = document.createElement("div");
  overlay.className = "modal-overlay";
  overlay.id = "approval-confirm-modal";
  overlay.innerHTML = `
    <section class="modal" role="dialog" aria-modal="true" aria-labelledby="approval-confirm-title">
      <header class="modal-header">
        <div>
          <h2 id="approval-confirm-title">승인 요청 확인</h2>
          <p>검증이 완료된 현재 파트 데이터를 승인 라인으로 제출합니다.</p>
        </div>
        <button class="icon-button" type="button" aria-label="닫기" title="닫기">×</button>
      </header>
      <div class="paste-preview-body">
        <div class="preview-summary">
          <span>전체 ${summary.total}건</span>
          <span>기밀 ${summary.confidential}건</span>
          <span>국가핵심 ${summary.nationalTech}건</span>
          <span>Compliance ${summary.compliance}건</span>
          <span>통합판정 ${summary.integrated}건</span>
        </div>
      </div>
      <div class="modal-actions">
        <button type="button" class="secondary-button" data-action="cancel">취소</button>
        <button type="button" class="primary-button" data-action="confirm-approval">승인 요청</button>
      </div>
    </section>
  `;
  overlay.addEventListener("click", async (event) => {
    if (event.target === overlay || event.target.closest(".icon-button, [data-action='cancel']")) {
      closeApprovalConfirm();
      return;
    }
    if (event.target.closest("[data-action='confirm-approval']")) {
      await onConfirm();
      closeApprovalConfirm();
    }
  });
  bindModalAccessibility(overlay, closeApprovalConfirm);
  document.body.append(overlay);
}

async function openExcelPreviewModal(file, orgId, onSaveRows) {
  closePastePreview();
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch(`/api/tasks/import/preview?org_id=${orgId}`, {
    method: "POST",
    headers: formDataHeaders(),
    body: formData,
  });
  if (!response.ok) {
    throw new Error(`Excel Import 미리보기 실패: ${response.status}`);
  }
  const result = await response.json();
  const rows = result.rows || [];
  const groupedErrors = groupValidationErrors(result.errors || []);
  let selectedIndexes = validPreviewIndexes(rows, groupedErrors);
  const overlay = document.createElement("div");
  overlay.className = "modal-overlay";
  overlay.id = "paste-preview-modal";
  overlay.innerHTML = `
    <section class="modal wide-modal" role="dialog" aria-modal="true" aria-labelledby="excel-preview-title">
      <header class="modal-header">
        <div>
          <h2 id="excel-preview-title">Excel Import 미리보기</h2>
          <p>소파트, 대업무, 세부업무만 검증하고 정상 행만 업로드합니다.</p>
        </div>
        <button class="icon-button" type="button" aria-label="닫기" title="닫기">×</button>
      </header>
      <div class="paste-preview-body">
        <div class="preview-summary" data-preview-summary>
          ${renderPreviewSummary(rows, groupedErrors, selectedIndexes)}
        </div>
        <div data-preview-result>${renderPreviewRows(rows, groupedErrors, selectedIndexes)}</div>
      </div>
      <div class="modal-actions">
        <button type="button" class="secondary-button" data-action="cancel">취소</button>
        <button type="button" class="secondary-button" data-action="preview-save-selected" ${result.valid_count ? "" : "disabled"}>선택 행 저장</button>
        <button type="button" class="primary-button" data-action="preview-save-all" ${result.valid_count ? "" : "disabled"}>전체 정상 행 저장</button>
      </div>
    </section>
  `;
  overlay.addEventListener("click", async (event) => {
    if (event.target === overlay || event.target.closest(".icon-button, [data-action='cancel']")) {
      closePastePreview();
      return;
    }
    if (event.target.closest("[data-action='preview-save-selected']")) {
      const validRows = selectedPreviewRows(rows, groupedErrors, selectedIndexes);
      await onSaveRows(validRows);
      closePastePreview();
      return;
    }
    if (event.target.closest("[data-action='preview-save-all']")) {
      const validRows = allValidPreviewRows(rows, groupedErrors);
      await onSaveRows(validRows);
      closePastePreview();
    }
  });
  overlay.addEventListener("change", (event) => {
    const checkbox = event.target.closest("[data-preview-row-select]");
    if (!checkbox) {
      return;
    }
    const rowIndex = Number(checkbox.dataset.previewRowSelect);
    if (checkbox.checked) {
      selectedIndexes.add(rowIndex);
    } else {
      selectedIndexes.delete(rowIndex);
    }
    updatePreviewActions(overlay, rows, groupedErrors, selectedIndexes);
  });
  updatePreviewActions(overlay, rows, groupedErrors, selectedIndexes);
  bindModalAccessibility(overlay, closePastePreview);
  document.body.append(overlay);
}

function renderRows(tasks, groupedErrors = new Map(), currentUser = null, rejection = null) {
  return tasks.map((task, index) => {
    const rowClasses = [
      groupedErrors.has(index) ? "invalid-row" : "",
      isRejectedTask(task, rejection) ? "rejected-review-row" : "",
    ].filter(Boolean).join(" ");
    return `
    <tr data-task-id="${task.id}" data-row-index="${index}" class="${rowClasses}">
      <td class="sticky-col sticky-no">${index + 1}</td>
      ${[
        ["sub_part", escapeHtml(task.sub_part || "-"), "sticky-col sticky-sub-part"],
        ["major_task", escapeHtml(task.major_task), "sticky-col sticky-major-task"],
        ["detail_task", escapeHtml(task.detail_task), "sticky-col sticky-detail-task"],
      ].map(([field, value, stickyClass]) => {
        const hasError = (groupedErrors.get(index) || []).some((error) => error.field === field);
        return `<td data-field="${field}" class="${stickyClass} ${hasError ? "cell-error" : ""}">${value}</td>`;
      }).join("")}
      <td>${badge(task.is_confidential ? "기밀" : "비기밀", task.is_confidential ? "danger" : "neutral")}</td>
      <td>${badge(task.is_national_tech ? "해당" : "비해당", task.is_national_tech ? "danger" : "neutral")}</td>
      <td>${badge(task.is_compliance ? "해당" : "비해당", task.is_compliance ? "warning" : "neutral")}</td>
      <td>${escapeHtml(assigneeSummary(task))}</td>
      <td>${badge(escapeHtml(task.status), statusTone(task.status))}</td>
      <td class="row-actions">
        ${canDeleteTask(task, currentUser)
          ? `<button type="button" class="secondary-button" data-delete-task="${task.id}">삭제</button>`
          : `<span class="muted-text">-</span>`}
      </td>
    </tr>
  `;
  }).join("");
}

function renderValidationPanel(errors) {
  if (!errors.length) {
    return "";
  }
  return `
    <div class="validation-panel" role="alert">
      <div>
        <strong>검증 오류 ${errors.length}건</strong>
        <span>오류 셀을 확인한 뒤 수정해 주세요.</span>
      </div>
      <button type="button" class="secondary-button" data-action="jump-first-error">첫 오류 이동</button>
      <ul>
        ${errors.slice(0, 8).map((error) => `
          <li>${error.row_index + 1}행 · ${escapeHtml(error.field)} · ${escapeHtml(error.message)}</li>
        `).join("")}
      </ul>
    </div>
  `;
}

function renderUploadedBlockPanel(count) {
  return `
    <div class="validation-panel" role="alert">
      <div>
        <strong>분류 저장 필요 ${count}건</strong>
        <span>Excel Import 또는 붙여넣기로 업로드한 행은 행을 열어 웹에서 분류를 저장한 뒤 승인 요청할 수 있습니다.</span>
      </div>
    </div>
  `;
}

export function hasTaskReviewComments(rejection) {
  return Array.isArray(rejection?.task_reviews) && rejection.task_reviews.some((review) => (
    review.comment || review.decision
  ));
}

export function hasRejectedTaskReviews(rejection) {
  return Array.isArray(rejection?.task_reviews) && rejection.task_reviews.some((review) => (
    review.decision === "REJECTED"
  ));
}

export function filterRejectedTasks(tasks, rejection) {
  const rejectedTaskIds = new Set((rejection?.task_reviews || [])
    .filter((review) => review.decision === "REJECTED")
    .map((review) => Number(review.task_id)));
  return tasks.filter((task) => rejectedTaskIds.has(Number(task.id)));
}

export function isRejectedTask(task, rejection) {
  return (rejection?.task_reviews || []).some((review) => (
    Number(review.task_id) === Number(task.id) && review.decision === "REJECTED"
  ));
}

export function prioritizeRejectedTasks(tasks, rejection) {
  const rejected = tasks.filter((task) => isRejectedTask(task, rejection));
  const rest = tasks.filter((task) => !isRejectedTask(task, rejection));
  return [...rejected, ...rest];
}

function reviewDecisionLabel(decision) {
  return decision === "REJECTED" ? "반려" : "승인";
}

function renderRejectionReviewTable(rejection) {
  if (!hasTaskReviewComments(rejection)) {
    return "";
  }
  return `
    <div class="rejection-review-panel">
      <table class="compact-table rejection-review-table">
        <thead>
          <tr>
            <th>항목</th>
            <th>검토결과</th>
            <th>검토의견</th>
            <th>검토자</th>
          </tr>
        </thead>
        <tbody>
          ${rejection.task_reviews.map((review) => `
            <tr>
              <td>${escapeHtml(review.major_task || `#${review.task_id}`)}</td>
              <td>${reviewDecisionLabel(review.decision)}</td>
              <td>${escapeHtml(review.comment || "-")}</td>
              <td>${escapeHtml(review.reviewer_employee_id || "-")}</td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    </div>
  `;
}

function headerWithTooltip(label, key, tooltips) {
  const tooltip = tooltips[key];
  if (!tooltip) {
    return label;
  }
  return `${label} <span class="info-dot" title="${escapeHtml(tooltip)}" aria-label="${escapeHtml(tooltip)}">(i)</span>`;
}

export function canDeleteTask(task, user) {
  if (!task || !user) {
    return false;
  }
  return user.role === "ADMIN" || task.created_by_employee_id === user.employee_id;
}

export async function renderSpreadsheet(container, options = {}) {
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
  const orgId = Number(selectedOrganization.id || orgIdOf(currentUser));
  const [tasks, questions, tooltipRows, deadline, rejection, partStatus, partMembers] = await Promise.all([
    fetchJson(`/api/tasks?org_id=${orgId}`),
    fetchJson("/api/questions"),
    fetchJson("/api/tooltips"),
    fetchJson("/api/settings/deadline"),
    fetchJson(`/api/tasks/rejection?org_id=${orgId}`),
    fetchJson(`/api/tasks/status?org_id=${orgId}`),
    fetchJson(`/api/part-members?org_id=${orgId}`),
  ]);
  const tooltips = tooltipMap(tooltipRows);
  const currentPartName = selectedOrganization.part_name || "";
  const partMemberCandidates = partMembers.filter((member) => member.part_name === currentPartName);
  let showRejectedOnly = false;
  const rejectedTasks = filterRejectedTasks(tasks, rejection);
  const prioritizedTasks = prioritizeRejectedTasks(tasks, rejection);

  function visibleTasks() {
    return showRejectedOnly ? rejectedTasks : prioritizedTasks;
  }

  container.innerHTML = `
    <section class="workspace">
      <div class="section-header">
        <div>
          <h2>데이터 입력</h2>
          <p>${escapeHtml(orgPathOfOrganization(selectedOrganization) || orgPathOf(currentUser))}</p>
        </div>
        <div class="toolbar">
          ${renderOrganizationSelector(editableOrganizations, selectedOrganization)}
          <button type="button" class="secondary-button" data-action="add-row">행 추가</button>
          <button type="button" class="secondary-button" data-action="save-all">전체 저장</button>
          <button type="button" class="secondary-button" data-action="download-template">양식</button>
          <label class="secondary-button file-button" for="task-excel-import">Excel Import
            <input id="task-excel-import" type="file" accept=".xlsx" data-action="excel-import">
          </label>
        <button type="button" class="secondary-button" data-action="paste-preview">Excel 붙여넣기</button>
          <button type="button" class="primary-button" data-action="submit-approval">승인 요청</button>
        </div>
      </div>
      ${rejection.has_rejection ? `
        <div class="alert-banner danger">
          <strong>반려 사유</strong>
          <span>${escapeHtml(rejection.reject_reason)}</span>
        </div>
        ${renderRejectionReviewTable(rejection)}
      ` : ""}
      <div class="status-strip">
        <span>기밀 문항 ${questions.confidential.length}개</span>
        <span>국가핵심기술 문항 ${questions.national_tech.length}개</span>
        <span>${formatDday(deadline)}</span>
        <span>전체 ${partStatus.total_tasks}건</span>
        <span>UPLOADED ${partStatus.status_counts.UPLOADED || 0}건</span>
        <span>DRAFT ${partStatus.status_counts.DRAFT}건</span>
        ${hasRejectedTaskReviews(rejection) ? `
          <button type="button" class="secondary-button compact-filter-button" data-action="toggle-rejected-only" aria-pressed="false">
            반려 항목만 ${rejectedTasks.length}건
          </button>
        ` : ""}
      </div>
      <div class="filter-summary" data-filter-summary></div>
      <div data-validation-panel></div>
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th class="sticky-col sticky-no">No</th>
              <th class="sticky-col sticky-sub-part">${headerWithTooltip("소파트", "sub_part", tooltips)}</th>
              <th class="sticky-col sticky-major-task">${headerWithTooltip("대업무", "major_task", tooltips)}</th>
              <th class="sticky-col sticky-detail-task">${headerWithTooltip("세부업무", "detail_task", tooltips)}</th>
              <th>${headerWithTooltip("기밀", "confidential", tooltips)}</th>
              <th>${headerWithTooltip("국가핵심기술", "national_tech", tooltips)}</th>
              <th>${headerWithTooltip("Compliance", "compliance", tooltips)}</th>
              <th>담당자</th>
              <th>상태</th>
              <th>작업</th>
            </tr>
          </thead>
          <tbody data-task-table-body>${renderRows(visibleTasks(), new Map(), currentUser, rejection)}</tbody>
        </table>
      </div>
    </section>
  `;

  async function saveTask(payload, task = {}) {
    let savedTask;
    if (task.id) {
      savedTask = await fetchJson(`/api/tasks/${task.id}`, {
        method: "PUT",
        body: JSON.stringify(payload),
      });
    } else {
      savedTask = await fetchJson("/api/tasks", {
        method: "POST",
        body: JSON.stringify({
          organization_id: orgId,
          ...payload,
        }),
      });
    }
    await renderSpreadsheet(container, { ...options, selectedOrgId: orgId });
    return savedTask;
  }

  function renderTaskTable(groupedErrors = new Map()) {
    container.querySelector("[data-task-table-body]").innerHTML = renderRows(visibleTasks(), groupedErrors, currentUser, rejection);
    const summary = container.querySelector("[data-filter-summary]");
    summary.innerHTML = showRejectedOnly
      ? `<span>반려 검토된 ${rejectedTasks.length}개 항목만 표시 중입니다.</span>`
      : "";
    const toggle = container.querySelector("[data-action='toggle-rejected-only']");
    if (toggle) {
      toggle.setAttribute("aria-pressed", String(showRejectedOnly));
      toggle.textContent = showRejectedOnly ? `전체 보기 ${tasks.length}건` : `반려 항목만 ${rejectedTasks.length}건`;
    }
  }

  async function saveImportedRows(rows) {
    if (!rows.length) {
      return;
    }
    await fetchJson("/api/tasks/bulk", {
      method: "POST",
      body: JSON.stringify(rows.map((row) => ({
        organization_id: orgId,
        ...row,
      }))),
    });
  }

  function openClipboardPreview(payload = {}) {
    openPastePreviewModal(payload, questions, orgId, async (rows) => {
      await saveImportedRows(rows);
      await renderSpreadsheet(container, { ...options, selectedOrgId: orgId });
    });
  }

  container.querySelector("[data-action='add-row']").addEventListener("click", () => {
    openTaskModal({}, saveTask, questions, { partMembers: partMemberCandidates });
  });

  container.querySelector("[data-action='select-work-org']")?.addEventListener("change", async (event) => {
    await renderSpreadsheet(container, { ...options, selectedOrgId: Number(event.target.value) });
  });

  container.querySelector("[data-action='paste-preview']").addEventListener("click", () => {
    openClipboardPreview();
  });

  container.querySelector("[data-action='save-all']").addEventListener("click", async () => {
    const result = await fetchJson("/api/tasks/validate", {
      method: "POST",
      body: JSON.stringify({ rows: tasks.map((task) => ({ ...task, organization_id: orgId })) }),
    });
    const errors = result.errors || [];
    const groupedErrors = groupValidationErrors(errors);
    renderTaskTable(groupedErrors);
    container.querySelector("[data-validation-panel]").innerHTML = errors.length
      ? renderValidationPanel(errors)
      : `<div class="validation-panel success-panel" role="status"><strong>전체 저장 상태 확인 완료</strong><span>현재 행은 서버에 저장되어 있으며 승인 요청할 수 있습니다.</span></div>`;
    container.querySelector("[data-action='jump-first-error']")?.addEventListener("click", () => {
      const rowIndex = firstErrorRow(errors);
      container.querySelector(`[data-row-index="${rowIndex}"]`)?.scrollIntoView({ block: "center" });
    });
  });

  container.querySelector("[data-action='toggle-rejected-only']")?.addEventListener("click", () => {
    showRejectedOnly = !showRejectedOnly;
    renderTaskTable();
  });

  container.querySelector("[data-action='download-template']").addEventListener("click", () => {
    window.location.href = "/api/tasks/template";
  });

  container.querySelector("[data-action='excel-import']").addEventListener("change", async (event) => {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }
    try {
      await openExcelPreviewModal(file, orgId, async (validRows) => {
        await saveImportedRows(validRows);
        await renderSpreadsheet(container, { ...options, selectedOrgId: orgId });
      });
    } catch (error) {
      container.querySelector("[data-validation-panel]").innerHTML = `
        <div class="validation-panel" role="alert"><strong>Excel Import 실패</strong><span>${escapeHtml(error.message)}</span></div>
      `;
    }
    event.target.value = "";
  });

  container.querySelector("[data-action='submit-approval']").addEventListener("click", async () => {
    const uploadedCount = tasks.filter((task) => task.status === "UPLOADED").length;
    if (uploadedCount) {
      container.querySelector("[data-validation-panel]").innerHTML = renderUploadedBlockPanel(uploadedCount);
      return;
    }
    const result = await fetchJson("/api/tasks/validate", {
      method: "POST",
      body: JSON.stringify({ rows: tasks.map((task) => ({ ...task, organization_id: orgId })) }),
    });
    const errors = result.errors || [];
    const groupedErrors = groupValidationErrors(errors);
    renderTaskTable(groupedErrors);
    container.querySelector("[data-validation-panel]").innerHTML = renderValidationPanel(errors);
    if (errors.length) {
      container.querySelector("[data-action='jump-first-error']")?.addEventListener("click", () => {
        const rowIndex = firstErrorRow(errors);
        container.querySelector(`[data-row-index="${rowIndex}"]`)?.scrollIntoView({ block: "center" });
      });
      return;
    }
    openApprovalConfirmModal(tasks, async () => {
      await fetchJson(`/api/approvals/submit?org_id=${orgId}`, { method: "POST" });
      await renderSpreadsheet(container, { ...options, selectedOrgId: orgId });
    });
  });

  container.addEventListener("paste", (event) => {
    const html = event.clipboardData?.getData("text/html") || "";
    const text = event.clipboardData?.getData("text/plain") || "";
    if (!html.includes("<table") && !text.includes("\t")) {
      return;
    }
    event.preventDefault();
    openClipboardPreview({ html, text });
  });

  container.querySelector("[data-task-table-body]").addEventListener("click", async (event) => {
    const deleteButton = event.target.closest("[data-delete-task]");
    if (deleteButton) {
      event.stopPropagation();
      const task = tasks.find((item) => String(item.id) === deleteButton.dataset.deleteTask);
      const confirmed = globalThis.confirm?.(deleteConfirmationMessage(task)) ?? true;
      if (!confirmed) {
        return;
      }
      try {
        await fetchJson(`/api/tasks/${deleteButton.dataset.deleteTask}`, { method: "DELETE" });
        await renderSpreadsheet(container, { ...options, selectedOrgId: orgId });
      } catch (deleteError) {
        container.querySelector("[data-validation-panel]").innerHTML = renderActionError("삭제 실패", deleteError.message);
      }
      return;
    }
    const row = event.target.closest("tr[data-task-id]");
    if (row) {
      const task = tasks.find((item) => String(item.id) === row.dataset.taskId);
      openTaskModal(task, saveTask, questions, { partMembers: partMemberCandidates });
    }
  });
}
