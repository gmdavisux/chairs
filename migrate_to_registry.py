#!/usr/bin/env python3
"""
migrate_to_registry.py - Migrate MDX files to registry-first ImageWithMeta usage

Converts inline ImageWithMeta components from:

    <ImageWithMeta
      src="/images/swan-chair-sketch.jpg"
      alt="..."
      caption="..."
    />

to registry-first form:

    <ImageWithMeta id="swan-chair-sketch" images={entryImages} />

Any metadata present inline but missing or stale in the frontmatter images[]
registry (e.g. real captions replacing "TBD", actual alt text) is merged INTO
the registry before the inline call is removed.

Usage:
    python migrate_to_registry.py                    # all MDX files
    python migrate_to_registry.py --slug swan-chair  # single file
    python migrate_to_registry.py --dry-run          # preview only
"""

import argparse
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).parent
CONTENT_DIR = ROOT / "src" / "content" / "blog"


def find_mdx_files(slug: str | None) -> list[Path]:
    if slug:
        for ext in [".mdx", ".md"]:
            p = CONTENT_DIR / f"{slug}{ext}"
            if p.exists():
                return [p]
        print(f"ERROR: No MDX file found for slug: {slug}")
        sys.exit(1)
    return sorted(CONTENT_DIR.glob("*.{mdx,md}")) or sorted(
        list(CONTENT_DIR.glob("*.mdx")) + list(CONTENT_DIR.glob("*.md"))
    )


def extract_prop(tag_body: str, prop: str) -> str | None:
    """Extract a quoted prop value from JSX tag body."""
    m = re.search(rf'\b{re.escape(prop)}="([^"]*)"', tag_body)
    return m.group(1) if m else None


def migrate_file(mdx_path: Path, dry_run: bool) -> tuple[bool, list[str]]:
    content = mdx_path.read_text(encoding="utf-8")
    changes: list[str] = []

    if not content.startswith("---"):
        return False, ["Missing frontmatter delimiter"]

    parts = content.split("---", 2)
    if len(parts) < 3:
        return False, ["Invalid frontmatter structure"]

    frontmatter_text = parts[1]
    body = parts[2]

    try:
        data = yaml.safe_load(frontmatter_text)
    except yaml.YAMLError as e:
        return False, [f"YAML parse error: {e}"]

    images: list[dict] = data.get("images") or []
    if not images:
        return True, ["No images array in frontmatter — nothing to migrate"]

    # Build a src→registry-entry lookup
    src_to_entry: dict[str, dict] = {img["src"]: img for img in images if img.get("src")}

    registry_changed = False

    def replace_tag(match: re.Match) -> str:
        nonlocal registry_changed
        tag_body = match.group(1)

        # Already uses id= — skip
        if re.search(r'\bid="', tag_body):
            return match.group(0)

        src = extract_prop(tag_body, "src")
        if not src:
            return match.group(0)

        entry = src_to_entry.get(src)
        if entry is None:
            changes.append(f"  WARN: no registry entry for src={src!r} — left unchanged")
            return match.group(0)

        img_id = entry.get("id", "")

        # Merge better metadata from inline into registry entry
        inline = {
            "alt":       extract_prop(tag_body, "alt"),
            "altStatus": extract_prop(tag_body, "altStatus"),
            "caption":   extract_prop(tag_body, "caption"),
            "source":    extract_prop(tag_body, "source"),
            "license":   extract_prop(tag_body, "license"),
            "origin":    extract_prop(tag_body, "origin"),
        }

        # alt: prefer non-"Proposed..." value
        if (
            inline["alt"]
            and not inline["alt"].startswith("Proposed")
            and (entry.get("alt") or "").startswith("Proposed")
        ):
            entry["alt"] = inline["alt"]
            entry["altStatus"] = "actual"
            changes.append(f"  [{img_id}] alt upgraded to actual text")
            registry_changed = True

        # altStatus: upgrade proposed→actual when inline says actual
        if inline["altStatus"] == "actual" and entry.get("altStatus") != "actual":
            entry["altStatus"] = "actual"
            changes.append(f"  [{img_id}] altStatus set to 'actual'")
            registry_changed = True

        # caption: replace TBD / empty with real value
        if inline["caption"] and inline["caption"] not in ("TBD", "") and entry.get("caption") in (
            "TBD", "", None
        ):
            entry["caption"] = inline["caption"]
            changes.append(f"  [{img_id}] caption updated")
            registry_changed = True

        # source: replace TBD / empty with real value
        if inline["source"] and inline["source"] not in ("TBD", "") and entry.get("source") in (
            "TBD", "", None
        ):
            entry["source"] = inline["source"]
            changes.append(f"  [{img_id}] source updated")
            registry_changed = True

        # license: replace unknown / empty with real value
        if inline["license"] and inline["license"] not in ("unknown", "") and entry.get("license") in (
            "unknown", "", None
        ):
            entry["license"] = inline["license"]
            changes.append(f"  [{img_id}] license updated")
            registry_changed = True

        # origin: replace placeholder / empty with real value
        if inline["origin"] and inline["origin"] not in ("placeholder", "") and entry.get("origin") in (
            "placeholder", "", None
        ):
            entry["origin"] = inline["origin"]
            changes.append(f"  [{img_id}] origin updated")
            registry_changed = True

        new_tag = f'<ImageWithMeta id="{img_id}" images={{props.entryImages}} />'
        changes.append(f"  [{img_id}] inline → registry-first")
        return new_tag

    new_body = re.sub(r"<ImageWithMeta\s+([\s\S]*?)/>", replace_tag, body)

    if not changes:
        return True, ["No inline ImageWithMeta tags to migrate"]

    if not dry_run:
        new_fm = yaml.safe_dump(
            data,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
            width=4096,
        )
        new_content = f"---\n{new_fm}---{new_body}"
        mdx_path.write_text(new_content, encoding="utf-8")

    return True, changes


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate MDX files to registry-first ImageWithMeta")
    parser.add_argument("--slug", help="Single chair slug to process (default: all)")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    args = parser.parse_args()

    files = find_mdx_files(args.slug)
    mode = "DRY RUN" if args.dry_run else "APPLYING"
    print(f"\n=== migrate_to_registry.py [{mode}] ===")
    print(f"Processing {len(files)} file(s)\n")

    all_ok = True
    for path in files:
        ok, changes = migrate_file(path, dry_run=args.dry_run)
        status = "✓" if ok else "✗"
        prefix = "[DRY RUN] " if args.dry_run else ""
        print(f"{status} {prefix}{path.name}")
        for c in changes:
            print(f"  {c}")
        if not ok:
            all_ok = False

    print()
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
