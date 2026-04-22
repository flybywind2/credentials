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
