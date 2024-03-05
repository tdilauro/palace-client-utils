from __future__ import annotations

import sys
from contextlib import nullcontext

from httpx import AsyncClient, Response

from client_utils.constants import DEFAULT_USER_AGENT

if sys.version_info < (3, 11):
    from typing_extensions import Self
else:
    from typing import Self


class HTTPXAsyncClient(AsyncClient):
    def __init__(self, user_agent: str = DEFAULT_USER_AGENT, **kwargs):
        super().__init__(**kwargs)
        self.user_agent = user_agent

    async def request(self, method, url, *, headers=None, **kwargs) -> Response:
        headers = {"User-Agent": self.user_agent} | (headers or {})
        return await super().request(method, url, headers=headers, **kwargs)

    async def post(self, *args, **kwargs) -> Response:
        return await self.request("POST", *args, **kwargs)

    async def get(self, *args, **kwargs) -> Response:
        return await self.request("GET", *args, **kwargs)

    @classmethod
    def with_existing_client(cls, *args, existing_client: Self | None = None, **kwargs):
        """Return an instance of our self.

        :param existing_client: A client to use instead of creating a new one.
        :return: A client instance.

        If `client` is provided, it will be returned.
        If not, a new one will be instantiated, using the provided arguments.
        """
        if existing_client:
            return nullcontext(enter_result=existing_client)
        else:
            return cls(*args, **kwargs)


def validate_response(response: Response, raise_for_status=True):
    if raise_for_status:
        response.raise_for_status()
    return response
