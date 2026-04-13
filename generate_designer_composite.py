#!/usr/bin/env python3
"""
generate_designer_composite.py — Fetch portrait references for a designer and use
Gemini to create a high-quality composite portrait, replacing the designer image.

Usage:
    python generate_designer_composite.py --chair swan-chair --designer "Arne Jacobsen"
"""

import argparse
import base64
import logging
import os
import sys
import time
from io import BytesIO
from pathlib import Path
from urllib.request import Request, urlopen

from typing import List, Optional

import requests
from dotenv import load_dotenv
from PIL import Image

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)

ROOT = Path(__file__).parent
IMAGES_DIR = ROOT / "public" / "images"
REFS_DIR = ROOT / "public" / "images" / "designers" / "references"

COMMONS_API = "https://commons.wikimedia.org/w/api.php"
WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
WIKIPEDIA_REST = "https://en.wikipedia.org/api/rest_v1"

# Friendly User-Agent per Wikimedia bot policy
WIKIMEDIA_UA = "ChairsProject/1.0 (educational; contact@example.com) python-requests"

# Known Wikimedia Commons filenames for designers (most reliable approach)
DESIGNER_KNOWN_FILES = {
    "Arne Jacobsen": [
        "Arne_Jacobsen_c1950.jpg",
        "Arne_Jacobsen.jpg",
        "ArneJacobsen.jpg",
        "Arne Jacobsen.jpg",
    ]
}

# Wikipedia article names to extract images from
DESIGNER_WIKIPEDIA_ARTICLES = {
    "Arne Jacobsen": "Arne_Jacobsen",
}

# Backup search terms if known files don't yield enough results
DESIGNER_SEARCH_TERMS = {
    "Arne Jacobsen": ["Arne Jacobsen architect portrait", "Arne Jacobsen photograph"],
}


HEADERS = {"User-Agent": WIKIMEDIA_UA}


