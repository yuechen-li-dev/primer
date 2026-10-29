# Language primers

Coding contracts for humans and coding agents. The aim is code whose ownership,
state, failure, and effects are apparent from nearby code, supported by the
language's types and appropriate checks.

The primers are ordinary **YAML**, not a separate “toon” format. They prescribe a
modern, practical subset without treating features as inherently suspect. A rule
must address a concrete failure mode and explain how to check it. No prose file,
compiler, or test suite guarantees that arbitrary programs are correct.

## Use a primer

Read [common-primer.yaml](common-primer.yaml), then the applicable profile and
examples. For Vulkan, also read the implementation language's profile.

| Profile | Focus | Examples |
| --- | --- | --- |
| [C++](cpp-primer.yaml) | C++23, `std::expected`, RAII, concepts, lifetime and ABI contracts | [C++ examples](cpp-primer-examples.yaml) |
| [C#](csharp-primer.yaml) | Nullability, domain types, disposal, owned async work | [C# examples](csharp-primer-examples.yaml) |
| [Python](python-primer.yaml) | Static types plus runtime validation, resources and effects | [Python examples](python-primer-examples.yaml) |
| [Rust](rust-primer.yaml) | Ownership, `Result`, enums, traits, unsafe and async contracts | [Rust examples](rust-primer-examples.yaml) |
| [Vulkan overlay](vulkan-primer.yaml) | Device capabilities, GPU lifetime, synchronization, presentation | [Host checks and review recipe](vulkan-primer-examples.yaml) |

Keep repository-specific architecture, build commands, supported targets, and
workflow instructions in `AGENTS.md`. Add references such as:

```markdown
Read primer/common-primer.yaml and primer/cpp-primer.yaml before changing C++.
Use primer/vulkan-primer.yaml for Vulkan changes. Read the linked examples as needed.
```

Place a versioned copy of the files at those paths, or use an explicitly pinned
dependency. Reading a profile includes its `uses` files. Primers complement local
instructions; surface a genuine conflict instead of silently changing policy.
The example toolchains are qualification fixtures, not compulsory upgrades for
every adopting repository. A declared older baseline needs an explicit supported
adapter or limit, especially for C++23 library facilities.

## Read the rules

Every rule has a stable `id`, a `level`, a `scope`, the `rule`, its `reason`, and
`verification` guidance:

- **requirement**: a correctness obligation within the stated scope. Satisfy it or
  report the unresolved failure with evidence.
- **default**: the usual design choice. A concrete domain or repository need can
  justify a different choice; explain the tradeoff without an approval ritual.

For example, C++ defaults to `[[nodiscard]] std::expected<T, E>` for recoverable
errors with a reason. It still requires an explicit exception policy: `expected`
does not make allocating or library code nonthrowing. Concepts, ranges, explicit
object parameters, and other supported tools are available when they clarify the
contract. A borrow's lifetime and a narrowing conversion's range still need proof.

The same goals use each language's own error and resource conventions; there is
no requirement to build a common Result framework across languages.

## Validate changes

Use Python 3.10+ and an isolated environment:

```sh
python -m venv .venv
# Activate .venv for your shell, or invoke its Python executable directly.
python -m pip install -r requirements-dev.txt
python tools/validate.py
python -m unittest discover -s tests -v
python -m mypy --strict tools/validate.py
python tools/validate.py --examples all
```

On PowerShell, activation is `.\.venv\Scripts\Activate.ps1`; on POSIX shells,
use `. .venv/bin/activate`. Activation is optional: `.\.venv\Scripts\python.exe`
and `.venv/bin/python` select the environment directly.

Example execution needs GCC 13+ with C++23 monadic `<expected>` support (`g++`, or an executable
selected by `CXX`), .NET SDK 10.x, and Rust 1.85+ with edition 2024. Individual lanes
are available with `--examples cpp`, `csharp`, `python`, or `rust`. The C++ lane also
includes Vulkan host examples. Missing tools fail the requested lane; structure-only
validation explicitly reports that examples were not executed.

The validator rejects duplicate YAML keys, malformed fields, unknown rule IDs,
broken profile/example links, and unclassified examples. It extracts the **actual
YAML code**, so separate test copies cannot drift:

- `run`: compile/type-check as appropriate, then run the complete program and its
  behavioral assertions. C++ and Rust warnings are errors; C# enables nullable
  analysis and warnings as errors; Python uses strict mypy checking.
- `compile_fail` / `type_fail`: require a nonzero result **and the intended diagnostic**.
  An unrelated missing tool or SDK is not a passing negative test.
- `illustrative`: visibly reported as unexecuted. These are review recipes, not
  runnable programs or qualification evidence.

CI runs these checks on Linux and Windows. The C++ example runner uses GCC; it
does not establish MSVC/Clang, sanitizer, or ABI qualification. Host-only Vulkan
tests do not establish shader validity, GPU synchronization, rendering, WSI, or
device-loss recovery. Those require the real target and the profile's runtime checks.
Rules without an executable example still require their stated review/runtime evidence.

## Contribute or migrate

Version 2 renames the former `*-primer.md` and `*-primer-examples.md` documents to
`.yaml`; the extensionless `vulkan-primer-examples` becomes
`vulkan-primer-examples.yaml`. C# is converted from Markdown into the same rule
schema, and gains an example file. `common-primer.yaml` holds shared obligations.
Update references in adopting repositories when deliberately upgrading their copy;
renaming upstream does not update vendored copies automatically.

This is a content revision, not a byte-preserving extension change. It replaces
repetitive feature bans with scoped contracts, raises the default C++ baseline
from C++20 to C++23, and replaces unqualified fragments with complete checked
examples and explicitly labelled recipes. Version 1 remains available in Git history.

When changing a primer, keep IDs stable for the same obligation, give each new
rule a concrete failure mode and verification, and update the canonical example
when useful. Add languages only with their own idioms, baseline, and checks.
Do not label a new API overlay as a language or introduce cross-language bans
that conflict with the host language's normal contracts. Use primary documentation
in `references` for subtle or version-sensitive claims and run the checks above.
