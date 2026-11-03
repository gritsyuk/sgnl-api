import re
from typing import Iterable, Tuple

# A scope looks like "project:list" or "docs:folder:create"; anything else is a typo the
# server would only report as a bare "ScopeError".
_SCOPE_PATTERN = re.compile(r"^[a-z_]+(:[a-z_]+)+$")

# Kept for code that passes it explicitly. It is no longer the default: SIGNAL refuses a
# token when any requested scope is missing from the integration, so the list must match it.
SCOPES_DEFAULT = (
    "project:read",
    "project:list",
    "project:user:list",
    "project:user:read",
    "project:role:list",
    "docs:object:create",
    "docs:signing:list",
    "docs:signing:create",
    "docs:folder:list",
    "docs:folder:create",
    "docs:folder:update",
    "docs:item:create",
    "docs:item:list",
    "docs:item:read",
    "docs:version:create",
    "docs:version:list"
)

SCOPES_HELP = (
    "Pass scopes=[...] with exactly the scopes enabled for the integration in SIGNAL "
    "(its \"Редактировать интеграцию\" form), e.g. scopes=[\"project:list\"]. "
    "Each method's docstring names the scope it needs (\"Required scopes: ...\")."
)


def validate_scopes(scopes: Iterable[str]) -> Tuple[str, ...]:
    """Checks the scope list before it is sent, so mistakes fail here with a clear message."""
    if scopes is None:
        raise ValueError("scopes is required. " + SCOPES_HELP)
    if isinstance(scopes, str):
        raise ValueError(f"scopes must be a list of strings, not a single string: use scopes=[{scopes!r}].")
    result = tuple(scopes)
    if not result:
        raise ValueError("scopes must not be empty. " + SCOPES_HELP)
    bad = [s for s in result if not isinstance(s, str) or not _SCOPE_PATTERN.match(s)]
    if bad:
        raise ValueError(
            f"Not a valid scope: {', '.join(map(repr, bad))}. Scopes look like 'project:list' or 'docs:folder:create'."
        )
    # Duplicates are harmless for the server, but keep the list tidy and the order stable.
    return tuple(dict.fromkeys(result))
