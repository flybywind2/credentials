import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import {
  approvalActionForStatus,
  deleteConfirmationMessage,
  editableOrganizationsForUser,
  firstErrorRow,
  groupValidationErrors,
  normalizeSubmitValidationErrors,
  previewSelectionSummary,
  renderActionError,
  selectedEditableOrganization,
  selectedPreviewRows,
} from "../js/spreadsheet.js";

const spreadsheetSource = readFileSync(new URL("../js/spreadsheet.js", import.meta.url), "utf8");
const formSource = readFileSync(new URL("../js/form.js", import.meta.url), "utf8");
const partMembersSource = readFileSync(new URL("../js/partMembers.js", import.meta.url), "utf8");
const spreadsheetModule = await import("../js/spreadsheet.js");

test("groupValidationErrors groups backend cell errors by row", () => {
  const grouped = groupValidationErrors([
    { row_index: 2, field: "major_task", message: "대업무 필수" },
    { row_index: 2, field: "detail_task", message: "세부업무 필수" },
    { row_index: 0, field: "organization_id", message: "권한 없음" },
  ]);

  assert.equal(grouped.get(2).length, 2);
  assert.equal(grouped.get(0)[0].field, "organization_id");
});

test("firstErrorRow returns the earliest row index", () => {
  assert.equal(firstErrorRow([{ row_index: 5 }, { row_index: 1 }]), 1);
  assert.equal(firstErrorRow([]), null);
});

test("normalizeSubmitValidationErrors maps task ids back to visible rows", () => {
  const errors = normalizeSubmitValidationErrors(
    {
      validationErrors: [
        { task_id: 20, field: "status", message: "분류 저장 필요" },
        { task_id: 99, field: "major_task", message: "대업무 필수" },
      ],
    },
    [{ id: 10 }, { id: 20 }],
  );

  assert.deepEqual(errors, [
    { task_id: 20, field: "status", message: "분류 저장 필요", row_index: 1 },
    { task_id: 99, field: "major_task", message: "대업무 필수", row_index: 0 },
  ]);
});

test("spreadsheet source includes approval confirmation and excel preview flow", () => {
  assert.match(spreadsheetSource, /approval-confirm-modal/);
  assert.match(spreadsheetSource, /\/api\/organizations/);
  assert.match(spreadsheetSource, /\/api\/tasks\/import\/preview/);
  assert.match(spreadsheetSource, /\/api\/tasks\/bulk/);
  assert.match(spreadsheetSource, /loadReadablePartMembers\(fetchJson, orgId\)/);
  assert.match(partMembersSource, /\/api\/part-members/);
  assert.match(spreadsheetSource, /data-action="select-work-org"/);
  assert.match(spreadsheetSource, /담당자/);
  assert.match(formSource, /assignee_knox_ids/);
  assert.match(formSource, /담당자 배정/);
  assert.match(spreadsheetSource, /status === "UPLOADED"/);
  assert.match(spreadsheetSource, /분류 저장 필요/);
  assert.match(spreadsheetSource, /data-action="save-all"/);
  assert.match(spreadsheetSource, /data-action="input-guide"/);
  assert.match(spreadsheetSource, /업무 입력 가이드/);
  assert.match(spreadsheetSource, /승인 요청 전 확인/);
  assert.match(spreadsheetSource, /\/api\/input-examples/);
  assert.match(spreadsheetSource, /data-action="toggle-example-data"/);
  assert.match(spreadsheetSource, /EXAMPLE_DATA_STORAGE_KEY/);
  assert.match(spreadsheetSource, /data-action="\$\{approvalAction\.action\}"/);
  assert.match(spreadsheetSource, /cancel-approval/);
  assert.match(spreadsheetSource, /\/api\/approvals\/\$\{partStatus\.active_approval_id\}\/cancel/);
  assert.match(spreadsheetSource, /data-action="preview-save-selected"/);
  assert.match(spreadsheetSource, /data-action="preview-save-all"/);
});

