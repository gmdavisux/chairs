#!/usr/bin/env python3
"""
update_mdx_images.py - Update MDX file image references after manual generation

After manually generating images with Google Gemini and saving them as PNGs,
use this script to update the MDX file to reference the new images.

Usage:
    python update_mdx_images.py wassily-chair
    python update_mdx_images.py wassily-chair --extension png
    python update_mdx_images.py wassily-chair --dry-run
"""

import argparse
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).parent
CONTENT_DIR = ROOT / "src" / "content" / "blog"
IMAGES_DIR = ROOT / "public" / "images"

IMAGE_SLOTS = ["hero", "silhouette", "context", "designer"]


def find_mdx_file(slug: str) -> Path:
    """Find the MDX or MD file for a slug."""
    for ext in [".mdx", ".md"]:
        path = CONTENT_DIR / f"{slug}{ext}"
        if path.exists():
            return path
    raise FileNotFoundError(f"No MDX/MD file found for: {slug}")


def check_image_files(slug: str, extension: str) -> dict[str, bool]:
    """Check which image files exist with the given extension."""
    status = {}
    for slot in IMAGE_SLOTS:
        path = IMAGES_DIR / f"{slug}-{slot}.{extension}"
        status[slot] = path.exists()
    return status


def update_mdx_references(mdx_path: Path, slug: str, extension: str, dry_run: bool = False) -> tuple[bool, list[str]]:
    """
    Update MDX file to use the specified image extension.
    
    Returns:
        (success, changes) tuple where changes is a list of change descriptions
    """
    content = mdx_path.read_text(encoding="utf-8")
    changes = []
    
    # Split frontmatter and body
    if not content.startswith("---"):
        return False, ["MDX file missing frontmatter"]
    
    parts = content.split("---", 2)
    if len(parts) < 3:
        return False, ["MDX file has invalid frontmatter structure"]
    
    frontmatter_text = parts[1]
    body = parts[2]
    
    # Parse YAML frontmatter
    try:
        data = yaml.safe_load(frontmatter_text)
    except yaml.YAMLError as e:
        return False, [f"Failed to parse YAML: {e}"]
    
    # Update heroImage
    if data.get("heroImage"):
        old_hero = data["heroImage"]
        new_hero = f"/images/{slug}-hero.{extension}"
        if old_hero != new_hero:
            data["heroImage"] = new_hero
            changes.append(f"Hero image: {old_hero} → {new_hero}")
    
    # Update images array
    if "images" in data and isinstance(data["images"], list):
        for img in data["images"]:
            if "src" in img:
                old_src = img["src"]
                # Replace extension in src
                for slot in IMAGE_SLOTS:
                    if slug in old_src and slot in old_src:
                        new_src = f"/images/{slug}-{slot}.{extension}"
                        if old_src != new_src:
                            img["src"] = new_src
                            changes.append(f"Image {slot}: {old_src} → {new_src}")
                        break
    
    if not changes:
        return True, ["No changes needed (already using correct extensions)"]
    
    if dry_run:
        return True, changes
    
    # Write back
    serialized = yaml.safe_dump(data, sort_keys=False, allow_unicode=True).strip()
    mdx_path.write_text(f"---\n{serialized}\n---{body}", encoding="utf-8")
    
    return True, changes


def main():
    parser = argparse.ArgumentParser(
        description="Update MDX file image references after manual generation"
    )
    parser.add_argument(
        "slug",
        help="Furniture piece slug (e.g., wassily-chair)",
    )
    parser.add_argument(
        "--extension",
        default="png",
        choices=["png", "jpg", "jpeg", "webp"],
        help="Image file extension to use (default: png)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without actually modifying files",
    )
    
    args = parser.parse_args()
    
    # Find MDX file
    try:
        mdx_path = find_mdx_file(args.slug)
        print(f"📄 Found MDX file: {mdx_path.name}")
    except FileNotFoundError as e:
        print(f"❌ {e}", file=sys.stderr)
        return 1
    
    # Check which images exist
    image_status = check_image_files(args.slug, args.extension)
    existing = [slot for slot, exists in image_status.items() if exists]
    missing = [slot for slot, exists in image_status.items() if not exists]
    
    print(f"\n📊 Image files with .{args.extension} extension:")
    print(f"   ✓ Found: {', '.join(existing) if existing else 'none'}")
    if missing:
        print(f"   ⚠️  Missing: {', '.join(missing)}")
    print()
    
    if not existing:
        print(f"❌ No .{args.extension} images found for {args.slug}", file=sys.stderr)
        print(f"   Expected files in: {IMAGES_DIR}", file=sys.stderr)
        return 1
    
    # Update MDX file
    mode = "DRY RUN" if args.dry_run else "UPDATE"
    print(f"🔧 {mode}: Updating MDX references...")
    print()
    
    success, changes = update_mdx_references(mdx_path, args.slug, args.extension, args.dry_run)
    
    if not success:
        print("❌ Failed to update MDX file:", file=sys.stderr)
        for msg in changes:
            print(f"   {msg}", file=sys.stderr)
        return 1
    
    # Print changes
    for change in changes:
        prefix = "  [would change]" if args.dry_run else "  ✓"
        print(f"{prefix} {change}")
    
    print()
    if args.dry_run:
        print("🔍 Dry run complete. Use without --dry-run to apply changes.")
    else:
        print(f"✅ MDX file updated successfully: {mdx_path}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
