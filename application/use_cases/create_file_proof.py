import shutil, zipfile, os, traceback
from datetime import datetime
from pathlib import Path
from ...domain.entities.proof_case import ProofCase
from ...domain.entities.error_log import ErrorLog
from ...shared.fs__shared_util import ensure_directory, sanitize_filename, hash_file_sha256

class CreateFileProofUseCase:
    def __init__(self, forensics, tsa, monitor, output_root):
        self.forensics = forensics
        self.tsa = tsa
        self.monitor = monitor
        self.output_root = Path(output_root)

    async def execute(self, path: str, forensic_mode: bool) -> dict:
        try:
            target = Path(path).resolve()
            if not target.exists(): raise FileNotFoundError(f"Missing: {path}")

            ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            case_name = f"local__{sanitize_filename(target.name)}__{ts_str}"
            case_dir = ensure_directory(self.output_root / case_name)
            
            case = ProofCase(case_type="FILE", input_target=str(target), output_dir=str(case_dir))
            
            dest_copy = case_dir / f"target_{hash_file_sha256(target)[:10]}{target.suffix}"
            shutil.copy2(target, dest_copy)

            if forensic_mode:
                await self.forensics.collect_metadata(str(target), str(case_dir))
                await self.forensics.collect_system_logs(str(case_dir))

            hashes_path = case_dir / "hashes.sha256"
            with open(hashes_path, "w") as hf:
                for p in case_dir.glob("*"):
                    if p.is_file():
                        h = hash_file_sha256(p)
                        case.add_artifact(p.name, {"sha256": h})
                        hf.write(f"{h} *{p.name}\n")
            
            ts_dir = ensure_directory(case_dir / "timestamps")
            await self.tsa.timestamp_file(str(hashes_path), str(ts_dir))

            with open(case_dir / "manifest.json", "w") as f: f.write(case.json(indent=2))

            zip_path = self.output_root / f"{case_name}.zip"
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for root, _, files in os.walk(case_dir):
                    for file in files:
                        fp = Path(root) / file
                        zf.write(fp, fp.relative_to(case_dir))

            return {"status": "success", "case_id": case.id}

        except Exception as e:
            await self.monitor.log_error(ErrorLog(message=str(e), stack_trace=traceback.format_exc(), context_data={"path": path}))
            raise e