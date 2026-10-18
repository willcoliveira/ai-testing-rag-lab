"""Architecture rules, checked on the source tree with the ast module.

1. `raglab.core` imports the standard library and `raglab.core` only.
2. Vendor SDKs are imported only inside `raglab.adapters`, statically or by a module name given
   at run time.
3. File-format parsers (pypdf, pytesseract, pyyaml, Pillow) are imported only inside
   `raglab.ingest`: they are not vendor SDKs, but the rest of raglab works on parsed documents.
4. The fake adapters (`raglab.adapters.fake`: HashingEmbedder, FakeChat) are imported only by
   `raglab.adapters.factory`, which builds FakeChat when a config says `provider = "fake"` (S3
   decision; before S3 no module imported them). A fake run has provenance fake and is never
   published; the unit tests import the module directly.
5. HTTP clients (httpx and the like) are imported only inside `raglab.adapters`, and the web
   framework (FastAPI, Starlette, uvicorn) only inside `raglab.api` (S3).

A run-time import is found by the call, not by tracking what importlib is bound to (S0 judge round
3: `importlib = __import__('importlib')`, `il, x = importlib, 1` or `sys.modules['importlib']`
bound it out of sight of a binding tracker):
- any call of an attribute named `import_module`, `__import__`, `find_spec` (importlib.util, whose
  spec `module_from_spec` and `exec_module` then load), `resolve_name` (pkgutil) or `run_module`
  (runpy), or of `getattr(<anything>, '<one of those>')`;
- a bare call of `__import__`, of one of the other names unless the file defines a function of
  that name (a local helper of that name is not an importer), or of a name an import or an
  assignment (simple, tuple or `:=`) binds to one of those;
- `sys.modules[...]` and `sys.modules.get/pop/setdefault(...)`, with sys bound by an import, an
  assignment or a run-time import of 'sys' (S0 judge round 3, D6).
The module name is the first argument (or `name=`, `mod_name=`, `fullname=`; the part before `:`
for `pkg.mod:obj`; a relative name is resolved against a literal `package`): a string literal names
the module, `__name__` and `__package__` name this module, anything else is a computed name,
reported outside `raglab.adapters`. A method of one of those names, called outside adapters with a
computed name, is reported too; rename it. A string that is only data (provider = "openai") is
never an import. Out of reach: loading by file path (spec_from_file_location, SourceFileLoader),
exec and eval (bandit flags those), and names reached through vars() or __dict__.

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
        "fastembed",
        "guardrails",
        "httpx",
        "huggingface_hub",
        "ollama",
        "onnxruntime",
        "openai",
        "qdrant_client",
    }
)


# file-format libraries, by import name: allowed only in raglab.ingest (rule 3)
PARSERS = frozenset({"pypdf", "pytesseract", "yaml", "PIL"})

# fake adapters, by module name relative to the package, and the one module that may import
# them (rule 4)
TEST_ONLY = frozenset({"adapters.fake"})
FAKE_IMPORTER = "adapters.factory"

# HTTP clients: only in raglab.adapters (rule 5); httpx is also in VENDORS
HTTP_CLIENTS = frozenset({"httpx", "aiohttp", "urllib3"})
# the web framework: only in raglab.api (rule 5)
WEB = frozenset({"fastapi", "starlette", "uvicorn"})


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
IMPORTERS = frozenset({"import_module", "__import__", "find_spec", "resolve_name", "run_module"})
NAME_KEYWORDS = frozenset({"name", "mod_name", "fullname"})
SYS_MODULES_METHODS = frozenset({"get", "pop", "setdefault"})
# names that hold this module's own name, not a vendor's
SELF_NAMES = frozenset({"__name__", "__package__"})


@dataclass(frozen=True)
class _Bindings:
    importers: frozenset[str]  # bare names that call an importer
    sys_names: frozenset[str]  # names bound to the sys module
    sys_modules: frozenset[str]  # names bound to sys.modules


def _pairs(target: ast.expr, value: ast.expr) -> list[tuple[str, ast.expr]]:
    """`name = value` pairs of one binding, tuple and list unpacking included."""
    if isinstance(target, ast.Name):
        return [(target.id, value)]
    if (
        isinstance(target, ast.Tuple | ast.List)
        and isinstance(value, ast.Tuple | ast.List)
        and len(target.elts) == len(value.elts)
    ):
        return [p for t, v in zip(target.elts, value.elts, strict=True) for p in _pairs(t, v)]
    return []


def _assignments(tree: ast.Module) -> list[tuple[str, ast.expr]]:
    """Bindings by assignment anywhere in the file (scopes are not told apart)."""
    pairs: list[tuple[str, ast.expr]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                pairs.extend(_pairs(target, node.value))
        elif isinstance(node, ast.AnnAssign | ast.NamedExpr) and node.value is not None:
            pairs.extend(_pairs(node.target, node.value))
    return pairs


def _local_functions(tree: ast.Module) -> frozenset[str]:
    """Functions the file defines outside a class body (a method is called as an attribute)."""
    methods = {
        id(item) for node in ast.walk(tree) if isinstance(node, ast.ClassDef) for item in node.body
    }
    return frozenset(
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and id(node) not in methods
    )


def _is_getattr_importer(node: ast.expr) -> bool:
    """getattr(<anything>, 'import_module')"""
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "getattr"
        and len(node.args) >= 2
        and isinstance(node.args[1], ast.Constant)
        and node.args[1].value in IMPORTERS
    )


def _importer_names(tree: ast.Module) -> frozenset[str]:
    """The bare names that call an importer in this file."""
    local = _local_functions(tree)
    names = {"__import__", *(name for name in IMPORTERS if name not in local)}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            names.update(
                alias.asname or alias.name for alias in node.names if alias.name in IMPORTERS
            )
    # im = importlib.import_module; im2 = im; im3, x = im2, 1
    assignments = _assignments(tree)
    changed = True
    while changed:
        changed = False
        for name, value in assignments:
            if name not in names and _calls_an_importer(value, frozenset(names)):
                names.add(name)
                changed = True
    return frozenset(names)


def _calls_an_importer(func: ast.expr, names: frozenset[str]) -> bool:
    if isinstance(func, ast.Name):
        return func.id in names
    if isinstance(func, ast.Attribute):
        return func.attr in IMPORTERS
    return _is_getattr_importer(func)


def _module_name(node: ast.expr | None) -> str | None:
    """A string literal names the module; __name__ and __package__ this module (None, not
    reported); anything else is COMPUTED."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name) and node.id in SELF_NAMES:
        return None
    return COMPUTED


