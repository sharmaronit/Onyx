import base64
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List

from cryptography.fernet import Fernet


class EncryptedQueue:
    def __init__(self, directory: Path, key: str, max_bytes: int = 10 * 1024 * 1024, max_age_days: int = 7):
        self.directory, self.max_bytes, self.max_age_seconds = directory, max_bytes, max_age_days * 86400
        directory.mkdir(parents=True, exist_ok=True)
        self.cipher = Fernet(key.encode("ascii"))

    def put(self, batch: Dict[str, Any]) -> List[str]:
        name = f"{batch['batch_id']}.queue"
        tmp = self.directory / (name + ".tmp")
        tmp.write_bytes(self.cipher.encrypt(json.dumps(batch, allow_nan=False).encode("utf-8")))
        os.replace(tmp, self.directory / name)
        return self.trim()

    def batches(self) -> List[Dict[str, Any]]:
        rows = []
        for path in sorted(self.directory.glob("*.queue"), key=lambda p: p.stat().st_mtime):
            try:
                rows.append(json.loads(self.cipher.decrypt(path.read_bytes()).decode("utf-8")))
            except Exception:
                path.unlink(missing_ok=True)
        return rows

    def acknowledge(self, batch_id: str) -> None:
        (self.directory / f"{batch_id}.queue").unlink(missing_ok=True)

    def trim(self) -> List[str]:
        now, removed, rows = time.time(), [], []
        for path in self.directory.glob("*.queue"):
            stat = path.stat()
            if now - stat.st_mtime > self.max_age_seconds:
                path.unlink(missing_ok=True); removed.append("age")
            else:
                rows.append((path, stat.st_size, stat.st_mtime))
        total = sum(size for _, size, _ in rows)
        for path, size, _ in sorted(rows, key=lambda item: item[2]):
            if total <= self.max_bytes:
                break
            path.unlink(missing_ok=True); total -= size; removed.append("size")
        return removed


def new_queue_key() -> str:
    return Fernet.generate_key().decode("ascii")
