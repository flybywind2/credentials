import { fetchJson } from "./api.js";
import { bindModalAccessibility } from "./modalAccessibility.js?v=20260421-p1b";

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function badge(label, tone = "status") {
  return `<span class="badge ${tone}">${escapeHtml(label)}</span>`;
}

function statusTone(status) {
  return `status-${String(status || "draft").toLowerCase()}`;
}

function classificationBadge(value, positiveLabel, negativeLabel) {
  return badge(value ? positiveLabel : negativeLabel, value ? "danger" : "neutral");
}

function formatRequestedAt(value) {
  if (!value) {
    return "요청일 -";
  }
  return `요청일 ${String(value).replace("T", " ").slice(0, 16)}`;
}

function formatPlainDateTime(value) {
  return value ? String(value).replace("T", " ").slice(0, 16) : "-";
}

function approvalStatusTone(status) {
  if (status === "APPROVED") {
    return "status-approved";
  }
  if (status === "REJECTED") {
    return "danger";
  }
  if (status === "PENDING") {
    return "status-submitted";
  }
  return "neutral";
}

function renderApprovalStep(row) {
  return row.current_step && row.total_steps ? `${row.current_step}/${row.total_steps}` : "-";
}

function renderSubordinateStatusSummary(summary = {}) {
  const rows = Array.isArray(summary.rows) ? summary.rows : [];
  return `
    <section class="approval-status-panel">
      <div class="section-header part-member-header">
        <div>
          <h3>하위 조직 현황</h3>
          <p>${escapeHtml(summary.scope_label || "하위 조직 현황")}</p>
        </div>
      </div>
      <div class="table-wrap">
        <table class="data-table compact-table">
          <thead>
            <tr>
              <th>구분</th>
              <th>조직</th>
              <th>전체</th>
              <th>UPLOADED</th>
              <th>DRAFT</th>
              <th>SUBMITTED</th>
              <th>APPROVED</th>
              <th>REJECTED</th>
              <th>승인요청 상태</th>
              <th>단계</th>
              <th>최근 요청일</th>
            </tr>
          </thead>
          <tbody>
            ${rows.length ? rows.map((row) => `
              <tr>
                <td>${escapeHtml(row.unit_type_label || row.unit_type || "-")}</td>
                <td>${escapeHtml(row.display_name || "-")}</td>
                <td>${row.task_count || 0}</td>
                <td>${row.status_counts?.UPLOADED || 0}</td>
                <td>${row.status_counts?.DRAFT || 0}</td>
                <td>${row.status_counts?.SUBMITTED || 0}</td>
                <td>${row.status_counts?.APPROVED || 0}</td>
                <td>${row.status_counts?.REJECTED || 0}</td>
                <td>${badge(row.approval_status_label || "미요청", approvalStatusTone(row.approval_status))}</td>
                <td>${escapeHtml(renderApprovalStep(row))}</td>
                <td>${escapeHtml(formatPlainDateTime(row.latest_requested_at))}</td>
              </tr>
            `).join("") : `<tr><td colspan="11" class="muted-text">조회된 하위 조직이 없습니다.</td></tr>`}
          </tbody>
        </table>
      </div>
    </section>
  `;
}

export function validateTaskReviewPayload(tasks, reviews, action) {
  const taskIds = new Set(tasks.map((task) => Number(task.id)));
  const reviewIds = new Set(reviews.map((review) => Number(review.task_id)));
  if (taskIds.size !== reviewIds.size || [...taskIds].some((taskId) => !reviewIds.has(taskId))) {
    return { valid: false, message: "모든 항목에 승인 또는 반려를 체크해 주세요." };
  }
  if (reviews.some((review) => !["APPROVED", "REJECTED"].includes(review.decision))) {
    return { valid: false, message: "모든 항목에 승인 또는 반려를 체크해 주세요." };
  }
  if (action === "approve" && reviews.some((review) => review.decision !== "APPROVED")) {
    return { valid: false, message: "최종 승인하려면 모든 항목이 승인으로 체크되어야 합니다." };
  }
  const rejectedReviews = reviews.filter((review) => review.decision === "REJECTED");
  if (action === "reject" && rejectedReviews.length === 0) {
    return { valid: false, message: "반려하려면 최소 1개 항목을 반려로 체크해 주세요." };
  }
  if (rejectedReviews.some((review) => !String(review.comment || "").trim())) {
    return { valid: false, message: "반려 항목에는 의견을 입력해 주세요." };
  }
  return { valid: true, message: "" };
}

