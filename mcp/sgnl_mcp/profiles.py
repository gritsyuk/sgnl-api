"""Access profiles and risk levels.

A profile decides two things: which tools are registered (the agent never sees tools above its
profile) and which scopes the API token is requested with: exactly those of the API routes the
profile may call (see guard.ROUTES), so delete scopes are never requested. The user never sets
scopes; if the integration lacks some, the server starts without them and names them on use.
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


def scopes_for(profile: Profile) -> list[str]:
    """The scopes the profile's token is requested with, derived from the routes it may call."""
    from .guard import scopes_for as from_routes  # guard imports this module
    return from_routes(profile)
