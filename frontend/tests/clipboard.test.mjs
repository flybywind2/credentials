import test from "node:test";
import assert from "node:assert/strict";

import { parseTsvToTasks } from "../js/clipboard.js";

const questions = {
  confidential: [
    { id: 11, question_text: "기밀 문항", options: ["해당 없음", "설계 자료", "공정 조건"] },
  ],
  national_tech: [
    { id: 21, question_text: "국가핵심기술 문항", options: ["해당 없음", "반도체 공정"] },
  ],
};

test("parseTsvToTasks maps standard column order into task payloads", () => {
  const tsv = [
    "소파트\t대업무\t세부업무\t기밀 문항 1\t기밀 데이터 유형\t기밀 소유자/사용자\t국가핵심기술 문항 1\t국가핵심기술 데이터 유형\t국가핵심기술 소유자/사용자\tCompliance 해당\tCompliance 데이터 유형\tCompliance 소유자/사용자\t보관 장소\t관련 메뉴\t공유 범위",
    "분석\t대업무 A\t세부업무 A\t설계 자료;공정 조건\t설계문서\t소유자\t해당 없음\t\t\tY\t계약정보\t사용자\t문서함\t분류 메뉴\t실/팀/그룹",
  ].join("\n");

  const rows = parseTsvToTasks(tsv, questions, { organizationId: 7 });

  assert.deepEqual(rows, [
    {
      organization_id: 7,
      sub_part: "분석",
      major_task: "대업무 A",
      detail_task: "세부업무 A",
      confidential_answers: [
        { question_id: 11, selected_options: ["설계 자료", "공정 조건"] },
      ],
      conf_data_type: "설계문서",
      conf_owner_user: "OWNER",
      national_tech_answers: [
        { question_id: 21, selected_options: ["해당 없음"] },
      ],
      ntech_data_type: "",
      ntech_owner_user: "",
      is_compliance: true,
      comp_data_type: "계약정보",
      comp_owner_user: "USER",
      storage_location: "문서함",
      related_menu: "분류 메뉴",
      share_scope: "ORG_UNIT",
    },
  ]);
});

test("parseTsvToTasks keeps empty rows out and supports Excel quoted cells", () => {
  const tsv = "\"파트\tA\"\t대업무 B\t\"세부업무\nB\"\t해당 없음\t\t\t반도체 공정\t기술자료\tOWNER\t비해당\t\t\t저장소\t메뉴\t사업부\n\n";

  const rows = parseTsvToTasks(tsv, questions);

  assert.equal(rows.length, 1);
  assert.equal(rows[0].sub_part, "파트\tA");
  assert.equal(rows[0].detail_task, "세부업무\nB");
  assert.equal(rows[0].national_tech_answers[0].selected_options[0], "반도체 공정");
  assert.equal(rows[0].ntech_owner_user, "OWNER");
  assert.equal(rows[0].is_compliance, false);
  assert.equal(rows[0].share_scope, "BUSINESS_UNIT");
});
