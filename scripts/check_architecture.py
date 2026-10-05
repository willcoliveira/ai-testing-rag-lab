"""Architecture rules, checked on the source tree with the ast module.

1. `raglab.core` imports the standard library and `raglab.core` only.
2. Vendor SDKs are imported only inside `raglab.adapters`, statically or through importlib.

Usage: python scripts/check_architecture.py [package_dir]   (default: src/raglab)
Prints one line per violation and exits 1 if there are any.
"""

import ast
import sys
from dataclasses import dataclass
from pathlib import Path

VENDORS = frozenset(
    {
        "anthropic",
        "boto3",
        "botocore",
        "deepeval",
        "guardrails",
        "ollama",
        "openai",
        "qdrant_client",
    }
)
DYNAMIC_IMPORTERS = frozenset({"import_module", "__import__"})


@dataclass(frozen=True)
class Violation:
    path: Path
    line: int
    message: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line}: {self.message}"


def _module_parts(package_dir: Path, file: Path) -> list[str]:
    rel = file.relative_to(package_dir.parent).with_suffix("")
    parts = list(rel.parts)
    if parts[-1] == "__init__":
        parts.pop()
    return parts


def _resolve_relative(
    module_parts: list[str], is_package: bool, level: int, name: str | None
) -> str:
    package = module_parts if is_package else module_parts[:-1]
    base = package[: len(package) - (level - 1)] if level > 1 else package
    return ".".join([*base, *([name] if name else [])])


def _imported_modules(tree: ast.Module, module_parts: list[str], is_package: bool):
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield node.lineno, alias.name
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                yield (
                    node.lineno,
                    _resolve_relative(module_parts, is_package, node.level, node.module),
                )
            elif node.module:
                yield node.lineno, node.module
        elif isinstance(node, ast.Call):
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
            arg = node.args[0] if node.args else None
            if (
                name in DYNAMIC_IMPORTERS
                and isinstance(arg, ast.Constant)
                and isinstance(arg.value, str)
            ):
                yield node.lineno, arg.value


def check(package_dir: Path) -> list[Violation]:
    violations: list[Violation] = []
    root_name = package_dir.name
    for file in sorted(package_dir.rglob("*.py")):
        parts = _module_parts(package_dir, file)
        layer = parts[1] if len(parts) > 1 else ""
        tree = ast.parse(file.read_text(encoding="utf-8"), filename=str(file))
        for line, module in _imported_modules(tree, parts, file.name == "__init__.py"):
            top = module.split(".")[0]
            if layer == "core":
                inside_core = module == f"{root_name}.core" or module.startswith(
                    f"{root_name}.core."
                )
                if top not in sys.stdlib_module_names and not inside_core:
                    violations.append(
                        Violation(
                            file,
                            line,
                            f"core may import only the standard library and {root_name}.core,"
                            f" not {module}",
                        )
                    )
            if layer != "adapters" and top in VENDORS:
                violations.append(
                    Violation(
                        file, line, f"vendor SDK {top} is imported outside {root_name}.adapters"
                    )
                )
    return violations


def main(argv: list[str]) -> int:
    package_dir = Path(argv[1]) if len(argv) > 1 else Path("src/raglab")
    if not package_dir.is_dir():
        print(f"no such package directory: {package_dir}", file=sys.stderr)
        return 2
    violations = check(package_dir)
    for violation in violations:
        print(violation)
    print(f"{len(violations)} architecture violations in {package_dir}")
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
