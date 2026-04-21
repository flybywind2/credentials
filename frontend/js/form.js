import { bindModalAccessibility } from "./modalAccessibility.js?v=20260421-p1b";

const NONE_OPTION = "해당 없음";

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function valueOf(task, key) {
  return task?.[key] ?? "";
}

function answerMap(task, key) {
  const answers = task?.[key] || [];
  const map = new Map();
  answers.forEach((answer, index) => {
    if (Array.isArray(answer)) {
      map.set(String(index + 1), answer);
      return;
    }
    map.set(String(answer.question_id), answer.selected_options || []);
  });
  return map;
}

function isOptionSelected(map, questionId, option) {
  return (map.get(String(questionId)) || []).includes(option);
}

function renderOwnerRadios(name, selectedValue) {
  return `
    <div class="radio-group" data-owner-group="${name}">
      ${[
        ["OWNER", "소유자"],
        ["USER", "사용자"],
      ].map(([value, label]) => `
        <label class="choice-chip" for="modal-${name}-${value.toLowerCase()}">
          <input
            id="modal-${name}-${value.toLowerCase()}"
            name="${name}"
            type="radio"
            value="${value}"
            ${selectedValue === value ? "checked" : ""}
          >
          <span>${label}</span>
        </label>
      `).join("")}
    </div>
  `;
}

function renderQuestionBlocks(type, questions, selectedAnswers) {
  if (!questions.length) {
    return `<p class="empty-note">등록된 문항이 없습니다.</p>`;
  }

  return questions.map((question) => `
    <div class="question-block" data-question-type="${type}" data-question-id="${question.id}">
      <p>${escapeHtml(question.question_text)}</p>
      <div class="checkbox-grid">
        ${question.options.map((option, optionIndex) => {
          const id = `modal-${type}-${question.id}-${optionIndex}`;
          return `
            <label class="choice-chip" for="${id}">
              <input
                id="${id}"
                name="${type}_${question.id}"
                type="checkbox"
                value="${escapeHtml(option)}"
                data-question-option
                ${option === NONE_OPTION ? "data-none-option=\"true\"" : ""}
                ${isOptionSelected(selectedAnswers, question.id, option) ? "checked" : ""}
              >
              <span>${escapeHtml(option)}</span>
            </label>
          `;
        }).join("")}
      </div>
      <p class="field-error" data-error-for="${type}_${question.id}"></p>
    </div>
  `).join("");
}

function renderClassificationSection({ type, title, resultLabel, questions, selectedAnswers, dataTypeName, ownerName, dataTypeValue, ownerValue }) {
  return `
    <section class="form-section" data-classification-section="${type}">
      <header class="form-section-header">
        <h3>${title}</h3>
        <span class="badge neutral" data-result-badge data-positive-label="${resultLabel}" data-negative-label="${type === "confidential" ? "비기밀" : "비해당"}">판정 전</span>
      </header>
      ${renderQuestionBlocks(type, questions, selectedAnswers)}
      <div class="dependent-grid" data-dependent-area="${type}">
        <label for="modal-${dataTypeName}">데이터 유형
          <input id="modal-${dataTypeName}" name="${dataTypeName}" value="${escapeHtml(dataTypeValue)}">
          <span class="field-error" data-error-for="${dataTypeName}"></span>
        </label>
        <div class="field-group">
          <span id="modal-${ownerName}-label">소유자/사용자</span>
          ${renderOwnerRadios(ownerName, ownerValue)}
          <span class="field-error" data-error-for="${ownerName}"></span>
        </div>
      </div>
    </section>
  `;
}

