const TRUE_VALUES = new Set(["Y", "YES", "TRUE", "1", "O", "해당"]);
const OWNER_VALUES = new Map([
  ["OWNER", "OWNER"],
  ["소유자", "OWNER"],
  ["USER", "USER"],
  ["사용자", "USER"],
]);
const SHARE_SCOPE_VALUES = new Map([
  ["DIVISION_BU", "DIVISION_BU"],
  ["부문/사업부", "DIVISION_BU"],
  ["부문", "DIVISION_BU"],
  ["BUSINESS_UNIT", "BUSINESS_UNIT"],
  ["사업부", "BUSINESS_UNIT"],
  ["ORG_UNIT", "ORG_UNIT"],
  ["실·팀·그룹", "ORG_UNIT"],
  ["실/팀/그룹", "ORG_UNIT"],
  ["실팀그룹", "ORG_UNIT"],
]);

function parseTsvRows(text) {
  const rows = [[]];
  let cell = "";
  let inQuotes = false;

  for (let index = 0; index < text.length; index += 1) {
    const char = text[index];
    const next = text[index + 1];

    if (inQuotes) {
      if (char === '"' && next === '"') {
        cell += '"';
        index += 1;
      } else if (char === '"') {
        inQuotes = false;
      } else {
        cell += char;
      }
      continue;
    }

    if (char === '"') {
      inQuotes = true;
    } else if (char === "\t") {
      rows.at(-1).push(cell);
      cell = "";
    } else if (char === "\r" || char === "\n") {
      rows.at(-1).push(cell);
      cell = "";
      if (char === "\r" && next === "\n") {
        index += 1;
      }
      rows.push([]);
    } else {
      cell += char;
    }
  }

  rows.at(-1).push(cell);
  return rows.filter((row) => row.some((value) => value.trim()));
}

function hasHeader(row) {
  return row[0]?.trim() === "소파트"
    && row[1]?.trim() === "대업무"
    && row[2]?.trim() === "세부업무";
}

function splitOptions(value) {
  return String(value ?? "")
    .split(/[;,|、]/)
    .map((option) => option.trim())
    .filter(Boolean);
}

function normalizeOwner(value) {
  const trimmed = String(value ?? "").trim();
  return OWNER_VALUES.get(trimmed.toUpperCase()) || OWNER_VALUES.get(trimmed) || trimmed;
}

function normalizeShareScope(value) {
  const trimmed = String(value ?? "").trim();
  return SHARE_SCOPE_VALUES.get(trimmed.toUpperCase())
    || SHARE_SCOPE_VALUES.get(trimmed)
    || trimmed;
}

function normalizeCompliance(value) {
  return TRUE_VALUES.has(String(value ?? "").trim().toUpperCase());
}

function mapAnswers(row, questions, startIndex) {
  return questions.map((question, offset) => ({
    question_id: question.id,
    selected_options: splitOptions(row[startIndex + offset] || ""),
  }));
}

export function parseTsvToTasks(text, questions = {}, options = {}) {
  const rows = parseTsvRows(text);
  if (rows.length && hasHeader(rows[0])) {
    rows.shift();
  }

  const confidentialQuestions = questions.confidential || [];
  const nationalTechQuestions = questions.national_tech || [];
  const organizationId = options.organizationId ?? 1;

  return rows.map((row) => {
    let cursor = 0;
    const subPart = row[cursor++]?.trim() || "";
    const majorTask = row[cursor++]?.trim() || "";
    const detailTask = row[cursor++]?.trim() || "";
    const confidentialAnswers = mapAnswers(row, confidentialQuestions, cursor);
    cursor += confidentialQuestions.length;
    const confDataType = row[cursor++]?.trim() || "";
    const confOwnerUser = normalizeOwner(row[cursor++] || "");
    const nationalTechAnswers = mapAnswers(row, nationalTechQuestions, cursor);
    cursor += nationalTechQuestions.length;
    const ntechDataType = row[cursor++]?.trim() || "";
    const ntechOwnerUser = normalizeOwner(row[cursor++] || "");
    const isCompliance = normalizeCompliance(row[cursor++] || "");
    const compDataType = row[cursor++]?.trim() || "";
    const compOwnerUser = normalizeOwner(row[cursor++] || "");
    const storageLocation = row[cursor++]?.trim() || "";
    const relatedMenu = row[cursor++]?.trim() || "";
    const shareScope = normalizeShareScope(row[cursor++] || "");

    return {
      organization_id: organizationId,
      sub_part: subPart,
      major_task: majorTask,
      detail_task: detailTask,
      confidential_answers: confidentialAnswers,
      conf_data_type: confDataType,
      conf_owner_user: confOwnerUser,
      national_tech_answers: nationalTechAnswers,
      ntech_data_type: ntechDataType,
      ntech_owner_user: ntechOwnerUser,
      is_compliance: isCompliance,
      comp_data_type: compDataType,
      comp_owner_user: compOwnerUser,
      storage_location: storageLocation,
      related_menu: relatedMenu,
      share_scope: shareScope,
    };
  });
}
