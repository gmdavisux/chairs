#!/usr/bin/env python3
"""
Enhance downloaded reference images with minimal AI cleanup instead of generating from scratch.

Uses high strength (0.90-0.95) to preserve original images while only:
- Cleaning backgrounds
- Adjusting to warm lighting
- Enhancing sharpness/texture

Usage:
    python enhance_reference_images.py wassily-chair
    python enhance_reference_images.py wassily-chair --strength 0.92
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

# Load environment
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
log = logging.getLogger(__name__)

# Paths
ROOT = Path(__file__).parent
REFERENCE_IMAGES_DIR = ROOT / "public" / "images" / "reference"
IMAGES_DIR = ROOT / "public" / "images"
PROMPTS_DIR = ROOT / "public" / "images" / "generated-prompts"

# Import from furniture_agent
sys.path.insert(0, str(ROOT))
from furniture_agent import (
    _file_sha256,
    _generate_with_fal,
    _safe_relpath,
)

# Minimal enhancement prompt - preserve everything, just cleanup
ENHANCEMENT_PROMPTS = {
    "hero": (
        "Professional museum photograph of iconic modernist chair. "
        "Clean neutral background, soft warm 2700K lighting, enhanced sharpness. "
        "Preserve ALL original colors, materials, proportions, and structural details exactly as shown. "
        "No changes to design, geometry, or materials."
    ),
    "detail-material": (
        "Professional close-up photograph showing material texture and surface detail. "
        "Clean background, soft warm 2700K lighting, macro focus enhancement. "
        "Preserve exact original colors, materials, and textures without alteration."
    ),
    "detail-structure": (
        "Professional detail photograph of structural connections and joinery. "
        "Clean background, soft warm 2700K lighting, enhanced focus on construction detail. "
        "Preserve all original structural elements, materials, and geometry exactly."
    ),
    "detail-silhouette": (
        "Professional profile photograph capturing distinctive form and proportions. "
        "Clean neutral background with subtle architectural context, soft warm 2700K rim lighting. "
        "Preserve exact original silhouette, proportions, and all structural elements."
    ),
}


def enhance_image(
    reference_path: Path,
    reference_url: str,
    output_path: Path,
    slot: str,
    title: str,
    strength: float = 0.92,
) -> dict:
    """
    Enhance a reference image with minimal changes using FAL img2img.
    
    Args:
        reference_path: Path to local reference image (for fallback copy)
        reference_url: HTTP URL to the reference image (for FAL)
        output_path: Where to save enhanced image  
        slot: Image slot type (hero, detail-material, etc.)
        title: Furniture title
        strength: How much to preserve original (0.9-0.95 = minimal changes)
    """
    if not reference_path.exists():
        raise FileNotFoundError(f"Reference image not found: {reference_path}")
    
    prompt = ENHANCEMENT_PROMPTS.get(slot, ENHANCEMENT_PROMPTS["hero"])
    prompt = f"{title}. {prompt}"
    
    log.info("Enhancing %s with strength %.2f from URL: %s", slot, strength, reference_url)
    
    try:
        import requests
        response = _generate_with_fal(
            prompt=prompt,
            negative_prompt=(
                "altered design, changed materials, incorrect colors, modified proportions, "
                "fabricated details, cluttered background, harsh lighting, cool lighting, "
                "over-saturated, text, logos, watermarks"
            ),
            size="1024x1024",
            model="fal-ai/flux/dev",
            reference_url=reference_url,
            strength=strength,
        )
        
        image_url = response.get("image_url")
        if image_url:
            img_data = requests.get(image_url, timeout=60).content
            output_path.write_bytes(img_data)
            
            return {
                "slot": slot,
                "status": "enhanced",
                "file": str(_safe_relpath(output_path)),
                "hash": f"sha256:{_file_sha256(output_path)}",
                "source": reference_url,
                "strength": strength,
                "prompt": prompt,
                "originalReference": str(reference_path.name),
            }
        else:
            raise RuntimeError("No image URL in response")
            
    except Exception as exc:
        log.error("Enhancement failed for %s: %s", slot, exc)
        # Fallback: just copy the reference image
        import shutil
        shutil.copy2(reference_path, output_path)
        log.info("Copied reference directly (no enhancement): %s", output_path)
        return {
            "slot": slot,
            "status": "reference_copy",
            "file": str(_safe_relpath(output_path)),
            "hash": f"sha256:{_file_sha256(output_path)}",
            "source": reference_url,
            "reason": str(exc),
        }


def main():
    parser = argparse.ArgumentParser(
        description="Enhance reference images with minimal AI cleanup",
    )
    parser.add_argument("slug", help="Article slug (e.g. wassily-chair)")
    parser.add_argument(
        "--strength",
        type=float,
        default=0.92,
        help="Preservation strength (0.9-0.95, higher = less change)",
    )
    parser.add_argument(
        "--copy-only",
        action="store_true",
        help="Skip AI enhancement, just copy best references directly",
    )
    
    args = parser.parse_args()
    slug = args.slug
    
    ref_dir = REFERENCE_IMAGES_DIR / f"{slug}-reference"
    if not ref_dir.exists():
        log.error("No reference images found at: %s", ref_dir)
        sys.exit(1)
    
    # Load reference metadata
    metadata_path = ref_dir / "reference-metadata.json"
    metadata = {}
    if metadata_path.exists():
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            title = metadata.get("title", slug)
        except Exception as exc:
            log.warning("Could not load metadata: %s", exc)
            title = slug
    else:
        title = slug
    
    # Find downloaded reference images and their URLs
    ref_items = []
    for item in metadata.get("items", []):
        local_path_str = item.get("localPath")
        download_url = item.get("downloadUrl")
        if local_path_str and download_url:
            local_path = ROOT / local_path_str
            if local_path.exists() and item.get("status") == "downloaded":
                ref_items.append({
                    "path": local_path,
                    "url": download_url,
                    "id": item.get("id"),
                })
    
    if not ref_items:
        log.error("No downloaded reference images with URLs found in metadata")
        sys.exit(1)
    
    log.info("Found %d reference images with URLs", len(ref_items))
    
    # Map references to slots (first image for hero, rotate through others for details)
    slot_mapping = {
        "hero": ref_items[0],
        "detail-material": ref_items[0],  # Can use same reference, different crops/enhancement
        "detail-structure": ref_items[1 % len(ref_items)],
        "detail-silhouette": ref_items[1 % len(ref_items)],
    }
    
    results = []
    
    for slot, ref_item in slot_mapping.items():
        output_path = IMAGES_DIR / f"{slug}-{slot}.jpg"
        ref_path = ref_item["path"]
        ref_url = ref_item["url"]
        
        if args.copy_only:
            # Just copy the reference directly
            import shutil
            shutil.copy2(ref_path, output_path)
            log.info("Copied %s → %s", ref_path.name, output_path.name)
            results.append({
                "slot": slot,
                "status": "reference_copy",
                "file": str(_safe_relpath(output_path)),
                "hash": f"sha256:{_file_sha256(output_path)}",
                "source": ref_url,
                "originalReference": ref_item["id"],
            })
        else:
            result = enhance_image(ref_path, ref_url, output_path, slot, title, args.strength)
            results.append(result)
    
    # Save provenance
    provenance = {
        "slug": slug,
        "title": title,
        "enhancedAt": datetime.utcnow().isoformat() + "Z",
        "method": "reference_copy" if args.copy_only else "reference_enhancement",
        "strength": args.strength,
        "results": results,
    }
    
    prov_dir = PROMPTS_DIR / slug
    prov_dir.mkdir(parents=True, exist_ok=True)
    prov_path = prov_dir / "provenance-enhanced.json"
    prov_path.write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    log.info("Provenance saved: %s", prov_path)
    
    log.info("\n✅ Complete! %d images processed", len(results))
    log.info("Review at: http://localhost:4321/blog/%s", slug)


if __name__ == "__main__":
    main()