function renderComplianceSection(task) {
  return `
    <section class="form-section" data-compliance-section>
      <header class="form-section-header">
        <h3>Compliance 이슈</h3>
        <span class="badge neutral" data-compliance-badge>비해당</span>
      </header>
      <label class="toggle-row" for="modal-is-compliance">
        <input id="modal-is-compliance" name="is_compliance" type="checkbox" ${task.is_compliance ? "checked" : ""}>
        <span>Compliance 이슈 해당</span>
      </label>
      <div class="dependent-grid" data-dependent-area="compliance">
        <label for="modal-comp_data_type">데이터 유형
          <input id="modal-comp_data_type" name="comp_data_type" value="${escapeHtml(valueOf(task, "comp_data_type"))}">
          <span class="field-error" data-error-for="comp_data_type"></span>
        </label>
        <div class="field-group">
          <span id="modal-comp_owner_user-label">소유자/사용자</span>
          ${renderOwnerRadios("comp_owner_user", valueOf(task, "comp_owner_user"))}
          <span class="field-error" data-error-for="comp_owner_user"></span>
        </div>
      </div>
    </section>
  `;
}

function getQuestionAnswers(form, type) {
  return [...form.querySelectorAll(`[data-question-type="${type}"]`)].map((block) => ({
    question_id: Number(block.dataset.questionId),
    selected_options: [...block.querySelectorAll("[data-question-option]:checked")]
      .map((input) => input.value),
  }));
}

function hasPositiveAnswer(answers) {
  return answers.some((answer) => answer.selected_options.some((option) => option !== NONE_OPTION));
}

function radioValue(form, name) {
  return form.querySelector(`input[name="${name}"]:checked`)?.value || "";
}

function setAreaEnabled(form, areaName, enabled) {
  form.querySelectorAll(`[data-dependent-area="${areaName}"] input`).forEach((input) => {
    input.disabled = !enabled;
    if (!enabled) {
      if (input.type === "radio") {
        input.checked = false;
      } else {
        input.value = "";
      }
    }
  });
}

function updateClassificationState(form) {
  [
    ["confidential", "기밀", "비기밀"],
    ["national_tech", "해당", "비해당"],
  ].forEach(([type, positiveLabel, negativeLabel]) => {
    const section = form.querySelector(`[data-classification-section="${type}"]`);
    const isPositive = hasPositiveAnswer(getQuestionAnswers(form, type));
    const badge = section.querySelector("[data-result-badge]");
    badge.textContent = isPositive ? positiveLabel : negativeLabel;
    badge.className = `badge ${isPositive ? "danger" : "neutral"}`;
    setAreaEnabled(form, type, isPositive);
  });

  const complianceChecked = form.elements.is_compliance.checked;
  const complianceBadge = form.querySelector("[data-compliance-badge]");
  complianceBadge.textContent = complianceChecked ? "해당" : "비해당";
  complianceBadge.className = `badge ${complianceChecked ? "warning" : "neutral"}`;
  setAreaEnabled(form, "compliance", complianceChecked);
}

function clearErrors(form) {
  form.querySelectorAll(".field-error").forEach((error) => {
    error.textContent = "";
  });
  form.querySelectorAll("[aria-invalid='true']").forEach((field) => {
    field.removeAttribute("aria-invalid");
  });
}

function showError(form, key, message) {
  const error = form.querySelector(`[data-error-for="${key}"]`);
  if (error) {
    error.textContent = message;
  }
  form.querySelector(`[name="${key}"]`)?.setAttribute("aria-invalid", "true");
}