def _module_argument(call: ast.Call) -> str | None:
    """The module a run-time import names: its first argument, or name=, mod_name=, fullname=."""
    arg = (
        call.args[0]
        if call.args
        else next((k.value for k in call.keywords if k.arg in NAME_KEYWORDS), None)
    )
    name = _module_name(None if isinstance(arg, ast.Starred) else arg)
    if name is None or name == COMPUTED:
        return name
    name = name.split(":")[0]  # pkgutil.resolve_name("pkg.mod:obj")
    if name.startswith("."):  # import_module(".types", package="openai")
        package = (
            call.args[1]
            if len(call.args) > 1
            else next((k.value for k in call.keywords if k.arg == "package"), None)
        )
        if package is not None:
            base = _module_name(package)
            return base + name if base and base != COMPUTED else COMPUTED
    return name


def _is_sys(node: ast.expr, sys_names: frozenset[str], importers: frozenset[str]) -> bool:
    """sys, a name bound to it, or a run-time import of 'sys'."""
    if isinstance(node, ast.Name):
        return node.id in sys_names
    return (
        isinstance(node, ast.Call)
        and _calls_an_importer(node.func, importers)
        and _module_argument(node) == "sys"
    )


def _is_sys_modules(node: ast.expr, bindings: _Bindings) -> bool:
    if isinstance(node, ast.Name):
        return node.id in bindings.sys_modules
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "modules"
        and _is_sys(node.value, bindings.sys_names, bindings.importers)
    )


