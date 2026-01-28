from transcription_service.domain.entities.transcription_case import TranscriptionCase


def test_transcription_case_add_artifact():
    case = TranscriptionCase(case_type="URL", input_target="http://example.com", output_dir="/tmp")
    case.add_artifact("file.txt", hash_sha256="abc123")
    assert len(case.artifacts) == 1
    assert case.artifacts[0].rel_path == "file.txt"
    assert case.artifacts[0].hash_sha256 == "abc123"
