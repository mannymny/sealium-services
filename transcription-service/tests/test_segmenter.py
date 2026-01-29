from transcription_service.processing.segmenter import parse_silencedetect_output, segments_from_silence


def test_segmenter_silence_parsing():
    output = """
[silencedetect @ 0x1] silence_start: 1.0
[silencedetect @ 0x1] silence_end: 2.0 | silence_duration: 1.0
[silencedetect @ 0x1] silence_start: 4.0
[silencedetect @ 0x1] silence_end: 4.5 | silence_duration: 0.5
"""
    silences = parse_silencedetect_output(output)
    assert silences == [(1.0, 2.0), (4.0, 4.5)]

    segments = segments_from_silence(silences, duration=6.0, max_chunk_seconds=2)
    assert segments[0] == (0.0, 1.0)
    assert segments[1] == (2.0, 4.0)
    assert segments[2] == (4.5, 6.0)


def test_segmenter_splits_long_segments():
    silences = []
    segments = segments_from_silence(silences, duration=5.0, max_chunk_seconds=2)
    assert segments == [(0.0, 2.0), (2.0, 4.0), (4.0, 5.0)]
