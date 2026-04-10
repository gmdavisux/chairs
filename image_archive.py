#!/usr/bin/env python3
"""
image_archive.py - Archive management for AI-generated images

Provides utilities to archive AI-generated images with timestamps and metadata
before copying them to their display locations. This prevents images from being
overwritten and maintains a history of all generated images.

Directory structure:
    public/images/generated/<slug>/
        YYYY-MM-DD-HHMMSS/
            hero.png
            sketch.png
            context.png
            designer.png
            metadata.json

Usage:
    from image_archive import archive_and_deploy_image
    
    # Save image to archive and deploy to display location
    archive_and_deploy_image(
        slug="wassily-chair",
        slot="hero",
        image_bytes=image_data,
        display_path=Path("/path/to/public/images/wassily-chair-hero.jpg"),
        metadata={
            "provider": "google",
            "model": "imagen-4.0",
            "prompt": "...",
        }
    )
"""

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

# Archive base directory
ROOT = Path(__file__).parent
ARCHIVE_BASE = ROOT / "public" / "images" / "generated"


def create_archive_directory(slug: str, timestamp: Optional[datetime] = None) -> Path:
    """
    Create a timestamped archive directory for a slug.
    
    Args:
        slug: The furniture piece slug (e.g., "wassily-chair")
        timestamp: Optional datetime for the archive (defaults to now)
    
    Returns:
        Path to the created archive directory
    """
    if timestamp is None:
        timestamp = datetime.now()
    
    timestamp_str = timestamp.strftime("%Y-%m-%d-%H%M%S")
    archive_dir = ARCHIVE_BASE / slug / timestamp_str
    archive_dir.mkdir(parents=True, exist_ok=True)
    
    log.info(f"Created archive directory: {archive_dir}")
    return archive_dir


def get_latest_archive_directory(slug: str) -> Optional[Path]:
    """
    Get the most recent archive directory for a slug.
    
    Args:
        slug: The furniture piece slug
    
    Returns:
        Path to the latest archive directory, or None if none exist
    """
    slug_dir = ARCHIVE_BASE / slug
    if not slug_dir.exists():
        return None
    
    # Get all timestamp directories (YYYY-MM-DD-HHMMSS format)
    archives = sorted([d for d in slug_dir.iterdir() if d.is_dir()], reverse=True)
    
    return archives[0] if archives else None


def list_archive_directories(slug: str) -> list[Path]:
    """
    List all archive directories for a slug, newest first.
    
    Args:
        slug: The furniture piece slug
    
    Returns:
        List of archive directory paths, sorted newest to oldest
    """
    slug_dir = ARCHIVE_BASE / slug
    if not slug_dir.exists():
        return []
    
    archives = sorted([d for d in slug_dir.iterdir() if d.is_dir()], reverse=True)
    return archives


def save_archive_metadata(archive_dir: Path, metadata: dict) -> None:
    """
    Save generation metadata to an archive directory.
    
    Args:
        archive_dir: Path to the archive directory
        metadata: Dictionary containing generation metadata
    """
    metadata_path = archive_dir / "metadata.json"
    
    # Add timestamp if not present
    if "timestamp" not in metadata:
        metadata["timestamp"] = datetime.now().isoformat()
    
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    log.debug(f"Saved archive metadata: {metadata_path}")


