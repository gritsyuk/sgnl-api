import mimetypes
import os
from typing import AsyncIterator, Optional, Tuple

import aiofiles

CHUNK_SIZE = 1024 * 1024


def file_info(file_path: str, mime_type: Optional[str] = None) -> Tuple[str, int]:
    """Returns (mime_type, size) of a local file to upload.

    Raises FileNotFoundError for a missing file and ValueError for an empty file or one whose
    MIME type cannot be guessed from its extension and was not given explicitly.
    """
    if not os.path.isfile(file_path):
        raise FileNotFoundError(file_path)
    size = os.path.getsize(file_path)
    if size == 0:
        raise ValueError(f"File is empty: {file_path}")
    if mime_type is None:
        mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type is None:
        raise ValueError(f"Cannot determine MIME type of {file_path}; pass mime_type explicitly")
    return mime_type, size


async def iter_file(file_path: str, chunk_size: int = CHUNK_SIZE) -> AsyncIterator[bytes]:
    """Streams a file in chunks, so large uploads are never held in memory whole."""
    async with aiofiles.open(file_path, 'rb') as file:
        while True:
            chunk = await file.read(chunk_size)
            if not chunk:
                break
            yield chunk