def fetch_wikimedia_file_url(filename: str) -> Optional[str]:
    """Resolve a Wikimedia Commons File: title to a direct image URL via the API."""
    # Use Special:FilePath as the simplest direct URL method
    clean = filename.replace("File:", "").replace(" ", "_")
    special_url = "https://commons.wikimedia.org/wiki/Special:FilePath/{}?width=1000".format(clean)
    try:
        resp = requests.head(special_url, headers=HEADERS, timeout=15, allow_redirects=True)
        if resp.status_code == 200:
            log.info("  Resolved via Special:FilePath: {}".format(resp.url[:80]))
            return resp.url
    except Exception:
        pass

    # Fallback: API query
    title = filename if filename.startswith("File:") else "File:{}".format(filename)
    params = {
        "action": "query",
        "format": "json",
        "titles": title,
        "prop": "imageinfo",
        "iiprop": "url|size|mime",
        "iiurlwidth": 1000,
    }
    try:
        resp = requests.get(COMMONS_API, params=params, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        pages = data.get("query", {}).get("pages", {})
        for page in pages.values():
            info_list = page.get("imageinfo", [])
            if info_list:
                url = info_list[0].get("thumburl") or info_list[0].get("url")
                if url:
                    log.info("  Resolved {} -> {}...".format(title, url[:80]))
                    return url
    except Exception as e:
        log.warning("Could not resolve {}: {}".format(title, e))
    return None


def fetch_wikipedia_article_images(article: str) -> list:
    """Get image URLs from a Wikipedia article via the REST API."""
    results = []
    try:
        # Get all images listed on the article
        params = {
            "action": "query",
            "format": "json",
            "titles": article,
            "prop": "images",
            "imlimit": 20,
        }
        resp = requests.get(WIKIPEDIA_API, params=params, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        pages = data.get("query", {}).get("pages", {})
        image_titles = []
        for page in pages.values():
            for img in page.get("images", []):
                t = img.get("title", "")
                # Skip icons, logos, flags, etc.
                name_lower = t.lower()
                if any(skip in name_lower for skip in ["flag", "icon", "logo", "sound", "svg", "wikimedia", "stub"]):
                    continue
                image_titles.append(t)

        # Resolve each image title to a URL
        if image_titles:
            params2 = {
                "action": "query",
                "format": "json",
                "titles": "|".join(image_titles[:10]),
                "prop": "imageinfo",
                "iiprop": "url|size|mime",
                "iiurlwidth": 1000,
            }
            resp2 = requests.get(WIKIPEDIA_API, params=params2, headers=HEADERS, timeout=20)
            resp2.raise_for_status()
            data2 = resp2.json()
            pages2 = data2.get("query", {}).get("pages", {})
            for page in pages2.values():
                info_list = page.get("imageinfo", [])
                if info_list:
                    info = info_list[0]
                    mime = info.get("mime", "")
                    if mime.startswith("image/jpeg") or mime.startswith("image/png"):
                        url = info.get("thumburl") or info.get("url")
                        if url:
                            results.append({
                                "title": page.get("title", ""),
                                "url": url,
                                "width": info.get("width", 0),
                                "height": info.get("height", 0),
                            })
        log.info("  Found {} images on Wikipedia article '{}'".format(len(results), article))
    except Exception as e:
        log.warning("Wikipedia article images failed for '{}': {}".format(article, e))
    return results


def search_wikimedia(designer_name: str, limit: int = 8) -> list:
    """Full-text search Wikimedia Commons for designer portraits."""
    terms = DESIGNER_SEARCH_TERMS.get(designer_name, [designer_name])
    results = []
    for term in terms:
        log.info("Searching Wikimedia for: {}".format(term))
        params = {
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrsearch": term,
            "gsrnamespace": "6",
            "gsrlimit": limit,
            "prop": "imageinfo",
            "iiprop": "url|size|mime",
            "iiurlwidth": 1000,
        }
        try:
            resp = requests.get(COMMONS_API, params=params, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            pages = data.get("query", {}).get("pages", {})
            for page in pages.values():
                info_list = page.get("imageinfo", [])
                if info_list:
                    info = info_list[0]
                    mime = info.get("mime", "")
                    if mime.startswith("image/"):
                        url = info.get("thumburl") or info.get("url")
                        if url:
                            results.append({
                                "title": page.get("title", ""),
                                "url": url,
                                "width": info.get("width", 0),
                                "height": info.get("height", 0),
                            })
        except Exception as e:
            log.warning("Search error for '{}': {}".format(term, e))
        time.sleep(0.5)
    return results


def download_image(url: str, output_path: Path) -> bool:
    """Download an image URL to a local JPEG file."""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (ChairsProject/1.0)"}
        req = Request(url, headers=headers)
        with urlopen(req, timeout=30) as response:
            data = response.read()
        img = Image.open(BytesIO(data))
        if img.mode in ("RGBA", "P", "LA"):
            bg = Image.new("RGB", img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None)
            img = bg
        elif img.mode != "RGB":
            img = img.convert("RGB")
        img.save(output_path, "JPEG", quality=92)
        log.info("  Saved -> {} ({} KB)".format(output_path.name, output_path.stat().st_size // 1024))
        return True
    except Exception as e:
        log.warning("  Download failed ({}...): {}".format(url[:60], e))
        return False


def collect_reference_images(designer_name: str, target_count: int = 4) -> List[Path]:
    """
    Collect reference portrait images of a designer.
    Tries known Wikimedia files first, then falls back to search.
    Returns list of local file paths.
    """
    ref_dir = REFS_DIR / designer_name.lower().replace(" ", "-")
    ref_dir.mkdir(parents=True, exist_ok=True)

    collected: List[Path] = []

    # Step 1: Try known filenames
    known = DESIGNER_KNOWN_FILES.get(designer_name, [])
    for i, filename in enumerate(known, start=1):
        out_path = ref_dir / "known-{:02d}.jpg".format(i)
        if out_path.exists() and out_path.stat().st_size > 10_000:
            log.info("  Using cached: {}".format(out_path.name))
            collected.append(out_path)
            continue
        url = fetch_wikimedia_file_url(filename)
        if url and download_image(url, out_path):
            collected.append(out_path)
        if len(collected) >= target_count:
            break

    # Step 2: Try Wikipedia article images
    if len(collected) < target_count:
        wiki_article = DESIGNER_WIKIPEDIA_ARTICLES.get(designer_name)
        if wiki_article:
            log.info("Checking Wikipedia article for images: {}".format(wiki_article))
            wiki_results = fetch_wikipedia_article_images(wiki_article)
            for result in wiki_results:
                if len(collected) >= target_count:
                    break
                if result["width"] < 150 or result["height"] < 150:
                    continue
                idx = len(collected) + 1
                out_path = ref_dir / "wiki-{:02d}.jpg".format(idx)
                if out_path.exists() and out_path.stat().st_size > 5_000:
                    log.info("  Using cached: {}".format(out_path.name))
                    collected.append(out_path)
                elif download_image(result["url"], out_path):
                    collected.append(out_path)

    # Step 3: Search Wikimedia Commons for more if needed
    if len(collected) < target_count:
        log.info("Have {}/{}, searching Wikimedia Commons…".format(len(collected), target_count))
        search_results = search_wikimedia(designer_name, limit=10)
        for result in search_results:
            if len(collected) >= target_count:
                break
            # Skip SVG and tiny images
            if result["width"] < 200 or result["height"] < 200:
                continue
            idx = len(collected) + 1
            out_path = ref_dir / "search-{:02d}.jpg".format(idx)
            if out_path.exists() and out_path.stat().st_size > 10_000:
                log.info("  Using cached: {}".format(out_path.name))
                collected.append(out_path)
            elif download_image(result["url"], out_path):
                collected.append(out_path)

    log.info(f"Collected {len(collected)} reference image(s) for {designer_name}")
    return collected


def generate_composite_portrait(
    designer_name: str,
    reference_paths: List[Path],
    api_key: Optional[str] = None,
    grayscale: bool = False,
) -> bytes:
    """
    Call Gemini with reference portraits and return PNG bytes of the composite.
    """
    if api_key is None:
        api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY is required.")

    try:
        from google import genai
        from google.genai import types
    except ImportError:
        raise RuntimeError("Install google-genai: pip install google-genai")

    prompt = (
        "Using the provided reference photographs as visual guides, create a high-quality "
        "photorealistic black-and-white portrait photograph of the Danish architect and designer "
        "{} (1902-1971). ".format(designer_name) +
        "The image should look like a genuine mid-century documentary photograph — "
        "sharp focus, fine grain, rich tonal range from deep blacks to clean whites, "
        "professional studio or natural light, neutral background. "
        "Match his actual likeness from the references: facial structure, silver-grey hair, "
        "serious but thoughtful expression, suit and tie. "
        "Output must be grayscale (black and white photography). "
        "Aspect ratio 3:4 (portrait orientation). "
        "No color, no text, no watermarks, no chair imagery — only the designer's likeness."
    )

    client = genai.Client(api_key=api_key)

    contents = [prompt]
    loaded = 0
    for path in reference_paths:
        try:
            img = Image.open(path)
            if img.mode not in ("RGB",):
                img = img.convert("RGB")
            contents.append(img)
            loaded += 1
            log.info("  Added reference: {} ({}x{})".format(path.name, img.size[0], img.size[1]))
        except Exception as e:
            log.warning("  Could not load {}: {}".format(path.name, e))

    if loaded == 0:
        raise RuntimeError("No reference images could be loaded for Gemini.")

    log.info("Sending {} reference(s) + prompt to Gemini...".format(loaded))

    response = client.models.generate_content(
        model="gemini-3.1-flash-image-preview",
        contents=contents,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
            image_config=types.ImageConfig(aspect_ratio="3:4"),
        ),
    )

    if not response or not response.parts:
        raise RuntimeError("Gemini returned no response parts.")

    pil_image = None
    for part in response.parts:
        if hasattr(part, "inline_data") and part.inline_data:
            try:
                img_bytes = part.inline_data.data
                if isinstance(img_bytes, str):
                    img_bytes = base64.b64decode(img_bytes)
                pil_image = Image.open(BytesIO(img_bytes))
                break
            except Exception as e:
                log.debug(f"inline_data extraction failed: {e}")
        if hasattr(part, "as_image"):
            try:
                genai_img = part.as_image()
                if genai_img:
                    if hasattr(genai_img, "_pil_image"):
                        pil_image = genai_img._pil_image
                    elif hasattr(genai_img, "to_pil"):
                        pil_image = genai_img.to_pil()
                    elif hasattr(genai_img, "_image_bytes"):
                        pil_image = Image.open(BytesIO(genai_img._image_bytes))
                    if pil_image:
                        break
            except Exception as e:
                log.debug(f"as_image() extraction failed: {e}")

    if pil_image is None:
        raise RuntimeError(
            "Could not extract image from Gemini response. "
            "Parts: {}".format([type(p).__name__ for p in response.parts])
        )

    if pil_image.mode not in ("RGB",):
        pil_image = pil_image.convert("RGB")

    if grayscale:
        pil_image = pil_image.convert("L").convert("RGB")  # grayscale stored as RGB JPEG

    buf = BytesIO()
    pil_image.save(buf, format="JPEG", quality=92)
    buf.seek(0)
    return buf.read()


def download_url_references(urls: List[str], designer_name: str) -> List[Path]:
    """Download a list of explicit reference URLs to local files."""
    ref_dir = REFS_DIR / designer_name.lower().replace(" ", "-")
    ref_dir.mkdir(parents=True, exist_ok=True)
    collected = []
    for i, url in enumerate(urls, start=1):
        ext = url.split("?")[0].rsplit(".", 1)[-1].lower()
        if ext not in ("jpg", "jpeg", "png", "webp"):
            ext = "jpg"
        out_path = ref_dir / "explicit-{:02d}.{}".format(i, ext)
        if out_path.exists() and out_path.stat().st_size > 5_000:
            log.info("  Using cached: {}".format(out_path.name))
            # Ensure it's a proper JPEG
            jpg_path = out_path.with_suffix(".jpg")
            if out_path.suffix.lower() != ".jpg":
                try:
                    img = Image.open(out_path).convert("RGB")
                    img.save(jpg_path, "JPEG", quality=92)
                    out_path = jpg_path
                except Exception:
                    pass
            collected.append(out_path)
            continue
        log.info("  Downloading reference {}: {}".format(i, url[:70]))
        if download_image(url, out_path.with_suffix(".jpg")):
            collected.append(out_path.with_suffix(".jpg"))
    return collected


def main():
    parser = argparse.ArgumentParser(description="Generate designer composite portrait via Gemini")
    parser.add_argument("--chair", default="swan-chair", help="Chair slug")
    parser.add_argument("--designer", default="Arne Jacobsen", help="Designer full name")
    parser.add_argument("--refs", type=int, default=4, help="Number of reference images to collect via Wikipedia/Commons")
    parser.add_argument("--reference-urls", help="Comma-separated explicit reference image URLs (skips auto-discovery)")
    parser.add_argument("--grayscale", action="store_true", help="Convert output to grayscale (black and white)")
    parser.add_argument("--dry-run", action="store_true", help="Download refs only, skip Gemini generation")
    args = parser.parse_args()

    output_path = IMAGES_DIR / "{}-designer.jpg".format(args.chair)

    log.info("=" * 60)
    log.info("Designer composite portrait: {}".format(args.designer))
    log.info("Chair: {}".format(args.chair))
    log.info("Output: {}".format(output_path))
    log.info("Grayscale: {}".format(args.grayscale))
    log.info("=" * 60)

    # Phase 1: Collect reference images
    if args.reference_urls:
        urls = [u.strip() for u in args.reference_urls.split(",") if u.strip()]
        log.info("\n[Phase 1] Downloading {} explicit reference URL(s)...".format(len(urls)))
        refs = download_url_references(urls, args.designer)
    else:
        log.info("\n[Phase 1] Collecting {}+ reference portraits via Wikipedia/Commons...".format(args.refs))
        refs = collect_reference_images(args.designer, target_count=args.refs)

    if len(refs) < 1:
        log.error("Could not collect any reference images. Aborting.")
        sys.exit(1)

    log.info("\nReference images collected ({}):".format(len(refs)))
    for p in refs:
        log.info("  {}".format(p))

    if args.dry_run:
        log.info("\n[dry-run] Skipping Gemini generation.")
        return

    if len(refs) < 3:
        log.warning("Only {} reference(s) found (wanted 3+). Proceeding anyway.".format(len(refs)))

    # Phase 2: Generate composite via Gemini
    log.info("\n[Phase 2] Generating {} portrait with Gemini...".format(
        "grayscale photographic" if args.grayscale else "photographic"
    ))
    try:
        jpg_bytes = generate_composite_portrait(args.designer, refs, grayscale=args.grayscale)
    except Exception as e:
        log.error("Gemini generation failed: {}".format(e))
        sys.exit(1)

    # Phase 3: Save output
    log.info("\n[Phase 3] Saving to {}...".format(output_path))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(jpg_bytes)
    size_kb = len(jpg_bytes) // 1024
    log.info("Saved {} KB -> {}".format(size_kb, output_path))
    log.info("\nDone! {}-designer.jpg replaced with Gemini composite portrait.".format(args.chair))


if __name__ == "__main__":
    main()
