import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import * as formModule from "../js/form.js";

const formSource = readFileSync(new URL("../js/form.js", import.meta.url), "utf8");

test("classification dependent fields stay editable in the task modal", () => {
  assert.doesNotMatch(formSource, /input\.disabled\s*=/);
  assert.doesNotMatch(formSource, /input\.value\s*=\s*""/);
});

test("classificationRequiredFieldErrors only requires metadata when a category applies", () => {
  assert.equal(typeof formModule.classificationRequiredFieldErrors, "function");

  assert.deepEqual(
    formModule.classificationRequiredFieldErrors({
      isConfidential: false,
      isNationalTech: false,
      isCompliance: false,
      values: {
        conf_data_type: "",
        conf_owner_user: "",
        ntech_data_type: "",
        ntech_owner_user: "",
        comp_data_type: "",
        comp_owner_user: "",
      },
    }),
    [],
  );

  const requiredErrors = formModule.classificationRequiredFieldErrors({
      isConfidential: true,
      isNationalTech: true,
      isCompliance: true,
      values: {
        conf_data_type: "",
        conf_owner_user: "",
        ntech_data_type: "",
        ntech_owner_user: "",
        comp_data_type: "",
        comp_owner_user: "",
      },
    });

  assert.deepEqual(
    requiredErrors.map((error) => error.field),
    [
      "conf_data_type",
      "conf_owner_user",
      "ntech_data_type",
      "ntech_owner_user",
      "comp_data_type",
      "comp_owner_user",
    ],
  );
  assert.equal(requiredErrors[1].message, "기밀 소유자/사용자를 입력해 주세요.");
});

test("task form shows a popup for missing required classification metadata", () => {
  assert.match(formSource, /globalThis\.alert\?/);
  assert.match(formSource, /입력해 주세요/);
});

test("task form keeps entered metadata in the payload even when a category is not selected", () => {
  assert.match(formSource, /conf_data_type:\s*form\.elements\.conf_data_type\.value\.trim\(\)/);
  assert.match(formSource, /ntech_data_type:\s*form\.elements\.ntech_data_type\.value\.trim\(\)/);
  assert.match(formSource, /comp_data_type:\s*form\.elements\.comp_data_type\.value\.trim\(\)/);
  assert.doesNotMatch(formSource, /conf_data_type:\s*isConfidential\s*\?/);
  assert.doesNotMatch(formSource, /ntech_data_type:\s*isNationalTech\s*\?/);
  assert.doesNotMatch(formSource, /comp_data_type:\s*isCompliance\s*\?/);
});

test("selectNoneOptionsForSection checks only none options in a classification section", () => {
  assert.equal(typeof formModule.selectNoneOptionsForSection, "function");

  const firstNone = { checked: false };
  const firstPositive = { checked: true };
  const secondNone = { checked: false };
  const secondPositive = { checked: true };
  const blocks = [
    {
      querySelector: () => firstNone,
      querySelectorAll: () => [firstNone, firstPositive],
    },
    {
      querySelector: () => secondNone,
      querySelectorAll: () => [secondNone, secondPositive],
    },
  ];
  const form = {
    querySelector: (selector) => {
      assert.equal(selector, '[data-classification-section="confidential"]');
      return {
        querySelectorAll: () => blocks,
      };
    },
  };

  formModule.selectNoneOptionsForSection(form, "confidential");

  assert.equal(firstNone.checked, true);
  assert.equal(firstPositive.checked, false);
  assert.equal(secondNone.checked, true);
  assert.equal(secondPositive.checked, false);
});

test("question none option is selected by default only when no answer exists", () => {
  assert.equal(typeof formModule.isQuestionOptionSelected, "function");

  assert.equal(formModule.isQuestionOptionSelected(undefined, "해당 없음"), true);
  assert.equal(formModule.isQuestionOptionSelected([], "해당 없음"), true);
  assert.equal(formModule.isQuestionOptionSelected([], "설계 자료"), false);
  assert.equal(formModule.isQuestionOptionSelected(["설계 자료"], "해당 없음"), false);
  assert.equal(formModule.isQuestionOptionSelected(["설계 자료"], "설계 자료"), true);
});

test("task form exposes bulk none selection buttons for confidential and national tech", () => {
  assert.match(formSource, /data-action="select-none-options"/);
  assert.match(formSource, /data-none-target="\$\{type\}"/);
  assert.match(formSource, /해당 없음 일괄 선택/);
});

test("task form reserves consistent field height and keeps owner radios compact", () => {
  const styleSource = readFileSync(new URL("../css/style.css", import.meta.url), "utf8");

  assert.match(formSource, /data-error-for="sub_part"/);
  assert.match(styleSource, /input:not\(\[type="radio"\]\):not\(\[type="checkbox"\]\)/);
  assert.match(styleSource, /\.dependent-grid label:not\(\.choice-chip\)/);
  assert.match(styleSource, /\.radio-group \.choice-chip/);
  assert.match(styleSource, /input\[type="radio"\]/);
});

test("task form keeps the modal open and shows a visible error when save fails", () => {
  assert.match(formSource, /data-form-error/);
  assert.match(formSource, /try\s*{/);
  assert.match(formSource, /catch\s*\(saveError\)/);
  assert.match(formSource, /저장 실패/);
  assert.match(formSource, /saveError\.message/);
});
