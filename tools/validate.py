"""Validate primer contracts and execute the canonical YAML examples."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import cast

import yaml


class ValidationError(ValueError):
    """A document or its executable evidence violates the primer format."""


class UniqueLoader(yaml.SafeLoader):
    """Safe YAML loading without silently overwriting duplicate fields."""


def unique_mapping(loader: UniqueLoader, node: yaml.MappingNode) -> dict[object, object]:
    result: dict[object, object] = {}
    # PyYAML's stub leaves this constructor untyped; validate its output at the boundary.
    construct = cast(Callable[[yaml.Node, bool], object], loader.construct_object)
    for key_node, value_node in node.value:
        key = construct(key_node, True)
        try:
            if key in result:
                raise ValidationError(f"duplicate YAML key: {key!r}")
            result[key] = construct(value_node, True)
        except TypeError as cause:
            raise ValidationError("YAML mapping keys must be hashable scalars") from cause
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


def mapping(value: object, where: str) -> dict[str, object]:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise ValidationError(f"{where}: expected a string-keyed mapping")
    return cast(dict[str, object], value)


def items(value: object, where: str) -> list[object]:
    if not isinstance(value, list):
        raise ValidationError(f"{where}: expected a list")
    return cast(list[object], value)


def text(value: object, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{where}: expected nonempty text")
    return value


def fields(value: dict[str, object], required: set[str], optional: set[str], where: str) -> None:
    missing = required - value.keys()
    extra = value.keys() - required - optional
    if missing or extra:
        raise ValidationError(f"{where}: missing={sorted(missing)} unexpected={sorted(extra)}")


def load_document(source: str, where: str) -> dict[str, object]:
    try:
        return mapping(yaml.load(source, Loader=UniqueLoader), where)
    except yaml.YAMLError as cause:
        raise ValidationError(f"{where}: invalid YAML: {cause}") from cause


def reference(value: object, documents: dict[str, dict[str, object]], where: str) -> str:
    name = text(value, where)
    if name not in documents:
        raise ValidationError(f"{where}: unknown document {name!r}")
    return name


def validate(documents: dict[str, dict[str, object]]) -> None:
    if not documents:
        raise ValidationError("no primer YAML documents found")
    rule_ids: set[str] = set()
    example_ids: set[str] = set()
    for filename, content in documents.items():
        metadata = mapping(content.get("document"), filename)
        fields(metadata, {"name", "format", "version", "kind"}, set(), filename)
        if metadata["name"] != Path(filename).stem or metadata["format"] != "yaml" or type(metadata["version"]) is not int or metadata["version"] != 2:
            raise ValidationError(f"{filename}: expected matching name, format yaml, version 2")
        kind = metadata["kind"]
        if kind == "examples":
            fields(content, {"document", "profile", "cases"}, set(), filename)
            continue
        required = {"document", "summary", "rules", "references"}
        if kind == "common":
            required.add("policy")
            policy = mapping(content.get("policy"), filename)
            fields(policy, {"adoption", "requirement", "default", "enforcement"}, set(), filename)
            for key, value in policy.items():
                text(value, f"{filename}.policy.{key}")
        elif kind in ("language", "api_overlay"):
            required.update({"uses", "baseline", "examples"})
            text(content.get("baseline"), f"{filename}.baseline")
        else:
            raise ValidationError(f"{filename}: unknown document kind {kind!r}")
        fields(content, required, set(), filename)
        text(content["summary"], f"{filename}.summary")
        rules = items(content["rules"], filename)
        if not rules:
            raise ValidationError(f"{filename}: no rules")
        for entry in rules:
            rule = mapping(entry, filename)
            fields(rule, {"id", "level", "scope", "rule", "reason", "verification"}, set(), filename)
            for key, value in rule.items():
                text(value, f"{filename}.{key}")
            rule_id = text(rule["id"], filename)
            if not re.fullmatch(r"[A-Z]+(?:-[A-Z0-9]+)+", rule_id) or rule_id in rule_ids:
                raise ValidationError(f"{filename}: invalid or duplicate rule id {rule_id}")
            rule_ids.add(rule_id)
            if rule["level"] not in ("requirement", "default"):
                raise ValidationError(f"{filename}: unknown rule level {rule['level']!r}")
        for entry in items(content["references"], filename):
            link = mapping(entry, filename)
            fields(link, {"title", "url"}, set(), filename)
            text(link["title"], filename)
            if not text(link["url"], filename).startswith("https://"):
                raise ValidationError(f"{filename}: references must use https")

    for filename, content in documents.items():
        kind = mapping(content["document"], filename)["kind"]
        if kind in ("language", "api_overlay"):
            parents = items(content["uses"], filename)
            if not parents:
                raise ValidationError(f"{filename}: missing common policy")
            for parent in parents:
                parent_name = reference(parent, documents, filename)
                if mapping(documents[parent_name]["document"], filename)["kind"] != "common":
                    raise ValidationError(f"{filename}: uses must refer to common policy")
            examples = reference(content["examples"], documents, filename)
            if documents[examples].get("profile") != filename:
                raise ValidationError(f"{filename}: examples must link back to profile")
        if kind != "examples":
            continue
        profile = reference(content["profile"], documents, filename)
        if documents[profile].get("examples") != filename:
            raise ValidationError(f"{filename}: profile must link back to examples")
        cases = items(content["cases"], filename)
        if not cases:
            raise ValidationError(f"{filename}: no examples")
        for entry in cases:
            case = mapping(entry, filename)
            fields(case, {"id", "language", "mode", "demonstrates", "description", "code"}, {"diagnostic"}, filename)
            case_id = text(case["id"], filename)
            if not re.fullmatch(r"[A-Z]+(?:-[A-Z0-9]+)+", case_id) or case_id in example_ids:
                raise ValidationError(f"{filename}: invalid or duplicate example id {case_id}")
            example_ids.add(case_id)
            for key in ("description", "code"):
                text(case[key], f"{filename}.{case_id}.{key}")
            if case["language"] not in ("cpp", "csharp", "python", "rust"):
                raise ValidationError(f"{case_id}: unknown language")
            mode = case["mode"]
            if mode not in ("run", "compile_fail", "type_fail", "illustrative"):
                raise ValidationError(f"{case_id}: unknown example mode {mode!r}")
            if (mode == "type_fail" and case["language"] != "python") or (mode == "compile_fail" and case["language"] == "python"):
                raise ValidationError(f"{case_id}: failure mode does not match language")
            if mode in ("compile_fail", "type_fail"):
                text(case.get("diagnostic"), f"{case_id}.diagnostic")
            elif "diagnostic" in case:
                raise ValidationError(f"{case_id}: only rejected examples have diagnostics")
            demonstrated = items(case["demonstrates"], case_id)
            if not demonstrated:
                raise ValidationError(f"{case_id}: no demonstrated rule")
            for demonstrated_id in demonstrated:
                if text(demonstrated_id, case_id) not in rule_ids:
                    raise ValidationError(f"{case_id}: unknown rule {demonstrated_id!r}")


def command(args: Sequence[str], directory: Path, *, reject: str | None = None) -> None:
    environment = os.environ.copy()
    environment["PYTHONOPTIMIZE"] = "0"  # The runnable specimens deliberately assert behavior.
    environment["DOTNET_CLI_UI_LANGUAGE"] = "en-US"
    try:
        completed = subprocess.run(args, cwd=directory, env=environment, capture_output=True, text=True, timeout=120, check=False)
    except (OSError, subprocess.TimeoutExpired) as cause:
        raise ValidationError(f"could not execute {args[0]}: {cause}") from cause
    output = completed.stdout + completed.stderr
    if reject is not None:
        if completed.returncode == 0 or reject not in output:
            raise ValidationError(f"expected rejection containing {reject!r}: {list(args)}\n{output}")
    elif completed.returncode != 0:
        raise ValidationError(f"command failed ({completed.returncode}): {list(args)}\n{output}")


def execute(case: dict[str, object], directory: Path) -> None:
    language = text(case["language"], "language")
    mode = text(case["mode"], "mode")
    diagnostic = text(case["diagnostic"], "diagnostic") if mode in ("compile_fail", "type_fail") else None
    suffix = {"cpp": ".cpp", "csharp": ".cs", "python": ".py", "rust": ".rs"}[language]
    source = directory / ("Program" + suffix)
    source.write_text(text(case["code"], "code"), encoding="utf-8")
    executable = directory / ("example.exe" if os.name == "nt" else "example")
    if language == "cpp":
        compiler = os.environ.get("CXX", "g++")
        resolved = shutil.which(compiler)
        if resolved is None:
            raise ValidationError(f"C++ compiler not found: {compiler}; CXX must name one executable")
        command([resolved, "-std=c++23", "-Wall", "-Wextra", "-Wconversion", "-Werror", "-pedantic-errors", str(source), "-o", str(executable)], directory, reject=diagnostic)
    elif language == "rust":
        command(["rustc", "--edition=2024", "-D", "warnings", str(source), "-o", str(executable)], directory, reject=diagnostic)
    elif language == "python":
        command([sys.executable, "-m", "mypy", "--strict", "--python-version", "3.10", "--no-incremental", "--cache-dir", str(directory / "mypy-cache"), str(source)], directory, reject=diagnostic)
        if mode == "run":
            command([sys.executable, "-B", str(source)], directory)
        return
    else:
        project = directory / "Example.csproj"
        project.write_text(
            '<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup>'
            '<OutputType>Exe</OutputType><TargetFramework>net10.0</TargetFramework>'
            '<LangVersion>14.0</LangVersion><Nullable>enable</Nullable>'
            '<TreatWarningsAsErrors>true</TreatWarningsAsErrors>'
            '<ImplicitUsings>disable</ImplicitUsings>'
            '</PropertyGroup></Project>', encoding="utf-8")
        command(["dotnet", "build", str(project), "--nologo", "-v:q", "-m:1", "-nr:false", "-p:UseSharedCompilation=false"], directory, reject=diagnostic)
        if mode == "run":
            command(["dotnet", str(directory / "bin/Debug/net10.0/Example.dll")], directory)
        return
    if mode == "run":
        command([str(executable)], directory)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--examples", nargs="+", choices=["cpp", "csharp", "python", "rust", "all"])
    options = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    try:
        documents = {path.name: load_document(path.read_text(encoding="utf-8"), path.name)
                     for path in sorted(root.glob("*-primer*.yaml"))}
        validate(documents)
        rules = sum(len(items(value["rules"], name)) for name, value in documents.items() if "rules" in value)
        print(f"PASS: {len(documents)} YAML documents; {rules} rules; references and example classifications valid", flush=True)
        if not options.examples:
            print("Examples not executed (use --examples all).")
            return 0
        selected = set(options.examples)
        executed = rejected = illustrative = 0
        with tempfile.TemporaryDirectory(prefix="primer-check-") as temporary:
            for content in documents.values():
                for entry in items(content.get("cases", []), "cases"):
                    case = mapping(entry, "case")
                    if "all" not in selected and case["language"] not in selected:
                        continue
                    if case["mode"] == "illustrative":
                        illustrative += 1
                        print(f"ILLUSTRATIVE (not executed): {case['id']}", flush=True)
                        continue
                    directory = Path(temporary) / text(case["id"], "id")
                    directory.mkdir()
                    execute(case, directory)
                    executed += case["mode"] == "run"
                    rejected += case["mode"] in ("compile_fail", "type_fail")
                    print(f"PASS {case['mode']}: {case['id']}", flush=True)
        print(f"PASS: {executed} programs ran; {rejected} intended rejections; {illustrative} illustrative recipes not executed")
        print("Vulkan GPU execution, other compilers/ABIs, and unrepresented rule behavior are not qualified by these examples.")
        return 0
    except (ValidationError, OSError) as cause:
        print(f"FAIL: {cause}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
