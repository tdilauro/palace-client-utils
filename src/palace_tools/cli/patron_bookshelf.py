#!/usr/bin/env python3

import asyncio
import json

import typer

from palace_tools.constants import DEFAULT_REGISTRY_URL
from palace_tools.models.api.opds2 import OPDS2Feed
from palace_tools.models.internal.bookshelf import print_bookshelf_summary
from palace_tools.roles.patron import authenticate
from palace_tools.utils.http.async_client import HTTPXAsyncClient
from palace_tools.utils.typer import run_typer_app_as_main

app = typer.Typer(rich_markup_mode="rich")


def main() -> None:
    run_typer_app_as_main(app)


@app.command(
    help="Print a patron's bookshelf.",
    epilog="[red]Use options from only one of the three numbered option groups.[/red]",
    no_args_is_help=True,
)
def patron_bookshelf(
    *,
    username: str = typer.Argument(
        None, help="Username to present to the OPDS server."
    ),
    password: str = typer.Argument(
        None, help="Password to present to the OPDS server."
    ),
    auth_doc_url: str = typer.Option(
        None,
        "--auth_doc",
        metavar="URL",
        help="An authentication document URL.",
        rich_help_panel="Group 1: Authentication Document",
    ),
    library: str = typer.Option(
        None,
        "--library",
        help="Name of the library in the registry.",
        metavar="FULL_NAME",
        rich_help_panel="Group 2: Library from Registry",
    ),
    registry_url: str = typer.Option(
        DEFAULT_REGISTRY_URL,
        "--registry-url",
        envvar="PALACE_REGISTRY_URL",
        show_default=True,
        metavar="URL",
        help="URL of the library registry.",
        rich_help_panel="Group 2: Library from Registry",
    ),
    allow_hidden_libraries: bool = typer.Option(
        False,
        "--include-hidden",
        "-a",
        is_flag=True,
        flag_value=True,
        help="Include hidden libraries from the library registry.",
        rich_help_panel="Group 2: Library from Registry",
    ),
    opds_server: str = typer.Option(
        None,
        "--opds-server",
        metavar="URL",
        help="An OPDS server endpoint URL.",
        rich_help_panel="Group 3: OPDS Server Heuristic",
    ),
    as_json: bool = typer.Option(
        False,
        "--json",
        "-j",
        is_flag=True,
        help="Output bookshelf as JSON.",
        rich_help_panel="Output",
    ),
) -> None:
    bookshelf = asyncio.run(
        fetch_bookshelf(
            username=username,
            password=password,
            registry_url=registry_url,
            library=library,
            opds_server=opds_server,
            auth_doc_url=auth_doc_url,
            allow_hidden_libraries=allow_hidden_libraries,
        )
    )
    if as_json:
        print(json.dumps(bookshelf.dict(), indent=2))
    else:
        print_bookshelf_summary(bookshelf)


async def fetch_bookshelf(
    *,
    username: str | None = None,
    password: str | None = None,
    registry_url: str = DEFAULT_REGISTRY_URL,
    library: str | None = None,
    opds_server: str | None = None,
    auth_doc_url: str | None = None,
    allow_hidden_libraries: bool = False,
) -> OPDS2Feed:
    async with HTTPXAsyncClient() as client:
        patron = await authenticate(
            username=username,
            password=password,
            auth_doc_url=auth_doc_url,
            library=library,
            registry_url=registry_url,
            allow_hidden_libraries=allow_hidden_libraries,
            opds_server=opds_server,
            http_client=client,
        )
        return await patron.patron_bookshelf(http_client=client)


if __name__ == "__main__":
    main()
