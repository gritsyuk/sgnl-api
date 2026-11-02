"""Access profiles and risk levels.

A profile decides two things: which tools are registered (the agent never sees tools above its
profile) and which scopes the API token is requested with (the SIGNAL server itself rejects
writes when the token has no write scopes). Delete scopes are never requested by any profile.
"""
from enum import IntEnum


class Risk(IntEnum):
    READ = 1
    WRITE = 2
    WORKFLOW = 3


class Profile(IntEnum):
    READ = 1
    WRITE = 2
    WORKFLOW = 3

    @classmethod
    def parse(cls, value: str) -> "Profile":
        return cls[value.strip().upper()]

    def allows(self, risk: Risk) -> bool:
        return int(risk) <= int(self)


READ_SCOPES = (
    "project:list",
    "project:read",
    "docs:folder:read",
    "docs:folder:list",
    "docs:item:list",
    "docs:item:read",
    "docs:version:list",
    "docs:docs_transfer:list",
    "docs:docs_transfer:read",
    "docs:issue:list",
    "docs:review:list",
    "docs:signing:list",
    "docs:attribute:list",
)

WRITE_SCOPES = (
    # checks before writing
    "company:user:list",
    # documents and versions
    "docs:object:create",
    "docs:version:create",
    "docs:version:update",
    "docs:item:create",
    # transfers: create and fill (sending also uses docs_transfer:update, see Workflow)
    "docs:docs_transfer:create",
    "docs:docs_transfer:update",
    # issues
    "docs:issue:update",
    # reviews: create and fill (starting also uses docs:review:update, see Workflow)
    "docs:review:create",
    "docs:review:update",
)

# Sending a transfer and starting a review need no scope beyond WRITE_SCOPES; the SIGNAL server
# cannot tell them apart from filling a transfer or a review. They are separated by MCP itself:
# Workflow tools are registered only in the workflow profile and always ask the human.
WORKFLOW_SCOPES: tuple = ()


def scopes_for(profile: Profile) -> list[str]:
    scopes = list(READ_SCOPES)
    if profile >= Profile.WRITE:
        scopes += WRITE_SCOPES
    if profile >= Profile.WORKFLOW:
        scopes += WORKFLOW_SCOPES
    return scopes
