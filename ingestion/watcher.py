
# Detects new or modified files via hashing against a persistent manifest.


from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md"}


def compute_file_hash(path: str | Path, chunk_size: int = 8192) -> str:

    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()


class FileWatcher:

    
    def __init__(self, manifest_path: str | Path):
        self.manifest_path = Path(manifest_path)
        self.manifest: dict[str, str] = self._load_manifest()

    def _load_manifest(self) -> dict[str, str]:
        if self.manifest_path.exists():
            try:
                with open(self.manifest_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning("Failed to load manifest %s: %s", self.manifest_path, e)
                

        metadata_path = self.manifest_path.parent / "metadata.json"
        if metadata_path.exists() and not self.manifest_path.exists():
            logger.info("Initializing watcher manifest from existing vector metadata... (preventing duplicates)")
            manifest: dict[str, str] = {}
            try:
                with open(metadata_path, "r", encoding="utf-8") as f:
                    metadata = json.load(f)
                

                indexed_files = {m["source_file"] for m in metadata if "source_file" in m}
                
                for p in indexed_files:
                    path_obj = Path(p)
                    if path_obj.exists():
                        manifest[str(path_obj.resolve())] = compute_file_hash(path_obj)
                        
                return manifest
            except Exception as e:
                logger.warning("Failed to retroactively build manifest: %s", e)
                
        return {}

    def save_manifest(self) -> None:

        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.manifest_path, "w", encoding="utf-8") as f:
            json.dump(self.manifest, f, indent=2, ensure_ascii=False)

    def scan(self, base_dir: str | Path, extensions: set[str] | None = None) -> list[str]:

        base = Path(base_dir).resolve()
        exts = extensions or SUPPORTED_EXTENSIONS
        
        if not base.is_dir():
            raise FileNotFoundError(f"Base directory not found: {base}")

        new_or_modified: list[str] = []
        
        for p in base.rglob("*"):
            if not p.is_file() or p.suffix.lower() not in exts:
                continue
                
            abs_path = str(p)
            file_hash = compute_file_hash(p)
            
            if self.manifest.get(abs_path) != file_hash:
                new_or_modified.append(abs_path)
                self.manifest[abs_path] = file_hash
                
        logger.info("Watcher scan found %d new/modified files", len(new_or_modified))
        return new_or_modified