function validateForm(form) {
  clearErrors(form);
  const confidentialAnswers = getQuestionAnswers(form, "confidential");
  const nationalTechAnswers = getQuestionAnswers(form, "national_tech");
  const isConfidential = hasPositiveAnswer(confidentialAnswers);
  const isNationalTech = hasPositiveAnswer(nationalTechAnswers);
  const isCompliance = form.elements.is_compliance.checked;
  let hasError = false;

  const requiredText = [
    ["major_task", "대업무는 필수입니다."],
    ["detail_task", "세부업무는 필수입니다."],
  ];

  if (isConfidential) {
    requiredText.push(["conf_data_type", "기밀 데이터 유형은 필수입니다."]);
  }
  if (isNationalTech) {
    requiredText.push(["ntech_data_type", "국가핵심기술 데이터 유형은 필수입니다."]);
  }
  if (isCompliance) {
    requiredText.push(["comp_data_type", "Compliance 데이터 유형은 필수입니다."]);
  }

  requiredText.forEach(([name, message]) => {
    if (!form.elements[name].value.trim()) {
      showError(form, name, message);
      hasError = true;
    }
  });

  [
    ["confidential", confidentialAnswers],
    ["national_tech", nationalTechAnswers],
  ].forEach(([type, answers]) => {
    answers.forEach((answer) => {
      if (!answer.selected_options.length) {
        showError(form, `${type}_${answer.question_id}`, "문항별로 1개 이상 선택해야 합니다.");
        hasError = true;
      }
    });
  });

  [
    [isConfidential, "conf_owner_user", "기밀 소유자/사용자는 필수입니다."],
    [isNationalTech, "ntech_owner_user", "국가핵심기술 소유자/사용자는 필수입니다."],
    [isCompliance, "comp_owner_user", "Compliance 소유자/사용자는 필수입니다."],
  ].forEach(([required, name, message]) => {
    if (required && !radioValue(form, name)) {
      showError(form, name, message);
      hasError = true;
    }
  });

  if (hasError) {
    form.querySelector("[aria-invalid='true'], .field-error:not(:empty)")?.scrollIntoView({ block: "center" });
    return null;
  }

  return {
    sub_part: form.elements.sub_part.value.trim(),
    major_task: form.elements.major_task.value.trim(),
    detail_task: form.elements.detail_task.value.trim(),
    confidential_answers: confidentialAnswers,
    conf_data_type: isConfidential ? form.elements.conf_data_type.value.trim() : "",
    conf_owner_user: isConfidential ? radioValue(form, "conf_owner_user") : "",
    national_tech_answers: nationalTechAnswers,
    ntech_data_type: isNationalTech ? form.elements.ntech_data_type.value.trim() : "",
    ntech_owner_user: isNationalTech ? radioValue(form, "ntech_owner_user") : "",
    is_compliance: isCompliance,
    comp_data_type: isCompliance ? form.elements.comp_data_type.value.trim() : "",
    comp_owner_user: isCompliance ? radioValue(form, "comp_owner_user") : "",
    storage_location: form.elements.storage_location.value.trim(),
    related_menu: form.elements.related_menu.value.trim(),
    share_scope: form.elements.share_scope.value,
  };
}

