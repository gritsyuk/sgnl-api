import asyncio
import os
from sgnl_api import DocsApi
from dotenv import load_dotenv

load_dotenv()
CLIENT_ID = os.getenv("CLIENT_ID")
SECRET_ID = os.getenv("SECRET_ID")


async def main():

    docs = await DocsApi.create(
        client_id=CLIENT_ID,
        client_secret=SECRET_ID
    )

    folder_root = await docs.project.root_folder("0289d9ce-2b30-46c1-a567-4a6a31794871")
    # return {'rootFolderId': 'e5fe1578-2dfa-4a5d-a1ca-085865d1aa0f', 'isStorageConfigured': True}
    folder_id = await docs.project.root_folder_id("0289d9ce-2b30-46c1-a567-4a6a31794871")
    # return 'e5fe1578-2dfa-4a5d-a1ca-085865d1aa0f'


if __name__ == "__main__":
    asyncio.run(main())

