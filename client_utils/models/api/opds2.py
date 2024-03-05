from collections.abc import Callable, Iterable, Mapping, Sequence
from typing import Any, TypeVar

from pydantic import Field

from client_utils.constants import (
    OPDS_ACQ_OPEN_ACCESS_REL,
    OPDS_ACQ_STANDARD_REL,
    OPDS_REVOKE_REL,
)
from client_utils.models.api.util import ApiBaseModel
from client_utils.utils.misc import ensure_list

"""
https://drafts.opds.io/opds-2.0.html

A JSON Schema for OPDS 2.0 is available under version control at
    https://github.com/opds-community/drafts/tree/master/schema

For the purpose of validating an OPDS 2.0 catalog, use the following JSON Schema resources:

    OPDS 2.0 Feed: https://drafts.opds.io/schema/feed.schema.json
    OPDS 2.0 Publication: https://drafts.opds.io/schema/publication.schema.json
"""


class OPDS2Link(ApiBaseModel):
    href: str
    rel: str | list[str]
    type: str | None = None
    title: str | None = None
    properties: Mapping[str, Any] | None = None
    templated: bool = False

    @property
    def is_acquisition(self):
        """Is this an acquisition link?"""
        return any(
            rel in [OPDS_ACQ_STANDARD_REL, OPDS_ACQ_OPEN_ACCESS_REL]
            for rel in ensure_list(self.rel)
        )

    @property
    def has_indirect_acquisition(self):
        """Does link have one or more indirect acquisition links?"""
        return bool(self.indirect_acquisition_links)

    @property
    def indirect_acquisition_links(self) -> Sequence[Mapping[str, Any]]:
        """Indirect acquisition link, if any."""
        return vars(self).get("properties", {}).get("indirectAcquisition", [])


class OPDS2(ApiBaseModel):
    catalogs: list = []
    links: list[OPDS2Link] = []
    metadata: Mapping[str, Any]


class Publisher(ApiBaseModel):
    name: str


class SubjectInfo(ApiBaseModel):
    scheme: str
    name: str
    sortAs: str


class Contributor(ApiBaseModel):
    name: str
    links: list[OPDS2Link] = []


class PublicationMetadata(ApiBaseModel):
    type: str = Field(..., alias="@type")
    title: str
    sortAs: str
    identifier: str
    language: str
    modified: str
    published: str
    description: str
    publisher: Publisher
    subject: list[SubjectInfo] = []
    duration: float | None = None
    author: Contributor | list[Contributor] = []
    narrator: Contributor | list[Contributor] = []


class Availability(ApiBaseModel):
    state: str
    since: str
    until: str


class IndirectAcquisitionItem(ApiBaseModel):
    type: str


class Properties(ApiBaseModel):
    availability: Availability
    indirectAcquisition: list[IndirectAcquisitionItem] = []
    lcp_hashed_passphrase: str | None = None


class Image(ApiBaseModel):
    href: str
    rel: str
    type: str


class Publication(ApiBaseModel):
    metadata: PublicationMetadata
    links: list[OPDS2Link]
    images: list[Image]

    @property
    def acquisition_links(self):
        return match_links(
            self.links,
            lambda link: link.rel in [OPDS_ACQ_STANDARD_REL, OPDS_ACQ_OPEN_ACCESS_REL],
        )

    @property
    def revoke_links(self):
        return match_links(self.links, lambda link: link.rel == OPDS_REVOKE_REL)

    @property
    def is_loan(self) -> bool:
        """A loan has at least one acquisition link."""
        return bool(self.acquisition_links)


class FeedMetadata(ApiBaseModel):
    title: str


class OPDS2Feed(ApiBaseModel):
    publications: list[Publication] = []
    catalogs: list = []
    links: list[OPDS2Link] = []
    metadata: Mapping[str, Any]
    facets: list


L = TypeVar("L", bound=Mapping[str, str] | OPDS2Link)


def match_links(links: Iterable[L], matcher: Callable[[L], bool]) -> list[L]:
    """Generate matching links.

    :param links: The links from which matches will be picked.
    :param matcher: The function that will perform the matching.
    """
    return [link for link in links if matcher(link)]
