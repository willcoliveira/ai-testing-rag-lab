"""Architecture rules, checked on the source tree with the ast module.

1. `raglab.core` imports the standard library and `raglab.core` only.
2. Vendor SDKs are imported only inside `raglab.adapters`, statically or through importlib.
   `__import__` is always an importer; `import_module` only when it is importlib's (imported from
   importlib, or called on a name bound to the importlib module), so a function of the file that
   happens to share the name is not one.

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
IMPORTLIB = "importlib"


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
    if level - 1 >= len(package):
        return "." * level + (name or "")  # above the top package: shown as written
    base = package[: len(package) - (level - 1)] if level > 1 else package
    return ".".join([*base, *([name] if name else [])])


COMPUTED = "<computed name>"


@dataclass(frozen=True)
class _Importers:
    functions: frozenset[str]  # names bound to __import__ or importlib.import_module
    modules: frozenset[str]  # names bound to the importlib module


def _assignments(tree: ast.Module) -> list[tuple[str, ast.expr]]:
    """`name = value` bindings anywhere in the file (scopes are not told apart)."""
    pairs: list[tuple[str, ast.expr]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            pairs.extend((t.id, node.value) for t in node.targets if isinstance(t, ast.Name))
        elif (
            isinstance(node, ast.AnnAssign | ast.NamedExpr)
            and node.value is not None
            and isinstance(node.target, ast.Name)
        ):
            pairs.append((node.target.id, node.value))
    return pairs


def _importers(tree: ast.Module) -> _Importers:
    """The names in this file that import a module by a runtime name: __import__ always,
    importlib.import_module through any import or simple assignment that binds it."""
    functions = {"__import__"}
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == IMPORTLIB:
                    modules.add(alias.asname or IMPORTLIB)
                elif alias.name.startswith(f"{IMPORTLIB}.") and not alias.asname:
                    modules.add(IMPORTLIB)  # `import importlib.util` binds importlib
        elif isinstance(node, ast.ImportFrom) and node.module == IMPORTLIB and not node.level:
            for alias in node.names:
                if alias.name in ("import_module", "*"):
                    functions.add(alias.asname or "import_module")
    # loader = importlib; im = importlib.import_module; im2 = im
    assignments = _assignments(tree)
    changed = True
    while changed:
        changed = False
        for name, value in assignments:
            if isinstance(value, ast.Name) and value.id in modules:
                target = modules
            elif (isinstance(value, ast.Name) and value.id in functions) or (
                isinstance(value, ast.Attribute)
                and value.attr == "import_module"
                and isinstance(value.value, ast.Name)
                and value.value.id in modules
            ):
                target = functions
            else:
                continue
            if name not in target:
                target.add(name)
                changed = True
    return _Importers(frozenset(functions), frozenset(modules))


def _is_importer_call(func: ast.expr, importers: _Importers) -> bool:
    if isinstance(func, ast.Name):
        return func.id in importers.functions
    if not isinstance(func, ast.Attribute):
        return False
    if func.attr == "__import__":  # builtins.__import__
        return True
    if func.attr != "import_module":
        return False
    receiver = func.value
    if isinstance(receiver, ast.Name):
        return receiver.id in importers.modules
    # __import__("importlib").import_module(...)
    return isinstance(receiver, ast.Call) and _is_importer_call(receiver.func, importers)


def _imported_modules(tree: ast.Module, module_parts: list[str], is_package: bool):
    importers = _importers(tree)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield node.lineno, alias.name
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.module is None:
                # `from .. import x`: each name is a module
                for alias in node.names:
                    yield (
                        node.lineno,
                        _resolve_relative(module_parts, is_package, node.level, alias.name),
                    )
            elif node.level:
                yield (
                    node.lineno,
                    _resolve_relative(module_parts, is_package, node.level, node.module),
                )
            elif node.module:
                yield node.lineno, node.module
        elif isinstance(node, ast.Call):
            if not _is_importer_call(node.func, importers):
                continue
            arg = node.args[0] if node.args else None
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                yield node.lineno, arg.value
            else:
                yield node.lineno, COMPUTED


def check(package_dir: Path) -> list[Violation]:
    violations: list[Violation] = []
    root_name = package_dir.name
    for file in sorted(package_dir.rglob("*.py")):
        parts = _module_parts(package_dir, file)
        layer = parts[1] if len(parts) > 1 else ""
        tree = ast.parse(file.read_text(encoding="utf-8"), filename=str(file))
        for line, module in _imported_modules(tree, parts, file.name == "__init__.py"):
            if module == COMPUTED:
                if layer != "adapters":
                    violations.append(
                        Violation(
                            file,
                            line,
                            f"dynamic import with a computed name outside {root_name}.adapters;"
                            " use a static import",
                        )
                    )
                continue
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
