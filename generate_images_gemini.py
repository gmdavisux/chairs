#!/usr/bin/env python3
"""
generate_images_gemini.py - Generate furniture images using Google Gemini

Usage:
    python generate_images_gemini.py wassily-chair
    python generate_images_gemini.py wassily-chair
    python generate_images_gemini.py wassily-chair --no-update-mdx
    python generate_images_gemini.py wassily-chair --custom-prompts prompts.json
    python generate_images_gemini.py wassily-chair --reference-images refs.json
    python generate_images_gemini.py wassily-chair --use-reference-metadata
    
The --use-reference-metadata flag will automatically include reference image URLs
from the reference-metadata.json file in the prompts (includes URLs in a "References:"
section, which Gemini can use for style guidance).
"""

import argparse
import base64
import json
import logging
import os
import sys
import time
from io import BytesIO
from pathlib import Path
from typing import Optional, Union
from urllib.request import Request, urlopen

import requests
import yaml
from dotenv import load_dotenv
from PIL import Image, ImageOps

from image_archive import archive_and_deploy_image, create_archive_directory

# Load environment variables
load_dotenv(override=False)  # Command line env vars take precedence

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
    ("silhouette", "silhouette.txt"),
    ("context", "context.txt"),
    ("designer", "designer.txt"),
    ("sketch", "sketch.txt"),
    ("detail-material", "detail-material.txt"),
]


