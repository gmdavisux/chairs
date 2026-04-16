#!/usr/bin/env python3
"""
sync_images.py - Sync existing image files into MDX frontmatter and body

Scans /public/images for chair images, adds missing ones to frontmatter,
and optionally inserts them into the post body.

Usage:
    # Sync all missing images for a specific chair
    python sync_images.py egg-chair
    
    # Sync all chairs
    python sync_images.py --all
    
    # Dry run to see what would change
    python sync_images.py egg-chair --dry-run
    
    # Also insert images into body
    python sync_images.py egg-chair --insert-body
"""

import argparse
import logging
import re
import sys
from pathlib import Path
from typing import Optional

import yaml

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

ROOT = Path(__file__).parent
CONTENT_DIR = ROOT / "src" / "content" / "blog"
IMAGES_DIR = ROOT / "public" / "images"

# Standard image slots (order matters for insertion)
STANDARD_SLOTS = [
    "hero",
    "sketch",
    "context",
    "silhouette",
    "detail-silhouette",
    "detail-material",
    "detail-structure",
    "designer",
]

# Slot descriptions for generating metadata
SLOT_DESCRIPTIONS = {
    "hero": "three-quarter view showing overall form and design",
    "sketch": "industrial design marker rendering highlighting sculptural form",
    "context": "in-situ setting showing the chair in its intended environment",
    "silhouette": "profile view capturing distinctive proportions and geometry",
    "detail-silhouette": "detailed profile view capturing distinctive proportions and geometry",
    "detail-material": "close-up detail showing surface texture and material quality",
    "detail-structure": "structural detail of frame construction and joinery",
    "designer": "portrait of the designer",
}


def extract_slot_from_prefixed_name(name: str, slug: str) -> str:
    """Extract full slot token from a slug-prefixed id/path stem."""
    prefix = f"{slug}-"
    if name.startswith(prefix):
        return name[len(prefix):]
    return name.rsplit("-", 1)[-1] if "-" in name else name


def find_mdx_file(slug: str) -> Optional[Path]:
    """Find the MDX or MD file for a slug."""
    for ext in [".mdx", ".md"]:
        path = CONTENT_DIR / f"{slug}{ext}"
        if path.exists():
            return path
    return None


def find_chair_images(slug: str) -> dict[str, Path]:
    """Find all image files for a chair slug."""
    images = {}
    
    for slot in STANDARD_SLOTS:
        # Check for both .jpg and .png
        for ext in [".jpg", ".png", ".jpeg"]:
            path = IMAGES_DIR / f"{slug}-{slot}{ext}"
            if path.exists():
                images[slot] = path
                break
    
    return images


