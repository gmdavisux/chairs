#!/usr/bin/env python3
"""
insert_image_slots.py - Automatically insert ImageWithMeta components for all image slots

This script finds image slots defined in the frontmatter images array and ensures
they are referenced in the blog post body. Any slots not already present (except hero)
will be automatically inserted as ImageWithMeta components.

Usage:
    python insert_image_slots.py tulip-chair
    python insert_image_slots.py tulip-chair --dry-run
"""

import argparse
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).parent
CONTENT_DIR = ROOT / "src" / "content" / "blog"


def find_mdx_file(slug: str) -> Path:
    """Find the MDX or MD file for a slug."""
    for ext in [".mdx", ".md"]:
        path = CONTENT_DIR / f"{slug}{ext}"
        if path.exists():
            return path
    raise FileNotFoundError(f"No MDX/MD file found for: {slug}")


def extract_slot_from_id(image_id: str) -> str:
    """
    Extract the slot name from an image id.
    Examples: tulip-chair-sketch -> sketch, tulip-chair-hero -> hero
    """
    parts = image_id.split("-")
    if len(parts) >= 2:
        return parts[-1]  # Last part is the slot name
    return image_id


def parse_mdx_file(mdx_path: Path) -> tuple[dict, str, str]:
    """
    Parse MDX file into frontmatter, body, and import section.
    
    Returns:
        (frontmatter_dict, body, import_statement)
    """
    content = mdx_path.read_text(encoding="utf-8")
    
    if not content.startswith("---"):
        raise ValueError("MDX file missing frontmatter")
    
    parts = content.split("---", 2)
    if len(parts) < 3:
        raise ValueError("MDX file has invalid frontmatter structure")
    
    frontmatter_text = parts[1]
    body = parts[2]
    
    # Parse YAML frontmatter
    try:
        frontmatter = yaml.safe_load(frontmatter_text)
    except yaml.YAMLError as e:
        raise ValueError(f"Failed to parse YAML: {e}")
    
    # Extract import statement if it exists
    import_pattern = r"^import\s+ImageWithMeta\s+from\s+['\"][^'\"]+['\"]\s*;\s*$"
    import_match = re.search(import_pattern, body, re.MULTILINE)
    import_statement = import_match.group(0) if import_match else ""
    
    return frontmatter, body, import_statement


def find_referenced_slots(body: str) -> set[str]:
    """
    Find all image slots already referenced in the body via ImageWithMeta components.
    Detects both registry-first (id="...") and legacy inline (src="/images/...") forms.
    """
    slots = set()

    # Registry-first: id="slug-slot" form — extract trailing slot name
    for match in re.finditer(r'\bid="([^"]+)"', body):
        img_id = match.group(1)
        if "-" in img_id:
            slot = img_id.split("-")[-1]
            slots.add(slot)

    # Legacy inline: src="/images/slug-slot.ext" form
    for match in re.finditer(r'src="([^"]+)"', body):
        src = match.group(1)
        if "/images/" in src:
            filename = src.split("/")[-1]
            name = filename.rsplit(".", 1)[0]
            if "-" in name:
                slot = name.split("-")[-1]
                slots.add(slot)

    return slots


def generate_image_component(image_data: dict) -> str:
    """
    Generate a registry-first ImageWithMeta component from image frontmatter data.

    Uses the image id to reference the frontmatter registry via the entryImages
    variable, which is available in MDX body scope from [...slug].astro.
    """
    img_id = image_data.get("id", "")
    return f'<ImageWithMeta id="{img_id}" images={{props.entryImages}} />'


def insert_missing_slots(
    mdx_path: Path,
    frontmatter: dict,
    body: str,
    import_statement: str,
    dry_run: bool = False
) -> tuple[bool, list[str]]:
    """
    Insert ImageWithMeta components for any slots not already in the body.
    
    Returns:
        (success, changes) tuple
    """
    changes = []
    
    # Get all images from frontmatter
    images = frontmatter.get("images", [])
    if not images:
        return True, ["No images defined in frontmatter"]
    
    # Find which slots are already referenced
    referenced_slots = find_referenced_slots(body)
    
    # Find which slots need to be added (exclude hero and sketch if sketch is the hero)
    # Hero is shown automatically at the top, and if sketch is the hero image, don't duplicate it
    hero_image_path = frontmatter.get("heroImage", "")
    hero_slot = None
    if "/images/" in hero_image_path:
        filename = hero_image_path.split("/")[-1]
        name = filename.rsplit(".", 1)[0]
        if "-" in name:
            hero_slot = name.split("-")[-1]
    
    missing_slots = []
    for img in images:
        slot = extract_slot_from_id(img.get("id", ""))
        # Skip if already referenced, or if it's the hero image (to avoid duplication)
        if slot not in referenced_slots and slot != "hero" and slot != hero_slot:
            missing_slots.append((slot, img))
    
    if not missing_slots:
        return True, ["All image slots already referenced in the body"]
    
    # Ensure import statement exists
    if not import_statement:
        import_statement = "import ImageWithMeta from '../../components/ImageWithMeta.astro';"
        changes.append("Added ImageWithMeta import statement")
    
    # Generate components for missing slots
    components_to_insert = []
    for slot, img in missing_slots:
        component = generate_image_component(img)
        components_to_insert.append(component)
        changes.append(f"Added ImageWithMeta for slot: {slot}")
    
    if dry_run:
        return True, changes
    
    # Insert components at the end of the body (before References section if it exists)
    references_pattern = r"^## References"
    references_match = re.search(references_pattern, body, re.MULTILINE)
    
    # Build the insertion text
    insertion_text = "\n\n" + "\n\n".join(components_to_insert) + "\n"
    
    if references_match:
        # Insert before References section
        insert_pos = references_match.start()
        new_body = body[:insert_pos] + insertion_text + "\n" + body[insert_pos:]
    else:
        # Insert at the end
        new_body = body + insertion_text
    
    # Ensure import statement is present
    if import_statement not in new_body:
        # Insert after frontmatter separator
        new_body = "\n" + import_statement + "\n" + new_body
    
    # Reconstruct the file
    frontmatter_text = yaml.safe_dump(frontmatter, sort_keys=False, allow_unicode=True).strip()
    new_content = f"---\n{frontmatter_text}\n---{new_body}"
    
    # Write back
    mdx_path.write_text(new_content, encoding="utf-8")
    
    return True, changes


def main():
    parser = argparse.ArgumentParser(
        description="Automatically insert ImageWithMeta components for all image slots"
    )
    parser.add_argument(
        "slug",
        help="Furniture piece slug (e.g., tulip-chair)",
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
    
    # Parse MDX file
    try:
        frontmatter, body, import_statement = parse_mdx_file(mdx_path)
    except Exception as e:
        print(f"❌ Failed to parse MDX file: {e}", file=sys.stderr)
        return 1
    
    # Insert missing slots
    mode = "DRY RUN" if args.dry_run else "UPDATE"
    print(f"🔧 {mode}: Inserting missing image slots...")
    print()
    
    success, changes = insert_missing_slots(
        mdx_path, frontmatter, body, import_statement, args.dry_run
    )
    
    if not success:
        print("❌ Failed to insert image slots:", file=sys.stderr)
        for msg in changes:
            print(f"   {msg}", file=sys.stderr)
        return 1
    
    # Print changes
    for change in changes:
        prefix = "  [would add]" if args.dry_run else "  ✓"
        print(f"{prefix} {change}")
    
    print()
    if args.dry_run:
        print("🔍 Dry run complete. Use without --dry-run to apply changes.")
    else:
        print(f"✅ MDX file updated successfully: {mdx_path}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