export function reviewCompletionAction(reviews) {
  return reviews.some((review) => review.decision === "REJECTED") ? "reject" : "approve";
}

function renderReviewControls(task) {
  return `
    <div class="review-choice-group" role="radiogroup" aria-label="${escapeHtml(task.major_task)} 검토 결과">
      <label>
        <input type="radio" name="task-review-${task.id}" value="APPROVED" checked>
        승인
      </label>
      <label>
        <input type="radio" name="task-review-${task.id}" value="REJECTED">
        반려
      </label>
    </div>
  `;
}

function renderTaskRows(tasks, reviewMode = false) {
  if (!tasks.length) {
    return `<tr><td colspan="${reviewMode ? 10 : 8}">조회된 업무가 없습니다.</td></tr>`;
  }

  return tasks.map((task, index) => `
    <tr data-task-id="${task.id}" ${reviewMode ? "data-task-review-row" : ""}>
      <td>${index + 1}</td>
      ${reviewMode ? `<td>${renderReviewControls(task)}</td>` : ""}
      ${reviewMode ? `<td><textarea id="task-review-comment-${task.id}" name="task_review_comment_${task.id}" class="review-comment" data-review-comment="${task.id}" aria-label="${escapeHtml(task.major_task)} 검토 의견" placeholder="반려 시 의견 필수"></textarea></td>` : ""}
      <td>${escapeHtml(task.sub_part || "-")}</td>
      <td>${escapeHtml(task.major_task)}</td>
      <td>${escapeHtml(task.detail_task)}</td>
      <td>${classificationBadge(task.is_confidential, "기밀", "비기밀")}</td>
      <td>${classificationBadge(task.is_national_tech, "해당", "비해당")}</td>
      <td>${badge(task.is_compliance ? "해당" : "비해당", task.is_compliance ? "warning" : "neutral")}</td>
      <td>${badge(task.status, statusTone(task.status))}</td>
    </tr>
  `).join("");
}

function collectTaskReviews(container) {
  return Array.from(container.querySelectorAll("[data-task-review-row]")).map((row) => {
    const taskId = Number(row.dataset.taskId);
    return {
      task_id: taskId,
      decision: row.querySelector(`input[name="task-review-${taskId}"]:checked`)?.value || "",
      comment: row.querySelector(`[data-review-comment="${taskId}"]`)?.value.trim() || "",
    };
  });
}

function renderReviewError(container, message) {
  container.querySelector("[data-review-error]").innerHTML = message
    ? `<div class="validation-panel" role="alert"><strong>검토 오류</strong><span>${escapeHtml(message)}</span></div>`
    : "";
}

function rejectReasonFromReviews(tasks, reviews) {
  return reviews
    .filter((review) => review.decision === "REJECTED")
    .map((review) => {
      const task = tasks.find((item) => Number(item.id) === Number(review.task_id));
      return `${task?.major_task || review.task_id}: ${review.comment}`;
    })
    .join("\n");
}

function renderTimeline(approval) {
  return `
    <ol class="approval-timeline">
      ${approval.steps.map((step) => `
        <li class="timeline-item ${step.status.toLowerCase()}">
          <strong>${step.step_order}. ${escapeHtml(step.approver_role)}</strong>
          <span>${escapeHtml(step.approver_name)} · ${escapeHtml(step.status)}</span>
        </li>
      `).join("")}
    </ol>
  `;
}

