import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const partStatusSource = readFileSync(new URL("../js/partStatus.js", import.meta.url), "utf8");
const partMembersSource = readFileSync(new URL("../js/partMembers.js", import.meta.url), "utf8");

test("part status page renders part members as a read-only list", () => {
  assert.match(partStatusSource, /loadReadablePartMembers/);
  assert.match(partMembersSource, /\/api\/part-members/);
  assert.match(partStatusSource, /파트원 명단/);
  assert.doesNotMatch(partStatusSource, /\/api\/part-members\/import/);
  assert.doesNotMatch(partStatusSource, /type="file"/);
  assert.doesNotMatch(partStatusSource, /text\/csv/);
});

test("part status page lets approvers choose a subordinate part scope", () => {
  assert.match(partStatusSource, /진행 현황/);
  assert.match(partStatusSource, /renderClassificationDonut/);
  assert.match(partStatusSource, /classification_summary/);
  assert.match(partStatusSource, /\/api\/organizations/);
  assert.match(partStatusSource, /editableOrganizationsForUser/);
  assert.match(partStatusSource, /selectedEditableOrganization/);
  assert.match(partStatusSource, /data-action="select-status-org"/);
  assert.match(partStatusSource, /\/api\/tasks\/status\?org_id=\$\{orgId\}/);
  assert.match(partStatusSource, /\/api\/tasks\/rejection\?org_id=\$\{orgId\}/);
  assert.match(partStatusSource, /loadReadablePartMembers\(fetchJson, orgId\)/);
  assert.match(partStatusSource, /renderPartStatus\(container, \{ \.\.\.options, selectedOrgId/);
});
