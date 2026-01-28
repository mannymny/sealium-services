import pytest
from unittest.mock import mock_open, patch
from proof_service.shared.fs__shared_util import sanitize_filename, hash_file_sha256

def test_sanitize_filename_removes_invalid_chars():
    unsafe_name = 'report: final/version?.pdf'
    expected = 'report_final_version_.pdf'
    assert sanitize_filename(unsafe_name) == expected

def test_sanitize_filename_trims_spaces():
    unsafe_name = '  my   file.txt  '
    expected = 'my_file.txt'
    assert sanitize_filename(unsafe_name) == expected

def test_hash_file_sha256():
    fake_content = b"content_for_hashing"
    with patch("builtins.open", mock_open(read_data=fake_content)):
        expected_hash = "6f2c668b59473b13768406566270ba4325492d35870094e9f733d0279a0b0d35"
        result = hash_file_sha256("dummy_path")
        assert result == expected_hash