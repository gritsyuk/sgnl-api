from typing import Optional

import httpx

from .resources import (
    AcceptanceCertificate,
    ApplicationUser,
    Attribute,
    AttributeType,
    AttributeTypeListItems,
    AttributeValue,
    Board,
    Booking,
    CadesSignature,
    Card,
    CardGroup,
    CardPublicLink,
    Company,
    CompanyUser,
    CompanyUserCustomRole,
    DocumentsTransfer,
    DocumentsTransferAcceptance,
    DocumentsTransferItem,
    DocumentsTransferType,
    EmbeddedSignature,
    File,
    Folder,
    FolderItemsNamingPattern,
    Forge,
    FormFieldType,
    FormType,
    FormTypeGroup,
    Issue,
    IssueAccesses,
    IssueAttachment,
    IssueComment,
    IssueEvents,
    IssueProjectSettings,
    IssueType,
    Item,
    Mchd,
    Permissions,
    Project,
    ProjectForm,
    ProjectFormFieldType,
    ProjectFormType,
    ProjectUser,
    ProjectUserCustomRole,
    Review,
    ReviewGroup,
    ReviewItem,
    ReviewProcess,
    ReviewType,
    Share,
    Slot,
    Storage,
    Tangl,
    UserLog,
    Version,
)
from .scopes import validate_scopes
from .transport import DEFAULT_MAX_RETRIES, DEFAULT_TIMEOUT, Transport


class DocsApi:
    """DocsApi client for interacting with the SGNL DOCS API.
    Do not initialize this class directly. Use the create() classmethod instead.
    ``scopes`` must list exactly the scopes enabled for the integration in SIGNAL: the server
    refuses the token (SgnlScopeError) if any of them is missing there.
    Example:
        ```python
        api = await DocsApi.create(client_id="your_id", client_secret="your_secret", scopes=["project:list"])
        ```
    Or as an async context manager, which closes the underlying connection pool on exit:
        ```python
        async with await DocsApi.create(client_id="your_id", client_secret="your_secret",
                                        scopes=["project:list"]) as api:
            ...
        ```
    """

    def __init__(self,
                 *,
                 client_id: str,
                 client_secret: str,
                 scopes: list[str],
                 timeout: float = DEFAULT_TIMEOUT,
                 max_retries: int = DEFAULT_MAX_RETRIES,
                 http_client: Optional[httpx.AsyncClient] = None) -> None:
        self._transport = Transport(
            client_id=client_id,
            client_secret=client_secret,
            scopes=list(validate_scopes(scopes)),
            base_url="https://api.sgnl.pro/public/v1",
            timeout=timeout,
            max_retries=max_retries,
            http_client=http_client
        )

        self.item = Item(self._transport)
        self.folder = Folder(self._transport)
        self.project = Project(self._transport)
        self.company = Company(self._transport)
        self.version = Version(self._transport)
        self.file = File(self._transport)

        self.acceptance_certificate = AcceptanceCertificate(self._transport)
        self.application_user = ApplicationUser(self._transport)
        self.attribute = Attribute(self._transport)
        self.attribute_type = AttributeType(self._transport)
        self.attribute_value = AttributeValue(self._transport)
        self.cades_signature = CadesSignature(self._transport)
        self.card_public_link = CardPublicLink(self._transport)
        self.company_user = CompanyUser(self._transport)
        self.company_user_custom_role = CompanyUserCustomRole(self._transport)
        self.documents_transfer = DocumentsTransfer(self._transport)
        self.documents_transfer_item = DocumentsTransferItem(self._transport)
        self.documents_transfer_type = DocumentsTransferType(self._transport)
        self.embedded_signature = EmbeddedSignature(self._transport)
        self.folder_items_naming_pattern = FolderItemsNamingPattern(self._transport)
        self.forge = Forge(self._transport)
        self.issue = Issue(self._transport)
        self.issue_accesses = IssueAccesses(self._transport)
        self.issue_attachment = IssueAttachment(self._transport)
        self.issue_comment = IssueComment(self._transport)
        self.issue_events = IssueEvents(self._transport)
        self.issue_project_settings = IssueProjectSettings(self._transport)
        self.issue_type = IssueType(self._transport)
        self.mchd = Mchd(self._transport)
        self.permissions = Permissions(self._transport)
        self.project_user = ProjectUser(self._transport)
        self.project_user_custom_role = ProjectUserCustomRole(self._transport)
        self.review = Review(self._transport)
        self.review_group = ReviewGroup(self._transport)
        self.review_item = ReviewItem(self._transport)
        self.share = Share(self._transport)
        self.storage = Storage(self._transport)
        self.tangl = Tangl(self._transport)
        self.user_log = UserLog(self._transport)
        self.attribute_type_list_items = AttributeTypeListItems(self._transport)
        self.board = Board(self._transport)
        self.booking = Booking(self._transport)
        self.card = Card(self._transport)
        self.card_group = CardGroup(self._transport)
        self.documents_transfer_acceptance = DocumentsTransferAcceptance(self._transport)
        self.form_field_type = FormFieldType(self._transport)
        self.form_type = FormType(self._transport)
        self.form_type_group = FormTypeGroup(self._transport)
        self.project_form = ProjectForm(self._transport)
        self.project_form_field_type = ProjectFormFieldType(self._transport)
        self.project_form_type = ProjectFormType(self._transport)
        self.review_process = ReviewProcess(self._transport)
        self.review_type = ReviewType(self._transport)
        self.slot = Slot(self._transport)

    @classmethod
    async def create(
            cls,
            *,
            client_id: str,
            client_secret: str,
            scopes: list[str],
            timeout: float = DEFAULT_TIMEOUT,
            max_retries: int = DEFAULT_MAX_RETRIES,
            http_client: Optional[httpx.AsyncClient] = None) -> "DocsApi":
        """Create and initialize a new DocsApi instance.
               Args:
                   client_id: Your SGNL DOCS API client ID
                   client_secret: Your SGNL DOCS API client secret
                   scopes: The scopes to request, e.g. ["project:list", "project:read"]. Must be
                       exactly the scopes enabled for the integration in SIGNAL ("Редактировать
                       интеграцию"); one missing there and the server refuses the token with
                       SgnlScopeError. Each method's docstring names the scope it needs.
                   timeout: Request timeout in seconds, applied to connect/read/write/pool
                   max_retries: How many times to retry a request that got 429 Too Many Requests,
                       waiting for the Retry-After interval between attempts. 0 disables retries.
                   http_client: Your own httpx.AsyncClient, e.g. with a custom transport that filters or
                       throttles requests. It is not closed by aclose(); its owner closes it.
               Returns:
                   An initialized DocsApi instance
               Example:
                   ```python
                   api = await DocsApi.create(
                       client_id="your_id",
                       client_secret="your_secret",
                       scopes=["project:list", "project:read"],
                   )
                   ```
               """
        instance = cls(
            client_id=client_id,
            client_secret=client_secret,
            scopes=scopes,
            timeout=timeout,
            max_retries=max_retries,
            http_client=http_client
        )
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
