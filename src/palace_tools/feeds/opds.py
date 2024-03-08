from __future__ import annotations

import json
import math
import sys
from typing import Any, TextIO

import httpx
from rich.progress import MofNCompleteColumn, Progress, SpinnerColumn


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


def fetch(url: str, username: str | None, password: str | None) -> list[dict[str, Any]]:
    # Create a session to fetch the documents
    client = httpx.Client()

    client.headers.update({"Accept": "application/opds+json", "User-Agent": "Palace"})
    client.timeout = httpx.Timeout(30.0)

    if username and password:
        client.auth = httpx.BasicAuth(username, password)

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
