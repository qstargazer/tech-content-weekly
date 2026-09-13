from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tech_content_weekly.vault import publish_markdown_to_vault


class VaultTest(unittest.TestCase):
    def test_publish_copies_with_target_name(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "weekly-2026-09-08.md"
            source.write_text("# 认知漫游周报\n", encoding="utf-8")
            vault = root / "vault"
            vault.mkdir()
            destination = publish_markdown_to_vault(
                source, vault, target_dir=Path("0 日常笔记/Weekly/认知漫游")
            )
            self.assertEqual(
                destination,
                (vault / "0 日常笔记/Weekly/认知漫游/2026-09-08 认知漫游周报.md").resolve(),
            )
            self.assertEqual(destination.read_text(encoding="utf-8"), "# 认知漫游周报\n")

    def test_publish_rejects_non_markdown_source(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "weekly-2026-09-08.txt"
            source.write_text("x", encoding="utf-8")
            vault = root / "vault"
            vault.mkdir()
            with self.assertRaises(ValueError):
                publish_markdown_to_vault(source, vault)

    def test_publish_rejects_absolute_target(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "weekly-2026-09-08.md"
            source.write_text("x", encoding="utf-8")
            vault = root / "vault"
            vault.mkdir()
            with self.assertRaises(ValueError):
                publish_markdown_to_vault(source, vault, target_dir=Path("/tmp/abs"))


if __name__ == "__main__":
    unittest.main()