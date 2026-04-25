import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const dashboardSource = readFileSync(new URL("../js/dashboard.js", import.meta.url), "utf8");
const partMemberAdminSource = readFileSync(new URL("../js/partMemberAdmin.js", import.meta.url), "utf8");

test("admin dashboard mounts the part member manager", () => {
  assert.match(dashboardSource, /renderPartMemberManager/);
  assert.match(dashboardSource, /part-member-manager-root/);
});

test("part member manager supports selected organization and all-part CSV upload", () => {
  assert.match(partMemberAdminSource, /파트원 명단 CSV 업로드/);
  assert.match(partMemberAdminSource, /파트명, 이름, knox_id/);
  assert.match(partMemberAdminSource, /\/api\/part-members\/import\?org_id=/);
  assert.match(partMemberAdminSource, /\/api\/part-members\/import\?scope=all/);
  assert.match(partMemberAdminSource, /전체 일괄 업로드/);
  assert.match(partMemberAdminSource, /name="organization_id"/);
  assert.match(partMemberAdminSource, /type="file"/);
  assert.match(partMemberAdminSource, /text\/csv/);
  assert.match(partMemberAdminSource, /paginateItems/);
  assert.match(partMemberAdminSource, /data-part-member-pagination/);
});
