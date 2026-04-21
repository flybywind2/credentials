import test from "node:test";
import assert from "node:assert/strict";

import { buildTaskFilterQuery, deriveHierarchyOptions, formatLatestReview } from "../js/adminTaskQuery.js";

test("buildTaskFilterQuery omits empty filters", () => {
  assert.equal(
    buildTaskFilterQuery({ part: "AI", status: "DRAFT", division: "", is_confidential: "true" }),
    "part=AI&status=DRAFT&is_confidential=true",
  );
});

test("formatLatestReview summarizes the latest task review", () => {
  assert.deepEqual(
    formatLatestReview({
      decision: "REJECTED",
      comment: "근거 보완 필요",
      reviewer_employee_id: "div001",
    }),
    {
      decision: "반려",
      comment: "근거 보완 필요",
      reviewer: "div001",
    },
  );
});

test("formatLatestReview returns dashes when no review exists", () => {
  assert.deepEqual(formatLatestReview(null), {
    decision: "-",
    comment: "-",
    reviewer: "-",
  });
});

test("deriveHierarchyOptions narrows teams, groups, and parts by selected parents", () => {
  const organizations = [
    { division_name: "A실", team_name: "A팀", group_name: "A그룹", part_name: "A파트" },
    { division_name: "A실", team_name: "A팀", group_name: "B그룹", part_name: "B파트" },
    { division_name: "B실", team_name: "B팀", group_name: "C그룹", part_name: "C파트" },
  ];

  assert.deepEqual(deriveHierarchyOptions(organizations, { division: "A실" }), {
    divisions: ["A실", "B실"],
    teams: ["A팀"],
    groups: ["A그룹", "B그룹"],
    parts: ["A파트", "B파트"],
  });
  assert.deepEqual(deriveHierarchyOptions(organizations, { division: "A실", group: "B그룹" }).parts, ["B파트"]);
});