function openTaskReadOnlyModal(task) {
  document.querySelector("#readonly-task-modal")?.remove();
  const overlay = document.createElement("div");
  overlay.className = "modal-overlay";
  overlay.id = "readonly-task-modal";
  overlay.innerHTML = `
    <section class="modal" role="dialog" aria-modal="true" aria-labelledby="readonly-task-title">
      <header class="modal-header">
        <div>
          <h2 id="readonly-task-title">${escapeHtml(task.major_task)}</h2>
          <p>${escapeHtml(task.detail_task)}</p>
        </div>
        <button class="icon-button" type="button" aria-label="닫기" title="닫기">×</button>
      </header>
      <div class="readonly-grid">
        <div><span>소파트</span><strong>${escapeHtml(task.sub_part || "-")}</strong></div>
        <div><span>기밀</span><strong>${task.is_confidential ? "기밀" : "비기밀"}</strong></div>
        <div><span>기밀 데이터 유형</span><strong>${escapeHtml(task.conf_data_type || "-")}</strong></div>
        <div><span>기밀 소유자/사용자</span><strong>${escapeHtml(task.conf_owner_user || "-")}</strong></div>
        <div><span>국가핵심기술</span><strong>${task.is_national_tech ? "해당" : "비해당"}</strong></div>
        <div><span>국가핵심기술 데이터 유형</span><strong>${escapeHtml(task.ntech_data_type || "-")}</strong></div>
        <div><span>Compliance</span><strong>${task.is_compliance ? "해당" : "비해당"}</strong></div>
        <div><span>Compliance 데이터 유형</span><strong>${escapeHtml(task.comp_data_type || "-")}</strong></div>
        <div><span>보관 장소</span><strong>${escapeHtml(task.storage_location || "-")}</strong></div>
        <div><span>관련 메뉴</span><strong>${escapeHtml(task.related_menu || "-")}</strong></div>
      </div>
      <div class="modal-actions">
        <button type="button" class="secondary-button" data-action="cancel">닫기</button>
      </div>
    </section>
  `;
  overlay.addEventListener("click", (event) => {
    if (event.target === overlay || event.target.closest(".icon-button, [data-action='cancel']")) {
      overlay.remove();
    }
  });
  bindModalAccessibility(overlay, () => overlay.remove());
  document.body.append(overlay);
}

function openRejectModal(approvalId, onRejected, taskReviews = [], defaultReason = "") {
  document.querySelector("#reject-modal")?.remove();
  const overlay = document.createElement("div");
  overlay.className = "modal-overlay";
  overlay.id = "reject-modal";
  overlay.innerHTML = `
    <section class="modal" role="dialog" aria-modal="true" aria-labelledby="reject-title">
      <header class="modal-header">
        <div>
          <h2 id="reject-title">반려 사유</h2>
          <p>입력자가 수정할 수 있도록 사유를 남깁니다.</p>
        </div>
        <button class="icon-button" type="button" aria-label="닫기" title="닫기">×</button>
      </header>
      <div class="paste-preview-body">
        <label for="reject-reason">사유
          <textarea id="reject-reason" name="reject_reason" class="preview-textarea">${escapeHtml(defaultReason)}</textarea>
          <span class="field-error" data-error-for="reject_reason"></span>
        </label>
      </div>
      <div class="modal-actions">
        <button type="button" class="secondary-button" data-action="cancel">취소</button>
        <button type="button" class="primary-button" data-action="confirm-reject">반려</button>
      </div>
    </section>
  `;
  overlay.addEventListener("click", async (event) => {
    if (event.target === overlay || event.target.closest(".icon-button, [data-action='cancel']")) {
      overlay.remove();
      return;
    }
    if (event.target.closest("[data-action='confirm-reject']")) {
      const reason = overlay.querySelector("#reject-reason").value.trim();
      const error = overlay.querySelector("[data-error-for='reject_reason']");
      if (!reason) {
        error.textContent = "반려 사유는 필수입니다.";
        return;
      }
      await fetchJson(`/api/approvals/${approvalId}/reject`, {
        method: "POST",
        body: JSON.stringify({ reject_reason: reason, task_reviews: taskReviews }),
      });
      overlay.remove();
      await onRejected();
    }
  });
  bindModalAccessibility(overlay, () => overlay.remove());
  document.body.append(overlay);
  overlay.querySelector("#reject-reason").focus();
}

async function renderApprovalList(container, context = {}) {
  if (context.navigateTo) {
    await context.navigateTo("approver");
    return;
  }
  await renderApproval(container, context);
}

async function approveApproval(approvalId, container, context = {}) {
  await fetchJson(`/api/approvals/${approvalId}/approve`, { method: "POST" });
  await renderApprovalList(container, context);
}

async function completeReviewedApproval(approvalId, container, tasks, context = {}) {
  const taskReviews = collectTaskReviews(container);
  const action = reviewCompletionAction(taskReviews);
  const validation = validateTaskReviewPayload(tasks, taskReviews, action);
  if (!validation.valid) {
    renderReviewError(container, validation.message);
    return;
  }
  if (action === "reject") {
    openRejectModal(
      approvalId,
      () => renderApprovalList(container, context),
      taskReviews,
      rejectReasonFromReviews(tasks, taskReviews),
    );
    return;
  }
  await fetchJson(`/api/approvals/${approvalId}/approve`, {
    method: "POST",
    body: JSON.stringify({ task_reviews: taskReviews }),
  });
  await renderApprovalList(container, context);
}