test("spreadsheet paste modal uses a grid-oriented Excel paste flow", () => {
  assert.match(spreadsheetSource, /parseClipboardToTasks/);
  assert.match(spreadsheetSource, /Excel 붙여넣기/);
  assert.match(spreadsheetSource, /text\/html/);
  assert.match(spreadsheetSource, /data-paste-dropzone/);
  assert.doesNotMatch(spreadsheetSource, /TSV 데이터/);
});

test("approvalActionForStatus switches to cancel while a pending request is active", () => {
  assert.deepEqual(
    approvalActionForStatus({ approval_status: "PENDING", active_approval_id: 10, can_cancel_approval: true }),
    { action: "cancel-approval", label: "요청 취소", className: "danger-button" },
  );
  assert.deepEqual(
    approvalActionForStatus({ approval_status: "PENDING", active_approval_id: 10, can_cancel_approval: false }),
    { action: "approval-pending", label: "승인 진행 중", className: "secondary-button", disabled: true },
  );
  assert.deepEqual(
    approvalActionForStatus({ approval_status: "CANCELLED", active_approval_id: null }),
    { action: "submit-approval", label: "승인 요청", className: "primary-button" },
  );
});

test("editableOrganizationsForUser returns subordinate parts for approvers", () => {
  const user = {
    role: "APPROVER",
    employee_id: "group001",
    organization_id: 1,
  };
  const organizations = [
    { id: 1, group_head_id: "group001", part_head_id: "part001", part_name: "A" },
    { id: 2, group_head_id: "group001", part_head_id: "part002", part_name: "B" },
    { id: 3, group_head_id: "other", part_head_id: "part003", part_name: "C" },
  ];

  assert.deepEqual(
    editableOrganizationsForUser(user, organizations).map((org) => org.id),
    [1, 2],
  );
});

test("editableOrganizationsForUser limits group approvers to their managed group", () => {
  const user = {
    role: "APPROVER",
    employee_id: "group001",
    organization_id: 1,
    organization: {
      id: 1,
      team_head_id: "team001",
      group_head_id: "group001",
      group_name: "AI/IT전략그룹",
      part_name: "A",
    },
  };
  const organizations = [
    { id: 1, team_head_id: "team001", group_head_id: "group001", group_name: "AI/IT전략그룹", part_name: "A" },
    { id: 2, team_head_id: "team001", group_head_id: "group001", group_name: "AI/IT전략그룹", part_name: "B" },
    { id: 3, team_head_id: "team001", group_head_id: "other", group_name: "정보전략팀", part_head_id: "group001", part_name: "C" },
    { id: 4, team_head_id: "team001", group_head_id: "group001", group_name: "승인알림그룹", part_name: "D" },
  ];

  assert.deepEqual(
    editableOrganizationsForUser(user, organizations).map((org) => org.id),
    [1, 2],
  );
});

test("editableOrganizationsForUser uses assigned group scope for managed approvers", () => {
  const user = {
    role: "APPROVER",
    employee_id: "manager001",
    managed: true,
    organization_id: 10,
    organization: {
      id: 10,
      group_head_id: "managed-group",
      group_name: "관리그룹",
      part_name: "관리파트A",
    },
  };
  const organizations = [
    { id: 10, group_head_id: "managed-group", group_name: "관리그룹", part_name: "관리파트A" },
    { id: 11, group_head_id: "managed-group", group_name: "관리그룹", part_name: "관리파트B" },
    { id: 12, group_head_id: "managed-group", group_name: "다른관리그룹", part_name: "관리파트C" },
    { id: 13, group_head_id: "other", group_name: "관리그룹", part_name: "관리파트D" },
  ];

  assert.deepEqual(
    editableOrganizationsForUser(user, organizations).map((org) => org.id),
    [10, 11],
  );
});

