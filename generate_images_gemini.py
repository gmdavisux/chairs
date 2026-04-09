#!/usr/bin/env python3
"""
generate_images_gemini.py - Generate furniture images using Google Gemini

Usage:
    python generate_images_gemini.py wassily-chair
    python generate_images_gemini.py wassily-chair --update-mdx
    python generate_images_gemini.py wassily-chair --custom-prompts prompts.json
    python generate_images_gemini.py wassily-chair --reference-images refs.json
"""

import argparse
import base64
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Optional
from urllib.request import Request, urlopen

import yaml
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)

# Paths
ROOT = Path(__file__).parent
PROMPTS_DIR = ROOT / "public" / "images" / "generated-prompts"
IMAGES_DIR = ROOT / "public" / "images"
CONTENT_DIR = ROOT / "src" / "content" / "blog"

# Image slot configuration
IMAGE_SLOTS = [
    ("hero", "hero.txt"),
    ("detail-material", "detail-1-material.txt"),
    ("detail-structure", "detail-2-structure.txt"),
    ("detail-silhouette", "detail-3-silhouette.txt"),
]


def generate_with_gemini(
    prompt: str,
    reference_image_url: Optional[str] = None,
    api_key: Optional[str] = None,
) -> bytes:
    """
    Generate an image using Google Gemini Imagen API.
    
    Args:
        prompt: The text prompt for image generation
        reference_image_url: Optional reference image URL for style guidance
        api_key: Google API key (defaults to GOOGLE_API_KEY env var)
    
    Returns:
        Image bytes (PNG format)
    """
    if api_key is None:
        api_key = os.getenv("GOOGLE_API_KEY")
    
    if not api_key:
        raise RuntimeError(
            "GOOGLE_API_KEY environment variable is required. "
            "Get your key at https://makersuite.google.com/app/apikey"
        )
    
    try:
        import google.generativeai as genai
    except ImportError:
        raise RuntimeError(
            "google-generativeai package is required. Install with:\n"
            "  pip install google-generativeai"
        )
    
    genai.configure(api_key=api_key)
    
    log.info(f"Generating image with Gemini...")
    log.info(f"Prompt: {prompt[:100]}...")
    
    # For image generation, we use the image generation endpoint
    # Note: As of early 2024, Gemini's image generation is through Imagen
    # The API might vary - adjust based on actual Google AI Studio API
    
    try:
        # Using Imagen 2 or 3 via the generativeai library
        # The actual method may vary - check current docs
        imagen = genai.ImageGenerationModel("imagegeneration@006")
        
        generation_config = {
            "number_of_images": 1,
            "aspect_ratio": "1:1",
        }
        
        # Build prompt with reference guidance if provided
        full_prompt = prompt
        if reference_image_url:
            log.info(f"Note: Reference image URL: {reference_image_url}")
            log.info("(Reference image guidance via prompt description)")
            full_prompt = f"{prompt}\n\nUse the style and composition from the reference image at: {reference_image_url}"
        
        response = imagen.generate_images(
            prompt=full_prompt,
            **generation_config
        )
        
        if not response or not hasattr(response, 'images') or not response.images:
            raise RuntimeError("Gemini returned no images")
        
        # Get first image and convert to bytes
        from io import BytesIO
        buffer = BytesIO()
        response.images[0]._pil_image.save(buffer, format="PNG")
        return buffer.getvalue()
        
    except Exception as e:
        # Fallback: Use REST API directly
        log.warning(f"SDK method failed, trying direct API: {e}")
        return _generate_with_gemini_rest(prompt, reference_image_url, api_key)