export function openTaskModal(task = {}, onSave, questions = { confidential: [], national_tech: [] }) {
  closeTaskModal();
  const isNew = !task.id;
  let currentTask = { ...task };
  const confidentialAnswers = answerMap(task, "confidential_answers");
  const nationalTechAnswers = answerMap(task, "national_tech_answers");

  const overlay = document.createElement("div");
  overlay.className = "modal-overlay";
  overlay.id = "task-modal";
  overlay.innerHTML = `
    <section class="modal" role="dialog" aria-modal="true" aria-labelledby="modal-title">
      <header class="modal-header">
        <div>
          <h2 id="modal-title">${isNew ? "신규 업무" : escapeHtml(task.major_task)}</h2>
          <p>${isNew ? "업무 정보를 입력합니다." : escapeHtml(task.detail_task)}</p>
        </div>
        <button class="icon-button" type="button" aria-label="닫기" title="닫기">×</button>
      </header>
      <form id="task-form" novalidate>
        <section class="form-section">
          <header class="form-section-header">
            <h3>업무 정보</h3>
          </header>
          <div class="detail-grid">
            <label for="modal-sub-part">소파트
              <input id="modal-sub-part" name="sub_part" value="${escapeHtml(valueOf(task, "sub_part"))}">
            </label>
            <label for="modal-major-task">대업무
              <input id="modal-major-task" name="major_task" value="${escapeHtml(valueOf(task, "major_task"))}">
              <span class="field-error" data-error-for="major_task"></span>
            </label>
            <label class="wide-field" for="modal-detail-task">세부업무
              <textarea id="modal-detail-task" name="detail_task">${escapeHtml(valueOf(task, "detail_task"))}</textarea>
              <span class="field-error" data-error-for="detail_task"></span>
            </label>
          </div>
        </section>
        ${renderClassificationSection({
          type: "confidential",
          title: "기밀 여부",
          resultLabel: "기밀",
          questions: questions.confidential || [],
          selectedAnswers: confidentialAnswers,
          dataTypeName: "conf_data_type",
          ownerName: "conf_owner_user",
          dataTypeValue: valueOf(task, "conf_data_type"),
          ownerValue: valueOf(task, "conf_owner_user"),
        })}
        ${renderClassificationSection({
          type: "national_tech",
          title: "국가핵심기술",
          resultLabel: "해당",
          questions: questions.national_tech || [],
          selectedAnswers: nationalTechAnswers,
          dataTypeName: "ntech_data_type",
          ownerName: "ntech_owner_user",
          dataTypeValue: valueOf(task, "ntech_data_type"),
          ownerValue: valueOf(task, "ntech_owner_user"),
        })}
        ${renderComplianceSection(task)}
        <section class="form-section">
          <header class="form-section-header">
            <h3>데이터 보관 정보</h3>
          </header>
          <div class="detail-grid">
            <label for="modal-storage-location">보관 장소
              <input id="modal-storage-location" name="storage_location" value="${escapeHtml(valueOf(task, "storage_location"))}">
            </label>
            <label for="modal-related-menu">관련 메뉴
              <input id="modal-related-menu" name="related_menu" value="${escapeHtml(valueOf(task, "related_menu"))}">
            </label>
            <label for="modal-share-scope">공유 범위
              <select id="modal-share-scope" name="share_scope">
                <option value="">선택</option>
                <option value="DIVISION_BU" ${task.share_scope === "DIVISION_BU" ? "selected" : ""}>부문/사업부</option>
                <option value="BUSINESS_UNIT" ${task.share_scope === "BUSINESS_UNIT" ? "selected" : ""}>사업부</option>
                <option value="ORG_UNIT" ${task.share_scope === "ORG_UNIT" ? "selected" : ""}>실·팀·그룹</option>
              </select>
            </label>
          </div>
        </section>
        <div class="modal-actions">
          <button type="button" class="secondary-button" data-action="cancel">취소</button>
          <button type="button" class="secondary-button" data-action="save-current">저장</button>
          <button type="submit" class="primary-button">저장 후 닫기</button>
        </div>
      </form>
    </section>
  `;

  overlay.addEventListener("click", (event) => {
    if (event.target === overlay || event.target.closest(".icon-button, [data-action='cancel']")) {
      closeTaskModal();
    }
  });
  bindModalAccessibility(overlay, closeTaskModal);

  const form = overlay.querySelector("#task-form");
  form.addEventListener("change", (event) => {
    if (event.target.matches("[data-question-option]")) {
      const block = event.target.closest("[data-question-type]");
      const noneOption = block.querySelector("[data-none-option='true']");
      if (event.target.dataset.noneOption === "true" && event.target.checked) {
        block.querySelectorAll("[data-question-option]").forEach((input) => {
          if (input !== event.target) {
            input.checked = false;
          }
        });
      }
      if (event.target.dataset.noneOption !== "true" && event.target.checked && noneOption) {
        noneOption.checked = false;
      }
    }
    updateClassificationState(form);
  });

  async function saveCurrent(closeAfterSave) {
    const payload = validateForm(form);
    if (!payload) {
      return;
    }
    const savedTask = await onSave?.(payload, currentTask);
    if (savedTask) {
      currentTask = { ...currentTask, ...savedTask };
    }
    if (closeAfterSave) {
      closeTaskModal();
    }
  }

  form.querySelector("[data-action='save-current']").addEventListener("click", async () => {
    await saveCurrent(false);
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    await saveCurrent(true);
  });

  document.body.append(overlay);
  updateClassificationState(form);
  form.elements.major_task.focus();
}

export function closeTaskModal() {
  document.querySelector("#task-modal")?.remove();
}
