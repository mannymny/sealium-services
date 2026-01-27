import shutil, zipfile, os, traceback, socket, ssl
from datetime import datetime
from pathlib import Path
from ...domain.entities.proof_case import ProofCase
from ...domain.entities.error_log import ErrorLog
from ...shared.fs__shared_util import ensure_directory, sanitize_filename, hash_file_sha256

class CreateUrlProofUseCase:
    def __init__(self, capture, tsa, monitor, output_root):
        self.capture = capture
        self.tsa = tsa
        self.monitor = monitor
        self.output_root = Path(output_root)

    async def execute(self, url: str) -> dict:
        try:
            ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            host_safe = sanitize_filename(url.split("//")[-1].split("/")[0])
            case_name = f"{ts_str}__{host_safe}"
            case_dir = ensure_directory(self.output_root / case_name)
            verify_dir = ensure_directory(case_dir / "verify")

            case = ProofCase(case_type="URL", input_target=url, output_dir=str(case_dir))

            try:
                domain = url.split("//")[-1].split("/")[0].split(":")[0]
                with open(case_dir / "dns_info.txt", "w") as f: f.write(str(socket.gethostbyname_ex(domain)))
                with open(case_dir / "tls_cert.pem", "w") as f: f.write(ssl.get_server_certificate((domain, 443)))
            except Exception: pass

            await self.capture.capture(url, str(case_dir))

            hashes_path = case_dir / "hashes.sha256"
            with open(hashes_path, "w") as hf:
                for path in case_dir.glob("*"):
                    if path.is_file():
                        h = hash_file_sha256(path)
                        case.add_artifact(path.name, {"sha256": h})
                        hf.write(f"{h} *{path.name}\n")

            shutil.copy(hashes_path, verify_dir / "hashes.sha256")
            await self.tsa.timestamp_file(str(verify_dir / "hashes.sha256"), str(verify_dir))

            with open(case_dir / "manifest.json", "w") as f: f.write(case.json(indent=2))

            zip_path = self.output_root / f"{case_name}.zip"
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for root, _, files in os.walk(case_dir):
                    for file in files:
                        fp = Path(root) / file
                        zf.write(fp, fp.relative_to(case_dir))

            return {"status": "success", "case_id": case.id, "path": str(case_dir)}

        except Exception as e:
            await self.monitor.log_error(ErrorLog(message=str(e), stack_trace=traceback.format_exc(), context_data={"url": url}))
            raise e