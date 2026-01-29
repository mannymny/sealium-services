import json
from pathlib import Path

from transcription_service.processing.merge import merge_partials


def test_merge_removes_overlaps_and_dedupes(tmp_path: Path):
    partials = tmp_path / "partials"
    partials.mkdir(parents=True, exist_ok=True)

    (partials / "0001.json").write_text(
        json.dumps(
            {
                "segments": [
                    {"start": 0.0, "end": 2.0, "text": "hello"},
                    {"start": 2.0, "end": 4.0, "text": "world"},
                ]
            }
        ),
        encoding="utf-8",
    )

    (partials / "0002.json").write_text(
        json.dumps(
            {
                "segments": [
                    {"start": 3.5, "end": 4.5, "text": "world"},
                    {"start": 4.5, "end": 6.0, "text": "again"},
                ]
            }
        ),
        encoding="utf-8",
    )

    merged_dir = tmp_path / "merged"
    merged_dir.mkdir(parents=True, exist_ok=True)

    segments = merge_partials(
        partials_dir=partials,
        final_json=merged_dir / "final.json",
        final_txt=merged_dir / "final.txt",
        final_vtt=merged_dir / "final.vtt",
        produce_json=True,
        produce_vtt=True,
    )

    for i in range(1, len(segments)):
        assert segments[i]["start"] >= segments[i - 1]["end"]
    for i in range(1, len(segments)):
        assert segments[i]["text"].lower() != segments[i - 1]["text"].lower()
