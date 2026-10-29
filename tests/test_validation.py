"""Regression checks for malformed documents and misleading example evidence."""

from copy import deepcopy
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from tools.validate import ValidationError, command, items, load_document, mapping, validate


ROOT = Path(__file__).resolve().parents[1]


class Documents(unittest.TestCase):
    def setUp(self) -> None:
        self.documents = {path.name: load_document(path.read_text(encoding="utf-8"), path.name)
                          for path in ROOT.glob("*-primer*.yaml")}

    def test_current_corpus(self) -> None:
        validate(self.documents)

    def test_duplicate_key_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValidationError, "duplicate YAML key"):
            load_document("document: {name: first, name: overwritten}", "duplicate")

    def test_invalid_yaml_has_a_named_diagnostic(self) -> None:
        with self.assertRaisesRegex(ValidationError, "broken: invalid YAML"):
            load_document("key: [unterminated", "broken")

    def test_unsafe_yaml_tags_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValidationError, "invalid YAML"):
            load_document("!!python/object:invalid {}", "unsafe")

    def test_bad_profile_schema_is_rejected(self) -> None:
        for key, value in (("rules", []), ("baseline", ""), ("uses", []), ("examples", "missing.yaml")):
            with self.subTest(key=key):
                documents = deepcopy(self.documents)
                documents["cpp-primer.yaml"][key] = value
                with self.assertRaises(ValidationError):
                    validate(documents)

    def test_metadata_version_must_be_integer(self) -> None:
        metadata = mapping(self.documents["cpp-primer.yaml"]["document"], "metadata")
        metadata["version"] = "2"
        with self.assertRaisesRegex(ValidationError, "version 2"):
            validate(self.documents)

    def test_examples_must_link_back(self) -> None:
        self.documents["cpp-primer-examples.yaml"]["profile"] = "rust-primer.yaml"
        with self.assertRaisesRegex(ValidationError, "link back"):
            validate(self.documents)

    def test_rule_failures_are_rejected(self) -> None:
        original = items(self.documents["cpp-primer.yaml"]["rules"], "rules")
        for key, value in (("level", "banned"), ("verification", ""), ("id", "not a stable id"), ("extra", "unknown")):
            with self.subTest(key=key):
                documents = deepcopy(self.documents)
                rule = mapping(items(documents["cpp-primer.yaml"]["rules"], "rules")[0], "rule")
                rule[key] = value
                with self.assertRaises(ValidationError):
                    validate(documents)
        original.append(deepcopy(original[0]))
        with self.assertRaisesRegex(ValidationError, "duplicate rule"):
            validate(self.documents)

    def test_example_failures_are_rejected(self) -> None:
        mutations = (("mode", "bad"), ("language", "unknown"), ("demonstrates", ["MISSING-RULE"]),
                     ("mode", "type_fail"), ("diagnostic", "not a rejected example"), ("code", ""))
        for key, value in mutations:
            with self.subTest(key=key, value=value):
                documents = deepcopy(self.documents)
                case = mapping(items(documents["cpp-primer-examples.yaml"]["cases"], "cases")[0], "case")
                case[key] = value
                with self.assertRaises(ValidationError):
                    validate(documents)


class Execution(unittest.TestCase):
    def test_success_is_not_an_expected_rejection(self) -> None:
        result = subprocess.CompletedProcess(["compiler"], 0, "CS9176", "")
        with patch("tools.validate.subprocess.run", return_value=result):
            with self.assertRaisesRegex(ValidationError, "expected rejection"):
                command(["compiler"], ROOT, reject="CS9176")

    def test_unrelated_failure_is_not_an_expected_rejection(self) -> None:
        result = subprocess.CompletedProcess(["compiler"], 1, "SDK missing", "")
        with patch("tools.validate.subprocess.run", return_value=result):
            with self.assertRaisesRegex(ValidationError, "expected rejection"):
                command(["compiler"], ROOT, reject="CS9176")

    def test_intended_rejection_is_accepted(self) -> None:
        result = subprocess.CompletedProcess(["compiler"], 1, "error CS9176", "")
        with patch("tools.validate.subprocess.run", return_value=result):
            command(["compiler"], ROOT, reject="CS9176")

    def test_missing_tool_is_an_execution_failure(self) -> None:
        with patch("tools.validate.subprocess.run", side_effect=FileNotFoundError("missing compiler")):
            with self.assertRaisesRegex(ValidationError, "could not execute"):
                command(["compiler"], ROOT, reject="CS9176")

    def test_timeout_is_an_execution_failure(self) -> None:
        with patch("tools.validate.subprocess.run", side_effect=subprocess.TimeoutExpired("compiler", 120)):
            with self.assertRaisesRegex(ValidationError, "could not execute"):
                command(["compiler"], ROOT, reject="CS9176")

    def test_real_runtime_failure_is_a_failure(self) -> None:
        with tempfile.TemporaryDirectory(prefix="primer-test-") as temporary:
            with self.assertRaisesRegex(ValidationError, "command failed"):
                command([sys.executable, "-c", "raise RuntimeError('regression')"], Path(temporary))

    def test_assertions_remain_enabled(self) -> None:
        with patch.dict("os.environ", {"PYTHONOPTIMIZE": "2"}):
            with self.assertRaisesRegex(ValidationError, "command failed"):
                command([sys.executable, "-c", "assert False, 'must execute'"], ROOT)


if __name__ == "__main__":
    unittest.main()
