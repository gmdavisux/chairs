#!/usr/bin/env python3
"""
Fetch designer portrait images from Wikimedia Commons and save with chair naming convention.

Usage:
    python fetch_designer_images.py --all
    python fetch_designer_images.py --chair barcelona-chair --designer "Ludwig Mies van der Rohe"
    python fetch_designer_images.py --enhance  # Enhance low-quality images with AI
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional
import requests
from PIL import Image
from io import BytesIO

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

ROOT = Path(__file__).parent
IMAGES_DIR = ROOT / "public" / "images"
DESIGNERS_DIR = IMAGES_DIR / "designers"
CONTENT_DIR = ROOT / "src" / "content" / "blog"

# Wikimedia Commons API
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
COMMONS_FILE_URL = "https://commons.wikimedia.org/wiki/Special:FilePath/{filename}?width=800"

# Designer Name Mapping (for better Wikimedia search results)
DESIGNER_SEARCH_TERMS = {
    "Ludwig Mies van der Rohe": ["Ludwig Mies van der Rohe", "Mies van der Rohe"],
    "Marcel Breuer": ["Marcel Breuer"],
    "Charles and Ray Eames": ["Charles Eames", "Ray Eames", "Charles and Ray Eames"],
    "Eero Saarinen": ["Eero Saarinen"],
    "Arne Jacobsen": ["Arne Jacobsen"],
    "Hans Wegner": ["Hans Wegner"],
}


def search_wikimedia_for_designer(designer_name: str, limit: int = 5) -> list:
    """
    Search Wikimedia Commons for images of a designer.
    
    Returns list of dicts with 'title', 'url', and 'pageurl' keys.
    """
    search_terms = DESIGNER_SEARCH_TERMS.get(designer_name, [designer_name])
    
    all_results = []
    
    for term in search_terms:
        log.info(f"Searching Wikimedia Commons for: {term}")
        
        # Search for images
        params = {
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrsearch": f"{term} portrait photograph",
            "gsrnamespace": "6",  # File namespace
            "gsrlimit": limit,
            "prop": "imageinfo",
            "iiprop": "url|size|mime",
            "iiurlwidth": 800,
        }
        
        try:
            response = requests.get(COMMONS_API, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if "query" in data and "pages" in data["query"]:
                pages = data["query"]["pages"]
                
                for page_id, page in pages.items():
                    if "imageinfo" in page and page["imageinfo"]:
                        info = page["imageinfo"][0]
                        result = {
                            "title": page.get("title", ""),
                            "url": info.get("url", ""),
                            "thumburl": info.get("thumburl", info.get("url", "")),
                            "pageurl": f"https://commons.wikimedia.org/wiki/{page.get('title', '').replace(' ', '_')}",
                            "width": info.get("width", 0),
                            "height": info.get("height", 0),
                            "mime": info.get("mime", ""),
                        }
                        all_results.append(result)
                        log.info(f"  Found: {result['title']}")
        
        except Exception as e:
            log.error(f"Error searching for {term}: {e}")
    
    return all_results


def download_image(url: str, output_path: Path) -> bool:
    """Download image from URL to output path."""
    try:
        log.info(f"Downloading from: {url}")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # Open and save image
        img = Image.open(BytesIO(response.content))
        
        # Convert to RGB if necessary
        if img.mode in ("RGBA", "P", "LA"):
            # Create white background
            background = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "RGBA" or img.mode == "LA":
                background.paste(img, mask=img.split()[-1])
            else:
                background.paste(img)
            img = background
        
        # Save as JPEG
        img.save(output_path, "JPEG", quality=90)
        log.info(f"Saved to: {output_path}")
        return True
    
    except Exception as e:
        log.error(f"Error downloading image: {e}")
        return False


def enhance_image_with_fal(input_path: Path, output_path: Path) -> bool:
    """Enhance a low-quality image using FAL AI upscaling."""
    try:
        import fal_client
    except ImportError:
        log.warning("fal-client not installed. Skipping enhancement.")
        return False
    
    if not os.getenv("FAL_KEY"):
        log.warning("FAL_KEY not set. Skipping enhancement.")
        return False
    
    try:
        log.info(f"Enhancing image: {input_path}")
        
        # Upload image
        image_url = fal_client.upload_file(str(input_path))
        
        # Use FAL's real-esrgan or similar upscaler
        result = fal_client.subscribe(
            "fal-ai/fast-sdxl",  # or use dedicated upscaler
            arguments={
                "image_url": image_url,
                "prompt": "professional portrait photograph, high quality, sharp details",
                "strength": 0.3,  # Minimal changes, just enhancement
            }
        )
        
        if "images" in result and result["images"]:
            enhanced_url = result["images"][0]["url"]
            return download_image(enhanced_url, output_path)
    
    except Exception as e:
        log.error(f"Error enhancing image: {e}")
        return False


def get_designer_from_mdx(mdx_path: Path) -> Optional[str]:
    """Extract designer name from MDX frontmatter."""
    try:
        content = mdx_path.read_text()
        # Simple regex to find designer field
        import re
        match = re.search(r'^designer:\s*["\']?([^"\'\n]+)["\']?', content, re.MULTILINE)
        if match:
            return match.group(1).strip()
    except Exception as e:
        log.error(f"Error reading {mdx_path}: {e}")
    return None


def is_placeholder_image(image_path: Path, max_size_kb: int = 50) -> bool:
    """Check if an image is likely a placeholder based on file size."""
    if not image_path.exists():
        return False
    size_kb = image_path.stat().st_size / 1024
    return size_kb < max_size_kb


def fetch_designer_for_chair(chair_slug: str, designer_name: str, enhance: bool = False, force: bool = False) -> bool:
    """
    Fetch designer image for a specific chair.
    
    Args:
        chair_slug: e.g., "barcelona-chair"
        designer_name: e.g., "Ludwig Mies van der Rohe"
        enhance: Whether to enhance low-quality images
        force: Force overwrite existing images
    
    Returns:
        True if successful
    """
    output_path = IMAGES_DIR / f"{chair_slug}-designer.jpg"
    
    # Check if already exists
    if output_path.exists() and not force:
        if is_placeholder_image(output_path):
            log.warning(f"Found placeholder image at {output_path} ({output_path.stat().st_size / 1024:.1f}KB)")
            response = input(f"Replace placeholder with real image? [Y/n]: ").strip().lower()
            if response and response != 'y':
                log.info("Skipping...")
                return True
            # Continue to fetch
        else:
            log.info(f"Designer image already exists: {output_path}")
            return True
    
    # Search Wikimedia
    results = search_wikimedia_for_designer(designer_name)
    
    if not results:
        log.warning(f"No images found for {designer_name}")
        return False
    
    # Interactive selection
    print(f"\nFound {len(results)} images for {designer_name}:")
    for i, result in enumerate(results[:10], 1):
        print(f"{i}. {result['title']}")
        print(f"   URL: {result['pageurl']}")
        print(f"   Size: {result['width']}x{result['height']}")
        print()
    
    try:
        choice = input(f"Select image (1-{min(len(results), 10)}) or 's' to skip: ").strip()
        if choice.lower() == 's':
            return False
        
        idx = int(choice) - 1
        if idx < 0 or idx >= len(results):
            log.error("Invalid selection")
            return False
        
        selected = results[idx]
        
        # Download
        success = download_image(selected["thumburl"], output_path)
        
        if success and enhance:
            # Enhance if requested
            temp_path = output_path.with_suffix(".original.jpg")
            output_path.rename(temp_path)
            if not enhance_image_with_fal(temp_path, output_path):
                # If enhancement fails, use original
                temp_path.rename(output_path)
                log.info("Using original (enhancement failed)")
            else:
                temp_path.unlink()  # Remove original
        
        return success
    
    except (ValueError, KeyboardInterrupt):
        log.error("Invalid input or cancelled")
        return False


def process_all_chairs(enhance: bool = False, force: bool = False):
    """Process all MDX files to fetch designer images."""
    mdx_files = list(CONTENT_DIR.glob("*.mdx"))
    
    for mdx_file in mdx_files:
        chair_slug = mdx_file.stem
        designer_name = get_designer_from_mdx(mdx_file)
        
        if not designer_name:
            log.info(f"No designer found in {mdx_file.name}, skipping")
            continue
        
        log.info(f"\n{'='*60}")
        log.info(f"Processing: {chair_slug}")
        log.info(f"Designer: {designer_name}")
        log.info(f"{'='*60}")
        
        fetch_designer_for_chair(chair_slug, designer_name, enhance, force)


def _query_wikidata_designer_image(designer_name: str) -> Optional[dict]:
    """Query Wikidata SPARQL for the canonical P18 (image) property of a designer.

    Returns a dict with 'url', 'title', 'source', 'license' or None.
    """
    # Build a SPARQL query that looks up a person by name and fetches their image.
    sparql_query = """
