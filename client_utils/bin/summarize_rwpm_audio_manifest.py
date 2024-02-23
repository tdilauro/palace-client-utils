#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path

import typer

from client_utils.models.interaction.audiobook.audiobook import Audiobook
from client_utils.utils.datetime import seconds_to_hms

app = typer.Typer()


def main() -> None:
    app(prog_name="summarize-manifest")


@app.command()
def command(
    manifest_file: Path = typer.Argument(...),
) -> None:
    audiobook = Audiobook.from_manifest_file(manifest_file)
    print(
        labeled_duration(
            f'Title: "{audiobook.manifest.metadata.title}"',
            duration=audiobook.manifest.metadata.duration,
        ),
        end="\n\n",
    )
    print_audio_summary(audiobook)
    print_track_summary(audiobook)
    print_toc_audio_segment_summary(audiobook)


def labeled_duration(label, duration: int, duration_label="duration") -> str:
    return f"{label} - {duration_label}: {duration}s / {seconds_to_hms(duration)}"


def print_audio_summary(audiobook: Audiobook) -> None:
    print(
        labeled_duration(
            "Audiobook ToC-based total duration", duration=audiobook.toc_total_duration
        ),
        labeled_duration(
            f"Number of tracks: {len(audiobook.manifest.reading_order)}",
            duration=sum(track.duration for track in audiobook.manifest.reading_order),
        ),
        labeled_duration(
            f"Audio segments: {sum(len(toc.audio_segments) for toc in audiobook.enhanced_toc_in_playback_order)}",
            duration=sum(
                sum(seg.duration for seg in toc.audio_segments)
                for toc in audiobook.enhanced_toc_in_playback_order
            ),
        ),
        sep="\n",
    )
    if segments := audiobook.pre_toc_unplayed_audio_segments:
        print(
            labeled_duration(
                "<*> Unplayed audio segments (before first ToC segment): "
                f"{len(segments)}",
                duration=sum(s.duration for s in segments),
            ),
        )
    print("\n")


def print_track_summary(audiobook: Audiobook) -> None:
    print(
        "Tracks (from manifest `reading_order`):",
        *[
            labeled_duration(
                f'  #{i} "{track.title}" {track.href}',
                duration=track.duration,
            )
            for i, track in enumerate(audiobook.manifest.reading_order)
        ],
        sep="\n",
        end="\n\n\n",
    )


def print_toc_audio_segment_summary(audiobook: Audiobook) -> None:
    if segments := audiobook.pre_toc_unplayed_audio_segments:
        print(
            labeled_duration(
                "<*> Unplayed audio segments (before first ToC segment):",
                duration=sum(s.duration for s in segments),
            ),
            *[
                f"""   {
                    labeled_duration(
                        f'Track "{s.track.title}" {s.track.href} from {s.start} to {s.end}',
                        duration=s.duration
                    )
                }"""
                for s in segments
            ],
            sep="\n",
            end="\n\n\n",
        )
    for i, toc in enumerate(audiobook.enhanced_toc_in_playback_order):
        indent = " " * toc.depth * 2
        print(
            f"""{indent}{labeled_duration(f'ToC Entry #{i} "{toc.title}"', duration=toc.duration)}""",
            labeled_duration(
                f"{indent}          href: {toc.href}",
                duration=toc.audio_segments[0].start,
                duration_label="offset",
            ),
            f"{indent}Number of tracks: {len(toc.audio_segments)}",
            *[
                f"""{indent}   {
                    labeled_duration(
                        f'Track "{s.track.title}" {s.track.href} from {s.start} to {s.end}',
                        duration=s.duration
                    )
                }"""
                for s in toc.audio_segments
            ],
            sep="\n",
            end="\n\n",
        )


if __name__ == "__main__":
    main()
