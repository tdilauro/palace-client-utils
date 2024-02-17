#!/usr/bin/env python3

from __future__ import annotations

import dataclasses
import datetime
import sys
from collections.abc import Generator
from functools import cached_property
from pathlib import Path

import typer
from pydantic import BaseModel, Field, model_validator

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

app = typer.Typer()


class ToCEntry(BaseModel):
    href: str
    title: str
    children: ToCEntries | None = None
    # Computed properties.
    track_href: str = ""
    track_offset: int = 0
    # Computed externally.
    toc_level: int = 0

    @model_validator(mode="after")
    def computed_values(self) -> Self:
        self.track_href, offset = self.href.split("#t=")
        self.track_offset = int(offset)
        return self

    def toc_hierarchy(
        self, level: int = 0
    ) -> Generator[tuple[int, ToCEntry], None, None]:
        """Iterator yielding all ToCEntries in the hierarchy, in the order they appear in the manifest."""
        yield level, self
        if self.children:
            child_level = level + 1
            for child in self.children:
                yield from child.toc_hierarchy(level=child_level)

    @classmethod
    def from_track(cls, track: AudioTrack, default_title="Track") -> ToCEntry:
        """Create a ToCEntry from an AudioTrack."""
        toc_href = f"{track.href}#t=0"
        toc_title = track.title or default_title
        return cls(href=toc_href, title=toc_title)


class AudioTrack(BaseModel):
    title: str | None = None
    href: str
    content_type: str = Field(..., alias="type")
    duration: int  # in seconds


class ManifestMetadata(BaseModel):
    object_type: str = Field(..., alias="@type")
    identifier: str
    title: str
    author: str
    publisher: str
    published: datetime.datetime
    language: str
    modified: datetime.datetime
    duration: int


class Manifest(BaseModel):
    context: str = Field(..., alias="@context")
    metadata: ManifestMetadata
    reading_order: list[AudioTrack] = Field(..., alias="readingOrder")
    toc: ToCEntries = []

    @property
    def track_count(self) -> int:
        return len(self.reading_order)

    @cached_property
    def tracks_by_href(self) -> dict[str, int]:
        return {t.href: i for i, t in enumerate(self.reading_order)}

    @cached_property
    def top_level_toc(self) -> ToCEntries:
        """The effective top-level table of contents for this manifest.

        If the manifest has no `toc` object, we will construct the ToC
        using the manifest's `readingOrder`.
        """
        return self.toc or [
            ToCEntry.from_track(track=track, default_title=f"Track {n}")
            for n, track in enumerate(self.reading_order, start=1)
        ]

    @cached_property
    def complete_toc(self) -> ToCEntries:
        return list(h[1] for h in self.toc_hierarchy(level=0))

    @cached_property
    def toc_len(self) -> int:
        return len(list(self.toc_hierarchy(level=0)))

    def toc_hierarchy(
        self, level: int = 0
    ) -> Generator[tuple[int, ToCEntry], None, None]:
        """Iterator yielding all ToCEntries in the hierarchy, in the order they appear in the manifest."""
        for entry in self.top_level_toc:
            yield from entry.toc_hierarchy(level=level)

    @cached_property
    def toc_info(self) -> list[TocInfo]:
        return [
            TocInfo(entry, get_track_sequence(entry, i, self))
            for i, entry in enumerate(self.complete_toc)
        ]

    @model_validator(mode="after")
    def populate_toc_levels(self) -> Self:
        """Populate the `toc_level` property on each ToCEntry after the model is fully loaded."""
        for level, entry in self.toc_hierarchy(level=0):
            entry.toc_level = level
        return self


@dataclasses.dataclass
class TrackSegment:
    track: AudioTrack
    start: int
    end: int
    # Post-init
    duration: int = dataclasses.field(init=False)
    hhmmss: str = dataclasses.field(init=False, repr=True)

    def __post_init__(self):
        self.duration = self.end - self.start
        self.hhmmss = seconds_to_hms(self.duration)


# Some aggregation types.
ToCEntries = list[ToCEntry]
TrackSequence = list[TrackSegment]


@dataclasses.dataclass
class TocInfo:
    toc_entry: ToCEntry
    track_sequence: TrackSequence
    # Post-init
    duration: int = dataclasses.field(init=False, repr=True)
    hhmmss: str = dataclasses.field(init=False, repr=True)

    def __post_init__(self):
        self.duration = sum(segment.duration for segment in self.track_sequence)
        self.hhmmss = seconds_to_hms(self.duration)


def seconds_to_hms(seconds: int) -> str:
    """Converts the given number of seconds to a string of format HH:MM:SS."""
    return str(datetime.timedelta(seconds=seconds))


def get_track_sequence(
    entry: ToCEntry, index: int, manifest: Manifest
) -> TrackSequence:
    next_index = index + 1
    next_entry = (
        manifest.complete_toc[next_index] if next_index < manifest.toc_len else None
    )

    entry_first_track = manifest.tracks_by_href[entry.track_href]
    entry_start_offset = entry.track_offset

    if not next_entry:
        entry_last_track = manifest.track_count - 1
        entry_end_offset = manifest.reading_order[entry_last_track].duration
    elif entry.track_href == next_entry.track_href:
        entry_last_track = entry_first_track
        entry_end_offset = next_entry.track_offset
    elif next_entry.track_offset == 0:
        entry_last_track = manifest.tracks_by_href[next_entry.track_href] - 1
        entry_end_offset = manifest.reading_order[entry_last_track].duration
    else:
        # the next ToC entry starts on a different track
        entry_last_track = manifest.tracks_by_href[next_entry.track_href]
        entry_end_offset = next_entry.track_offset

    track_1_segment = TrackSegment(
        track=manifest.reading_order[entry_first_track],
        start=entry_start_offset,
        end=(
            entry_end_offset
            if entry_first_track == entry_last_track
            else manifest.reading_order[entry_first_track].duration
        ),
    )

    # We populate a last track object only if the first and last
    # tracks are not the same.
    track_n_segment = (
        None
        if entry_first_track == entry_last_track
        else TrackSegment(
            track=manifest.reading_order[entry_last_track],
            start=0,
            end=entry_end_offset,
        )
    )

    middle_tracks = manifest.reading_order[entry_first_track + 1 : entry_last_track]
    middle_tracks_segments = [
        TrackSegment(track=track, start=0, end=track.duration)
        for track in middle_tracks
    ]
    return list(
        filter(None, (track_1_segment, *middle_tracks_segments, track_n_segment))
    )


@app.command()
def command(
    manifest_file: Path = typer.Argument(...),
) -> None:
    manifest = Manifest.parse_file(manifest_file)
    for i, toc_info in enumerate(manifest.toc_info):
        indent = " " * toc_info.toc_entry.toc_level * 2
        toc_entry = toc_info.toc_entry
        seq = toc_info.track_sequence
        print(
            f'{indent}Entry #{i} "{toc_entry.title}" {toc_entry.href} - duration: {toc_info.duration} / {toc_info.hhmmss}',
            f"{indent}Number of tracks: {len(seq)}",
            *[
                f'{indent}   Track "{t.track.title}" {t.track.href} from {t.start} to {t.end} ({t.duration}s / {t.hhmmss})'
                for t in seq
            ],
            sep="\n  ",
            end="\n\n",
        )


if __name__ == "__main__":
    app()
