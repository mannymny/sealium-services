import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from proof_service.application.use_cases.create_url_proof import CreateUrlProofUseCase

@pytest.mark.asyncio
async def test_execute_success(tmp_path):
    mock_capture = AsyncMock()
    mock_tsa = AsyncMock()
    mock_monitor = AsyncMock()
    mock_tsa.timestamp_file.return_value = "/tmp/mock.tsr"
    use_case = CreateUrlProofUseCase(mock_capture, mock_tsa, mock_monitor, str(tmp_path))

    with patch("builtins.open", new_callable=MagicMock), \
         patch("socket.gethostbyname_ex"), \
         patch("ssl.get_server_certificate"), \
         patch("shutil.copy"), \
         patch("zipfile.ZipFile"):
        result = await use_case.execute("https://google.com")

    assert result["status"] == "success"
    mock_capture.capture.assert_called_once()
    mock_tsa.timestamp_file.assert_called_once()
    mock_monitor.log_error.assert_not_called()

@pytest.mark.asyncio
async def test_execute_failure_logs_error(tmp_path):
    mock_capture = AsyncMock()
    mock_capture.capture.side_effect = Exception("Browser Error")
    mock_monitor = AsyncMock()
    use_case = CreateUrlProofUseCase(mock_capture, AsyncMock(), mock_monitor, str(tmp_path))
    with pytest.raises(Exception):
        await use_case.execute("https://fail.com")
    mock_monitor.log_error.assert_called_once()