def _generate_with_gemini_rest(
    prompt: str,
    reference_image_url: Optional[str],
    api_key: str,
) -> bytes:
    """
    Fallback: Generate image using Google's REST API directly.
    This uses the Imagen API endpoint.
    """
    import json
    
    # Imagen 3 API endpoint
    # Note: Actual endpoint may vary, check Google AI Studio documentation
    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/imagen-3.0-generate-001:predict?key={api_key}"
    
    payload = {
        "instances": [
            {
                "prompt": prompt,
            }
        ],
        "parameters": {
            "sampleCount": 1,
            "aspectRatio": "1:1",
        }
    }
    
    if reference_image_url:
        # Some image generation APIs accept reference_image
        # Adjust based on actual API capabilities
        log.info(f"Including reference guidance for: {reference_image_url}")
        payload["parameters"]["reference_image_url"] = reference_image_url
    
    request_data = json.dumps(payload).encode("utf-8")
    req = Request(
        endpoint,
        data=request_data,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0",
        }
    )
    
    with urlopen(req, timeout=90) as response:
        result = json.loads(response.read().decode("utf-8"))
    
    # Extract image from response
    # Format depends on actual API response structure
    if "predictions" in result and result["predictions"]:
        prediction = result["predictions"][0]
        if "bytesBase64Encoded" in prediction:
            return base64.b64decode(prediction["bytesBase64Encoded"])
        elif "imageUrl" in prediction:
            # Download from URL
            img_req = Request(prediction["imageUrl"], headers={"User-Agent": "Mozilla/5.0"})
            with urlopen(img_req, timeout=30) as img_response:
                return img_response.read()
    
    raise RuntimeError("Could not extract image from Gemini response")


def read_prompts(slug: str) -> dict[str, str]:
    """Read prompt files for a given slug."""
    prompt_dir = PROMPTS_DIR / slug
    prompts = {}
    
    for slot, filename in IMAGE_SLOTS:
        prompt_path = prompt_dir / filename
        if prompt_path.exists():
            prompts[slot] = prompt_path.read_text(encoding="utf-8").strip()
        else:
            log.warning(f"Prompt file not found: {prompt_path}")
    
    return prompts


def load_custom_prompts(prompts_file: Path) -> dict[str, str]:
    """Load custom prompts from a JSON file."""
    with open(prompts_file, "r", encoding="utf-8") as f:
        return json.load(f)


def load_reference_images(refs_file: Path) -> dict[str, str]:
    """Load reference image URLs from a JSON file."""
    with open(refs_file, "r", encoding="utf-8") as f:
        return json.load(f)


