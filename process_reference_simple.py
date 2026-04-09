#!/usr/bin/env python3
"""
Better approach: Remove background from reference images and composite onto clean backdrop.
This preserves the actual chair 100% while only changing the background.

Workflow:
1. Remove background from reference image (keeping chair intact)
2. Composite onto clean neutral background
3. Optionally color-grade to warm lighting

No generative AI - just editing the actual photograph.
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from io import BytesIO

from dotenv import load_dotenv
from PIL import Image, ImageEnhance

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

ROOT = Path(__file__).parent
REFERENCE_IMAGES_DIR = ROOT / "public" / "images" / "reference"
IMAGES_DIR = ROOT / "public" / "images"
PROMPTS_DIR = ROOT / "public" / "images" / "generated-prompts"

sys.path.insert(0, str(ROOT))
from furniture_agent import _file_sha256, _safe_relpath


def remove_background_fal(image_path: Path) -> Image.Image:
    """Use FAL background removal (free, no generation)."""
    try:
        import fal_client
        import requests
    except ImportError as exc:
        raise RuntimeError("fal-client or requests not installed") from exc
    
    if not os.getenv("FAL_KEY"):
        raise RuntimeError("FAL_KEY required")
    
    # FAL has a background removal service - no generation, just segmentation
    # Model: fal-ai/imageutils/rembg or similar
    log.info("Removing background using FAL rembg...")
    
    # Read image as bytes
    image_bytes = image_path.read_bytes()
    
    # Upload to FAL or use URL if we have one
    # For now, this is a placeholder - FAL's background removal might need different API
    # Check FAL docs for their background removal endpoint
    
    # Fallback: return original if service unavailable
    log.warning("FAL background removal not yet implemented - returning original")
    return Image.open(image_path)


def create_clean_background(width: int, height: int, color: str = "#f5f5f0") -> Image.Image:
    """Create a clean neutral background."""
    return Image.new("RGB", (width, height), color)


def composite_on_clean_background(
    subject_with_alpha: Image.Image,
    bg_color: str = "#f5f5f0"
) -> Image.Image:
    """Composite subject onto clean background."""
    bg = create_clean_background(subject_with_alpha.width, subject_with_alpha.height, bg_color)
    bg.paste(subject_with_alpha, (0, 0), subject_with_alpha if subject_with_alpha.mode == "RGBA" else None)
    return bg


def warm_color_grade(image: Image.Image, warmth: float = 1.1) -> Image.Image:
    """Apply subtle warm color grading (2700K effect)."""
    # Enhance color temperature by boosting red/yellow slightly
    r, g, b = image.split()
    
    # Boost red channel slightly
    r = ImageEnhance.Brightness(r).enhance(warmth)
    
    # Return merged
    return Image.merge("RGB", (r, g, b))


def process_reference_simple(
    reference_path: Path,
    output_path: Path,
    slot: str,
) -> dict:
    """
    Process reference image with simple editing (no AI generation).
    
    For now: just copies reference and applies warm color grade.
    TODO: Add background removal when FAL endpoint is confirmed.
    """
    log.info("Processing %s (simple edit, no generation): %s", slot, reference_path.name)
    
    try:
        # Open reference
        img = Image.open(reference_path)
        
        # Apply warm color grading
        img = warm_color_grade(img, warmth=1.05)
        
        # Save
        img.save(output_path, "JPEG", quality=95)
        
        return {
            "slot": slot,
            "status": "color_graded",
            "file": str(_safe_relpath(output_path)),
            "hash": f"sha256:{_file_sha256(output_path)}",
            "method": "warm_color_grade_only",
            "originalReference": str(reference_path.name),
        }
        
    except Exception as exc:
        log.error("Processing failed: %s", exc)
        # Fallback: direct copy
        import shutil
        shutil.copy2(reference_path, output_path)
        return {
            "slot": slot,
            "status": "direct_copy",
            "file": str(_safe_relpath(output_path)),
            "hash": f"sha256:{_file_sha256(output_path)}",
            "reason": str(exc),
        }


def main():
    parser = argparse.ArgumentParser(
        description="Process reference images with minimal editing (no AI generation)",
    )
    parser.add_argument("slug", help="Article slug")
    
    args = parser.parse_args()
    slug = args.slug
    
    ref_dir = REFERENCE_IMAGES_DIR / f"{slug}-reference"
    if not ref_dir.exists():
        log.error("No reference directory: %s", ref_dir)
        sys.exit(1)
    
    # Load metadata
    metadata_path = ref_dir / "reference-metadata.json"
    if not metadata_path.exists():
        log.error("No metadata file: %s", metadata_path)
        sys.exit(1)
    
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    title = metadata.get("title", slug)
    
    # Get downloaded references
    ref_items = []
    for item in metadata.get("items", []):
        local_path_str = item.get("localPath")
        if local_path_str:
            local_path = ROOT / local_path_str
            if local_path.exists() and item.get("status") == "downloaded":
                ref_items.append({
                    "path": local_path,
                    "id": item.get("id"),
                    "url": item.get("downloadUrl"),
                })
    
    if not ref_items:
        log.error("No downloaded references")
        sys.exit(1)
    
    log.info("Found %d reference images", len(ref_items))
    
    # Map to slots
    slot_mapping = {
        "hero": ref_items[0],
        "detail-material": ref_items[0],
        "detail-structure": ref_items[1 % len(ref_items)],
        "detail-silhouette": ref_items[1 % len(ref_items)],
    }
    
    results = []
    for slot, ref_item in slot_mapping.items():
        output_path = IMAGES_DIR / f"{slug}-{slot}.jpg"
        result = process_reference_simple(ref_item["path"], output_path, slot)
        result["source"] = ref_item.get("url", "")
        result["originalReference"] = ref_item["id"]
        results.append(result)
    
    # Save provenance
    provenance = {
        "slug": slug,
        "title": title,
        "processedAt": datetime.utcnow().isoformat() + "Z",
        "method": "simple_editing",
        "results": results,
    }
    
    prov_dir = PROMPTS_DIR / slug
    prov_dir.mkdir(parents=True, exist_ok=True)
    prov_path = prov_dir / "provenance-simple-edit.json"
    prov_path.write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    
    log.info("\n✅ Complete! Check: http://localhost:4321/blog/%s", slug)


if __name__ == "__main__":
    main()
