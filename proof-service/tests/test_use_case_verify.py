import pytest
from pathlib import Path
from unittest.mock import AsyncMock
from zipfile import ZipFile

from proof_service.application.use_cases.verify_proof_case import VerifyProofCaseUseCase
from proof_service.shared.fs__shared_util import hash_file_sha256, ensure_directory


@pytest.mark.asyncio
async def test_verify_success(tmp_path):
    proof_dir = tmp_path / "case_1"
    proof_dir.mkdir()
    (proof_dir / "a.txt").write_text("hello")
    (proof_dir / "b.txt").write_text("world")

    hashes_path = proof_dir / "hashes.sha256"
    with open(hashes_path, "w", encoding="utf-8") as f:
        for name in ["a.txt", "b.txt"]:
            fp = proof_dir / name
            f.write(f"{hash_file_sha256(fp)} *{name}\n")

    verify_dir = ensure_directory(proof_dir / "verify")
    zip_path = verify_dir / f"{proof_dir.name}.zip"
    with ZipFile(zip_path, "w") as zf:
        zf.write(proof_dir / "a.txt", "a.txt")

    zip_sha = hash_file_sha256(zip_path)
    (verify_dir / f"{proof_dir.name}.zip.sha256.txt").write_text(f"sha256 = {zip_sha}\n", encoding="utf-8")

    use_case = VerifyProofCaseUseCase(AsyncMock())
    res = await use_case.execute(str(proof_dir))

    assert res["status"] == "success"
    assert res["errors"] == 0
    assert Path(res["report_path"]).exists()


@pytest.mark.asyncio
async def test_verify_missing_file(tmp_path):
    proof_dir = tmp_path / "case_2"
    proof_dir.mkdir()
    (proof_dir / "a.txt").write_text("hello")

    hashes_path = proof_dir / "hashes.sha256"
    with open(hashes_path, "w", encoding="utf-8") as f:
        f.write(f"{hash_file_sha256(proof_dir / 'a.txt')} *a.txt\n")
        f.write("deadbeef" * 8 + " *missing.txt\n")

    use_case = VerifyProofCaseUseCase(AsyncMock())
    res = await use_case.execute(str(proof_dir))

    assert res["status"] == "failed"
    assert res["errors"] >= 1
    assert Path(res["report_path"]).exists()


@pytest.mark.asyncio
async def test_verify_zip_hash_mismatch(tmp_path):
    proof_dir = tmp_path / "case_3"
    proof_dir.mkdir()
    (proof_dir / "a.txt").write_text("hello")

    hashes_path = proof_dir / "hashes.sha256"
    hashes_path.write_text(f"{hash_file_sha256(proof_dir / 'a.txt')} *a.txt\n", encoding="utf-8")

    verify_dir = ensure_directory(proof_dir / "verify")
    zip_path = verify_dir / f"{proof_dir.name}.zip"
    with ZipFile(zip_path, "w") as zf:
        zf.writestr("a.txt", "hello")

    (verify_dir / f"{proof_dir.name}.zip.sha256.txt").write_text(
        "sha256 = " + ("0" * 64) + "\n",
        encoding="utf-8",
    )

    use_case = VerifyProofCaseUseCase(AsyncMock())
    res = await use_case.execute(str(proof_dir))

    assert res["status"] == "failed"
    assert res["errors"] >= 1
