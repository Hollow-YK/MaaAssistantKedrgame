#!/usr/bin/env python3
"""版本解析 / 比较的单元测试。

运行:
    python -m unittest discover -s tools/android -p "test_*.py"
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_versions import compare_versions, normalize_version  # noqa: E402
from resolve_versions import core_candidates, select_core  # noqa: E402


class NormalizeVersionTest(unittest.TestCase):
    def test_strips_v_prefix(self) -> None:
        self.assertEqual(normalize_version("v5.14.0"), "5.14.0")
        self.assertEqual(normalize_version("5.14.0"), "5.14.0")

    def test_prerelease_spellings_match(self) -> None:
        self.assertEqual(
            normalize_version("5.15.0-beta.1"),
            normalize_version("5.15.0b1"),
        )
        self.assertEqual(
            normalize_version("5.15.0-rc.2"),
            normalize_version("5.15.0rc2"),
        )


class CompareVersionTest(unittest.TestCase):
    def test_release_order(self) -> None:
        self.assertEqual(compare_versions("5.14.0", "5.14"), 0)
        self.assertEqual(compare_versions("5.13.0", "5.14.0"), -1)
        self.assertEqual(compare_versions("5.15.0", "5.14.0"), 1)

    def test_prerelease_is_lower_than_release(self) -> None:
        self.assertEqual(compare_versions("5.14.0b1", "5.14.0"), -1)
        self.assertEqual(compare_versions("5.14.0rc1", "5.14.0b1"), 1)


class SelectCoreTest(unittest.TestCase):
    CANDIDATES = [
        ("5.14.0", "3.13.15-maafw5.14.0"),
        ("5.13.0", "3.13.15-maafw5.13.0"),
    ]

    def test_exact_match(self) -> None:
        tag, version, fallback = select_core(self.CANDIDATES, "5.14.0")
        self.assertEqual(tag, "3.13.15-maafw5.14.0")
        self.assertEqual(version, "5.14.0")
        self.assertFalse(fallback)

    def test_fallback_to_highest_lower(self) -> None:
        tag, version, fallback = select_core(self.CANDIDATES, "5.15.0")
        self.assertEqual(tag, "3.13.15-maafw5.14.0")
        self.assertEqual(version, "5.14.0")
        self.assertTrue(fallback)

    def test_no_lower_candidate_fails(self) -> None:
        with self.assertRaises(SystemExit):
            select_core(self.CANDIDATES, "5.12.0")

    def test_skips_unpaired_tags(self) -> None:
        releases = [
            {"tag_name": "3.13.15-maafw5.14.0"},
            {"tag_name": "3.13.15-maafw5.13.0"},
            {"tag_name": "v5.12.0"},
            {"tag_name": "3.13.15-maafw5.15.0", "draft": True},
        ]
        self.assertEqual(len(core_candidates(releases)), 2)


if __name__ == "__main__":
    unittest.main()
