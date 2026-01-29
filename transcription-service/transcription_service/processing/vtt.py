from __future__ import annotations


def format_timestamp(seconds: float) -> str:
    if seconds < 0:
        seconds = 0
    ms_total = int(round(seconds * 1000.0))
    hours = ms_total // 3_600_000
    minutes = (ms_total % 3_600_000) // 60_000
    secs = (ms_total % 60_000) // 1000
    ms = ms_total % 1000
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{ms:03d}"


def segments_to_vtt(segments: list[dict]) -> str:
    lines: list[str] = ["WEBVTT", ""]
    for idx, seg in enumerate(segments, start=1):
        start = format_timestamp(float(seg.get("start", 0.0) or 0.0))
        end = format_timestamp(float(seg.get("end", 0.0) or 0.0))
        text = (seg.get("text") or "").strip()
        if not text:
            continue
        lines.append(str(idx))
        lines.append(f"{start} --> {end}")
        lines.append(text)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
