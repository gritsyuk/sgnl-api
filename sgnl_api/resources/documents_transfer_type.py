from ..transport import Transport


class DocumentsTransferType:
    def __init__(self, transport: Transport):
        self._transport = transport

    async def get_list(self, filter: dict) -> list[dict]:
        """
        Returns a list of document transfer types matching the given filter.
        Required scopes: docs:docs_transfer:list
        :param filter: DocumentsTransferTypeFind payload, e.g. {"projectId": ...}
        """
        return await self._transport.request(method='POST', path='/documents-transfers/types', json=filter)
