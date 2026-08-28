from __future__ import annotations

import argparse
from pathlib import Path

from tech_content_weekly.vault import DEFAULT_VAULT_TARGET, publish_markdown_to_vault


def main() -> None:
    parser = argparse.ArgumentParser(description="Copy a generated weekly report into an Obsidian Vault working tree")
    parser.add_argument("--source", type=Path, required=True, help="Generated weekly report Markdown file")
    parser.add_argument("--vault-dir", type=Path, required=True, help="Local checkout of the Obsidian Vault repository")
    parser.add_argument("--target-dir", type=Path, default=DEFAULT_VAULT_TARGET, help="Relative directory inside the Vault")
    args = parser.parse_args()
    destination = publish_markdown_to_vault(args.source, args.vault_dir, args.target_dir)
    print(f"Published weekly report: {destination}")


if __name__ == "__main__":
    main()
