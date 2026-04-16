#!/usr/bin/env python3
"""
audit_image_registry.py - Audit MDX files for image metadata quality

Reports:
  - Inline src= calls that escaped migration (regression check)
  - Registry entries with caption: TBD
    - Registry entries with altStatus: pending
  - Image src paths that don't exist on disk
  - Registry entries referenced by id= but missing from frontmatter

Usage:
    python audit_image_registry.py                    # all MDX files
    python audit_image_registry.py --slug swan-chair  # single file
    python audit_image_registry.py --fix-tbd          # list TBD items for editing
"""

import argparse
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).parent
CONTENT_DIR = ROOT / "src" / "content" / "blog"
IMAGES_DIR = ROOT / "public" / "images"


def find_mdx_files(slug: str | None) -> list[Path]:
    if slug:
        for ext in [".mdx", ".md"]:
            p = CONTENT_DIR / f"{slug}{ext}"
            if p.exists():
                return [p]
        print(f"ERROR: No MDX file found for slug: {slug}")
        sys.exit(1)
    return sorted(
        list(CONTENT_DIR.glob("*.mdx")) + list(CONTENT_DIR.glob("*.md"))
    )


def audit_file(mdx_path: Path) -> list[dict]:
    """Return a list of issue dicts for the given MDX file."""
    content = mdx_path.read_text(encoding="utf-8")
    issues: list[dict] = []

    if not content.startswith("---"):
        return [{"level": "error", "msg": "Missing frontmatter delimiter"}]

    parts = content.split("---", 2)
    if len(parts) < 3:
        return [{"level": "error", "msg": "Invalid frontmatter structure"}]

    frontmatter_text = parts[1]
    body = parts[2]

    try:
        data = yaml.safe_load(frontmatter_text)
    except yaml.YAMLError as e:
        return [{"level": "error", "msg": f"YAML parse error: {e}"}]

    images: list[dict] = data.get("images") or []
    registry_by_id = {img["id"]: img for img in images if img.get("id")}

    # ── 1. Inline src= calls (migration regression) ──────────────────────────
    inline_tags = re.findall(r"<ImageWithMeta\s+([\s\S]*?)/>", body)
    for tag_body in inline_tags:
        if not re.search(r'\bid="', tag_body):
            src = re.search(r'src="([^"]*)"', tag_body)
            issues.append({
                "level": "error",
                "msg": f"Unmigrated inline src= call: {src.group(1) if src else '(unknown)'}",
            })

    # ── 2. id= references with no registry entry ─────────────────────────────
    id_refs = re.findall(r'id="([^"]+)"', body)
    for ref_id in id_refs:
        if ref_id not in registry_by_id:
            issues.append({
                "level": "error",
                "msg": f"id={ref_id!r} used in body but not found in frontmatter images[]",
            })

    # ── 3. Registry quality checks ────────────────────────────────────────────
    for img in images:
        img_id = img.get("id", "(no id)")

        if img.get("caption") in ("TBD", "", None):
            issues.append({"level": "warn", "msg": f"[{img_id}] caption is TBD"})

        if img.get("altStatus", "pending") == "pending":
            issues.append({"level": "warn", "msg": f"[{img_id}] altStatus is 'pending'"})

        if img.get("source") in ("TBD", "", None):
            issues.append({"level": "info", "msg": f"[{img_id}] source is TBD"})

        # ── 4. Missing image files on disk ────────────────────────────────────
        src = img.get("src", "")
        if src.startswith("/images/"):
            disk_path = IMAGES_DIR / src[len("/images/"):]
            if not disk_path.exists():
                issues.append({
                    "level": "info",
                    "msg": f"[{img_id}] image file not on disk: {src}",
                })

    # ── 5. Hero image quality ─────────────────────────────────────────────────
    if data.get("heroImageCaption") in ("TBD", "", None):
        issues.append({"level": "warn", "msg": "heroImageCaption is TBD"})

    if data.get("heroImageAltStatus", "pending") == "pending":
        issues.append({"level": "warn", "msg": "heroImageAltStatus is 'pending'"})

    return issues


LEVEL_ICON = {"error": "✗", "warn": "⚠", "info": "·"}
LEVEL_ORDER = {"error": 0, "warn": 1, "info": 2}


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit MDX image registry quality")
    parser.add_argument("--slug", help="Single chair slug (default: all)")
    parser.add_argument(
        "--level",
        choices=["error", "warn", "info"],
        default="warn",
        help="Minimum severity to show (default: warn)",
    )
    args = parser.parse_args()

    files = find_mdx_files(args.slug)
    min_level = LEVEL_ORDER[args.level]

    print(f"\n=== audit_image_registry.py ===")
    print(f"Processing {len(files)} file(s)  [showing: {args.level}+]\n")

    total_errors = total_warns = 0
    for path in files:
        issues = [i for i in audit_file(path) if LEVEL_ORDER[i["level"]] <= min_level]
        if not issues:
            print(f"  ✓ {path.name}")
            continue

        print(f"  {path.name}")
        for issue in sorted(issues, key=lambda x: LEVEL_ORDER[x["level"]]):
            icon = LEVEL_ICON[issue["level"]]
            print(f"    {icon} {issue['msg']}")
            if issue["level"] == "error":
                total_errors += 1
            elif issue["level"] == "warn":
                total_warns += 1

    print(f"\nSummary: {total_errors} error(s), {total_warns} warning(s)")
    return 1 if total_errors else 0


if __name__ == "__main__":
    sys.exit(main())