async function renderApprovalDetail(container, approvalId, context = {}) {
  const approval = await fetchJson(`/api/approvals/${approvalId}/history`);
  const tasks = await fetchJson(`/api/tasks?org_id=${approval.organization_id}`);

  container.innerHTML = `
    <section class="workspace">
      <div class="section-header">
        <div>
          <button type="button" class="secondary-button compact-button" data-action="back-to-approvals">목록</button>
          <h2>${escapeHtml(approval.part_name)} 승인 검토</h2>
          <p>${escapeHtml(approval.requester || "-")} · ${tasks.length}건 · ${approval.status} · ${formatRequestedAt(approval.requested_at)}</p>
        </div>
        <div class="approval-actions">
          <button type="button" class="primary-button" data-action="complete-detail">검토 완료</button>
        </div>
      </div>
      <div class="approval-detail">
        ${renderTimeline(approval)}
      </div>
      <div data-review-error></div>
      <div class="table-wrap">
        <table class="data-table review-table">
          <thead>
            <tr>
              <th>No</th>
              <th>검토</th>
              <th>의견</th>
              <th>소파트</th>
              <th>대업무</th>
              <th>세부업무</th>
              <th>기밀</th>
              <th>국가핵심기술</th>
              <th>Compliance</th>
              <th>상태</th>
            </tr>
          </thead>
          <tbody>${renderTaskRows(tasks, true)}</tbody>
        </table>
      </div>
    </section>
  `;

  container.querySelector("[data-action='back-to-approvals']").addEventListener("click", () => {
    renderApprovalList(container, context);
  });
  container.querySelector("[data-action='complete-detail']").addEventListener("click", () => {
    completeReviewedApproval(approvalId, container, tasks, context);
  });
  container.querySelectorAll("tbody tr[data-task-id]").forEach((row) => {
    row.addEventListener("click", (event) => {
      if (event.target.closest("input, textarea, label, button")) {
        return;
      }
      const task = tasks.find((item) => String(item.id) === row.dataset.taskId);
      openTaskReadOnlyModal(task);
    });
  });
}

export async function renderApproval(container, context = {}) {
  const approvalIdFromPath = context.params?.approvalId;
  if (approvalIdFromPath) {
    await renderApprovalDetail(container, approvalIdFromPath, context);
    return;
  }

  const [approvals, subordinateStatus] = await Promise.all([
    fetchJson("/api/approvals/pending"),
    fetchJson("/api/approvals/subordinate-status"),
  ]);
  container.innerHTML = `
    <section class="workspace">
      <div class="section-header">
        <div>
          <h2>승인 대기 목록</h2>
          <p>내 승인 차례인 파트 단위 요청을 검토합니다.</p>
        </div>
      </div>
      ${renderSubordinateStatusSummary(subordinateStatus)}
      <div class="approval-list">
        ${approvals.length ? approvals.map((approval) => `
          <article class="approval-row" data-approval-id="${approval.id}">
            <div>
              <strong>${escapeHtml(approval.part_name)}</strong>
              <span>${escapeHtml(approval.requester)} · ${approval.task_count}건 · ${formatRequestedAt(approval.requested_at)}</span>
            </div>
            <div class="approval-actions">
              <span class="badge status">${approval.current_step}/${approval.total_steps}</span>
              <button type="button" class="primary-button" data-action="open-detail">검토</button>
            </div>
          </article>
        `).join("") : `<p class="empty-note">승인 대기 건이 없습니다.</p>`}
      </div>
    </section>
  `;

  container.querySelectorAll("[data-approval-id]").forEach((row) => {
    const approvalId = row.dataset.approvalId;
    row.addEventListener("click", () => {
      if (context.navigateTo) {
        context.navigateTo("approver", { approvalId });
        return;
      }
      renderApprovalDetail(container, approvalId, context);
    });
    row.querySelector("[data-action='open-detail']").addEventListener("click", (event) => {
      event.stopPropagation();
      if (context.navigateTo) {
        context.navigateTo("approver", { approvalId });
        return;
      }
      renderApprovalDetail(container, approvalId, context);
    });
  });
}
