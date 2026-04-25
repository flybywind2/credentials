import { fetchJson } from "./api.js";

const NONE_OPTION = "해당 없음";
const POSITIVE_OPTION = "해당 됨";

const QUESTION_CONFIGS = [
  {
    key: "confidential",
    title: "기밀 판단 항목",
    description: "세부업무의 기밀 여부를 판정할 체크 문항을 관리합니다.",
    listPath: "/api/questions/confidential",
    adminPath: "/api/admin/questions/confidential",
    inputPrefix: "confidential-question",
  },
  {
    key: "national-tech",
    title: "국가핵심기술 판단 항목",
    description: "국가핵심기술 해당 여부를 판정할 체크 문항을 관리합니다.",
    listPath: "/api/questions/national-tech",
    adminPath: "/api/admin/questions/national-tech",
    inputPrefix: "national-tech-question",
  },
];

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

export function normalizeQuestionOptions(input) {
  return [POSITIVE_OPTION];
}

export function moveQuestionId(ids, questionId, direction) {
  const next = [...ids];
  const index = next.indexOf(questionId);
  const targetIndex = direction === "up" ? index - 1 : index + 1;
  if (index < 0 || targetIndex < 0 || targetIndex >= next.length) {
    return next;
  }
  [next[index], next[targetIndex]] = [next[targetIndex], next[index]];
  return next;
}

export function moveQuestionIdBefore(ids, questionId, targetId) {
  const next = ids.filter((id) => id !== questionId);
  const targetIndex = next.indexOf(targetId);
  if (targetIndex < 0 || questionId === targetId) {
    return ids;
  }
  next.splice(targetIndex, 0, questionId);
  return next;
}

function renderQuestionList(config, questions) {
  if (!questions.length) {
    return `<p class="empty-note">등록된 판단 항목이 없습니다.</p>`;
  }

  return `
    <div class="question-admin-list">
      ${questions.map((question) => `
        <article
          class="question-admin-row"
          draggable="true"
          data-question-row
          data-question-type="${config.key}"
          data-question-id="${question.id}"
        >
          <div>
            <strong>${escapeHtml(question.question_text)}</strong>
            <span>${question.options.map(escapeHtml).join(" · ")}</span>
          </div>
          <button
            type="button"
            class="secondary-button"
            data-question-type="${config.key}"
            data-move-question="${question.id}"
            data-move-direction="up"
          >
            위
          </button>
          <button
            type="button"
            class="secondary-button"
            data-question-type="${config.key}"
            data-move-question="${question.id}"
            data-move-direction="down"
          >
            아래
          </button>
          <button
            type="button"
            class="secondary-button"
            data-question-type="${config.key}"
            data-delete-question="${question.id}"
          >
            삭제
          </button>
        </article>
      `).join("")}
    </div>
  `;
}

function renderQuestionPanel(config, questions, activeKey) {
  return `
    <section
      class="question-admin-panel"
      data-question-panel="${config.key}"
      ${config.key === activeKey ? "" : "hidden"}
      role="tabpanel"
      aria-labelledby="question-tab-${config.key}"
    >
      <div class="question-admin-panel-header">
        <div>
          <h3>${config.title}</h3>
          <p>${config.description}</p>
        </div>
        <span class="badge neutral">${questions.length}개</span>
      </div>
      <form class="question-admin-form" data-question-form="${config.key}" novalidate>
        <label for="${config.inputPrefix}-text">문항
          <input id="${config.inputPrefix}-text" name="question_text" placeholder="예: 외부 공개가 제한되는 설계 정보가 포함됩니까?">
        </label>
        <p class="muted-note">선택지는 “해당 없음”과 “해당 됨”으로 고정됩니다.</p>
        <p class="field-error" data-question-error="${config.key}"></p>
        <div class="question-admin-actions">
          <span>선택지 수정 없이 문항만 추가합니다.</span>
          <button type="submit" class="primary-button">항목 추가</button>
        </div>
      </form>
      ${renderQuestionList(config, questions)}
    </section>
  `;
}

function showQuestionError(container, key, message) {
  const error = container.querySelector(`[data-question-error="${key}"]`);
  if (error) {
    error.textContent = message;
  }
}

async function createQuestion(container, config, form) {
  const questionText = form.elements.question_text.value.trim();
  const options = normalizeQuestionOptions();
  showQuestionError(container, config.key, "");

  if (!questionText) {
    showQuestionError(container, config.key, "문항을 입력하세요.");
    return;
  }
  await fetchJson(config.adminPath, {
    method: "POST",
    body: JSON.stringify({
      question_text: questionText,
      options,
    }),
  });
  await renderQuestionManager(container, config.key);
}

