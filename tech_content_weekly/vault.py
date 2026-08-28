from __future__ import annotations

import re
import shutil
from pathlib import Path


DEFAULT_VAULT_TARGET = Path("0 日常笔记/Weekly/认知漫游")
SUFFIX = "认知漫游周报"


def publish_markdown_to_vault(source: Path, vault_dir: Path, target_dir: Path = DEFAULT_VAULT_TARGET) -> Path:
    """Copy a generated weekly report into an Obsidian Vault working tree.

    This intentionally performs no Git operation. The caller remains responsible
    for reviewing, committing, and pushing the Vault work tree.
    """
    source = source.resolve()
    vault_dir = vault_dir.resolve()
    if not source.is_file() or source.suffix.lower() != ".md":
        raise ValueError(f"Weekly report Markdown was not found: {source}")
    if not vault_dir.is_dir():
        raise ValueError(f"Vault work tree was not found: {vault_dir}")
    if target_dir.is_absolute() or ".." in target_dir.parts:
        raise ValueError("Vault target directory must be a relative path inside the Vault")

    destination_dir = vault_dir / target_dir
    destination_dir.mkdir(parents=True, exist_ok=True)
    stem = re.sub(r"^weekly[-_]", "", source.stem)
    destination = destination_dir / f"{stem} {SUFFIX}.md"
    shutil.copyfile(source, destination)
    return destination
