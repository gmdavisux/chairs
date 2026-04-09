# Google Gemini Integration - Summary

## ✅ What's Been Added

Google Gemini (Imagen) is now integrated as a **primary image generation provider** in `furniture_agent.py`.

## Configuration

### Basic Setup

Add to your `.env`:
```bash
# Set Google as primary provider
FURNITURE_IMAGE_PROVIDER=google
GOOGLE_API_KEY=your_key_here

# Optional: Configure fallback chain
FURNITURE_IMAGE_FALLBACKS=google,fal,openai

# Optional: Generate only hero image to avoid detail hallucinations
FURNITURE_IMAGE_MAX_PER_PAGE=1
```

### Provider Fallback Chain

The script tries providers in order until one succeeds:

**Default fallback order:**
1. Google Gemini (if `GOOGLE_API_KEY` set)
2. FAL (if `FAL_KEY` set)
3. OpenAI (if `OPENAI_API_KEY` set and not placeholder)

**Custom fallback order:**
```bash
# Try FAL first, then Google, skip OpenAI
FURNITURE_IMAGE_FALLBACKS=fal,google
```

## How It Works

### When you run `furniture_agent.py`:

1. **Text generation**: Uses GitHub Models (GPT-4o, etc.)
2. **Prompt creation**: Generates image prompts
3. **Image generation**: 
   - Tries Google Gemini first (if configured)
   - Falls back to FAL if Google fails
   - Falls back to OpenAI if FAL fails
   - Skips image if all providers fail (continues with placeholders)

### Delayed Generation Option

To skip image generation entirely (useful for free tier limits):

```bash
# Set to 0 to skip images, only generate prompts
FURNITURE_IMAGE_MAX_PER_PAGE=0
```

Then generate images later manually:
```bash
python prepare_gemini_batch.py barcelona-chair --simple --output batch.txt
# Generate in AI Studio
python update_mdx_images.py barcelona-chair
```

## Addressing Hallucinations

Detail photos often contain **invented/fake details**. Solutions:

### Option 1: Hero Only
```bash
FURNITURE_IMAGE_MAX_PER_PAGE=1  # Only generate hero image
```

### Option 2: Manual Details
```bash
FURNITURE_IMAGE_MAX_PER_PAGE=1  # Generate hero
# Then manually add detail photos from reference collection
```

See [docs/hallucination-issues.md](hallucination-issues.md) for details.

## All Available Settings

```bash
# ── Primary Provider ────────────────────────────────────────
FURNITURE_IMAGE_PROVIDER=google    # google, fal, or openai

# ── Google Gemini ───────────────────────────────────────────
GOOGLE_API_KEY=your_key_here
GOOGLE_IMAGE_MODEL=imagen-3.0-generate-001

# ── FAL (FLUX) ──────────────────────────────────────────────
FAL_KEY=your_fal_key_here
FURNITURE_IMAGE_MODEL=fal-ai/flux/dev

# ── OpenAI ──────────────────────────────────────────────────
OPENAI_API_KEY=your_openai_key_here
OPENAI_IMAGE_MODEL=gpt-image-1

# ── Fallback & Control ──────────────────────────────────────
FURNITURE_IMAGE_FALLBACKS=google,fal,openai  # Comma-separated
FURNITURE_IMAGE_MAX_PER_PAGE=4               # 0=skip, 1=hero only, 4=all
FURNITURE_IMAGE_SIZE=1024x1024
FURNITURE_IMAGE_TIMEOUT_SECONDS=60
```

## Example Workflows

### Workflow 1: Full Automation (Hero Only)
```bash
# .env settings:
FURNITURE_IMAGE_PROVIDER=google
FURNITURE_IMAGE_MAX_PER_PAGE=1
GOOGLE_API_KEY=your_key

# Run:
python furniture_agent.py
# Creates article + hero image, skips details
```

### Workflow 2: Prompts Only, Generate Later
```bash
# .env settings:
FURNITURE_IMAGE_MAX_PER_PAGE=0

# Run:
python furniture_agent.py
# Creates article + prompts, no images

# Later, when ready:
python prepare_gemini_batch.py barcelona-chair --output batch.txt
# Generate manually in AI Studio
python update_mdx_images.py barcelona-chair
```

### Workflow 3: Google with FAL Fallback
```bash
# .env settings:
FURNITURE_IMAGE_PROVIDER=google
FURNITURE_IMAGE_FALLBACKS=google,fal
FURNITURE_IMAGE_MAX_PER_PAGE=4

# Run:
python furniture_agent.py
# Tries Google for all images, falls back to FAL if quota exceeded
```

## Testing

Test the integration:
```bash
# Test with a simple chair
FURNITURE_IMAGE_MAX_PER_PAGE=1 python furniture_agent.py

# Check logs for:
# "Generating hero with google (reference: ...)"
# "✓ Saved: .../barcelona-chair-hero.jpg"
```

## Free Tier Considerations

Google Gemini free tier has daily quotas:
- Generate images during off-peak times
- Use `FURNITURE_IMAGE_MAX_PER_PAGE=1` (hero only)
- Or use `FURNITURE_IMAGE_MAX_PER_PAGE=0` and batch-generate later

The fallback system ensures the script continues even if quota is exceeded.
