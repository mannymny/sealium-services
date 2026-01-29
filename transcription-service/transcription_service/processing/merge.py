from __future__ import annotations

import json
from pathlib import Path

from .vtt import segments_to_vtt


def _normalize_segments(segments: list[dict]) -> list[dict]:
    segments = sorted(segments, key=lambda s: (float(s.get("start", 0.0)), float(s.get("end", 0.0))))
    merged: list[dict] = []
    for seg in segments:
        text = (seg.get("text") or "").strip()
        if not text:
            continue
        start = float(seg.get("start", 0.0) or 0.0)
        end = float(seg.get("end", 0.0) or 0.0)
        if end <= start:
            continue
        seg = {"start": start, "end": end, "text": text}

        if merged:
            prev = merged[-1]
            if start < prev["end"]:
                if start > prev["start"]:
                    prev["end"] = start
                    if prev["end"] <= prev["start"]:
                        merged.pop()
                if text.lower() == prev.get("text", "").lower():
                    continue
        merged.append(seg)
    return merged


def merge_partials(
    *,
    partials_dir: Path,
    final_json: Path,
    final_txt: Path,
    final_vtt: Path | None,
    produce_json: bool = True,
    produce_vtt: bool = True,
) -> list[dict]:
    segments: list[dict] = []
    for partial in sorted(partials_dir.glob("*.json")):
        data = json.loads(partial.read_text(encoding="utf-8"))
        for seg in data.get("segments", []):
            segments.append(seg)

    merged = _normalize_segments(segments)
    full_text = " ".join([s["text"] for s in merged]).strip()

    final_txt.write_text(full_text + "\n", encoding="utf-8")

    payload = {"segments": merged, "text": full_text}
    if produce_json:
        final_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    if produce_vtt and final_vtt is not None:
        final_vtt.write_text(segments_to_vtt(merged), encoding="utf-8")

    return merged