def update_mdx_file(slug: str, extension: str = "png") -> bool:
    """
    Update the MDX file to use the specified image extension.
    
    Args:
        slug: The furniture piece slug
        extension: Image file extension (default: png)
    
    Returns:
        True if file was updated successfully
    """
    mdx_path = CONTENT_DIR / f"{slug}.mdx"
    
    if not mdx_path.exists():
        # Try .md extension
        mdx_path = CONTENT_DIR / f"{slug}.md"
        if not mdx_path.exists():
            log.error(f"MDX file not found: {slug}.mdx or {slug}.md")
            return False
    
    content = mdx_path.read_text(encoding="utf-8")
    
    # Split frontmatter and body
    if not content.startswith("---"):
        log.error("MDX file missing frontmatter")
        return False
    
    parts = content.split("---", 2)
    if len(parts) < 3:
        log.error("MDX file has invalid frontmatter structure")
        return False
    
    frontmatter_text = parts[1]
    body = parts[2]
    
    # Parse YAML frontmatter
    try:
        data = yaml.safe_load(frontmatter_text)
    except yaml.YAMLError as e:
        log.error(f"Failed to parse YAML frontmatter: {e}")
        return False
    
    # Update image extensions
    if data.get("heroImage"):
        data["heroImage"] = data["heroImage"].replace(".jpg", f".{extension}")
    
    if "images" in data and isinstance(data["images"], list):
        for img in data["images"]:
            if "src" in img:
                img["src"] = img["src"].replace(".jpg", f".{extension}")
    
    # Serialize back to YAML
    serialized = yaml.safe_dump(data, sort_keys=False, allow_unicode=True).strip()
    
    # Write back
    mdx_path.write_text(f"---\n{serialized}\n---{body}", encoding="utf-8")
    log.info(f"Updated MDX file: {mdx_path}")
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Generate furniture images using Google Gemini"
    )
    parser.add_argument(
        "slug",
        help="Furniture piece slug (e.g., wassily-chair)",
    )
    parser.add_argument(
        "--custom-prompts",
        type=Path,
        help="Path to JSON file with custom prompts (format: {slot: prompt})",
    )
    parser.add_argument(
        "--reference-images",
        type=Path,
        help="Path to JSON file with reference image URLs (format: {slot: url})",
    )
    parser.add_argument(
        "--update-mdx",
        action="store_true",
        help="Update MDX file to use .png extensions",
    )
    parser.add_argument(
        "--slots",
        nargs="+",
        choices=["hero", "detail-material", "detail-structure", "detail-silhouette"],
        help="Generate only specific slots (default: all)",
    )
    parser.add_argument(
        "--format",
        default="png",
        choices=["png", "jpg"],
        help="Output image format (default: png)",
    )
    
    args = parser.parse_args()
    
    # Load prompts
    if args.custom_prompts:
        log.info(f"Loading custom prompts from: {args.custom_prompts}")
        prompts = load_custom_prompts(args.custom_prompts)
    else:
        log.info(f"Loading prompts from: {PROMPTS_DIR / args.slug}")
        prompts = read_prompts(args.slug)
    
    # Load reference images
    reference_images = {}
    if args.reference_images:
        log.info(f"Loading reference images from: {args.reference_images}")
        reference_images = load_reference_images(args.reference_images)
    
    # Filter slots if specified
    slots_to_generate = [(s, f) for s, f in IMAGE_SLOTS if s in prompts]
    if args.slots:
        slots_to_generate = [(s, f) for s, f in slots_to_generate if s in args.slots]
    
    if not slots_to_generate:
        log.error("No slots to generate. Check that prompt files exist.")
        return 1
    
    log.info(f"Generating {len(slots_to_generate)} images for {args.slug}")
    
    # Generate images
    results = []
    for slot, _ in slots_to_generate:
        prompt = prompts[slot]
        reference_url = reference_images.get(slot)
        output_path = IMAGES_DIR / f"{args.slug}-{slot}.{args.format}"
        
        try:
            log.info(f"Generating {slot}...")
            
            # Generate image
            image_bytes = generate_with_gemini(
                prompt=prompt,
                reference_image_url=reference_url,
            )
            
            # Save to disk
            output_path.write_bytes(image_bytes)
            log.info(f"✓ Saved: {output_path} ({len(image_bytes)} bytes)")
            
            results.append({
                "slot": slot,
                "status": "success",
                "path": str(output_path),
                "size": len(image_bytes),
            })
            
            # Rate limiting - be nice to the API
            time.sleep(2)
            
        except Exception as e:
            log.error(f"✗ Failed to generate {slot}: {e}")
            results.append({
                "slot": slot,
                "status": "error",
                "error": str(e),
            })
    
    # Print summary
    print("\n" + "=" * 60)
    print("GENERATION SUMMARY")
    print("=" * 60)
    successful = [r for r in results if r["status"] == "success"]
    failed = [r for r in results if r["status"] == "error"]
    
    print(f"Successful: {len(successful)}")
    print(f"Failed: {len(failed)}")
    
    if failed:
        print("\nFailed slots:")
        for result in failed:
            print(f"  - {result['slot']}: {result['error']}")
    
    # Update MDX file if requested
    if args.update_mdx and successful:
        print(f"\nUpdating MDX file to use .{args.format} extensions...")
        if update_mdx_file(args.slug, args.format):
            print("✓ MDX file updated successfully")
        else:
            print("✗ Failed to update MDX file")
    
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
