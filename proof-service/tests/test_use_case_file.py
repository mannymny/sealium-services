import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
from proof_service.application.use_cases.create_file_proof import CreateFileProofUseCase

@pytest.mark.asyncio
async def test_file_proof_success(tmp_path):
    dummy_file = tmp_path / "evidence.txt"
    dummy_file.write_text("dato importante")
    mock_forensics = AsyncMock()
    mock_tsa = AsyncMock()
    mock_monitor = AsyncMock()
    use_case = CreateFileProofUseCase(mock_forensics, mock_tsa, mock_monitor, str(tmp_path))
    with patch("shutil.copy2") as mock_copy, patch("zipfile.ZipFile"):
        res = await use_case.execute(str(dummy_file), forensic_mode=True)
    assert res["status"] == "success"
    assert "zip_path" in res
    assert "path" in res
    mock_forensics.collect_metadata.assert_called_once()
    mock_copy.assert_called()

@pytest.mark.asyncio
async def test_file_not_found_error(tmp_path):
    use_case = CreateFileProofUseCase(AsyncMock(), AsyncMock(), AsyncMock(), str(tmp_path))
    with pytest.raises(FileNotFoundError):
        await use_case.execute("archivo_imaginario.txt", False)

@pytest.mark.asyncio
async def test_file_proof_no_keep_dir(tmp_path):
    dummy_file = tmp_path / "evidence.txt"
    dummy_file.write_text("important data")
    use_case = CreateFileProofUseCase(AsyncMock(), AsyncMock(), AsyncMock(), str(tmp_path), keep_dir=False)
    with patch("shutil.copy2"), patch("zipfile.ZipFile"):
        res = await use_case.execute(str(dummy_file), forensic_mode=False)
    assert res["status"] == "success"
    assert "zip_path" in res
    assert "path" not in res