SELECT ?file ?fileLabel WHERE {
  ?person wdt:P18 ?file .
  ?person rdfs:label "%s"@en .
  BIND(CONCAT("File:", STRAFTER(STR(?file), "Special:FilePath/")) AS ?fileLabel)
}
LIMIT 1
""" % designer_name.replace('"', '\\"')

    endpoint = "https://query.wikidata.org/sparql"
    headers = {
        "Accept": "application/sparql-results+json",
        "User-Agent": "DesignerPortraitFetcher/1.0 (chairs-site-bot)",
    }
    try:
        response = requests.get(
            endpoint,
            params={"query": sparql_query, "format": "json"},
            headers=headers,
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()
        bindings = data.get("results", {}).get("bindings", [])
        if not bindings:
            return None

        file_url = bindings[0].get("file", {}).get("value", "")
        if not file_url.startswith("http"):
            return None

        # file_url is already a Special:FilePath direct URL from Wikimedia
        log.info("Wikidata portrait found for %s: %s", designer_name, file_url)
        return {
            "url": file_url,
            "title": bindings[0].get("fileLabel", {}).get("value", ""),
            "source": f"https://www.wikidata.org/wiki/Special:Search/{designer_name.replace(' ', '_')}",
            "license": "public domain or CC-BY-SA (Wikimedia Commons)",
            "width": 0,
            "height": 0,
        }
    except Exception as exc:
        log.warning("Wikidata SPARQL query failed for %s: %s", designer_name, exc)
        return None


def _rank_wikimedia_results_with_ai(designer_name: str, results: list) -> Optional[dict]:
    """Use Gemini Vision to visually select the best portrait candidate from Wikimedia results.

    Downloads thumbnails and sends them to Gemini multimodal for visual identification.
    Falls back to heuristic selection if Gemini is unavailable.
    """
    if not results:
        return None

    api_key = os.getenv("GOOGLE_API_KEY")
    if api_key:
        try:
            import google.generativeai as genai
            from io import BytesIO as _BytesIO

            genai.configure(api_key=api_key)
            vision_model = genai.GenerativeModel("gemini-1.5-flash")

            # Download thumbnails for visual inspection (up to 6 candidates)
            candidates = results[:6]
            content_parts: list = [
                f"I need to identify a real portrait photograph of the furniture designer {designer_name}. "
                f"Below are up to {len(candidates)} images from Wikimedia Commons numbered 1 to {len(candidates)}. "
                "Reply with ONLY the number (1-based) of the image that best shows this designer's face as a "
                "real portrait photograph (not a sketch, building, chair, or illustration). "
                "If none clearly show the designer's face, reply with 0. Reply with just the number."
            ]
            valid_candidates = []
            for r in candidates:
                thumb_url = r.get("thumburl") or r.get("url", "")
                if not thumb_url:
                    continue
                try:
                    thumb_resp = requests.get(thumb_url, timeout=10)
                    thumb_resp.raise_for_status()
                    img = Image.open(_BytesIO(thumb_resp.content)).convert("RGB")
                    content_parts.append(img)
                    valid_candidates.append(r)
                except Exception:
                    pass  # skip unloadable thumbnails

            if valid_candidates:
                response = vision_model.generate_content(content_parts)
                choice_str = response.text.strip().split()[0].rstrip(".")
                choice = int(choice_str)
                if 1 <= choice <= len(valid_candidates):
                    log.info("Gemini Vision selected candidate %d for %s", choice, designer_name)
                    return valid_candidates[choice - 1]
                if choice == 0:
                    log.info("Gemini Vision found no suitable portrait for %s", designer_name)
                    return None
        except Exception as exc:
            log.warning("Gemini Vision ranking unavailable (%s), using heuristic fallback", exc)

    # Heuristic fallback: prefer items with "portrait" in title, highest resolution
    PORTRAIT_KEYWORDS = ("portrait", "photo", "photograph", "headshot", "mugshot")
    EXCLUDE_KEYWORDS = ("chair", "furniture", "building", "design", "sketch", "drawing", "plan")

    def score(r: dict) -> float:
        title_lower = r.get("title", "").lower()
        if any(kw in title_lower for kw in EXCLUDE_KEYWORDS):
            return -1.0
        portrait_bonus = 2.0 if any(kw in title_lower for kw in PORTRAIT_KEYWORDS) else 0.0
        # Prefer larger images
        area = r.get("width", 0) * r.get("height", 0)
        return portrait_bonus + area / 1_000_000

    scored = sorted(results[:10], key=score, reverse=True)
    best = scored[0]
    if score(best) < 0:
        return None
    log.info("Heuristic selected: %s for %s", best.get("title"), designer_name)
    return best


def fetch_designer_auto(designer_name: str) -> Optional[dict]:
    """Non-interactive: find the best real portrait for a designer.

    Pipeline:
      1. Wikidata SPARQL (P18 canonical image) — structured data, most reliable
      2. Wikimedia Commons text search + Gemini/heuristic ranking

    Returns a dict with keys: url, title, source, license
    Returns None if no suitable image found.
    """
    log.info("Auto-fetching designer portrait for: %s", designer_name)

    # Step 1: Wikidata canonical portrait
    wikidata_result = _query_wikidata_designer_image(designer_name)
    if wikidata_result and wikidata_result.get("url"):
        return wikidata_result

    # Step 2: Wikimedia Commons search + AI ranking
    commons_results = search_wikimedia_for_designer(designer_name, limit=10)
    if commons_results:
        best = _rank_wikimedia_results_with_ai(designer_name, commons_results)
        if best:
            best.setdefault("source", best.get("pageurl", ""))
            best.setdefault("license", "public domain or CC-BY-SA (Wikimedia Commons)")
            return best

    log.warning("No suitable designer portrait found for: %s", designer_name)
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Fetch designer portrait images from Wikimedia Commons"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Process all chairs in content directory"
    )
    parser.add_argument(
        "--chair",
        help="Chair slug (e.g., barcelona-chair)"
    )
    parser.add_argument(
        "--designer",
        help="Designer name (e.g., 'Ludwig Mies van der Rohe')"
    )
    parser.add_argument(
        "--enhance",
        action="store_true",
        help="Enhance low-quality images with AI upscaling"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force overwrite existing images (useful for replacing placeholders)"
    )
    
    args = parser.parse_args()
    
    # Ensure images directory exists
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    
    if args.all:
        process_all_chairs(args.enhance, args.force)
    elif args.chair and args.designer:
        fetch_designer_for_chair(args.chair, args.designer, args.enhance, args.force)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