def parse_mdx_file(mdx_path: Path) -> tuple[dict, str]:
    """
    Parse MDX file into frontmatter and body.
    
    Returns:
        (frontmatter_dict, body)
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
    
    return frontmatter, body


def get_existing_slots(frontmatter: dict, slug: str) -> set[str]:
    """Get slots already defined in frontmatter images array."""
    slots = set()
    
    # Check heroImage
    hero_path = frontmatter.get("heroImage", "")
    if hero_path and "/images/" in hero_path:
        filename = hero_path.split("/")[-1]
        name = filename.rsplit(".", 1)[0]
        if "-" in name:
            slot = extract_slot_from_prefixed_name(name, slug)
            slots.add(slot)
    
    # Check images array
    images = frontmatter.get("images", [])
    for img in images:
        img_id = img.get("id", "")
        if "-" in img_id:
            slot = extract_slot_from_prefixed_name(img_id, slug)
            slots.add(slot)
    
    return slots


def create_image_metadata(slug: str, slot: str, image_path: Path, title: str) -> dict:
    """Generate metadata dict for an image slot."""
    ext = image_path.suffix
    description = SLOT_DESCRIPTIONS.get(slot, f"{slot} view of the chair")
    
    return {
        "id": f"{slug}-{slot}",
        "src": f"/images/{slug}-{slot}{ext}",
        "alt": f"{title}, {description}",
        "altStatus": "actual",
        "caption": f"{description.capitalize()}",
        "source": "Original studio composition created for this site, based on public-domain reference photographs and historical documentation.",
        "license": "Original work for educational and archival purposes",
        "origin": "studio_composition",
    }


def find_referenced_slots_in_body(body: str, slug: str) -> set[str]:
    """Find image slots already referenced in the body."""
    slots = set()
    
    # Find src="/images/slug-slot.ext" references and extract full slot token.
    image_pattern = rf'/images/{re.escape(slug)}-([a-z0-9-]+)\.(?:jpg|png|jpeg|webp)'
    for match in re.finditer(image_pattern, body):
        slot = match.group(1)
        slots.add(slot)
    
    return slots


def generate_image_component(image_data: dict) -> str:
    """Generate an ImageWithMeta component from image metadata."""
    src = image_data.get("src", "")
    alt = image_data.get("alt", "")
    caption = image_data.get("caption", "")
    
    return f'''<ImageWithMeta
  src="{src}"
  alt="{alt}"
  caption="{caption}"
/>'''


def sync_chair_images(
    slug: str,
    dry_run: bool = False,
    insert_body: bool = False
) -> tuple[bool, list[str]]:
    """
    Sync images for a chair: add missing images to frontmatter and optionally body.
    
    Returns:
        (success, changes) tuple
    """
    changes = []
    
    # Find MDX file
    mdx_path = find_mdx_file(slug)
    if not mdx_path:
        return False, [f"No MDX file found for: {slug}"]
    
    # Find available images
    available_images = find_chair_images(slug)
    if not available_images:
        return True, [f"No images found in /public/images for: {slug}"]
    
    log.info(f"Found {len(available_images)} images for {slug}: {', '.join(available_images.keys())}")
    
    # Parse MDX file
    try:
        frontmatter, body = parse_mdx_file(mdx_path)
    except Exception as e:
        return False, [f"Error parsing MDX: {e}"]
    
    title = frontmatter.get("title", slug.replace("-", " ").title())
    
    # Get existing slots
    existing_slots = get_existing_slots(frontmatter, slug)
    log.info(f"Existing slots in frontmatter: {', '.join(existing_slots) if existing_slots else 'none'}")
    
    # Find missing slots
    missing_slots = set(available_images.keys()) - existing_slots
    
    if not missing_slots:
        return True, ["All available images already in frontmatter"]
    
    log.info(f"Missing slots to add: {', '.join(missing_slots)}")
    
    # Add missing images to frontmatter
    if "images" not in frontmatter:
        frontmatter["images"] = []
    
    for slot in missing_slots:
        if slot == "designer":
            # Designer image goes in designerImage field, not images array
            if "designerImage" not in frontmatter or not frontmatter["designerImage"]:
                image_path = available_images[slot]
                ext = image_path.suffix
                frontmatter["designerImage"] = f"/images/{slug}-{slot}{ext}"
                changes.append(f"Added designerImage: {slug}-{slot}{ext}")
        elif slot == "hero":
            # Hero image goes in heroImage field
            if "heroImage" not in frontmatter or not frontmatter["heroImage"]:
                image_path = available_images[slot]
                ext = image_path.suffix
                frontmatter["heroImage"] = f"/images/{slug}-{slot}{ext}"
                changes.append(f"Added heroImage: {slug}-{slot}{ext}")
        else:
            # Other images go in the images array
            image_path = available_images[slot]
            metadata = create_image_metadata(slug, slot, image_path, title)
            frontmatter["images"].append(metadata)
            changes.append(f"Added {slot} to images array")
    
    if dry_run:
        return True, changes
    
    # Optionally insert into body
    body_insertions = []
    if insert_body:
        referenced_slots = find_referenced_slots_in_body(body, slug)
        for slot in missing_slots:
            if slot not in referenced_slots and slot not in ["hero", "designer"]:
                # Find the metadata we just created
                for img in frontmatter["images"]:
                    if img.get("id", "").endswith(f"-{slot}"):
                        component = generate_image_component(img)
                        body_insertions.append(component)
                        changes.append(f"Inserted {slot} component in body")
                        break
        
        if body_insertions:
            # Insert before References section or at end
            references_pattern = r"^## References"
            references_match = re.search(references_pattern, body, re.MULTILINE)
            
            insertion_text = "\n\n" + "\n\n".join(body_insertions) + "\n"
            
            if references_match:
                insert_pos = references_match.start()
                body = body[:insert_pos] + insertion_text + "\n" + body[insert_pos:]
            else:
                body = body + insertion_text
            
            # Ensure import exists
            if "import ImageWithMeta" not in body:
                import_line = "\nimport ImageWithMeta from '../../components/ImageWithMeta.astro';\n"
                body = import_line + body
    
    # Write back to file
    frontmatter_text = yaml.safe_dump(frontmatter, sort_keys=False, allow_unicode=True).strip()
    new_content = f"---\n{frontmatter_text}\n---{body}"
    
    mdx_path.write_text(new_content, encoding="utf-8")
    log.info(f"Updated {mdx_path}")
    
    return True, changes


def main():
    parser = argparse.ArgumentParser(
        description="Sync existing image files into MDX frontmatter and body"
    )
    parser.add_argument(
        "slug",
        nargs="?",
        help="Chair slug (e.g., egg-chair, tulip-chair)"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Process all chairs"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without making changes"
    )
    parser.add_argument(
        "--insert-body",
        action="store_true",
        help="Also insert ImageWithMeta components into post body"
    )
    
    args = parser.parse_args()
    
    if not args.slug and not args.all:
        parser.print_help()
        sys.exit(1)
    
    if args.all:
        # Process all MDX files
        mdx_files = list(CONTENT_DIR.glob("*.mdx")) + list(CONTENT_DIR.glob("*.md"))
        for mdx_file in mdx_files:
            slug = mdx_file.stem
            log.info(f"\n{'='*60}")
            log.info(f"Processing: {slug}")
            log.info(f"{'='*60}")
            success, changes = sync_chair_images(slug, args.dry_run, args.insert_body)
            
            if success:
                for change in changes:
                    log.info(f"  {change}")
            else:
                log.error(f"  Failed: {', '.join(changes)}")
    else:
        success, changes = sync_chair_images(args.slug, args.dry_run, args.insert_body)
        
        if success:
            for change in changes:
                log.info(change)
        else:
            log.error(f"Failed: {', '.join(changes)}")
            sys.exit(1)


if __name__ == "__main__":
    main()
