from __future__ import annotations

import json
import math
import sys
from base64 import b64encode
from enum import Enum
from typing import Any, TextIO, Generator, Mapping

import httpx
from rich.progress import MofNCompleteColumn, Progress, SpinnerColumn


class AuthType(Enum):
    BASIC = "basic"
    OAUTH = "oauth"
    NONE = "none"


class OAuthAuth(httpx.Auth):
    requires_response_body = True

    def __init__(self, username: str, password: str) -> None:
        self.username = username
        self.password = password
        self.token: str | None = None

    @staticmethod
    def _get_oauth_url_from_auth_document(
        url: str, auth_document: Mapping[str, Any]
    ) -> str:
        auth_types: list[dict[str, Any]] = auth_document.get("authentication", [])
        oauth_authentication = [
            tlinks
            for t in auth_types
            if t.get("type") == "http://opds-spec.org/auth/oauth/client_credentials"
            and (tlinks := t.get("links")) is not None
        ]
        if not oauth_authentication:
            print(f"Unable to find supported authentication type ({url})")
            print(f"Auth document: {json.dumps(auth_document)}")
            sys.exit(-1)

        links = oauth_authentication[0]
        auth_links: list[str] = [
            lhref
            for l in links
            if l.get("rel") == "authenticate" and (lhref := l.get("href")) is not None
        ]
        if len(auth_links) != 1:
            print(f"Unable to find valid authentication link ({url})")
            print(f"Found {len(auth_links)} authentication links. Auth document: {json.dumps(auth_document)}")
            sys.exit(-1)
        return auth_links[0]

    @staticmethod
    def _oauth_token_request(url: str, username: str, password: str) -> httpx.Request:
        userpass = ":".join((username, password))
        token = b64encode(userpass.encode()).decode()
        headers = {"Authorization": f"Basic {token}"}
        return httpx.Request("POST", url, headers=headers, data={"grant_type": "client_credentials"})

    def auth_flow(self, request: httpx.Request) -> Generator[httpx.Request, httpx.Response, None]:
        if self.token is not None:
            request.headers["Authorization"] = f"Bearer {self.token}"
        response = yield request
        if response.status_code == 401 and response.headers.get("Content-Type") == "application/vnd.opds.authentication.v1.0+json":
            oauth_url = self._get_oauth_url_from_auth_document(request.url, response.json())
            response = yield self._oauth_token_request(oauth_url, self.username, self.password)
            if response.status_code != 200:
                print(f"Error: {response.status_code}")
                print(response.text)
                sys.exit(-1)
            if (access_token := response.json().get("access_token")) is None:
                print("No access token in response")
                print(response.text)
                sys.exit(-1)
            self.token = access_token
            request.headers["Authorization"] = f"Bearer {self.token}"
            yield request


def make_request(session: httpx.Client, url: str) -> dict[str, Any]:
    response = session.get(url)
    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        print(f"Headers: {json.dumps(dict(response.headers), indent=4)}")
        print(response.text)
        sys.exit(-1)
    return response.json()  # type: ignore[no-any-return]


def write_json(file: TextIO, data: list[dict[str, Any]]) -> None:
    file.write(json.dumps(data, indent=4))


def fetch(url: str, username: str | None, password: str | None, auth_type: AuthType) -> list[dict[str, Any]]:
    # Create a session to fetch the documents
    client = httpx.Client()

    client.headers.update({"Accept": "application/opds+json, application/json;q=0.9, */*;q=0.1", "User-Agent": "Palace"})
    client.timeout = httpx.Timeout(30.0)

    if username and password:
        if auth_type == AuthType.BASIC:
            client.auth = httpx.BasicAuth(username, password)
        elif auth_type == AuthType.OAUTH:
            client.auth = OAuthAuth(username, password)
    elif auth_type != AuthType.NONE:
        print("Username and password are required for authentication")
        sys.exit(-1)

    publications = []

    # Get the first page
    response = make_request(client, url)
    items = response.get("metadata", {}).get("numberOfItems")
    items_per_page = response.get("metadata", {}).get("itemsPerPage")

    if items is None or items_per_page is None:
        pages = None
    else:
        pages = math.ceil(items / items_per_page)

    # Fetch the rest of the pages:
    next_url: str | None = url
    with Progress(
        SpinnerColumn(), *Progress.get_default_columns(), MofNCompleteColumn()
    ) as progress:
        download_task = progress.add_task(f"Downloading Feed", total=pages)
        while next_url is not None:
            response = make_request(client, next_url)
            publications.extend(response["publications"])
            next_url = None
            for link in response["links"]:
                if link["rel"] == "next":
                    next_url = link["href"]
                    break
            progress.update(download_task, advance=1)

    return publications
