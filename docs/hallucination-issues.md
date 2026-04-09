# Image Generation: Hallucination Issues

## Problem: Detail Photos Create Fake Details

AI image generators (particularly for detail shots) tend to **hallucinate non-existent details** when asked to create close-ups of furniture:

- Invented joinery that doesn't match the actual chair
- Fabricated hardware, screws, or fasteners
- Wrong materials or finishes
- Made-up structural details

This is especially problematic for historical accuracy in a furniture archive.

## Why This Happens

Detail prompts are very specific but AIs don't have fine-grained knowledge of exact construction techniques. When asked for "close-up of leather strap attachment hardware," the AI invents plausible-looking but inaccurate details.

## Solutions

### Option 1: Skip Detail Images (Generate Hero Only)

Add to `.env`:
```bash
# Only generate hero image (1), skip 3 detail shots
FURNITURE_IMAGE_MAX_PER_PAGE=1
```

This generates:
- ✅ Hero image (full chair view - harder to hallucinate)
- ❌ Skip detail-material
- ❌ Skip detail-structure  
- ❌ Skip detail-silhouette

### Option 2: Manual Detail Photos

```bash
# Generate hero automatically, add details manually later
FURNITURE_IMAGE_MAX_PER_PAGE=1
```

Then manually:
1. Generate hero with script
2. For details: Use actual reference photos or generate manually with very simple prompts
3. Update MDX with: `python update_mdx_images.py <slug>`

### Option 3: Very Simple Detail Prompts

Create simplified prompts that don't ask for specific structural details:

**Bad (causes hallucination):**
> "Close-up of leather strap attachment hardware showing screws and fastening method"

**Better:**
> "Close-up of black leather and chrome steel on Wassily Chair"

Use `prepare_gemini_batch.py --simple` to auto-simplify prompts.

### Option 4: Use Reference Photos Directly

For detail shots, using actual museum/archive photographs is more historically accurate than AI-generated images anyway.

## Recommended Workflow

For maximum historical accuracy:

1. **Hero image**: Generate with AI (gets overall form correct)
2. **Detail images**: Use actual reference photos from Wikimedia/museums
3. **Update MDX** with proper attribution

```bash
# Generate only hero
FURNITURE_IMAGE_MAX_PER_PAGE=1 python furniture_agent.py

# Then manually add detail photos from reference collection
```

## Settings Summary

```bash
# Generate all 4 images (risk of hallucinations in details)
FURNITURE_IMAGE_MAX_PER_PAGE=4

# Generate only hero (safe, no hallucinated details)
FURNITURE_IMAGE_MAX_PER_PAGE=1

# Skip all image generation (prompts only)
FURNITURE_IMAGE_MAX_PER_PAGE=0
```
