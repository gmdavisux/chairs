#!/usr/bin/env python3
"""
use_reference_images.py — Replace placeholder images with downloaded references.

When furniture_agent.py completes but AI generation failed/wasn't configured,
this script swaps the placeholder images with the best downloaded reference
images from the reference-metadata.json file.

Usage:
    python use_reference_images.py <slug>
    python use_reference_images.py <slug> --interactive
    python use_reference_images.py tulip-chair --dry-run

Options:
    --interactive    Review each image before copying
    --dry-run        Show what would be done without making changes
"""

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).parent
IMAGES_DIR = ROOT / "public" / "images"
REFERENCE_IMAGES_DIR = IMAGES_DIR / "reference"
CONTENT_DIR = ROOT / "src" / "content" / "blog"

MODERN_SLOT_ORDER = ["hero", "detail-material", "detail-structure", "silhouette"]
LEGACY_SLOT_ORDER = ["hero", "sketch", "context", "designer"]


def resolve_slot_order(slug: str) -> list[str]:
    """Pick slot order based on existing image filenames for the slug."""
    modern_markers = [
        IMAGES_DIR / f"{slug}-detail-material.jpg",
        IMAGES_DIR / f"{slug}-detail-structure.jpg",
        IMAGES_DIR / f"{slug}-silhouette.jpg",
    ]
    if any(path.exists() for path in modern_markers):
        return MODERN_SLOT_ORDER
    return LEGACY_SLOT_ORDER


def load_reference_metadata(slug: str) -> dict:
    """Load the reference-metadata.json file for a given slug."""
    ref_dir = REFERENCE_IMAGES_DIR / f"{slug}-reference"
    metadata_path = ref_dir / "reference-metadata.json"
    
    if not metadata_path.exists():
        print(f"❌ No reference metadata found at: {metadata_path}")
        sys.exit(1)
    
    try:
        return json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"❌ Failed to read reference metadata: {exc}")
        sys.exit(1)


def get_available_references(metadata: dict) -> list[dict]:
    """Extract items that have successfully downloaded local files."""
    items = metadata.get("items", [])
    available = []
    
    for item in items:
        local_path = item.get("localPath")
        if not local_path:
            continue
        
        full_path = ROOT / local_path
        if full_path.exists():
            available.append({
                "id": item.get("id", "unknown"),
                "path": full_path,
                "source": item.get("sourcePage", ""),
                "license": item.get("license", "unknown"),
                "origin": item.get("origin", "licensed"),
            })
    
    return available


def _slot_alt_and_caption_reference(slot: str, title: str, designer: str) -> tuple[str, str]:
    """Return (alt, caption) text for a reference image slot."""
    slot_meta = {
        "hero": (
            f"{title} — archival reference photograph",
            f"Reference photograph of the {title} by {designer}.",
        ),
        "silhouette": (
            f"{title} profile silhouette — archival reference",
            f"Reference silhouette of the {title} by {designer}.",
        ),
        "context": (
            f"{title} in context — archival reference photograph",
            f"Reference photograph of the {title} by {designer} in situ.",
        ),
        "designer": (
            f"Archival photograph of {designer}, designer of the {title}",
            f"Archival portrait of {designer}.",
        ),
        "sketch": (
            f"Design drawing of the {title}",
            f"Archival design drawing of the {title} by {designer}.",
        ),
        "detail-material": (
            f"Material detail of the {title} — archival reference photograph",
            f"Archival material detail of the {title} by {designer}.",
        ),
        "detail-structure": (
            f"Structural detail of the {title} — archival reference photograph",
            f"Archival structural detail of the {title} by {designer}.",
        ),
        "silhouette": (
            f"Silhouette of the {title} — archival reference photograph",
            f"Archival silhouette view of the {title} by {designer}.",
        ),
    }
    return slot_meta.get(slot, (f"{title} — {slot} reference", f"Reference {slot} image for the {title}."))


