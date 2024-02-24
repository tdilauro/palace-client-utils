#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path

import typer

from client_utils.models.internal.rwpm_audio.audiobook import Audiobook
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
        text_with_time_delta(
            f'Title: "{audiobook.manifest.metadata.title}"',
            delta_secs=audiobook.manifest.metadata.duration,
        ),
        end="\n\n",
    )
    print_audio_summary(audiobook)
    print_track_summary(audiobook)
    print_toc_audio_segment_summary(audiobook)


def text_with_time_delta(text: str, delta_secs: int, delta_label="duration") -> str:
    """Append a time delta in seconds and hours:minutes:seconds to some label text.

    :param text: The label text.
    :param delta_secs: The duration in seconds.
    :param delta_label: (Optional) Label characterizing the time delta.
    :return: The label text with the duration appended.
    """
    return f"{text} - {delta_label}: {delta_secs}s / {seconds_to_hms(delta_secs)}"


def print_audio_summary(audiobook: Audiobook) -> None:
    print(
        text_with_time_delta(
            "Audiobook ToC-based total duration",
            delta_secs=audiobook.toc_total_duration,
        ),
        text_with_time_delta(
            f"Number of tracks: {len(audiobook.manifest.reading_order)}",
            delta_secs=sum(
                track.duration for track in audiobook.manifest.reading_order
            ),
            delta_label="total duration",
        ),
        text_with_time_delta(
            f"Audio segments: {sum(len(toc.audio_segments) for toc in audiobook.enhanced_toc_in_playback_order)}",
            delta_secs=sum(
                sum(seg.duration for seg in toc.audio_segments)
                for toc in audiobook.enhanced_toc_in_playback_order
            ),
            delta_label="total duration",
        ),
        sep="\n",
    )
    if segments := audiobook.pre_toc_unplayed_audio_segments:
        print(
            text_with_time_delta(
                "<*> Un-played audio segments (before first ToC segment): "
                f"{len(segments)}",
                delta_secs=sum(s.duration for s in segments),
                delta_label="total duration",
            ),
        )
    print("\n")


def print_track_summary(audiobook: Audiobook) -> None:
    print(
        "Tracks (from manifest `reading_order`):",
        *[
            text_with_time_delta(
                f'  #{i} "{track.title}" {track.href}',
                delta_secs=track.duration,
            )
            for i, track in enumerate(audiobook.manifest.reading_order)
        ],
        sep="\n",
        end="\n\n\n",
    )


def print_toc_audio_segment_summary(audiobook: Audiobook) -> None:
    if segments := audiobook.pre_toc_unplayed_audio_segments:
        print(
            text_with_time_delta(
                "<*> Un-played audio segments (before first ToC segment):",
                delta_secs=sum(s.duration for s in segments),
            ),
            *[
                f"""   {
                    text_with_time_delta(
                        f'Track "{s.track.title}" {s.track.href} from {s.start} to {s.end}',
                        delta_secs=s.duration
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
            f"""{indent}{
                text_with_time_delta(
                    f'ToC Entry #{i} "{toc.title}"',
                    delta_secs=toc.duration,
                    delta_label="total duration",
                )
            }""",
            text_with_time_delta(
                f"{indent}          href: {toc.href}",
                delta_secs=toc.audio_segments[0].start,
                delta_label="offset",
            ),
            f"{indent}Number of tracks: {len(toc.audio_segments)}",
            *[
                f"""{indent}   {
                    text_with_time_delta(
                        f'Track "{s.track.title}" {s.track.href} from {s.start} to {s.end}',
                        delta_secs=s.duration
                    )
                }"""
                for s in toc.audio_segments
            ],
            sep="\n",
            end="\n\n",
        )


if __name__ == "__main__":
    main()
