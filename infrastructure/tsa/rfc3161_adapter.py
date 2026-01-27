import hashlib
import requests
import os
from pathlib import Path
from asn1crypto import tsp, algos
from ...domain.ports.tsa_port import TimeStampingPort

class Rfc3161Adapter(TimeStampingPort):
    def __init__(self, tsa_url: str):
        self.tsa_url = tsa_url

    async def timestamp_file(self, file_path: str, output_dir: str) -> str:
        p_file = Path(file_path)
        p_out = Path(output_dir)
        
        sha256 = hashlib.sha256()
        with open(p_file, "rb") as f:
            while chunk := f.read(4096): sha256.update(chunk)
        
        nonce = int.from_bytes(os.urandom(8), 'big')
        tsq = tsp.TimeStampReq({
            'version': 'v1',
            'message_imprint': tsp.MessageImprint({
                'hash_algorithm': algos.DigestAlgorithm({'algorithm': 'sha256'}),
                'hashed_message': sha256.digest()
            }),
            'nonce': nonce, 'cert_req': True
        })
        
        with open(p_out / (p_file.name + ".tsq"), "wb") as f: f.write(tsq.dump())
        
        headers = {'Content-Type': 'application/timestamp-query'}
        res = requests.post(self.tsa_url, data=tsq.dump(), headers=headers, timeout=10)
        res.raise_for_status()
        
        tsr_path = p_out / (p_file.name + ".tsr")
        with open(tsr_path, "wb") as f: f.write(res.content)
        return str(tsr_path)