def generate_with_gemini(
    prompt: str,
    reference_image_url: Optional[Union[str, list]] = None,
    api_key: Optional[str] = None,
) -> bytes:
    """
    Generate an image using Google Gemini with up to 14 reference images.
    
    Uses gemini-3.1-flash-image-preview model which supports multi-reference
    image generation according to official Google documentation.
    
    Args:
        prompt: The text prompt for image generation
        reference_image_url: Optional reference image URL(s) or local file path(s).
                           Can be a single path/URL string or a list of up to 14.
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
        from google import genai
        from google.genai import types
    except ImportError:
        raise RuntimeError(
            "google-genai package is required. Install with:\n"
            "  pip install google-genai"
        )
    
    client = genai.Client(api_key=api_key)
    
    log.info(f"Generating image with Google Gemini...")
    log.info(f"Prompt: {prompt[:100]}...")
    
    try:
        # Build contents array: [prompt, image1, image2, ...]
        contents = [prompt]
        
        # Load reference images if provided
        if reference_image_url:
            # Handle both single path/URL and list
            paths = reference_image_url if isinstance(reference_image_url, list) else [reference_image_url]
            
            # Limit to 14 reference images per Google documentation
            if len(paths) > 14:
                log.warning(f"Limiting from {len(paths)} to 14 reference images (API maximum)")
                paths = paths[:14]
            
            log.info(f"Loading {len(paths)} reference image(s)...")
            
            for path in paths:
                try:
                    # Check if it's a local file path or URL
                    if path.startswith(('http://', 'https://')):
                        # Download from URL
                        req = Request(path, headers={'User-Agent': 'Mozilla/5.0'})
                        with urlopen(req, timeout=30) as response:
                            img_data = response.read()
                        ref_image = Image.open(BytesIO(img_data))
                    else:
                        # Load from local file
                        ref_path = Path(path) if not Path(path).is_absolute() else Path(path)
                        if not ref_path.exists():
                            # Try relative to ROOT
                            ref_path = ROOT / path
                        ref_image = Image.open(ref_path)
                    
                    # Convert to RGB if needed (remove alpha channel)
                    if ref_image.mode in ('RGBA', 'LA', 'P'):
                        ref_image = ref_image.convert('RGB')
                    
                    contents.append(ref_image)
                    log.debug(f"Loaded reference: {path}")
                    
                except Exception as e:
                    log.warning(f"Failed to load reference image {path}: {e}")
        
        # Use Gemini 3.1 Flash Image model with generate_content
        # This model supports up to 14 reference images according to official docs
        response = client.models.generate_content(
            model='gemini-3.1-flash-image-preview',
            contents=contents,
            config=types.GenerateContentConfig(
                response_modalities=['IMAGE'],  # Image only, no text
                image_config=types.ImageConfig(
                    aspect_ratio='4:3',
                ),
            )
        )
        
        # Extract the generated image from response
        if not response or not response.parts:
            raise RuntimeError("Gemini returned no response parts")
        
        # Find the image part
        pil_image = None
        for part in response.parts:
            # Try as_image() method first (returns google.genai.types.Image)
            if hasattr(part, 'as_image'):
                try:
                    genai_image = part.as_image()
                    if genai_image:
                        # Convert genai Image to PIL Image
                        # The genai Image object has a _pil_image attribute
                        if hasattr(genai_image, '_pil_image'):
                            pil_image = genai_image._pil_image
                        elif hasattr(genai_image, 'to_pil'):
                            pil_image = genai_image.to_pil()
                        else:
                            # Try to get bytes and convert
                            img_bytes = genai_image._image_bytes if hasattr(genai_image, '_image_bytes') else None
                            if img_bytes:
                                pil_image = Image.open(BytesIO(img_bytes))
                        if pil_image:
                            break
                except Exception as e:
                    log.debug(f"Could not extract image via as_image(): {e}")
                    
            # Try inline_data
            if hasattr(part, 'inline_data') and part.inline_data:
                try:
                    img_bytes = part.inline_data.data
                    if isinstance(img_bytes, str):
                        # Base64 encoded
                        img_bytes = base64.b64decode(img_bytes)
                    pil_image = Image.open(BytesIO(img_bytes))
                    break
                except Exception as e:
                    log.debug(f"Could not extract from inline_data: {e}")
        
        if pil_image is None:
            # Last resort: dump response structure for debugging
            parts_info = []
            for i, part in enumerate(response.parts):
                attrs = [attr for attr in dir(part) if not attr.startswith('_')]
                parts_info.append(f"Part {i}: {type(part).__name__}, attrs={attrs}")
            raise RuntimeError(
                f"Could not extract image from Gemini response.\n"
                f"Response has {len(response.parts)} parts:\n" + "\n".join(parts_info)
            )
        
        # Ensure RGB mode for PNG
        if pil_image.mode in ('RGBA', 'LA', 'P'):
            pil_image = pil_image.convert('RGB')
        
        # Convert to PNG format
        buffer = BytesIO()
        pil_image.save(buffer, format="PNG")
        buffer.seek(0)
        
        log.info(f"Generated image: {pil_image.size[0]}x{pil_image.size[1]} -> {len(buffer.getvalue())} bytes")
        return buffer.getvalue()
        
    except Exception as e:
        raise RuntimeError(f"Google Gemini generation failed: {e}")


def generate_with_fal(
    prompt: str,
    reference_image_url: Optional[str] = None,
    api_key: Optional[str] = None,
) -> bytes:
    """
    Generate an image using FAL FLUX API with img2img support.
    
    Args:
        prompt: The text prompt for image generation
        reference_image_url: Optional reference image URL for img2img
        api_key: FAL API key (defaults to FAL_KEY env var)
    
    Returns:
        Image bytes (PNG format)
    """
    if api_key is None:
        api_key = os.getenv("FAL_KEY")
    
    if not api_key:
        raise RuntimeError(
            "FAL_KEY environment variable is required. "
            "Get your key at https://fal.ai"
        )
    
    try:
        import fal_client
    except ImportError:
        raise RuntimeError(
            "fal-client package is required. Install with:\n"
            "  pip install fal-client"
        )
    
    log.info(f"Generating image with FAL (FLUX)...")
    log.info(f"Prompt: {prompt[:100]}...")
    if reference_image_url:
        log.info(f"Using reference image: {reference_image_url}")
    
    try:
        model = "fal-ai/flux/dev"
        arguments = {
            "prompt": prompt,
            "image_size": {"width": 1280, "height": 1024},  # 5:4 ratio
            "num_inference_steps": 40,
            "guidance_scale": 3.5,
            "num_images": 1,
            "enable_safety_checker": False,
        }
        
        # Add reference image for img2img if provided
        if reference_image_url:
            # Convert local path to URL if needed
            if not reference_image_url.startswith(('http://', 'https://')):
                # For local files, we need to upload or use a different approach
                log.warning(f"Local reference images not yet supported with FAL. Skipping reference.")
            else:
                arguments["image_url"] = reference_image_url
                arguments["strength"] = float(os.getenv("FURNITURE_IMAGE_STRENGTH", "0.6"))
        
        response = fal_client.run(model, arguments=arguments)
        
        if not response or "images" not in response or not response["images"]:
            raise RuntimeError("FAL returned no images")
        
        # Get first image URL
        image_url = response["images"][0]["url"]
        
        # Download the image (FAL returns JPEG by default)
        response = requests.get(image_url, timeout=60)
        response.raise_for_status()
        image_bytes = response.content
        
        # Convert to PNG format as promised by the function signature
        pil_image = Image.open(BytesIO(image_bytes))
        
        buffer = BytesIO()
        pil_image.save(buffer, format="PNG")
        buffer.seek(0)
        
        log.debug(f"Converted FAL image to PNG format ({len(buffer.getvalue())} bytes)")
        return buffer.getvalue()
        
    except Exception as e:
        raise RuntimeError(f"FAL generation failed: {e}")


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


def load_reference_metadata(slug: str) -> list[str]:
    """
    Load reference image paths from the reference-metadata.json file.
    
    Returns a list of local file paths for successfully downloaded reference images.
    These can be directly loaded as PIL Images and passed to Gemini.
    """
    ref_dir = IMAGES_DIR / "reference" / f"{slug}-reference"
    metadata_path = ref_dir / "reference-metadata.json"
    
    if not metadata_path.exists():
        log.warning(f"No reference metadata found at: {metadata_path}")
        return []
    
    try:
        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)
        
        paths = []
        for item in metadata.get("items", []):
            # Only include items that have been successfully downloaded
            if item.get("status") == "downloaded" and item.get("localPath"):
                local_path = item["localPath"]
                # Convert to absolute path from ROOT
                full_path = ROOT / local_path
                if full_path.exists():
                    paths.append(str(full_path))
                else:
                    log.warning(f"Reference file not found: {full_path}")
        
        log.info(f"Found {len(paths)} downloaded reference images for {slug}")
        return paths
        
    except (OSError, json.JSONDecodeError) as e:
        log.warning(f"Failed to load reference metadata: {e}")
        return []


def get_references_for_slot(slot: str, all_references: list[str]) -> list[str]:
    """
    Return reference images ordered so Gemini anchors on the right subject.

    Gemini weights the first image most heavily, so ordering matters:
    - sketch: all chair references passed as-is — subject accuracy is paramount.
    - other slots: rotate starting index so each slot draws from a different
                   primary source.
    - designer: no chair references (would bias toward the chair form).

    FAL callers should take only the first element (single-image limit).

    Args:
        slot: Image slot name (hero, silhouette, context, designer, sketch)
        all_references: List of all available reference image paths

    Returns:
        Ordered list with the preferred reference first, or [] for designer/empty.
    """
    if not all_references:
        return []

    # Designer slot should NOT use chair reference images
    if slot == "designer":
        return []

    # Sketch: pass all chair references unchanged — subject accuracy is the
    # only priority; no style reference injected.
    if slot == "sketch":
        log.info(
            f"Slot 'sketch': {len(all_references)} chair ref(s), "
            f"leading with {Path(all_references[0]).name}"
        )
        return list(all_references)

    # Map each slot to a different starting index so every slot begins
    # from a distinct reference — Gemini will weight that first image most.
    slot_preferences = {
        "hero": 0,        # First reference — typically primary product shot
        "silhouette": 1,  # Second reference — different angle/view
        "context": 2,     # Third reference — architectural or setting shot
    }

    preferred_index = slot_preferences.get(slot, 0) % len(all_references)

    # Rotate the list so the preferred reference is first
    rotated = all_references[preferred_index:] + all_references[:preferred_index]
    log.info(
        f"Slot '{slot}': using {len(rotated)} reference(s), leading with "
        f"{Path(rotated[0]).name}"
    )
    return rotated


# Keep old name as thin alias so external callers aren't broken.
def select_reference_for_slot(slot: str, all_references: list[str]) -> Optional[str]:
    """Deprecated alias — returns only the preferred (first) reference path."""
    refs = get_references_for_slot(slot, all_references)
    return refs[0] if refs else None


def _slot_alt_and_caption(slot: str, title: str, designer: str) -> tuple[str, str]:
    """Return (alt, caption) text for a generated image slot."""
    slot_meta = {
        "hero": (
            f"{title} — studio composition highlighting form and materials",
            f"AI-generated studio photograph of the {title} by {designer}.",
        ),
        "silhouette": (
            f"{title} profile silhouette showing signature geometry",
            f"AI-generated silhouette of the {title} by {designer}.",
        ),
        "context": (
            f"{title} in a mid-century modern interior setting",
            f"AI-generated context photograph of the {title} by {designer} in situ.",
        ),
        "designer": (
            f"Portrait of {designer}, designer of the {title}",
            f"AI-generated portrait of {designer}.",
        ),
        "sketch": (
            f"Industrial design marker rendering of the {title}",
            f"AI-generated design sketch of the {title} by {designer}.",
        ),
        "detail-material": (
            f"Close-up of material texture on the {title}",
            f"AI-generated material detail of the {title} by {designer}.",
        ),
        "detail-structure": (
            f"Structural detail showing joints and frame of the {title}",
            f"AI-generated structural detail of the {title} by {designer}.",
        ),
    }
    return slot_meta.get(slot, (f"{title} — {slot}", f"AI-generated {slot} image for the {title}."))


def update_mdx_file(
    slug: str,
    extension: str = "png",
    generated_slots: Optional[list[str]] = None,
    provider: str = "google",
    model: str = "",
) -> bool:
    """
    Update the MDX file to use the specified image extension and, for any
    successfully generated slots, replace placeholder alt/caption/status/
    source/license/origin with real values.

    Args:
        slug: The furniture piece slug
        extension: Image file extension (default: png)
        generated_slots: Slots that were successfully generated (metadata updated)
        provider: Image provider name for source label
        model: Model name for source label

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

    title = data.get("title", "")
    designer = data.get("designer", "")
    source_label = f"AI generated via {provider}/{model}" if model else f"AI generated via {provider}"
    slots_set = set(generated_slots or [])

    # Update image extensions
    if data.get("heroImage"):
        data["heroImage"] = data["heroImage"].replace(".jpg", f".{extension}")

    # Update hero-level metadata if hero was generated
    if "hero" in slots_set:
        alt, caption = _slot_alt_and_caption("hero", title, designer)
        data["heroImageAlt"] = alt
        data["heroImageAltStatus"] = "actual"
        data["heroImageCaption"] = caption
        data["heroImageSource"] = source_label
        data["heroImageLicense"] = "ai_generated"
        data["heroImageOrigin"] = "ai_generated"

    # Update designer image path if designer slot was generated
    if "designer" in slots_set:
        data["designerImage"] = f"/images/{slug}-designer.{extension}"

    if "images" in data and isinstance(data["images"], list):
        for img in data["images"]:
            if "src" in img:
                img["src"] = img["src"].replace(".jpg", f".{extension}")
            # Update metadata for generated slots
            if slots_set:
                img_id = str(img.get("id", ""))
                for slot in slots_set:
                    if img_id.endswith(slot):
                        alt, caption = _slot_alt_and_caption(slot, title, designer)
                        img["alt"] = alt
                        img["altStatus"] = "actual"
                        img["caption"] = caption
                        img["source"] = source_label
                        img["license"] = "ai_generated"
                        img["origin"] = "ai_generated"
                        break

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
        "--use-reference-metadata",
        action="store_true",
        help="Automatically include reference image URLs from reference-metadata.json",
    )
    parser.add_argument(
        "--no-update-mdx",
        dest="update_mdx",
        action="store_false",
        help="Skip updating the MDX file after generation",
    )
    parser.set_defaults(update_mdx=True)
    parser.add_argument(
        "--slots",
        nargs="+",
        choices=["hero", "silhouette", "context", "designer", "sketch", "detail-material"],
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
    reference_urls_from_metadata = []
    
    if args.reference_images:
        log.info(f"Loading reference images from: {args.reference_images}")
        reference_images = load_reference_images(args.reference_images)
    
    if args.use_reference_metadata:
        log.info(f"Loading reference URLs from metadata for {args.slug}")
        reference_urls_from_metadata = load_reference_metadata(args.slug)

    # Filter slots if specified
    slots_to_generate = [(s, f) for s, f in IMAGE_SLOTS if s in prompts]
    if args.slots:
        slots_to_generate = [(s, f) for s, f in slots_to_generate if s in args.slots]

    if not slots_to_generate:
        log.error("No slots to generate. Check that prompt files exist.")
        return 1

    # Sketch slot requires chair reference images for subject accuracy.
    # Auto-load from metadata if not already loaded; abort with guidance if missing.
    generating_sketch = any(s == "sketch" for s, _ in slots_to_generate)
    if generating_sketch and not reference_urls_from_metadata and not reference_images.get("sketch"):
        reference_urls_from_metadata = load_reference_metadata(args.slug)
        if not reference_urls_from_metadata:
            ref_dir = IMAGES_DIR / "reference" / f"{args.slug}-reference"
            log.error(
                "Sketch slot requires chair reference images but none were found.\n"
                f"  Expected: {ref_dir}\n"
                "  To fix, run:  python furniture_agent.py --plan  (then rebuild the page)\n"
                "  Or provide a reference manually:\n"
                f"    python generate_images_gemini.py {args.slug} --slots sketch "
                "--reference-images refs.json\n"
                "  where refs.json contains: {\"sketch\": \"https://example.com/chair.jpg\"}"
            )
            return 1
        log.info(f"Auto-loaded {len(reference_urls_from_metadata)} chair reference(s) for sketch slot")
    
    log.info(f"Generating {len(slots_to_generate)} images for {args.slug}")
    
    # Determine provider
    provider = os.getenv("FURNITURE_IMAGE_PROVIDER", "google").lower()
    log.info(f"Using provider: {provider}")
    
    # Create archive directory for this generation batch
    archive_dir = create_archive_directory(args.slug)
    log.info(f"Archive directory: {archive_dir}")
    
    # Generate images
    results = []
    for slot, _ in slots_to_generate:
        prompt = prompts[slot]
        
        # Determine reference(s) to use for this slot.
        # slot_refs is a list (may be empty); for Gemini we pass the full list
        # so it sees all references with the preferred one leading.
        # For FAL (single-image limit) we pass only the first element.
        explicit_ref = reference_images.get(slot)
        if explicit_ref:
            slot_refs = [explicit_ref]
        elif reference_urls_from_metadata:
            slot_refs = get_references_for_slot(slot, reference_urls_from_metadata)
        else:
            slot_refs = []

        output_path = IMAGES_DIR / f"{args.slug}-{slot}.{args.format}"

        try:
            log.info(f"Generating {slot}...")

            # Generate image with selected provider.
            # Designer slot always uses Gemini regardless of provider setting —
            # FAL doesn't handle human portraits reliably. If Gemini fails for
            # this slot, the exception propagates and the slot is skipped; there
            # is no FAL fallback for designer images.
            if slot == "designer" or provider != "fal":
                image_bytes = generate_with_gemini(
                    prompt=prompt,
                    reference_image_url=slot_refs if slot_refs else None,
                )
            else:  # provider == "fal" for non-designer slots
                # FAL supports only one reference image
                fal_ref = slot_refs[0] if slot_refs else None
                image_bytes = generate_with_fal(
                    prompt=prompt,
                    reference_image_url=fal_ref,
                )

            # Enforce grayscale for designer slot
            if slot == "designer":
                # Archive original color image before converting
                original_path = archive_dir / f"designer-original.{args.format}"
                original_path.write_bytes(image_bytes)
                log.info(f"Archived original color designer image: {original_path}")
                # Convert to grayscale
                _img = Image.open(BytesIO(image_bytes))
                _img = ImageOps.grayscale(_img).convert("RGB")
                _buf = BytesIO()
                _img.save(_buf, format="PNG")
                image_bytes = _buf.getvalue()
                log.info("Converted designer image to grayscale")
            
            # Archive and deploy image
            archive_info = archive_and_deploy_image(
                slug=args.slug,
                slot=slot,
                image_bytes=image_bytes,
                display_path=output_path,
                metadata={
                    "provider": provider,
                    "prompt": prompt,
                    "reference_urls": slot_refs,
                    "primary_reference": slot_refs[0] if slot_refs else None,
                },
                archive_dir=archive_dir,
                extension=args.format,
            )
            
            log.info(f"✓ Archived: {archive_info['archive_path']}")
            log.info(f"✓ Deployed: {archive_info['display_path']} ({archive_info['size']} bytes)")
            
            results.append({
                "slot": slot,
                "status": "success",
                "path": str(output_path),
                "archive_path": archive_info['archive_path'],
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
    
    if successful:
        print(f"\n📁 Archive: {archive_dir}")
        print("   Images have been archived and deployed to display locations.")
    
    if failed:
        print("\nFailed slots:")
        for result in failed:
            print(f"  - {result['slot']}: {result['error']}")
    
    # Update MDX file unless explicitly skipped
    if args.update_mdx and successful:
        successful_slots = [r["slot"] for r in successful]
        # Determine model name for source label (use env var or generic fallback)
        gemini_model = os.getenv("GEMINI_IMAGE_MODEL", "gemini-imagen")
        print(f"\nUpdating MDX file (extensions + metadata for {successful_slots})...")
        if update_mdx_file(
            args.slug,
            args.format,
            generated_slots=successful_slots,
            provider=provider,
            model=gemini_model,
        ):
            print("✓ MDX file updated successfully")
            # Auto-insert any missing ImageWithMeta slots (registry-first format)
            import subprocess
            result = subprocess.run(
                [sys.executable, str(ROOT / "insert_image_slots.py"), args.slug],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                print("✓ Image slots inserted/verified")
            else:
                print(f"⚠ insert_image_slots.py exited {result.returncode}: {result.stderr.strip()}")
        else:
            print("✗ Failed to update MDX file")

    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