test("editableOrganizationsForUser uses team scope for managed team approvers", () => {
  const user = {
    role: "APPROVER",
    employee_id: "team001",
    managed: true,
    organization_id: 20,
    organization: {
      id: 20,
      team_head_id: "team001",
      team_name: "정보전략팀",
      group_head_id: "group001",
      group_name: "AI/IT전략그룹",
      part_name: "전략기획파트",
    },
  };
  const organizations = [
    { id: 20, team_head_id: "team001", team_name: "정보전략팀", group_head_id: "group001", group_name: "AI/IT전략그룹", part_name: "전략기획파트" },
    { id: 21, team_head_id: "team001", team_name: "정보전략팀", group_head_id: "group002", group_name: "생성형AI그룹", part_name: "AI개발파트" },
    { id: 22, team_head_id: "team001", team_name: "다른팀", group_head_id: "group003", group_name: "동명이인그룹", part_name: "제외파트" },
    { id: 23, team_head_id: "team999", team_name: "정보전략팀", group_head_id: "group004", group_name: "타팀그룹", part_name: "제외파트" },
  ];

  assert.deepEqual(
    editableOrganizationsForUser(user, organizations).map((org) => org.id),
    [20, 21, 23],
  );
});

test("editableOrganizationsForUser uses group name scope for group heads", () => {
  const user = {
    role: "APPROVER",
    employee_id: "group001",
    organization_id: 24,
    organization: {
      id: 24,
      team_name: "정보전략팀",
      group_head_id: "group001",
      group_name: "AI/IT전략그룹",
      part_name: "전략파트",
    },
  };
  const organizations = [
    { id: 24, team_name: "정보전략팀", group_head_id: "group001", group_name: "AI/IT전략그룹", part_name: "전략파트" },
    { id: 25, team_name: "정보전략팀", group_head_id: "csv-group-head", group_name: "AI/IT전략그룹", part_name: "자동화파트" },
    { id: 26, team_name: "정보전략팀", group_head_id: "group001", group_name: "다른전략그룹", part_name: "제외파트" },
  ];

  assert.deepEqual(
    editableOrganizationsForUser(user, organizations).map((org) => org.id),
    [24, 25],
  );
});

test("editableOrganizationsForUser uses team name scope for team heads", () => {
  const user = {
    role: "APPROVER",
    employee_id: "team001",
    organization_id: 27,
    organization: {
      id: 27,
      team_head_id: "team001",
      team_name: "정보전략팀",
      group_name: "AI/IT전략그룹",
      part_name: "전략파트",
    },
  };
  const organizations = [
    { id: 27, team_head_id: "team001", team_name: "정보전략팀", group_name: "AI/IT전략그룹", part_name: "전략파트" },
    { id: 28, team_head_id: "csv-team-head", team_name: "정보전략팀", group_name: "생성형AI그룹", part_name: "AI파트" },
    { id: 29, team_head_id: "team001", team_name: "다른정보전략팀", group_name: "타그룹", part_name: "제외파트" },
  ];

  assert.deepEqual(
    editableOrganizationsForUser(user, organizations).map((org) => org.id),
    [27, 28],
  );
});

test("editableOrganizationsForUser uses division name scope for division heads", () => {
  const user = {
    role: "APPROVER",
    employee_id: "div001",
    organization_id: 30,
    organization: {
      id: 30,
      division_head_id: "div001",
      division_name: "AI개발실",
      team_name: "정보전략팀",
      part_name: "전략파트",
    },
  };
  const organizations = [
    { id: 30, division_head_id: "div001", division_name: "AI개발실", team_name: "정보전략팀", part_name: "전략파트" },
    { id: 31, division_head_id: "csv-div-head", division_name: "AI개발실", team_name: "Generative AI팀", part_name: "AI파트" },
    { id: 32, division_head_id: "div001", division_name: "다른개발실", team_name: "타팀", part_name: "제외파트" },
  ];

  assert.deepEqual(
    editableOrganizationsForUser(user, organizations).map((org) => org.id),
    [30, 31],
  );
});

