"""Headscale API module."""

from .config import HeadscaleConfig  # noqa # type: ignore
from .headscale import Headscale

if __name__ == "__main__":
    import asyncio
    import os

    from .schema.headscale.v1 import GetUserRequest, ListApiKeysRequest

    async def main(index: int, headscale: Headscale):
        """Run some basic API test."""
        async with headscale.session:
            if not await headscale.health_check():
                print("Not healthy!")
                return

            print(f"{index}: Server healthy!")
            print(f"{index}: {await headscale.get_user(GetUserRequest('marek'))}")
            print(f"{index}: {await headscale.list_api_keys(ListApiKeysRequest())}")

    async def multi_main():
        """Test concurrent connections with a single session."""
        headscale = Headscale(
            os.getenv("HEADSCALE_APIURL", "localhost:5000"),
            api_key=os.getenv("HEADSCALE_APIKEY", None),
        )
        async with asyncio.TaskGroup() as tasks:
            for index in range(10):
                tasks.create_task(main(index, headscale))

    asyncio.run(multi_main())
