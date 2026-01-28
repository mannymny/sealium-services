from proof_service.domain.entities.proof_case import ProofCase
from proof_service.domain.entities.error_log import ErrorLog

def test_proof_case_initialization():
    case = ProofCase(case_type="URL", input_target="https://example.com", output_dir="/tmp/out")
    assert case.id is not None
    assert len(case.id) > 0
    assert case.created_at_utc is not None
    assert case.artifacts == []

def test_proof_case_add_artifact():
    case = ProofCase(case_type="FILE", input_target="test.txt", output_dir="/tmp")
    case.add_artifact("captura.png", {"width": "1920"})
    assert len(case.artifacts) == 1
    artifact = case.artifacts[0]
    assert artifact.rel_path == "captura.png"
    assert artifact.metadata["width"] == "1920"

def test_error_log_structure():
    err = ErrorLog(message="Fallo de red")
    assert err.timestamp_utc is not None
    assert err.message == "Fallo de red" 