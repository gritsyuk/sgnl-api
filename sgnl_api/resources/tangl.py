from uuid import UUID

from ..transport import Transport


class Tangl:
    def __init__(self, transport: Transport):
        self._transport = transport

    async def convert(self, version_id: UUID, revit_version: str = None) -> None:
        """
        Initiates model conversion using Tangl. Supported file formats: .rvt, .ifc.
        Required scopes: docs:viewer:execute
        :param revit_version: Revit version, required for .rvt files (supported: 2019-2026)
        """
        payload = {'versionId': version_id}
        if revit_version is not None:
            payload['revitVersion'] = revit_version
        return await self._transport.request(method='POST', path='/tangl/convert', json=payload)
