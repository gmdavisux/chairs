# Image Slots Update - Summary

## What Changed

The image generation system now uses **four new slot types** instead of detail shots that hallucinate fake details.

### Old Slots (Deprecated)
- ❌ `detail-material` - Close-up of materials (hallucinated textures)
- ❌ `detail-structure` - Close-up of joinery (invented hardware)
- ❌ `detail-silhouette` - Profile view (now renamed)

### New Slots
- ✅ `hero` - Photorealistic museum view (unchanged)
- ✅ `silhouette` - Industrial design marker rendering
- ✅ `context` - Chair in period-appropriate interior setting
- ✅ `designer` - Archival portrait of designer (optional)

## Why the Change?

**Problem**: AI generates close-up detail shots with **invented structural details** - fake screws, non-existent joinery, wrong materials. This is historically inaccurate.

**Solution**: 
- **Silhouette rendering** = Abstract away details, show pure form
- **Context/lifestyle** = Focus on composition, not details
- **Designer portrait** = Use actual archival photos, no fabrication

## Configuration

```bash
# In .env:

# Generate all 4 new slot types
FURNITURE_IMAGE_MAX_PER_PAGE=4

# Generate hero + silhouette + context (skip designer)
FURNITURE_IMAGE_MAX_PER_PAGE=3

# Hero only (safest, no hallucinations)
FURNITURE_IMAGE_MAX_PER_PAGE=1
```

## Prompt Files

Create these in `public/images/generated-prompts/{slug}/`:

### Required
- `hero.txt` - Photorealistic chair view
- `silhouette.txt` - Marker rendering style
- `context.txt` - Interior/lifestyle setting

### Optional
- `designer.txt` - Designer portrait

See [docs/example-prompts-new-slots.md](example-prompts-new-slots.md) for examples.

## Migration Guide

### For New Projects
Just run `furniture_agent.py` - it will generate prompts using the new slot system.

### For Existing Projects (wassily-chair, barcelona-chair, etc.)

You have two options:

#### Option 1: Keep Existing Images
Do nothing. Old slot names are aliased for backward compatibility.

#### Option 2: Regenerate with New Slots

1. **Delete old prompt files:**
```bash
cd public/images/generated-prompts/wassily-chair/
rm detail-1-material.txt detail-2-structure.txt detail-3-silhouette.txt
```

2. **Create new prompt files:**
```bash
# Copy examples from docs/example-prompts-new-slots.md
# Or let the agent regenerate them
```

3. **Regenerate images:**
```bash
python generate_images_gemini.py wassily-chair --update-mdx
```

## Backwards Compatibility

Old slot names still work via aliases:
- `detail-silhouette` → `silhouette`
- `detail-context` → `context`

But `detail-material` and `detail-structure` are deprecated (use `hero` instead).

## Benefits

✅ No hallucinated details  
✅ Visual variety (photo, sketch, lifestyle, portrait)  
✅ Historical authenticity  
✅ Better storytelling  
✅ Flexible (skip designer if no reference)  

## Quick Start

```bash
# 1. Add Google API key
echo "GOOGLE_API_KEY=your_key" >> .env

# 2. Set image slots
echo "FURNITURE_IMAGE_MAX_PER_PAGE=3" >> .env  # hero + silhouette + context

# 3. Run agent
python furniture_agent.py

# Creates article + 3 images with new slot types
```

## Documentation

- [Image Slot Strategy](image-slot-strategy.md) - Detailed explanation
- [Example Prompts](example-prompts-new-slots.md) - Prompt templates for all slots
- [Google Gemini Integration](google-gemini-integration.md) - API setup
- [Hallucination Issues](hallucination-issues.md) - Why we changed
