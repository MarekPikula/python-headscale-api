"""Headscale API module."""

from .config import HeadscaleConfig  # noqa # type: ignore
from .headscale import Headscale  # noqa

if __name__ == "__main__":
    import asyncio
    import os

    headscale = Headscale(
        os.getenv("HEADSCALE_APIURL", "localhost:5000"),
        api_key=os.getenv("HEADSCALE_APIKEY", None),
    )
    print(asyncio.run(headscale.get_user(name="marek")))
