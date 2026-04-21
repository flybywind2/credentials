import { fetchJson } from "./api.js";

const NONE_OPTION = "해당 없음";

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
  const seen = new Set();
  return String(input ?? "")
    .split(/[,\n;]/)
    .map((option) => option.trim())
    .filter((option) => option && option !== NONE_OPTION)
    .filter((option) => {
      if (seen.has(option)) {
        return false;
      }
      seen.add(option);
      return true;
    });
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

function renderQuestionList(config, questions) {
  if (!questions.length) {
    return `<p class="empty-note">등록된 판단 항목이 없습니다.</p>`;
  }

  return `
    <div class="question-admin-list">
      ${questions.map((question) => `
        <article class="question-admin-row">
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

function renderQuestionPanel(config, questions) {
  return `
    <section class="question-admin-panel" data-question-panel="${config.key}">
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
        <label for="${config.inputPrefix}-options">선택지
          <textarea id="${config.inputPrefix}-options" name="options" placeholder="쉼표, 세미콜론 또는 줄바꿈으로 구분"></textarea>
        </label>
        <p class="field-error" data-question-error="${config.key}"></p>
        <div class="question-admin-actions">
          <span>“해당 없음”은 자동 포함됩니다.</span>
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
  const options = normalizeQuestionOptions(form.elements.options.value);
  showQuestionError(container, config.key, "");

  if (!questionText) {
    showQuestionError(container, config.key, "문항을 입력하세요.");
    return;
  }
  if (!options.length) {
    showQuestionError(container, config.key, "선택지를 1개 이상 입력하세요.");
    return;
  }

  await fetchJson(config.adminPath, {
    method: "POST",
    body: JSON.stringify({
      question_text: questionText,
      options,
    }),
  });
  await renderQuestionManager(container);
}

async function deleteQuestion(container, config, questionId) {
  await fetchJson(`${config.adminPath}/${questionId}`, { method: "DELETE" });
  await renderQuestionManager(container);
}

async function reorderQuestion(container, config, questions, questionId, direction) {
  const ids = moveQuestionId(questions.map((question) => question.id), Number(questionId), direction);
  await fetchJson(`${config.adminPath}/reorder`, {
    method: "PUT",
    body: JSON.stringify({ question_ids: ids }),
  });
  await renderQuestionManager(container);
}

export async function renderQuestionManager(container) {
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
      <div class="question-admin-grid">
        ${questionGroups.map(({ config, questions }) => renderQuestionPanel(config, questions)).join("")}
      </div>
    </section>
  `;

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
}
