import test from "node:test";
import assert from "node:assert/strict";

import { parseClipboardToTasks, parseTsvToTasks } from "../js/clipboard.js";

const questions = {
  confidential: [
    { id: 11, question_text: "기밀 문항", options: ["해당 없음", "설계 자료", "공정 조건"] },
  ],
  national_tech: [
    { id: 21, question_text: "국가핵심기술 문항", options: ["해당 없음", "반도체 공정"] },
  ],
};

test("parseTsvToTasks maps only task identity columns for web classification", () => {
  const tsv = [
    "소파트\t대업무\t세부업무",
    "분석\t대업무 A\t세부업무 A",
  ].join("\n");

  const rows = parseTsvToTasks(tsv, questions, { organizationId: 7 });

  assert.deepEqual(rows, [
    {
      organization_id: 7,
      sub_part: "분석",
      major_task: "대업무 A",
      detail_task: "세부업무 A",
      confidential_answers: [],
      conf_data_type: "",
      conf_owner_user: "",
      national_tech_answers: [],
      ntech_data_type: "",
      ntech_owner_user: "",
      is_compliance: false,
      comp_data_type: "",
      comp_owner_user: "",
      storage_location: "",
      related_menu: "",
      share_scope: "",
    },
  ]);
});

test("parseTsvToTasks keeps empty rows out and supports Excel quoted cells", () => {
  const tsv = "\"파트\tA\"\t대업무 B\t\"세부업무\nB\"\n\n";

  const rows = parseTsvToTasks(tsv, questions);

  assert.equal(rows.length, 1);
  assert.equal(rows[0].sub_part, "파트\tA");
  assert.equal(rows[0].detail_task, "세부업무\nB");
  assert.deepEqual(rows[0].national_tech_answers, []);
  assert.equal(rows[0].is_compliance, false);
  assert.equal(rows[0].share_scope, "");
});

test("parseClipboardToTasks prefers Excel html tables over plain text", () => {
  const html = `
    <html>
      <body>
        <table>
          <tr><th>소파트</th><th>대업무</th><th>세부업무</th></tr>
          <tr><td>기획</td><td>연간 계획</td><td>부서별 계획 수립</td></tr>
        </table>
      </body>
    </html>
  `;
  const rows = parseClipboardToTasks(
    { html, text: "무시\t무시\t무시" },
    questions,
    { organizationId: 9 },
  );

  assert.equal(rows.length, 1);
  assert.equal(rows[0].organization_id, 9);
  assert.equal(rows[0].sub_part, "기획");
  assert.equal(rows[0].major_task, "연간 계획");
  assert.equal(rows[0].detail_task, "부서별 계획 수립");
});

test("parseClipboardToTasks falls back to TSV text", () => {
  const rows = parseClipboardToTasks(
    { html: "", text: "소파트\t대업무\t세부업무\n운영\t정기 점검\t월간 점검" },
    questions,
  );

  assert.equal(rows.length, 1);
  assert.equal(rows[0].sub_part, "운영");
  assert.equal(rows[0].major_task, "정기 점검");
  assert.equal(rows[0].detail_task, "월간 점검");
});
