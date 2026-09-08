from __future__ import annotations

import ast
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).parents[1]


class RepositoryMetadataTests(unittest.TestCase):
    def test_version_and_registry_metadata_match(self) -> None:
        init_tree = ast.parse((ROOT / "__init__.py").read_text(encoding="utf-8"))
        version = next(
            node.value.value
            for node in init_tree.body
            if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == "__version__" for target in node.targets)
            and isinstance(node.value, ast.Constant)
        )
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        declared = re.search(r'^version = "([^"]+)"$', pyproject, re.MULTILINE)
        self.assertIsNotNone(declared)
        self.assertEqual(version, declared.group(1))
        self.assertIn('PublisherId = "zihaomu"', pyproject)
        self.assertIn('license = { file = "LICENSE" }', pyproject)

    def test_public_files_do_not_contain_credentials(self) -> None:
        pattern = re.compile(r"Bearer\s+[A-Za-z0-9_-]{16,}|H3_API_KEY=[A-Za-z0-9_-]{16,}")
        for path in ROOT.rglob("*"):
            if not path.is_file() or ".git" in path.parts or "__pycache__" in path.parts:
                continue
            if path.suffix not in {".py", ".md", ".json", ".toml", ".yml", ".yaml"}:
                continue
            with self.subTest(path=path.relative_to(ROOT)):
                self.assertIsNone(pattern.search(path.read_text(encoding="utf-8")))


if __name__ == "__main__":
    unittest.main()
