import io
import os
import hashlib
import json
import mimetypes
from dataclasses import dataclass
from typing import List, Dict, Any

try:
    import magic as _magic  # optional: python-magic
except Exception:
    _magic = None

try:
    import pefile  # optional: pefile for EXE parsing
except Exception:
    pefile = None

import zipfile
import tarfile
import gzip


@dataclass
class BinaryExtractionResult:
    job_id: str
    extracted_files: List[Dict[str, Any]]
    relationships: List[Dict[str, str]]
    metadata: Dict[str, Any]


class BinaryExtractor:
    """Lightweight binary extraction and metadata service.

    Notes:
    - Uses stdlib archives for ZIP/TAR/GZ extraction.
    - Uses `pefile` (if available) for basic EXE analysis and resource extraction.
    - Uses `python-magic` (if available) for MIME detection; otherwise falls back to
      `mimetypes`.
    - MSI handling is best-effort (metadata extraction); full content extraction may
      require platform-specific tools and is left as a graceful fallback.
    """

    def __init__(self):
        self._magic = _magic

    def _sha256(self, data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    def _mime_type(self, filename: str, data: bytes) -> str:
        if self._magic:
            try:
                return self._magic.from_buffer(data, mime=True)
            except Exception:
                pass
        # Fallback
        mime, _ = mimetypes.guess_type(filename)
        return mime or "application/octet-stream"

    def extract(self, filename: str, data: bytes, job_id: str = None) -> BinaryExtractionResult:
        """Dispatch extraction based on filename / magic.

        Returns BinaryExtractionResult with extracted files list and relationships.
        """
        lower = filename.lower()
        extracted = []
        relationships = []

        # Container dispatch
        if lower.endswith('.zip'):
            extracted = self._extract_zip(data)
        elif lower.endswith('.tar') or lower.endswith('.tar.gz') or lower.endswith('.tgz'):
            extracted = self._extract_tar(data)
        elif lower.endswith('.gz') and not lower.endswith('.tar.gz'):
            extracted = self._extract_gz(data, filename)
        elif lower.endswith('.exe'):
            extracted = self._analyze_exe(data, filename)
        elif lower.endswith('.msi'):
            extracted = self._analyze_msi(data, filename)
        else:
            # Unknown: attempt to detect if it's an archive by magic
            if self._magic:
                try:
                    mime = self._magic.from_buffer(data, mime=True)
                    if mime in ("application/zip", "application/x-tar"):
                        # fall back to zip
                        extracted = self._extract_zip(data)
                except Exception:
                    pass

        # If nothing extracted, treat the uploaded file as a single document
        if not extracted:
            metadata = {
                "path": filename,
                "size": len(data),
                "sha256": self._sha256(data),
                "mime_type": self._mime_type(filename, data),
            }
            extracted = [metadata]

        # Build simple parent-child relationships: root -> each file
        for f in extracted:
            relationships.append({"parent": filename, "child": f.get("path"), "type": "contains"})

        meta = {"original_filename": filename, "files_count": len(extracted)}
        return BinaryExtractionResult(job_id=(job_id or ""), extracted_files=extracted, relationships=relationships, metadata=meta)

    def _extract_zip(self, data: bytes) -> List[Dict[str, Any]]:
        extracted = []
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            for info in z.infolist():
                if info.is_dir():
                    continue
                path = info.filename
                content = z.read(path)
                entry = {
                    "path": path,
                    "size": len(content),
                    "sha256": self._sha256(content),
                    "mime_type": self._mime_type(path, content),
                }
                extracted.append(entry)
        return extracted

    def _extract_tar(self, data: bytes) -> List[Dict[str, Any]]:
        extracted = []
        # tarfile can read gzip-compressed tarballs transparently
        fileobj = io.BytesIO(data)
        try:
            with tarfile.open(fileobj=fileobj, mode='r:*') as tar:
                for member in tar.getmembers():
                    if not member.isfile():
                        continue
                    f = tar.extractfile(member)
                    if f is None:
                        continue
                    content = f.read()
                    entry = {
                        "path": member.name,
                        "size": len(content),
                        "sha256": self._sha256(content),
                        "mime_type": self._mime_type(member.name, content),
                    }
                    extracted.append(entry)
        except Exception:
            # Not a tar archive (or unsupported compression)
            pass
        return extracted

    def _extract_gz(self, data: bytes, filename: str) -> List[Dict[str, Any]]:
        extracted = []
        try:
            with gzip.GzipFile(fileobj=io.BytesIO(data)) as gz:
                content = gz.read()
                inner_name = filename[:-3] if filename.lower().endswith('.gz') else filename + '.out'
                entry = {
                    "path": inner_name,
                    "size": len(content),
                    "sha256": self._sha256(content),
                    "mime_type": self._mime_type(inner_name, content),
                }
                extracted.append(entry)
        except Exception:
            pass
        return extracted

    def _analyze_exe(self, data: bytes, filename: str) -> List[Dict[str, Any]]:
        extracted = []
        # Basic metadata about PE
        entry = {"path": filename, "size": len(data), "sha256": self._sha256(data), "mime_type": "application/x-ms-dos-executable"}
        if pefile:
            try:
                pe = pefile.PE(data=data)
                # collect section names and sizes
                sections = [{"name": s.Name.decode(errors='ignore').strip('\x00'), "size": s.SizeOfRawData} for s in pe.sections]
                entry["pe_sections"] = sections
                # resources
                resources = []
                if hasattr(pe, 'DIRECTORY_ENTRY_RESOURCE'):
                    for res in pe.DIRECTORY_ENTRY_RESOURCE.entries:
                        resources.append(str(res.struct))
                entry["pe_resources_count"] = len(resources)
            except Exception:
                pass
        extracted.append(entry)
        return extracted

    def _analyze_msi(self, data: bytes, filename: str) -> List[Dict[str, Any]]:
        # MSI is a database file; for now extract metadata and surface it.
        entry = {"path": filename, "size": len(data), "sha256": self._sha256(data), "mime_type": "application/x-msi"}
        # More advanced parsing may use platform tools; leave for future enhancement.
        return [entry]
