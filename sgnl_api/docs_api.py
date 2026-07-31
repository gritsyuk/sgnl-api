from .resources import Company, File, Folder, Item, Project, Version
from .scopes import SCOPES_DEFAULT
from .transport import DEFAULT_TIMEOUT, Transport


class DocsApi:
    """DocsApi client for interacting with the SGNL DOCS API.
    Do not initialize this class directly. Use the create() classmethod instead:
    Example:
        ```python
        api = await DocsApi.create(client_id="your_id", client_secret="your_secret")
        ```
    Or as an async context manager, which closes the underlying connection pool on exit:
        ```python
        async with await DocsApi.create(client_id="your_id", client_secret="your_secret") as api:
            ...
        ```
    """

    def __init__(self,
                 *,
                 client_id: str,
                 client_secret: str,
                 scopes: list[str] = SCOPES_DEFAULT,
                 timeout: float = DEFAULT_TIMEOUT) -> None:
        self._transport = Transport(
            client_id=client_id,
            client_secret=client_secret,
            scopes=[*scopes],
            base_url="https://api.sgnl.pro/public/v1",
            timeout=timeout
        )

        self.item = Item(self._transport)
        self.folder = Folder(self._transport)
        self.project = Project(self._transport)
        self.company = Company(self._transport)
        self.version = Version(self._transport)
        self.file = File(self._transport)

    @classmethod
    async def create(
            cls,
            *,
            client_id: str,
            client_secret: str,
            scopes: list[str] = SCOPES_DEFAULT,
            timeout: float = DEFAULT_TIMEOUT) -> "DocsApi":
        """Create and initialize a new DocsApi instance.
               Args:
                   client_id: Your SGNL DOCS API client ID
                   client_secret: Your SGNL DOCS API client secret
                   scopes: List of scopes
                   timeout: Request timeout in seconds, applied to connect/read/write/pool
               Returns:
                   An initialized DocsApi instance
               Example:
                   ```python
                   api = await DocsApi.create(
                       client_id="your_id",
                       client_secret="your_secret"
                   )
                   ```
               """
        instance = cls(client_id=client_id, client_secret=client_secret, scopes=scopes, timeout=timeout)
        await instance._transport._ensure_token()
        return instance

    async def aclose(self) -> None:
        """Closes the underlying HTTP connection pool. Call this when done using the client,
        unless it is used as an async context manager."""
        await self._transport.aclose()

    async def __aenter__(self) -> "DocsApi":
        return self

    async def __aexit__(self, *exc_info) -> None:
        await self.aclose()
