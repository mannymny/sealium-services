from __future__ import annotations

import os
import zipfile
from pathlib import Path

from ...domain.ports.packager_port import PackagerPort


class ZipPackagerAdapter(PackagerPort):
    def create_zip(self, source_dir: Path, zip_path: Path) -> Path:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(source_dir):
                for file in files:
                    fp = Path(root) / file
                    zf.write(fp, fp.relative_to(source_dir))
        return zip_path
