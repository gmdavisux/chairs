#!/usr/bin/env python3
"""
generate_images.py - Generate furniture images using AI providers (Gemini, FAL)

Usage:
    python generate_images.py wassily-chair
    python generate_images.py wassily-chair --update-mdx
    python generate_images.py wassily-chair --custom-prompts prompts.json
    python generate_images.py wassily-chair --reference-images refs.json
    
When using --update-mdx, the script will:
1. Generate images for specified slots
2. Update the MDX frontmatter with new image references
3. Automatically insert ImageWithMeta components for any new image slots
   (this happens via insert_image_slots.py which runs automatically)
"""

import argparse
import base64
import json
import logging
import os
import subprocess
import sys
import time
from io import BytesIO
from pathlib import Path
from typing import Optional
from urllib.request import Request, urlopen

import requests
import yaml
from dotenv import load_dotenv
from PIL import Image

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
    ("sketch", "sketch.txt"),
    ("context", "context.txt"),
    ("designer", "designer.txt"),
]


def generate_with_gemini(
    prompt: str,
    reference_image_url: Optional[str] = None,
    api_key: Optional[str] = None,
) -> bytes:
    """
    Generate an image using Google Gemini with multimodal reference support.
    
    When reference_image_url is provided, uses Gemini's multimodal model
    (gemini-1.5-flash) to understand the reference image and generate an
    enhanced prompt, which can then be used for image generation.
    
    Args:
        prompt: The text prompt for image generation
        reference_image_url: Optional reference image URL/path for visual guidance
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
    
    # Configure the API
    genai.configure(api_key=api_key)
    
    log.info(f"Generating image with Google Gemini...")
    log.info(f"Prompt: {prompt[:100]}...")
    
    try:
        # Load reference image if provided
        pil_ref_image = None
        if reference_image_url:
            log.info(f"Loading reference image: {reference_image_url}")
            
            # Download or load the reference image
            if reference_image_url.startswith(('http://', 'https://')):
                response_img = requests.get(reference_image_url, timeout=30)
                response_img.raise_for_status()
                ref_image_bytes = response_img.content
            else:
                # Load from local file
                ref_path = Path(reference_image_url)
                if not ref_path.is_absolute():
                    ref_path = ROOT / reference_image_url
                with open(ref_path, 'rb') as f:
                    ref_image_bytes = f.read()
            
            # Load as PIL Image
            pil_ref_image = Image.open(BytesIO(ref_image_bytes))
            log.info(f"Reference image loaded: {pil_ref_image.size}")
        
        # Method 1: Use multimodal model to enhance prompt with reference understanding
        # This is the recommended approach per Google's documentation
        enhanced_prompt = prompt
        if pil_ref_image:
            log.info("Using Gemini multimodal model to understand reference image...")
            
            # Use gemini-1.5-flash for multimodal understanding
            # Place image BEFORE prompt as recommended by documentation
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            # Create an enhanced prompt that asks Gemini to generate based on reference
            multimodal_prompt = (
                f"Based on this reference image, generate a photorealistic image with these specifications: "
                f"{prompt}\n\n"
                f"Maintain the same style, lighting, and composition quality as the reference image. "
                f"Focus on accuracy and authenticity."
            )
            
            # Generate content with image understanding
            # Image comes first, then prompt (per documentation best practices)
            response = model.generate_content([pil_ref_image, multimodal_prompt])
            
            # For now, we extract enhanced understanding and use text-to-image
            # In future, Gemini may support direct image generation with references
            if response.text:
                log.info(f"Gemini understanding: {response.text[:200]}...")
                enhanced_prompt = f"{prompt}. Style guidance: {response.text[:500]}"
        
        # Method 2: Generate image using text prompt
        # Note: As of April 2026, direct image generation uses Imagen model
        # which may have limited reference support in the Python SDK
        
        # For now, we use FAL or manual workflow with AI Studio for true reference support
        # This is a limitation documented in the Google AI documentation
        
        log.warning(
            "Note: Direct API-based image generation with reference images is limited. "
            "For best results with reference images, use Google AI Studio manually or FAL."
        )
        
        # Fallback: Use text-to-image without reference
        # You would need to use Imagen API or vertex AI for production
        raise RuntimeError(
            "Direct image generation with Gemini API requires manual workflow. "
            "Use 'prepare_gemini_batch.py' to create prompts for manual generation in AI Studio, "
            "or set FURNITURE_IMAGE_PROVIDER=fal to use FAL with img2img support."
        )
        
    except Exception as e:
        log.error(f"Google Gemini generation failed: {e}")
        raise RuntimeError(
            f"Gemini API error: {e}\n\n"
            "For reference image support, use one of these approaches:\n"
            "  1. Manual: python prepare_gemini_batch.py [slug] --simple --output batch.txt\n"
            "  2. Auto with FAL: Set FURNITURE_IMAGE_PROVIDER=fal in .env\n"
            "  3. Vertex AI: Use Google Cloud Vertex AI Python SDK (enterprise)"
        )


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
            "image_size": "square_hd",  # 1024x1024
            "num_inference_steps": 50,  # Increased from 40 for better quality
            "guidance_scale": 3.5,
            "num_images": 1,
            "enable_safety_checker": False,
            "output_format": "png",  # Request PNG directly to avoid JPEG compression
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
        description="Generate furniture images using AI providers (Gemini or FAL)"
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
        choices=["hero", "sketch", "context", "designer"],
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
        reference_url = reference_images.get(slot)
        output_path = IMAGES_DIR / f"{args.slug}-{slot}.{args.format}"
        
        try:
            log.info(f"Generating {slot}...")
            
            # Generate image with selected provider
            if provider == "fal":
                image_bytes = generate_with_fal(
                    prompt=prompt,
                    reference_image_url=reference_url,
                )
            else:  # default to google/gemini
                image_bytes = generate_with_gemini(
                    prompt=prompt,
                    reference_image_url=reference_url,
                )
            
            # Archive and deploy image
            archive_info = archive_and_deploy_image(
                slug=args.slug,
                slot=slot,
                image_bytes=image_bytes,
                display_path=output_path,
                metadata={
                    "provider": provider,
                    "prompt": prompt,
                    "reference_url": reference_url,
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
    
    # Update MDX file if requested
    if args.update_mdx and successful:
        print(f"\nUpdating MDX file to use .{args.format} extensions...")
        if update_mdx_file(args.slug, args.format):
            print("✓ MDX file updated successfully")
            
            # Automatically insert missing image slots into the blog post
            print("\nInserting missing image slots into blog post...")
            try:
                import subprocess
                result = subprocess.run(
                    [sys.executable, str(ROOT / "insert_image_slots.py"), args.slug],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if result.returncode == 0:
                    # Parse output to show what was added
                    if "All image slots already referenced" in result.stdout:
                        print("✓ All image slots already present in the body")
                    else:
                        print("✓ Image slots inserted automatically")
                        # Show which slots were added
                        for line in result.stdout.split("\n"):
                            if "Added ImageWithMeta for slot:" in line:
                                print(f"  {line.strip()}")
                else:
                    print(f"⚠ Warning: Could not auto-insert image slots: {result.stderr}")
            except Exception as e:
                print(f"⚠ Warning: Could not auto-insert image slots: {e}")
        else:
            print("✗ Failed to update MDX file")
    
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
