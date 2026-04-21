import test from "node:test";
import assert from "node:assert/strict";

import { parseOrganizationCsvPreview } from "../js/organizationAdmin.js";

test("parseOrganizationCsvPreview maps Korean headers and org type", () => {
  const csv = [
    "실명,실장명,실장ID,팀명,팀장명,팀장ID,그룹명,그룹장명,그룹장ID,파트명,파트장명,파트장ID",
    "AI실,김실장,div01,AI팀,이팀장,team01,AI그룹,박그룹장,group01,AI파트,최파트장,part01",
    "직속실,김실장,div02,,,,,,직속파트,오파트장,part02",
  ].join("\n");

  const rows = parseOrganizationCsvPreview(csv);

  assert.equal(rows.length, 2);
  assert.equal(rows[0].part_name, "AI파트");
  assert.equal(rows[0].org_type, "NORMAL");
  assert.equal(rows[0].part_head_email, "part01@samsung.com");
  assert.equal(rows[1].org_type, "DIV_DIRECT");
});

test("parseOrganizationCsvPreview reports missing required headers", () => {
  assert.throws(
    () => parseOrganizationCsvPreview("실명,파트명\nAI실,AI파트"),
    /필수 헤더/,
  );
});