async function deleteQuestion(container, config, questionId) {
  await fetchJson(`${config.adminPath}/${questionId}`, { method: "DELETE" });
  await renderQuestionManager(container, config.key);
}

async function reorderQuestion(container, config, questions, questionId, direction) {
  const ids = moveQuestionId(questions.map((question) => question.id), Number(questionId), direction);
  await fetchJson(`${config.adminPath}/reorder`, {
    method: "PUT",
    body: JSON.stringify({ question_ids: ids }),
  });
  await renderQuestionManager(container, config.key);
}

async function reorderQuestionDrop(container, config, questions, questionId, targetId) {
  const ids = moveQuestionIdBefore(
    questions.map((question) => question.id),
    Number(questionId),
    Number(targetId),
  );
  await fetchJson(`${config.adminPath}/reorder`, {
    method: "PUT",
    body: JSON.stringify({ question_ids: ids }),
  });
  await renderQuestionManager(container, config.key);
}

export async function renderQuestionManager(container, activeKey = QUESTION_CONFIGS[0].key) {
  const questionGroups = await Promise.all(
    QUESTION_CONFIGS.map(async (config) => ({
      config,
      questions: await fetchJson(config.listPath),
    })),
  );

  container.innerHTML = `
    <section class="question-admin-section">
      <div class="section-header question-admin-main-header">
        <div>
          <h2>판정 문항 관리</h2>
          <p>기밀 판단 항목과 국가핵심기술 판단 항목을 설정합니다.</p>
        </div>
      </div>
      <div class="question-admin-tabs" role="tablist" aria-label="판정 문항 유형">
        ${QUESTION_CONFIGS.map((config) => `
          <button
            id="question-tab-${config.key}"
            type="button"
            role="tab"
            aria-selected="${config.key === activeKey}"
            data-question-tab="${config.key}"
          >
            ${config.title}
          </button>
        `).join("")}
      </div>
      <div class="question-admin-grid">
        ${questionGroups.map(({ config, questions }) => renderQuestionPanel(config, questions, activeKey)).join("")}
      </div>
    </section>
  `;

  container.querySelectorAll("[data-question-tab]").forEach((button) => {
    button.addEventListener("click", async () => {
      await renderQuestionManager(container, button.dataset.questionTab);
    });
  });

  container.querySelectorAll("[data-question-form]").forEach((form) => {
    const config = QUESTION_CONFIGS.find((item) => item.key === form.dataset.questionForm);
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      await createQuestion(container, config, form);
    });
  });

  container.querySelectorAll("[data-delete-question]").forEach((button) => {
    const config = QUESTION_CONFIGS.find((item) => item.key === button.dataset.questionType);
    button.addEventListener("click", async () => {
      await deleteQuestion(container, config, button.dataset.deleteQuestion);
    });
  });

  container.querySelectorAll("[data-move-question]").forEach((button) => {
    const group = questionGroups.find(({ config }) => config.key === button.dataset.questionType);
    button.addEventListener("click", async () => {
      await reorderQuestion(
        container,
        group.config,
        group.questions,
        button.dataset.moveQuestion,
        button.dataset.moveDirection,
      );
    });
  });

  container.querySelectorAll("[data-question-row]").forEach((row) => {
    row.addEventListener("dragstart", (event) => {
      event.dataTransfer.effectAllowed = "move";
      event.dataTransfer.setData("text/plain", row.dataset.questionId);
      event.dataTransfer.setData("application/x-question-type", row.dataset.questionType);
      row.classList.add("dragging");
    });
    row.addEventListener("dragend", () => {
      row.classList.remove("dragging");
    });
    row.addEventListener("dragover", (event) => {
      event.preventDefault();
      event.dataTransfer.dropEffect = "move";
    });
    row.addEventListener("drop", async (event) => {
      event.preventDefault();
      const questionId = event.dataTransfer.getData("text/plain");
      const questionType = event.dataTransfer.getData("application/x-question-type");
      if (!questionId || questionType !== row.dataset.questionType) {
        return;
      }
      const group = questionGroups.find(({ config }) => config.key === questionType);
      await reorderQuestionDrop(container, group.config, group.questions, questionId, row.dataset.questionId);
    });
  });
}
