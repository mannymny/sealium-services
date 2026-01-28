import re, traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from ...domain.entities.error_log import ErrorLog
from ...shared.fs__shared_util import ensure_directory, hash_file_sha256


class VerifyProofCaseUseCase:
    def __init__(self, monitor):
        self.monitor = monitor

    async def execute(self, proof_dir: str) -> dict:
        try:
            proof_path = Path(proof_dir).resolve()
            if not proof_path.exists():
                raise FileNotFoundError(f"ProofDir not found: {proof_dir}")

            if proof_path.name.lower() == "verify":
                proof_path = proof_path.parent

            verify_dir = ensure_directory(proof_path / "verify")

            hashes_path = proof_path / "hashes.sha256"
            if not hashes_path.exists():
                alt = verify_dir / "hashes.sha256"
                if alt.exists():
                    hashes_path = alt
                else:
                    raise FileNotFoundError(f"hashes.sha256 not found in: {proof_path}")

            report_path = verify_dir / f"verify_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

            log: List[str] = []
            log.append("VERIFY REPORT")
            log.append("=============")
            log.append(f"ProofDir: {proof_path}")
            log.append(f"Hashes:   {hashes_path}")
            log.append(f"UTC Now:  {datetime.now(timezone.utc).isoformat()}")
            log.append("")

            errors = 0
            log.append("FOLDER FILE HASH CHECK")
            log.append("----------------------")

            for line in hashes_path.read_text(encoding="utf-8").splitlines():
                t = line.strip()
                if not t:
                    continue
                parts = t.split(" ", 1)
                if len(parts) < 2:
                    continue
                expected = parts[0].strip().lower()
                rel = parts[1].strip().lstrip("*").strip()
                file_path = proof_path / rel
                if not file_path.exists():
                    log.append(f"[MISSING] {rel}")
                    errors += 1
                    continue
                actual = hash_file_sha256(file_path)
                if actual != expected:
                    log.append(f"[HASH MISMATCH] {rel}")
                    log.append(f"  expected: {expected}")
                    log.append(f"  actual:   {actual}")
                    errors += 1
                else:
                    log.append(f"[OK] {rel}")

            log.append("")
            if errors == 0:
                log.append("Folder: SUCCESS")
            else:
                log.append(f"Folder: FAILED with {errors} issue(s).")

            zip_path = self._resolve_zip_path(proof_path, verify_dir)
            log.append("")
            log.append("ZIP CHECK")
            log.append("---------")

            if zip_path and zip_path.exists():
                log.append(f"ZipPath: {zip_path}")
                zip_errors = self._verify_zip_sidefiles(zip_path, verify_dir, log)
                errors += zip_errors
            else:
                log.append("(No ZIP found next to folder; skipping ZIP verification.)")

            log.append("")
            if errors > 0:
                log.append(f"FAILED overall with {errors} issue(s).")
                self._write_report(report_path, log)
                return {
                    "status": "failed",
                    "errors": errors,
                    "report_path": str(report_path),
                    "proof_dir": str(proof_path),
                    "hashes_path": str(hashes_path),
                    "zip_path": str(zip_path) if zip_path else None,
                }

            log.append("SUCCESS overall.")
            self._write_report(report_path, log)
            return {
                "status": "success",
                "errors": 0,
                "report_path": str(report_path),
                "proof_dir": str(proof_path),
                "hashes_path": str(hashes_path),
                "zip_path": str(zip_path) if zip_path else None,
            }

        except Exception as e:
            await self.monitor.log_error(
                ErrorLog(
                    message=str(e),
                    stack_trace=traceback.format_exc(),
                    context_data={"proof_dir": proof_dir},
                )
            )
            raise e

    def _resolve_zip_path(self, proof_path: Path, verify_dir: Path) -> Optional[Path]:
        leaf = proof_path.name
        parent = proof_path.parent
        zip_path = verify_dir / f"{leaf}.zip"
        if not zip_path.exists():
            zip_path = parent / f"{leaf}.zip"
        return zip_path

    def _verify_zip_sidefiles(self, zip_path: Path, verify_dir: Path, log: List[str]) -> int:
        errors = 0
        leaf = zip_path.stem

        zip_sha_txt_in_verify = verify_dir / f"{leaf}.zip.sha256.txt"
        zip_sha_txt_next = Path(f"{zip_path}.sha256.txt")
        zip_sha_txt = zip_sha_txt_in_verify if zip_sha_txt_in_verify.exists() else zip_sha_txt_next

        if not zip_sha_txt.exists():
            log.append(f"[MISSING] zip sha256 sidefile: {zip_sha_txt}")
            errors += 1
        else:
            lines = zip_sha_txt.read_text(encoding="utf-8").splitlines()
            line = lines[0].strip() if lines else ""
            expected_zip = None
            m = re.search(r"sha256\s*=\s*([0-9a-fA-F]{64})", line)
            if m:
                expected_zip = m.group(1).lower()
            if not expected_zip:
                log.append(f"[BAD FORMAT] {zip_sha_txt}")
                errors += 1
            else:
                actual_zip = hash_file_sha256(zip_path)
                if actual_zip != expected_zip:
                    log.append("[HASH MISMATCH] ZIP")
                    log.append(f"  expected: {expected_zip}")
                    log.append(f"  actual:   {actual_zip}")
                    errors += 1
                else:
                    log.append(f"[OK] ZIP hash matches {zip_sha_txt}")

        zip_tsq_in_verify = verify_dir / f"{leaf}.zip.sha256.tsq"
        zip_tsr_in_verify = verify_dir / f"{leaf}.zip.sha256.tsr"
        zip_tsq_next = Path(f"{zip_path}.sha256.tsq")
        zip_tsr_next = Path(f"{zip_path}.sha256.tsr")
        tsq = zip_tsq_in_verify if zip_tsq_in_verify.exists() else zip_tsq_next
        tsr = zip_tsr_in_verify if zip_tsr_in_verify.exists() else zip_tsr_next

        if tsq.exists() or tsr.exists():
            if not tsq.exists():
                log.append(f"[MISSING] {tsq}")
                errors += 1
            else:
                log.append(f"[OK] {tsq}")
            if not tsr.exists():
                log.append(f"[MISSING] {tsr}")
                errors += 1
            else:
                log.append(f"[OK] {tsr}")
        else:
            log.append("(No TSA sidefiles found for ZIP; timestamp may be disabled.)")

        return errors

    def _write_report(self, report_path: Path, log: List[str]) -> None:
        report_path.write_text("\n".join(log) + "\n", encoding="utf-8")
