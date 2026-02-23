import re
import os

import pytest

LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")


def test_no_internal_links_missing_md_extension():
    docs_dir = os.path.join(os.path.dirname(__file__), "..", "docs")
    issues = []
    for root, _, files in os.walk(docs_dir):
        for fname in sorted(files):
            if not fname.endswith(".md"):
                continue
            for lineno, line in enumerate(open(os.path.join(root, fname)), 1):
                for m in LINK_RE.finditer(line):
                    url = m.group(2)
                    if (
                        not url.startswith("http")
                        and not url.startswith("#")
                        and ".md" not in url
                    ):
                        rel = os.path.relpath(os.path.join(root, fname), docs_dir)
                        issues.append(f"{rel}:{lineno}: {url}")
    assert issues == [], "Internal links missing .md extension:\n" + "\n".join(issues)