def update_frontmatter_metadata(slug: str, slot_updates: dict[str, dict], dry_run: bool = False) -> bool:
    """Update the frontmatter with reference image metadata."""
    # Support both .md and .mdx
    article_path = CONTENT_DIR / f"{slug}.mdx"
    if not article_path.exists():
        article_path = CONTENT_DIR / f"{slug}.md"
    if not article_path.exists():
        print(f"⚠️  Article not found at: {CONTENT_DIR / slug}(.mdx/.md)")
        return False

    raw = article_path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", raw, flags=re.DOTALL)
    if not match:
        print(f"⚠️  Could not parse frontmatter in {article_path}")
        return False

    try:
        import yaml
    except ImportError:
        print(f"⚠️  PyYAML not installed; frontmatter update skipped")
        return False

    frontmatter_raw = match.group(1)
    body = match.group(2)
    data = yaml.safe_load(frontmatter_raw) or {}

    title = data.get("title", "")
    designer = data.get("designer", "")

    # Update hero metadata
    hero_update = slot_updates.get("hero")
    if hero_update:
        alt, caption = _slot_alt_and_caption_reference("hero", title, designer)
        data["heroImageAlt"] = alt
        data["heroImageAltStatus"] = "actual"
        data["heroImageCaption"] = caption
        data["heroImageSource"] = hero_update.get("source", "archival reference")
        data["heroImageLicense"] = hero_update.get("license", "unknown")
        data["heroImageOrigin"] = hero_update.get("origin", "licensed")

    # Update images array
    images = data.get("images")
    if isinstance(images, list):
        for entry in images:
            if not isinstance(entry, dict):
                continue

            entry_id = str(entry.get("id", ""))
            entry_src = str(entry.get("src", ""))

            for slot, update in slot_updates.items():
                if slot in entry_id or slot in entry_src:
                    alt, caption = _slot_alt_and_caption_reference(slot, title, designer)
                    entry["alt"] = alt
                    entry["altStatus"] = "actual"
                    entry["caption"] = caption
                    entry["source"] = update.get("source", "archival reference")
                    entry["license"] = update.get("license", "unknown")
                    entry["origin"] = update.get("origin", "licensed")
                    break

    if dry_run:
        print(f"  [DRY RUN] Would update frontmatter metadata in {article_path}")
        return False

    serialized = yaml.safe_dump(data, sort_keys=False, allow_unicode=False).strip()
    article_path.write_text(f"---\n{serialized}\n---\n{body.lstrip()}", encoding="utf-8")
    print(f"  ✓ Updated frontmatter metadata in {article_path}")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Replace placeholder images with downloaded reference images.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("slug", help="Page slug (e.g., tulip-chair)")
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Review each image assignment before copying",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    args = parser.parse_args()
    
    slug = args.slug
    slot_order = resolve_slot_order(slug)
    metadata = load_reference_metadata(slug)
    available = get_available_references(metadata)
    
    if not available:
        print(f"❌ No downloaded reference images found for {slug}")
        print(f"   Check: {REFERENCE_IMAGES_DIR / f'{slug}-reference'}")
        sys.exit(1)
    
    print(f"\n{'='*70}")
    print(f"📸 Using Reference Images for: {slug}")
    print(f"{'='*70}")
    print(f"\nFound {len(available)} downloaded reference image(s)")
    
    # Assign references to slots (round-robin distribution)
    slot_assignments: dict[str, dict] = {}
    slot_updates: dict[str, dict] = {}
    
    for idx, slot in enumerate(slot_order):
        ref_item = available[idx % len(available)]
        slot_assignments[slot] = ref_item
        slot_updates[slot] = {
            "source": ref_item["source"],
            "license": ref_item["license"],
            "origin": ref_item["origin"],
        }
    
    # Display plan
    print(f"\n📋 PLANNED ASSIGNMENTS:")
    for slot in slot_order:
        ref_item = slot_assignments[slot]
        dest_file = IMAGES_DIR / f"{slug}-{slot}.jpg"
        source_name = ref_item["path"].name
        
        print(f"\n  {slot}:")
        print(f"    From: {source_name}")
        print(f"    To:   {dest_file.name}")
        print(f"    Source: {ref_item['source'][:60]}...")
        print(f"    License: {ref_item['license']}")
    
    if args.dry_run:
        print(f"\n[DRY RUN] No files were modified.")
        return
    
    if args.interactive:
        response = input(f"\nProceed with copying? [y/N]: ").strip().lower()
        if response not in ("y", "yes"):
            print("Cancelled.")
            return
    
    # Copy files
    print(f"\n📦 COPYING FILES:")
    copied_count = 0
    for slot in slot_order:
        ref_item = slot_assignments[slot]
        dest_file = IMAGES_DIR / f"{slug}-{slot}.jpg"
        
        try:
            shutil.copyfile(ref_item["path"], dest_file)
            print(f"  ✓ Copied {ref_item['path'].name} → {dest_file.name}")
            copied_count += 1
        except Exception as exc:
            print(f"  ✗ Failed to copy {slot}: {exc}")
    
    # Update frontmatter metadata
    print(f"\n📝 UPDATING FRONTMATTER:")
    update_frontmatter_metadata(slug, slot_updates)
    
    print(f"\n{'='*70}")
    print(f"✅ COMPLETE: Copied {copied_count} reference images for {slug}")
    print(f"{'='*70}")
    print(f"\nNext steps:")
    print(f"  • Review images at: http://localhost:4321/blog/{slug}")
    print(f"  • Update captions in: src/content/blog/{slug}.md")
    print(f"  • Verify license info is correct")
    print(f"\n")


if __name__ == "__main__":
    main()