test("selectedEditableOrganization accepts selected subordinate part and falls back to current org", () => {
  const user = {
    role: "APPROVER",
    employee_id: "group001",
    organization_id: 1,
    organization: { id: 1, group_head_id: "group001", group_name: "선택그룹", part_name: "A" },
  };
  const organizations = [
    { id: 1, group_head_id: "group001", group_name: "선택그룹", part_head_id: "part001", part_name: "A" },
    { id: 2, group_head_id: "csv-group-head", group_name: "선택그룹", part_head_id: "part002", part_name: "B" },
  ];

  assert.equal(selectedEditableOrganization(user, organizations, 2).id, 2);
  assert.equal(selectedEditableOrganization(user, organizations, 999).id, 1);
});

test("approver organization selector stays visible with a single managed part", () => {
  assert.equal(
    typeof spreadsheetModule.shouldShowOrganizationSelector,
    "function",
  );
  assert.equal(
    spreadsheetModule.shouldShowOrganizationSelector({ role: "APPROVER" }, [{ id: 1 }]),
    true,
  );
  assert.equal(
    spreadsheetModule.shouldShowOrganizationSelector({ role: "INPUTTER" }, [{ id: 1 }]),
    false,
  );
  assert.equal(
    spreadsheetModule.shouldShowOrganizationSelector({ role: "APPROVER" }, []),
    false,
  );
});

test("spreadsheet source marks fixed columns for sticky layout", () => {
  assert.match(spreadsheetSource, /sticky-col sticky-no/);
  assert.match(spreadsheetSource, /sticky-col sticky-sub-part/);
  assert.match(spreadsheetSource, /sticky-col sticky-major-task/);
  assert.match(spreadsheetSource, /sticky-col sticky-detail-task/);
});

test("previewSelectionSummary counts valid, invalid, and selected rows", () => {
  const rows = [{ id: 1 }, { id: 2 }, { id: 3 }];
  const groupedErrors = new Map([[1, [{ message: "대업무 필수" }]]]);
  const selectedIndexes = new Set([0, 1, 2]);

  assert.deepEqual(previewSelectionSummary(rows, groupedErrors, selectedIndexes), {
    total: 3,
    valid: 2,
    errorRows: 1,
    selectedValid: 2,
  });
});

test("selectedPreviewRows returns only checked valid rows", () => {
  const rows = [{ major_task: "저장" }, { major_task: "오류" }, { major_task: "미선택" }];
  const groupedErrors = new Map([[1, [{ message: "세부업무 필수" }]]]);
  const selectedIndexes = new Set([0, 1]);

  assert.deepEqual(selectedPreviewRows(rows, groupedErrors, selectedIndexes), [
    { major_task: "저장" },
  ]);
});

test("deleteConfirmationMessage includes the task label when available", () => {
  assert.equal(
    deleteConfirmationMessage({ major_task: "고객 계약" }),
    "\"고객 계약\" 항목을 삭제하시겠습니까?",
  );
  assert.equal(deleteConfirmationMessage({}), "선택한 항목을 삭제하시겠습니까?");
});

test("renderActionError escapes and displays action failure details", () => {
  const html = renderActionError("삭제 실패", "서버 <오류>");

  assert.match(html, /role="alert"/);
  assert.match(html, /삭제 실패/);
  assert.match(html, /서버 &lt;오류&gt;/);
});

test("spreadsheet delete flow confirms before deletion and reports failures", () => {
  assert.match(spreadsheetSource, /deleteConfirmationMessage/);
  assert.match(spreadsheetSource, /globalThis\.confirm\?/);
  assert.match(spreadsheetSource, /catch\s*\(deleteError\)/);
  assert.match(spreadsheetSource, /삭제 실패/);
});
