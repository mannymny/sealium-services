import json
from pathlib import Path

from transcription_service.processing.merge import merge_partials


def test_merge_partials_creates_outputs(tmp_path: Path):
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
                    {"start": 3.5, "end": 5.0, "text": "world"},
                    {"start": 5.0, "end": 6.0, "text": "again"},
                ]
            }
        ),
        encoding="utf-8",
    )

    merged_dir = tmp_path / "merged"
    merged_dir.mkdir(parents=True, exist_ok=True)

    final_json = merged_dir / "final.json"
    final_txt = merged_dir / "final.txt"
    final_vtt = merged_dir / "final.vtt"

    segments = merge_partials(
        partials_dir=partials,
        final_json=final_json,
        final_txt=final_txt,
        final_vtt=final_vtt,
        produce_json=True,
        produce_vtt=True,
    )

    assert final_txt.exists()
    text = final_txt.read_text(encoding="utf-8")
    assert "hello" in text
    assert "world" in text
    assert final_vtt.read_text(encoding="utf-8").startswith("WEBVTT")
    assert len(segments) >= 2
