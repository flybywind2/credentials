import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import { approvalDonutStyle, filterDepartmentItems, sortDepartmentItems } from "../js/dashboard.js";

const dashboardSource = readFileSync(new URL("../js/dashboard.js", import.meta.url), "utf8");

test("filterDepartmentItems matches division, team, group, and part text", () => {
  const items = [
    { division_name: "AI실", team_name: "플랫폼팀", group_name: "A그룹", part_name: "검색파트" },
    { division_name: "보안실", team_name: "보안팀", group_name: "B그룹", part_name: "관제파트" },
  ];

  assert.deepEqual(filterDepartmentItems(items, "보안").map((item) => item.part_name), ["관제파트"]);
  assert.deepEqual(filterDepartmentItems(items, "").length, 2);
});

test("sortDepartmentItems sorts by completion rate and part name", () => {
  const items = [
    { part_name: "B파트", completion_rate: 10 },
    { part_name: "A파트", completion_rate: 90 },
  ];

  assert.deepEqual(sortDepartmentItems(items, "completion_desc").map((item) => item.part_name), ["A파트", "B파트"]);
  assert.deepEqual(sortDepartmentItems(items, "part_asc").map((item) => item.part_name), ["A파트", "B파트"]);
});

test("approvalDonutStyle creates a conic-gradient chart style", () => {
  assert.match(approvalDonutStyle({ PENDING: 1, IN_PROGRESS: 1, APPROVED: 2, REJECTED: 0 }), /conic-gradient/);
});

test("dashboard source renders integrated ratio, donut chart, and summary controls", () => {
  assert.match(dashboardSource, /integrated_classification_ratio/);
  assert.match(dashboardSource, /approval-donut/);
  assert.match(dashboardSource, /data-summary-filter/);
  assert.match(dashboardSource, /data-summary-sort/);
  assert.match(dashboardSource, /data-admin-toggle/);
  assert.match(dashboardSource, /data-department-pagination/);
  assert.match(dashboardSource, /renderInputExampleManager/);
  assert.match(dashboardSource, /입력 예시 데이터 관리/);
});
