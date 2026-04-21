import { fetchJson } from "./api.js";
import { parseTsvToTasks } from "./clipboard.js";
import { formatDday } from "./deadlineAdmin.js?v=20260421-p1b";
import { bindModalAccessibility } from "./modalAccessibility.js?v=20260421-p1b";
import { openTaskModal } from "./form.js";
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

function closePastePreview() {
  document.querySelector("#paste-preview-modal")?.remove();
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

function renderPreviewRows(rows, groupedErrors) {
  if (!rows.length) {
    return `<p class="empty-note">미리보기할 행이 없습니다.</p>`;
  }

  return `
    <div class="table-wrap preview-table-wrap">
      <table class="data-table preview-table">
        <thead>
          <tr>
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

function openPastePreviewModal(initialText, questions, onSaveRows) {
  closePastePreview();
  const overlay = document.createElement("div");
  overlay.className = "modal-overlay";
  overlay.id = "paste-preview-modal";
  overlay.innerHTML = `
    <section class="modal wide-modal" role="dialog" aria-modal="true" aria-labelledby="paste-preview-title">
      <header class="modal-header">
        <div>
          <h2 id="paste-preview-title">붙여넣기 미리보기</h2>
          <p>Excel에서 복사한 TSV 데이터를 검증하고 정상 행만 저장합니다.</p>
        </div>
        <button class="icon-button" type="button" aria-label="닫기" title="닫기">×</button>
      </header>
      <div class="paste-preview-body">
        <label for="paste-preview-text">TSV 데이터
          <textarea id="paste-preview-text" name="paste_preview_text" class="preview-textarea">${escapeHtml(initialText)}</textarea>
        </label>
        <div class="preview-summary" data-preview-summary>
          <span>전체 0행</span>
          <span>정상 0행</span>
          <span>오류 0행</span>
        </div>
        <div data-preview-result>${renderPreviewRows([], new Map())}</div>
      </div>
      <div class="modal-actions">
        <button type="button" class="secondary-button" data-action="cancel">취소</button>
        <button type="button" class="secondary-button" data-action="preview-validate">미리보기</button>
        <button type="button" class="primary-button" data-action="preview-save" disabled>정상 행 저장</button>
      </div>
    </section>
  `;

  let currentRows = [];
  let currentGroupedErrors = new Map();

  async function validatePreview() {
    const text = overlay.querySelector("#paste-preview-text").value;
    currentRows = parseTsvToTasks(text, questions, { organizationId: 1 });
    const result = currentRows.length
      ? await fetchJson("/api/tasks/validate", {
        method: "POST",
        body: JSON.stringify({ rows: currentRows }),
      })
      : { errors: [] };
    currentGroupedErrors = groupValidationErrors(result.errors || []);
    const validCount = currentRows.filter((_, index) => !currentGroupedErrors.has(index)).length;
    const errorRowCount = currentGroupedErrors.size;
    overlay.querySelector("[data-preview-summary]").innerHTML = `
      <span>전체 ${currentRows.length}행</span>
      <span>정상 ${validCount}행</span>
      <span>오류 ${errorRowCount}행</span>
    `;
    overlay.querySelector("[data-preview-result]").innerHTML = renderPreviewRows(currentRows, currentGroupedErrors);
    overlay.querySelector("[data-action='preview-save']").disabled = validCount === 0;
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
    if (event.target.closest("[data-action='preview-save']")) {
      const validRows = currentRows.filter((_, index) => !currentGroupedErrors.has(index));
      for (const row of validRows) {
        await onSaveRows(row);
      }
      closePastePreview();
    }
  });
  bindModalAccessibility(overlay, closePastePreview);

  document.body.append(overlay);
  if (initialText.trim()) {
    validatePreview();
  } else {
    overlay.querySelector("#paste-preview-text").focus();
  }
}

function renderRows(tasks, groupedErrors = new Map(), currentUser = null, rejection = null) {
  return tasks.map((task, index) => {
    const rowClasses = [
      groupedErrors.has(index) ? "invalid-row" : "",
      isRejectedTask(task, rejection) ? "rejected-review-row" : "",
    ].filter(Boolean).join(" ");
    return `
    <tr data-task-id="${task.id}" data-row-index="${index}" class="${rowClasses}">
      <td>${index + 1}</td>
      ${[
        ["sub_part", escapeHtml(task.sub_part || "-")],
        ["major_task", escapeHtml(task.major_task)],
        ["detail_task", escapeHtml(task.detail_task)],
      ].map(([field, value]) => {
        const hasError = (groupedErrors.get(index) || []).some((error) => error.field === field);
        return `<td data-field="${field}" class="${hasError ? "cell-error" : ""}">${value}</td>`;
      }).join("")}
      <td>${badge(task.is_confidential ? "기밀" : "비기밀", task.is_confidential ? "danger" : "neutral")}</td>
      <td>${badge(task.is_national_tech ? "해당" : "비해당", task.is_national_tech ? "danger" : "neutral")}</td>
      <td>${badge(task.is_compliance ? "해당" : "비해당", task.is_compliance ? "warning" : "neutral")}</td>
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

export async function renderSpreadsheet(container) {
  const [tasks, questions, tooltipRows, deadline, rejection, partStatus, currentUser] = await Promise.all([
    fetchJson("/api/tasks"),
    fetchJson("/api/questions"),
    fetchJson("/api/tooltips"),
    fetchJson("/api/settings/deadline"),
    fetchJson("/api/tasks/rejection?org_id=1"),
    fetchJson("/api/tasks/status?org_id=1"),
    fetchJson("/api/auth/me"),
  ]);
  const tooltips = tooltipMap(tooltipRows);
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
          <p>파트 업무를 행 단위로 확인하고 상세 내용을 편집합니다.</p>
        </div>
        <div class="toolbar">
          <button type="button" class="secondary-button" data-action="add-row">행 추가</button>
          <button type="button" class="secondary-button" data-action="download-template">양식</button>
          <label class="secondary-button file-button" for="task-excel-import">Excel Import
            <input id="task-excel-import" type="file" accept=".xlsx" data-action="excel-import">
          </label>
          <button type="button" class="secondary-button" data-action="paste-preview">붙여넣기</button>
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
              <th>No</th>
              <th>${headerWithTooltip("소파트", "sub_part", tooltips)}</th>
              <th>${headerWithTooltip("대업무", "major_task", tooltips)}</th>
              <th>${headerWithTooltip("세부업무", "detail_task", tooltips)}</th>
              <th>${headerWithTooltip("기밀", "confidential", tooltips)}</th>
              <th>${headerWithTooltip("국가핵심기술", "national_tech", tooltips)}</th>
              <th>${headerWithTooltip("Compliance", "compliance", tooltips)}</th>
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
    if (task.id) {
      await fetchJson(`/api/tasks/${task.id}`, {
        method: "PUT",
        body: JSON.stringify(payload),
      });
    } else {
      await fetchJson("/api/tasks", {
        method: "POST",
        body: JSON.stringify({
          organization_id: 1,
          ...payload,
        }),
      });
    }
    await renderSpreadsheet(container);
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

  async function savePastedRow(row) {
    await fetchJson("/api/tasks", {
      method: "POST",
      body: JSON.stringify(row),
    });
  }

  function openClipboardPreview(text = "") {
    openPastePreviewModal(text, questions, async (row) => {
      await savePastedRow(row);
      await renderSpreadsheet(container);
    });
  }

  container.querySelector("[data-action='add-row']").addEventListener("click", () => {
    openTaskModal({}, saveTask, questions);
  });

  container.querySelector("[data-action='paste-preview']").addEventListener("click", () => {
    openClipboardPreview();
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
    const formData = new FormData();
    formData.append("file", file);
    const response = await fetch("/api/tasks/import", { method: "POST", body: formData });
    if (!response.ok) {
      container.querySelector("[data-validation-panel]").innerHTML = `
        <div class="validation-panel" role="alert"><strong>Excel Import 실패</strong><span>${response.status}</span></div>
      `;
      return;
    }
    await renderSpreadsheet(container);
  });

  container.querySelector("[data-action='submit-approval']").addEventListener("click", async () => {
    const result = await fetchJson("/api/tasks/validate", {
      method: "POST",
      body: JSON.stringify({ rows: tasks }),
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
    await fetchJson("/api/approvals/submit?org_id=1", { method: "POST" });
    await renderSpreadsheet(container);
  });

  container.addEventListener("paste", (event) => {
    const text = event.clipboardData?.getData("text/plain") || "";
    if (!text.includes("\t")) {
      return;
    }
    event.preventDefault();
    openClipboardPreview(text);
  });

  container.querySelector("[data-task-table-body]").addEventListener("click", async (event) => {
    const deleteButton = event.target.closest("[data-delete-task]");
    if (deleteButton) {
      event.stopPropagation();
      await fetchJson(`/api/tasks/${deleteButton.dataset.deleteTask}`, { method: "DELETE" });
      await renderSpreadsheet(container);
      return;
    }
    const row = event.target.closest("tr[data-task-id]");
    if (row) {
      const task = tasks.find((item) => String(item.id) === row.dataset.taskId);
      openTaskModal(task, saveTask, questions);
    }
  });
}
