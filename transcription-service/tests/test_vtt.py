from transcription_service.processing.vtt import format_timestamp, segments_to_vtt


def test_vtt_formatting():
    assert format_timestamp(0) == "00:00:00.000"
    assert format_timestamp(61.005) == "00:01:01.005"

    vtt = segments_to_vtt([
        {"start": 0.0, "end": 1.5, "text": "hello"},
        {"start": 1.5, "end": 3.0, "text": "world"},
    ])

    assert vtt.startswith("WEBVTT")
    assert "00:00:00.000 --> 00:00:01.500" in vtt
    assert "hello" in vtt