def archive_and_deploy_image(
    slug: str,
    slot: str,
    image_bytes: bytes,
    display_path: Path,
    metadata: Optional[dict] = None,
    archive_dir: Optional[Path] = None,
    extension: str = "png",
) -> dict:
    """
    Archive an AI-generated image and deploy it to its display location.
    
    This function:
    1. Creates an archive directory (or uses provided one)
    2. Saves the image to the archive with original quality
    3. Copies the image to the display location
    4. Updates archive metadata
    
    Args:
        slug: The furniture piece slug (e.g., "wassily-chair")
        slot: The image slot (hero, sketch, context, designer)
        image_bytes: The raw image data
        display_path: Final path where the image should be deployed
        metadata: Optional metadata about the generation (provider, model, prompt, etc.)
        archive_dir: Optional specific archive directory (defaults to new timestamped dir)
        extension: File extension for the archived image (default: png)
    
    Returns:
        Dictionary with archive information:
        {
            "archive_path": str,
            "display_path": str,
            "archive_dir": str,
            "size": int,
        }
    """
    # Create or use provided archive directory
    if archive_dir is None:
        archive_dir = create_archive_directory(slug)
    
    # Save to archive with original extension
    archive_filename = f"{slot}.{extension}"
    archive_path = archive_dir / archive_filename
    archive_path.write_bytes(image_bytes)
    
    log.info(f"Archived image: {archive_path} ({len(image_bytes)} bytes)")
    
    # Copy to display location
    display_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(archive_path, display_path)
    
    log.info(f"Deployed image: {display_path}")
    
    # Update archive metadata
    archive_metadata_path = archive_dir / "metadata.json"
    
    # Load existing metadata if present
    if archive_metadata_path.exists():
        with open(archive_metadata_path, "r", encoding="utf-8") as f:
            archive_metadata = json.load(f)
    else:
        archive_metadata = {
            "slug": slug,
            "timestamp": datetime.now().isoformat(),
            "images": [],
        }
    
    # Add this image's metadata
    image_metadata = {
        "slot": slot,
        "filename": archive_filename,
        "size": len(image_bytes),
        "deployed_to": str(display_path),
    }
    
    if metadata:
        image_metadata.update(metadata)
    
    # Update or append image metadata
    existing_idx = None
    for idx, img in enumerate(archive_metadata.get("images", [])):
        if img.get("slot") == slot:
            existing_idx = idx
            break
    
    if existing_idx is not None:
        archive_metadata["images"][existing_idx] = image_metadata
    else:
        archive_metadata.setdefault("images", []).append(image_metadata)
    
    save_archive_metadata(archive_dir, archive_metadata)
    
    return {
        "archive_path": str(archive_path),
        "display_path": str(display_path),
        "archive_dir": str(archive_dir),
        "size": len(image_bytes),
    }


def archive_existing_image(
    slug: str,
    slot: str,
    source_path: Path,
    metadata: Optional[dict] = None,
    archive_dir: Optional[Path] = None,
) -> Optional[dict]:
    """
    Archive an existing image file without deploying.
    
    Useful for backing up images before regeneration.
    
    Args:
        slug: The furniture piece slug
        slot: The image slot
        source_path: Path to the existing image file
        metadata: Optional metadata to store
        archive_dir: Optional specific archive directory
    
    Returns:
        Dictionary with archive information, or None if source doesn't exist
    """
    if not source_path.exists():
        log.warning(f"Source image not found for archival: {source_path}")
        return None
    
    image_bytes = source_path.read_bytes()
    extension = source_path.suffix.lstrip(".")
    
    # Create or use provided archive directory
    if archive_dir is None:
        archive_dir = create_archive_directory(slug)
    
    archive_filename = f"{slot}.{extension}"
    archive_path = archive_dir / archive_filename
    archive_path.write_bytes(image_bytes)
    
    log.info(f"Archived existing image: {archive_path} ({len(image_bytes)} bytes)")
    
    # Update metadata
    archive_metadata_path = archive_dir / "metadata.json"
    
    if archive_metadata_path.exists():
        with open(archive_metadata_path, "r", encoding="utf-8") as f:
            archive_metadata = json.load(f)
    else:
        archive_metadata = {
            "slug": slug,
            "timestamp": datetime.now().isoformat(),
            "images": [],
        }
    
    image_metadata = {
        "slot": slot,
        "filename": archive_filename,
        "size": len(image_bytes),
        "source": str(source_path),
        "archived_only": True,
    }
    
    if metadata:
        image_metadata.update(metadata)
    
    archive_metadata.setdefault("images", []).append(image_metadata)
    save_archive_metadata(archive_dir, archive_metadata)
    
    return {
        "archive_path": str(archive_path),
        "archive_dir": str(archive_dir),
        "size": len(image_bytes),
    }
