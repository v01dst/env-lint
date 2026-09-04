"""env-lint — validate .env files: syntax, duplicates, secrets hygiene. Pure stdlib."""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass, field

EXPORT_RE = re.compile(r"^export\s+")
LINE_RE = re.compile(r"^(?P<key>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?P<value>.*)$")
KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

SECRET_HINTS = ("secret", "token", "password", "passwd", "api_key", "apikey", "private_key", "access_key", "auth")

COMMON_TRUE = {"true", "1", "yes", "on"}
COMMON_FALSE = {"false", "0", "no", "off"}


@dataclass
class Issue:
    line: int
    severity: str  # "error" | "warning"
    rule: str
    message: str

    def format(self, path: str) -> str:
        return f"{path}:{self.line}: {self.severity}: [{self.rule}] {self.message}"


@dataclass
class LintResult:
    issues: list[Issue] = field(default_factory=list)
    vars_seen: dict[str, int] = field(default_factory=dict)

    @property
    def errors(self) -> int:
        return sum(1 for i in self.issues if i.severity == "error")

    @property
    def warnings(self) -> int:
        return sum(1 for i in self.issues if i.severity == "warning")


def strip_inline_comment(value: str) -> str:
    if value.startswith(("'", '"')):
        quote = value[0]
        end = value.find(quote, 1)
        if end != -1:
            return value
    for marker in (" #", "\t#"):
        idx = value.find(marker)
        if idx != -1:
            return value[:idx]
    return value


def looks_like_secret(key: str) -> bool:
    k = key.lower()
    return any(h in k for h in SECRET_HINTS)


def lint_env(content: str) -> LintResult:
    result = LintResult()
    seen: dict[str, tuple[int, str]] = {}
    lines = content.split("\n")

    for lineno, raw in enumerate(lines, start=1):
        line = raw.strip()

        if not line or line.startswith("#"):
            continue

        line = EXPORT_RE.sub("", line)

        if "=" not in line:
            result.issues.append(
                Issue(lineno, "error", "syntax", f"expected KEY=VALUE, got: {raw.strip()[:60]}")
            )
            continue

        m = LINE_RE.match(line)
        if not m:
            result.issues.append(
                Issue(lineno, "error", "key-format", f"invalid key in: {line[:60]}")
            )
            continue

        key = m.group("key")
        value = m.group("value")
        result.vars_seen[key] = result.vars_seen.get(key, 0) + 1

        if key in seen:
            result.issues.append(
                Issue(lineno, "error", "duplicate-key", f"'{key}' already defined on line {seen[key][0]}")
            )
        else:
            seen[key] = (lineno, value)

        if looks_like_secret(key) and value not in ("", '""', "''"):
            if len(value) < 8:
                result.issues.append(
                    Issue(lineno, "warning", "weak-secret", f"'{key}' looks like a secret but is shorter than 8 chars")
                )
            if not (value.startswith(("'", '"')) or "${" in value) and (" " in value):
                result.issues.append(
                    Issue(lineno, "warning", "unquoted-secret", f"'{key}' contains spaces and is unquoted")
                )

        if value.startswith('"') and not value.rstrip().endswith('"') and len(value) < 2:
            result.issues.append(Issue(lineno, "error", "unterminated-quote", "quote never closed"))

        if value.count('"') % 2 == 1 and value.startswith('"'):
            result.issues.append(Issue(lineno, "error", "unterminated-quote", f"odd number of quotes in '{key}'"))

        if (
            value == value.lower()
            and value.isalpha()
            and len(value) > 3
            and key.isupper()
            and value not in COMMON_TRUE
            and value not in COMMON_FALSE
        ):
            result.issues.append(
                Issue(lineno, "warning", "suspicious-value", f"'{key}' is uppercase but its value looks like a word — misplaced value?")
            )

    result.issues.sort(key=lambda i: (i.line, i.rule))
    return result


def compare_with_example(env_content: str, example_path: str) -> list[Issue]:
    issues: list[Issue] = []
    try:
        with open(example_path, encoding="utf-8") as f:
            example_content = f.read()
    except OSError as e:
        return [Issue(0, "warning", "example-missing", f"cannot read {example_path}: {e}")]

    def keys_of(text: str) -> set[str]:
        out = set()
        for raw in text.split("\n"):
            line = EXPORT_RE.sub("", raw.strip())
            if not line or line.startswith("#"):
                continue
            m = LINE_RE.match(line)
            if m:
                out.add(m.group("key"))
        return out

    env_keys = keys_of(env_content)
    example_keys = keys_of(example_content)
    for key in sorted(example_keys - env_keys):
        issues.append(Issue(0, "warning", "missing-in-env", f"'{key}' declared in example but missing from env"))
    for key in sorted(env_keys - example_keys):
        issues.append(Issue(0, "warning", "extra-in-env", f"'{key}' set in env but not declared in example"))
    return issues


def lint_file(path: str, example: str | None = None) -> LintResult:
    try:
        with open(path, encoding="utf-8") as f:
            content = f.read()
    except OSError as e:
        result = LintResult()
        result.issues.append(Issue(0, "error", "io", str(e)))
        return result
    result = lint_env(content)
    if example:
        result.issues.extend(compare_with_example(content, example))
    result.issues.sort(key=lambda i: (i.line, i.rule))
    return result


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    path = ".env"
    example: str | None = None
    strict = False
    as_json = False

    i = 0
    while i < len(args):
        a = args[i]
        if a in ("-f", "--file") and i + 1 < len(args):
            path = args[i + 1]
            i += 2
            continue
        if a in ("-e", "--example") and i + 1 < len(args):
            example = args[i + 1]
            i += 2
            continue
        if a in ("-s", "--strict"):
            strict = True
            i += 1
            continue
        if a == "--json":
            as_json = True
            i += 1
            continue
        if a in ("-h", "--help"):
            print("env-lint [-f FILE] [-e EXAMPLE] [--strict] — validate .env files")
            return 0
        path = a
        i += 1

    result = lint_file(path, example)
    if as_json:
        print(
            json.dumps(
                {
                    "file": path,
                    "vars": len(result.vars_seen),
                    "errors": result.errors,
                    "warnings": result.warnings,
                    "issues": [
                        {"line": i.line, "severity": i.severity, "rule": i.rule, "message": i.message}
                        for i in result.issues
                    ],
                },
                indent=2,
            )
        )
        return 1 if result.errors or (strict and result.warnings) else 0
    for issue in result.issues:
        print(issue.format(path))
    if not result.issues:
        print(f"✓ {path}: {len(result.vars_seen)} vars, no issues")

    code = 0
    if result.errors:
        code = 1
    if strict and result.warnings:
        code = 1
    return code


if __name__ == "__main__":
    sys.exit(main())
