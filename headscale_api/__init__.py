"""Headscale API module."""

from .config import HeadscaleConfig  # noqa # type: ignore
from .headscale import Headscale

if __name__ == "__main__":
    import asyncio
    import os

    from .schema.headscale.v1 import GetUserRequest, ListApiKeysRequest

    headscale = Headscale(
        os.getenv("HEADSCALE_APIURL", "localhost:5000"),
        api_key=os.getenv("HEADSCALE_APIKEY", None),
    )
    print(asyncio.run(headscale.get_user(GetUserRequest("marek"))))
    print(asyncio.run(headscale.list_api_keys(ListApiKeysRequest())))
