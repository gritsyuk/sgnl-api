import aiofiles
import mimetypes
import os


async def read_file(file_path):
    async with aiofiles.open(file_path, 'rb') as file:
        file_data = await file.read()

    mime_type, _ = mimetypes.guess_type(file_path)
    size = os.path.getsize(file_path)

    if size == 0 or mime_type is None:
        return None

    return file_data, mime_type, size


