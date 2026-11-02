"""Compare the SGNL OpenAPI spec against the endpoints this wrapper calls.

Usage:
    uv run scripts/check_api_coverage.py                      # downloads the spec from api.sgnl.pro
    uv run scripts/check_api_coverage.py path/to/schema.yml   # uses a local copy

Reports:
  * endpoints in the spec that the wrapper does not call;
  * endpoints the wrapper calls that are not in the spec (removed or renamed in the API);
  * query parameters / body fields of matched endpoints that the wrapper does not expose
    or sends without the spec defining them.

Methods that pass a whole filter dict through as the request body (``json=filter``) are not
checked field by field: their payload is whatever the caller builds from the spec.

Exits with code 1 if the wrapper calls anything missing from the spec or a required field is
not exposed, so it can be used in CI.
"""
import ast
import re
import sys
from pathlib import Path

import httpx
import yaml

SPEC_URL = "https://api.sgnl.pro/openapi/v1/schema.yml"
PREFIX = "/public/v1"
RESOURCES_DIR = Path(__file__).resolve().parent.parent / "sgnl_api" / "resources"
# Called by Transport itself, not by a resource method.
INTERNAL_ENDPOINTS = {("POST", "/auth/token")}
# Names of method arguments that are forwarded as the request body unchanged.
PASSTHROUGH_ARGS = {"filter", "find", "values", "items", "review", "share", "data"}


def load_spec(source: str = None) -> dict:
    if source:
        text = Path(source).read_text(encoding="utf-8")
    else:
        response = httpx.get(SPEC_URL, timeout=30)
        response.raise_for_status()
        text = response.text
    return yaml.safe_load(text)


def norm(path: str) -> str:
    if path.startswith(PREFIX):
        path = path[len(PREFIX):]
    return re.sub(r"\{[^}]+\}", "{}", path)


def dict_keys(node) -> set:
    """Literal keys of a dict display, or keyword names of a drop_none(...) call."""
    if isinstance(node, ast.Dict):
        return {k.value for k in node.keys if isinstance(k, ast.Constant)}
    if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "drop_none":
        return {k.arg for k in node.keywords if k.arg}
    return set()


def local_keys(fn: ast.AsyncFunctionDef, var: str) -> set:
    """Keys a local variable (e.g. ``params`` / ``payload``) is built with inside a function."""
    keys = set()
    for node in ast.walk(fn):
        if not isinstance(node, ast.Assign):
            continue
        target = node.targets[0]
        if isinstance(target, ast.Name) and target.id == var:
            keys |= dict_keys(node.value)
        elif (isinstance(target, ast.Subscript) and getattr(target.value, "id", None) == var
              and isinstance(target.slice, ast.Constant)):
            keys.add(target.slice.value)
    return keys


def argument_keys(fn: ast.AsyncFunctionDef, node) -> tuple:
    """Returns (keys, is_passthrough) for a ``params=`` / ``json=`` argument."""
    if node is None:
        return set(), False
    if isinstance(node, ast.BoolOp):  # e.g. ``filter or {}``
        node = node.values[0]
    if isinstance(node, ast.Name):
        if node.id in PASSTHROUGH_ARGS:
            return set(), True
        return local_keys(fn, node.id), False
    return dict_keys(node), False


def wrapper_calls() -> dict:
    calls = {}
    for f in sorted(RESOURCES_DIR.glob("*.py")):
        tree = ast.parse(f.read_text(encoding="utf-8"))
        for cls in (n for n in tree.body if isinstance(n, ast.ClassDef)):
            for fn in (n for n in cls.body if isinstance(n, ast.AsyncFunctionDef)):
                for call in ast.walk(fn):
                    if not (isinstance(call, ast.Call) and getattr(call.func, "attr", None) == "request"):
                        continue
                    kw = {k.arg: k.value for k in call.keywords}
                    if "method" not in kw or "path" not in kw:
                        continue
                    path_node = kw["path"]
                    if isinstance(path_node, ast.Constant):
                        path = path_node.value
                    else:  # f-string
                        path = "".join(v.value if isinstance(v, ast.Constant) else "{}" for v in path_node.values)
                    params, _ = argument_keys(fn, kw.get("params"))
                    body, passthrough = argument_keys(fn, kw.get("json"))
                    calls.setdefault((kw["method"].value, norm(path)), []).append(
                        (f"{cls.name}.{fn.name}", params, body, passthrough)
                    )
    return calls


def main() -> int:
    spec = load_spec(sys.argv[1] if len(sys.argv) > 1 else None)
    schemas = spec.get("components", {}).get("schemas", {})

    def resolve(schema):
        if not schema:
            return {}
        if "$ref" in schema:
            return schemas[schema["$ref"].split("/")[-1]]
        if "allOf" in schema:
            return resolve(schema["allOf"][0])
        return schema

    spec_ops = {}
    for path, methods in spec["paths"].items():
        for method, op in methods.items():
            if method.upper() in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
                spec_ops[(method.upper(), norm(path))] = (path, op)

    calls = wrapper_calls()
    failed = False

    missing = sorted(set(spec_ops) - set(calls) - INTERNAL_ENDPOINTS)
    print(f"=== In spec, not in wrapper ({len(missing)}) ===")
    for key in missing:
        path, op = spec_ops[key]
        print(f"  {key[0]:6} {path}  [{', '.join(op.get('tags', []))}] {op.get('summary', '').splitlines()[0] if op.get('summary') else ''}")

    stale = sorted(set(calls) - set(spec_ops))
    print(f"\n=== In wrapper, not in spec ({len(stale)}) ===")
    for key in stale:
        failed = True
        print(f"  {key[0]:6} {key[1]}  <- {', '.join(c[0] for c in calls[key])}")

    print("\n=== Parameter differences ===")
    for key in sorted(set(spec_ops) & set(calls)):
        path, op = spec_ops[key]
        query = {p["name"] for p in op.get("parameters", []) if p.get("in") == "query"}
        query_required = {p["name"] for p in op.get("parameters", []) if p.get("in") == "query" and p.get("required")}
        body_schema = resolve(op.get("requestBody", {}).get("content", {}).get("application/json", {}).get("schema"))
        body = set(body_schema.get("properties", {}))
        body_required = set(body_schema.get("required", []))
        for name, params, sent_body, passthrough in calls[key]:
            issues = []
            if query - params:
                issues.append(f"query not exposed: {sorted(query - params)}")
            if query_required - params:
                failed = True
                issues.append(f"REQUIRED query not sent: {sorted(query_required - params)}")
            if params - query:
                issues.append(f"query sent but not in spec: {sorted(params - query)}")
            if not passthrough and body:
                if body - sent_body:
                    issues.append(f"body fields not exposed: {sorted(body - sent_body)}")
                if body_required - sent_body:
                    failed = True
                    issues.append(f"REQUIRED body fields not sent: {sorted(body_required - sent_body)}")
                if sent_body - body:
                    failed = True
                    issues.append(f"body fields sent but not in spec: {sorted(sent_body - body)}")
            if issues:
                print(f"  {key[0]:6} {path}  <- {name}")
                for issue in issues:
                    print(f"         {issue}")

    print(f"\nspec operations: {len(spec_ops)}, wrapper endpoints: {len(calls)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
