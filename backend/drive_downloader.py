"""
Google Drive folder downloader.

Accepts public Google Drive folder share links (anyone with the link can view)
and downloads all PDF/DOCX/TXT files to a local directory.

Uses gdown for reliable Drive downloads without requiring OAuth credentials.
"""

from __future__ import annotations

import re
import tempfile
import time
from pathlib import Path
from typing import Callable, List, Optional

SUPPORTED_EXTS = {".pdf", ".docx", ".doc", ".txt"}


def _extract_folder_id(link: str) -> Optional[str]:
    """Extract Drive folder ID from various link formats."""
    patterns = [
        r"folders/([a-zA-Z0-9_-]{25,})",
        r"id=([a-zA-Z0-9_-]{25,})",
        r"open\?id=([a-zA-Z0-9_-]{25,})",
    ]
    for pat in patterns:
        m = re.search(pat, link)
        if m:
            return m.group(1)
    # Bare folder ID
    if re.match(r"^[a-zA-Z0-9_-]{25,}$", link.strip()):
        return link.strip()
    return None


def _extract_file_id(link: str) -> Optional[str]:
    """Extract single file ID from Drive link."""
    patterns = [
        r"/d/([a-zA-Z0-9_-]{25,})",
        r"id=([a-zA-Z0-9_-]{25,})",
    ]
    for pat in patterns:
        m = re.search(pat, link)
        if m:
            return m.group(1)
    return None


def download_drive_folder(
    link: str,
    dest_dir: Optional[Path] = None,
    progress_cb: Optional[Callable[[str], None]] = None,
) -> List[Path]:
    """
    Download all resume files from a public Google Drive folder link.

    Returns list of local file paths that were downloaded successfully.
    Raises ValueError for invalid links.
    Raises RuntimeError if gdown fails or no files found.
    """
    import gdown

    if dest_dir is None:
        dest_dir = Path(tempfile.mkdtemp(prefix="signalrank_resumes_"))
    dest_dir.mkdir(parents=True, exist_ok=True)

    folder_id = _extract_folder_id(link)
    if not folder_id:
        raise ValueError(
            f"Could not extract a Google Drive folder ID from: {link!r}\n"
            "Expected a link like: https://drive.google.com/drive/folders/FOLDER_ID"
        )

    if progress_cb:
        progress_cb(f"Downloading from Google Drive folder: {folder_id[:12]}…")

    try:
        gdown.download_folder(
            id=folder_id,
            output=str(dest_dir),
            quiet=True,
            remaining_ok=True,
        )
    except Exception as e:
        raise RuntimeError(
            f"gdown failed to download folder {folder_id!r}: {e}\n"
            "Make sure the folder is publicly shared (Anyone with the link → Viewer)."
        ) from e

    # Collect downloaded files (recursively)
    files = [
        p for p in dest_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS
    ]

    if not files:
        raise RuntimeError(
            f"No resume files (PDF/DOCX/TXT) found in the downloaded folder.\n"
            f"Downloaded to: {dest_dir}\n"
            "Check that the folder contains PDF, DOCX, or TXT files."
        )

    if progress_cb:
        progress_cb(f"Downloaded {len(files)} resume file(s).")

    return sorted(files)


def download_single_drive_file(
    link: str,
    dest_dir: Optional[Path] = None,
    progress_cb: Optional[Callable[[str], None]] = None,
) -> Path:
    """Download a single file from a Google Drive share link."""
    import gdown

    if dest_dir is None:
        dest_dir = Path(tempfile.mkdtemp(prefix="signalrank_resume_"))
    dest_dir.mkdir(parents=True, exist_ok=True)

    file_id = _extract_file_id(link)
    if not file_id:
        raise ValueError(f"Could not extract file ID from link: {link!r}")

    url = f"https://drive.google.com/uc?id={file_id}"
    out_path = str(dest_dir / "resume.pdf")

    if progress_cb:
        progress_cb(f"Downloading file {file_id[:12]}…")

    try:
        result = gdown.download(url, out_path, quiet=True, fuzzy=True)
    except Exception as e:
        raise RuntimeError(f"Download failed: {e}") from e

    if not result or not Path(result).exists():
        raise RuntimeError("Download returned no file. Check that the link is public.")

    # Detect real extension from content
    p = Path(result)
    if p.suffix.lower() not in SUPPORTED_EXTS:
        # Try renaming based on content magic bytes
        content = p.read_bytes()[:8]
        if content.startswith(b"%PDF"):
            new_p = p.with_suffix(".pdf")
            p.rename(new_p)
            p = new_p
        elif content[:2] == b"PK":  # ZIP-based (DOCX)
            new_p = p.with_suffix(".docx")
            p.rename(new_p)
            p = new_p

    return p
