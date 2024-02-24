# Readium Web Publication Audio Manifest Processing

## Concepts

### Manifest

A [Readium Web Publication Manifest (RWPM)](https://github.com/readium/webpub-manifest) in (roughly) the [Audiobook Profile](https://github.com/readium/webpub-manifest/blob/master/profiles/audiobook.md).

### Track

A track represents an audio file. The list of tracks in playback order can be found in the
`readingOrder` object of the manifest.

### Table of Contents

The table of contents (ToC) is derived from the manifest, either from the entries (and their recursive children)
in the `manifest.toc` object or -- if that property is missing, null, or an empty list -- from the list of
tracks in `manifest.readingOrder`. In the latter case, each track is treated as a single, top-level ToC entry.
Whichever case is present in a manifest can be seen as the "effective ToC", such that any reference to
the "ToC," "ToC entry," or "ToC Entries" below encompasses and is supported in both scenarios.

### Audio Segment

Audio segment is not a concept that exists currently in the RWPM or its Audiobook Profile. It is used here
to conceptualize how the effective table of contents entries are mapped to one or more audio
tracks for playback. An audio segment is associated with a single track and has a start and end offset
within that track.

A ToC entry is associated with zero or more audio segments.

## Workflow

The effective ToC contains entries with the starting track and time offset, but not the duration or an ending
track/offset. So, to determine the duration and “audio segments” comprising a ToC entry, it is necessary to
use the next ToC entry (or the fact that there isn't one) and, possibly, the durations of the tracks involved.

For the following to work, any hierarchical ToC entries (i.e., any with `children` objects) must be
recursively linearized into playback order before being fed into the flow below.

### Process for each ToC entry

Roughly, here’s the logic:

If there is NO next ToC entry, then:

- the audio segments involved are (1) the ToC track from the specified offset and (2) the entirety of all remaining tracks;
- the duration is the sum of the remaining time on the ToC track plus the full durations
  of all subsequent tracks.

If the next ToC entry starts on the same track, then:
- the ToC entry is entirely contained on a single track;
- the audio segment involved is the ToC track from the specified offset to the offset
  specified for the next track;
- the duration is the difference in the start times of the two entries.

If the next ToC entry starts at t=0 of its track, then:
- it is necessarily on a different track,
- tracks segments involved are:
    - the ToC track from the specified offset;
    - the entirety of all subsequent tracks up to, but NOT including, that of the next ToC;
- the duration is the sum of the remaining time on the ToC track plus the full durations
  of the other involved tracks.

Finally, if the next ToC entry starts anywhere other than the beginning of a different track, then:
- the audio segments involved are:
    - the ToC track from the specified offset;
    - the entirety of all tracks between (but not including) the current ToC entry’s starting
      track and the next ToC entry’s starting track;
    - the duration is the next ToC entry’s starting track up to the next ToC’s offset.
- the duration is the sum of:
    - the remaining time on the current ToC entry’s starting track,
    - the entire durations of all intervening complete tracks,
    - the offset of the next ToC entry minus 1.

## Notes

- These concepts and workflow were reverse engineered by reviewing a fairly small set of manifests and there may
be cases that are not represented or are not properly handled by this approach.
- The approach here assumes that:
    - `manifest.readingOrder` is always the intended temporal order for track playback.
    - A ToC entry always should play before its `.children`.
    - A ToC entry and all of its descendants should always play in order before its next sibling.
- Because a ToC entry identifies only the starting track and start offset:
    - It is possible that audio content not intended for the listener (e.g., production metadata) is played back.
    - This kind of non-playback content might seem to be associated with and played back at the end of the preceding
linearized ToC entry because there wasn't a way to indicate that it was not meant to be played.
- If the first ToC entry does not begin at the beginning of the first track, the audio up until the first ToC's
first audio segment will not be played.
