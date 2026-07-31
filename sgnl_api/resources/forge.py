from uuid import UUID

from ..transport import Transport


class Forge:
    def __init__(self, transport: Transport):
        self._transport = transport

    async def convert(self, version_id: UUID) -> None:
        """
        Initiates model conversion using Forge.
        Supported formats: .cad, .dwg, .rvt, .rfa, .rte, .nwc, .nwd, .dwf, .dwfx, .dxf, .dgn, .rvn,
        .fbx, .3ds, .3dm, .skp, .rng, .pln, .obj, .dae, .nwf, .stl, .ifc, .sat, .step, .stp, .pdf.
        Required scopes: docs:viewer:execute
        """
        return await self._transport.request(method='POST', path='/forge/convert', json={'versionId': version_id})

    async def get_viewers_data(self, project_id: UUID, item_version_ids: list[UUID]) -> dict:
        """
        Retrieves the auth token and model identifiers (URNs) needed to render documents in the Forge Viewer.
        Required scopes: docs:viewer:read
        :param item_version_ids: min 1, max 25 items
        """
        return await self._transport.request(
            method='POST',
            path='/forge/item-versions/viewer',
            json={'projectId': project_id, 'itemVersionIds': item_version_ids}
        )