def _bindings(tree: ast.Module) -> _Bindings:
    importers = _importer_names(tree)
    sys_names: set[str] = set()
    sys_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            sys_names.update(a.asname or a.name for a in node.names if a.name == "sys")
        elif isinstance(node, ast.ImportFrom) and node.module == "sys" and not node.level:
            sys_modules.update(a.asname or a.name for a in node.names if a.name == "modules")
    # s = sys; s = __import__("sys"); m = sys.modules; m, x = s.modules, 1
    assignments = _assignments(tree)
    changed = True
    while changed:
        changed = False
        for name, value in assignments:
            if name not in sys_names and _is_sys(value, frozenset(sys_names), importers):
                sys_names.add(name)
                changed = True
            elif name not in sys_modules and _is_sys_modules(
                value, _Bindings(importers, frozenset(sys_names), frozenset(sys_modules))
            ):
                sys_modules.add(name)
                changed = True
    return _Bindings(importers, frozenset(sys_names), frozenset(sys_modules))


def _run_time_imports(node: ast.expr, bindings: _Bindings) -> str | None:
    """The module a run-time import in this node names (None when it is not one, or names this
    module itself)."""
    if isinstance(node, ast.Call) and _calls_an_importer(node.func, bindings.importers):
        return _module_argument(node)
    if isinstance(node, ast.Subscript) and _is_sys_modules(node.value, bindings):
        return _module_name(node.slice)
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in SYS_MODULES_METHODS
        and _is_sys_modules(node.func.value, bindings)
    ):
        return _module_name(node.args[0] if node.args else None)
    return None


def _imported_modules(tree: ast.Module, module_parts: list[str], is_package: bool):
    bindings = _bindings(tree)
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
        elif isinstance(node, ast.expr) and (module := _run_time_imports(node, bindings)):
            yield node.lineno, module


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
            if layer != "adapters" and top in HTTP_CLIENTS - VENDORS:
                violations.append(
                    Violation(
                        file, line, f"HTTP client {top} is imported outside {root_name}.adapters"
                    )
                )
            if layer != "api" and top in WEB:
                violations.append(
                    Violation(
                        file, line, f"web framework {top} is imported outside {root_name}.api"
                    )
                )
            if layer != "adapters" and top in VENDORS:
                violations.append(
                    Violation(
                        file, line, f"vendor SDK {top} is imported outside {root_name}.adapters"
                    )
                )
            if layer != "ingest" and top in PARSERS:
                violations.append(
                    Violation(
                        file, line, f"parser library {top} is imported outside {root_name}.ingest"
                    )
                )
        violations.extend(_test_only_violations(file, tree, parts, root_name))
    return violations


def _from_import_names(tree: ast.Module, module_parts: list[str], is_package: bool):
    """`from a.b import c` also names the module a.b.c (c may be a module)."""
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            base = (
                _resolve_relative(module_parts, is_package, node.level, node.module)
                if node.level
                else node.module
            )
            for alias in node.names:
                yield node.lineno, f"{base}.{alias.name}"


def _test_only_violations(
    file: Path, tree: ast.Module, parts: list[str], root_name: str
) -> list[Violation]:
    """Rule 4: no module of the package imports a fake adapter, except the module itself and the
    factory."""
    is_package = file.name == "__init__.py"
    dotted = ".".join(parts[1:])
    found: list[Violation] = []
    seen: set[tuple[int, str]] = set()
    names = [
        *_imported_modules(tree, parts, is_package),
        *_from_import_names(tree, parts, is_package),
    ]
    for line, module in names:
        for test_only in TEST_ONLY:
            target = f"{root_name}.{test_only}"
            if dotted in (test_only, FAKE_IMPORTER) or (line, target) in seen:
                continue
            if module == target or module.startswith(f"{target}."):
                seen.add((line, target))
                found.append(
                    Violation(
                        file,
                        line,
                        f"{target} is built only by {root_name}.{FAKE_IMPORTER} (provider fake) "
                        "and the unit tests; no other module imports it",
                    )
                )
    return found


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
