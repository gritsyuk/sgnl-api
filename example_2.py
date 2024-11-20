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
    # print(await docs.item.count("430abdfd-22e4-4672-9978-84e062f80ea8"))
    print(await docs.project.get_list())
    # print(await docs.project.users("c472ae31-4fa8-4b1d-812f-8cf9c14a9739"))
    # print(await docs.folder.get_list("42a7c495-a7de-4136-a10f-56b1bd60012a"))
    # print(await docs.project.root_folder("c472ae31-4fa8-4b1d-812f-8cf9c14a9739"))
    # print(await docs.project.root_folder_id("c472ae31-4fa8-4b1d-812f-8cf9c14a9739"))
    # print(await docs.company.users_list())
    # print(await docs.file.upload("0289d9ce-2b30-46c1-a567-4a6a31794871", "0051-PD-KR-08-001.pdf"))
if __name__ == '__main__':
    asyncio.run(main())
