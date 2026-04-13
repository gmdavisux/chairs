# Automated Gemini Workflow

This guide shows you three ways to work with Google Gemini for image generation, from fully automated to manual with helper scripts.

## Quick Start

### Option 1: Fully Automated (if you have API access)

```bash
# Install dependencies
pip install google-generativeai

# Add your API key to .env
echo "GOOGLE_API_KEY=your_key_here" >> .env

# Generate all images and update MDX
python generate_images.py wassily-chair --update-mdx
```

### Option 2: Semi-Automated (prepare batch for manual generation)

This is what you did manually, but automated:

**NEW: Enhanced AI Studio Prompt Generator** ⭐

```bash
# Generate prompts with multiple reference URLs for AI Studio
python generate_aistudio_prompts.py wassily-chair --output batch.txt

# This creates a formatted batch file with:
# - Each prompt optimized for AI Studio
# - Multiple reference URLs per slot (2-3 for best results)
# - Clear instructions for manual workflow
# - Track which images are already generated

# Then open the batch file and follow instructions
open batch.txt
```

**Original workflow (still works)**:

```bash
# Step 1: Prepare a batch file with prompts and references
python prepare_gemini_batch.py wassily-chair --simple --output gemini-batch.txt

# Step 2: Open the batch file and use it to generate images in AI Studio
#         Copy each prompt, paste into AI Studio, attach reference, generate, save as PNG

# Step 3: After saving all PNGs, update your MDX file automatically
python update_mdx_images.py wassily-chair
```

**Why the new tool is better**:
- Formats **multiple reference URLs** per slot (not just one)
- Shows which images already exist (✓) vs need generation (⚠️)
- Includes style guide integration
- Better organized output for manual workflow

### Option 3: Custom Prompts + References

When generated prompts don't work (like your detail images):

```bash
# Create custom simple prompts
cat > my-prompts.json << 'EOF'
{
  "hero": "Wassily Chair, chrome steel and black leather",
  "detail-material": "Close-up leather and steel connection",
  "detail-structure": "Bent tubular steel frame detail",
  "detail-silhouette": "Side profile showing cantilevered design"
}
EOF

# Create reference image mapping
cat > my-refs.json << 'EOF'
{
  "hero": "https://commons.wikimedia.org/.../ref-001.jpg",
  "detail-material": "https://commons.wikimedia.org/.../ref-002.jpg",
  "detail-structure": "https://commons.wikimedia.org/.../ref-001.jpg",
  "detail-silhouette": "https://commons.wikimedia.org/.../ref-002.jpg"
}
EOF

# Option A: Generate automatically
python generate_images.py wassily-chair \
  --custom-prompts my-prompts.json \
  --reference-images my-refs.json \
  --update-mdx

# Option B: Prepare for manual generation
python prepare_gemini_batch.py wassily-chair \
  --simple \
  --output batch.txt
# Then manually create images and run:
python update_mdx_images.py wassily-chair
```

## The Three Scripts

### 1. `generate_images.py` - Fully Automated

**What it does:**
- Reads prompts from `generated-prompts` folder or custom JSON
- Calls Google Gemini API to generate images
- Downloads images as PNGs
- Optionally updates MDX file

**Requirements:**
- Google API key in `.env`
- `google-generativeai` package installed

**Examples:**

```bash
# Basic: use existing prompts
python generate_images.py wassily-chair

# With custom prompts
python generate_images.py wassily-chair --custom-prompts simple.json

# With reference images
python generate_images.py wassily-chair --reference-images refs.json

# Generate only specific slots
python generate_images.py wassily-chair --slots hero detail-material

# Auto-update MDX after generation
python generate_images.py wassily-chair --update-mdx
```

### 2. `prepare_gemini_batch.py` - Batch Preparation Helper

**What it does:**
- Reads all prompts and reference images
- Creates a formatted document for manual copy-paste
- Shows which images already exist
- Simplifies prompts if requested

**Use when:**
- You prefer using Google AI Studio web interface
- You want to review each prompt before generating
- You want to tweak prompts on the fly

**Examples:**

```bash
# Create a batch file with simplified prompts
python prepare_gemini_batch.py wassily-chair --simple --output batch.txt

# Print to console
python prepare_gemini_batch.py wassily-chair --simple

# JSON output for programmatic use
python prepare_gemini_batch.py wassily-chair --json
```

**Output format:**
```
================================================================================
SLOT: HERO [⚠️  NEEDS GENERATION]
================================================================================

OUTPUT FILENAME:
  wassily-chair-hero.png

PROMPT:
--------------------------------------------------------------------------------
Wassily Chair, chrome steel and black leather, warm museum lighting
--------------------------------------------------------------------------------

SUGGESTED REFERENCE:
  https://commons.wikimedia.org/.../ref-001.jpg
```

### 3. `update_mdx_images.py` - MDX Update Helper

**What it does:**
- Checks which images exist
- Updates MDX frontmatter to use correct file extensions
- Shows what changed

**Use when:**
- After manually generating images
- After converting .jpg to .png
- When verifying MDX references are correct

**Examples:**

```bash
# Update to use PNG files
python update_mdx_images.py wassily-chair

# Preview changes without modifying
python update_mdx_images.py wassily-chair --dry-run

# Use different extension
python update_mdx_images.py wassily-chair --extension jpg
```

**Output:**
```
📄 Found MDX file: wassily-chair.mdx

📊 Image files with .png extension:
   ✓ Found: hero, detail-material, detail-structure, detail-silhouette

🔧 UPDATE: Updating MDX references...

  ✓ Hero image: /images/wassily-chair-hero.jpg → /images/wassily-chair-hero.png
  ✓ Image hero: /images/wassily-chair-hero.jpg → /images/wassily-chair-hero.png
  ✓ Image detail-material: /images/wassily-chair-detail-material.jpg → ...png
  
✅ MDX file updated successfully
```

## Your Workflow (Replicated)

Here's exactly what you did, but automated:

```bash
# 1. Prepare batch with simple prompts
python prepare_gemini_batch.py wassily-chair --simple --output batch.txt

# 2. Open batch.txt
open batch.txt

# 3. For each slot in the batch file:
#    - Copy the prompt
#    - Open Google AI Studio
#    - Paste prompt
#    - Attach suggested reference image (or pick different one)
#    - Generate image
#    - Download as PNG
#    - Save to public/images/wassily-chair-{slot}.png

# 4. After all images are saved, update MDX automatically
python update_mdx_images.py wassily-chair

# Done! 🎉
```

## Tips & Best Practices

### Prompt Simplification

Complex prompts with style guidance often confuse Gemini. Use `--simple` to strip them down:

**Complex (from FAL):**
> Photorealistic museum-catalog image of Wassily Chair by Marcel Breuer. Slot intent: hero. Marcel Breuer Wassily Chair (Model B3) from 1925, three-quarter view showing the iconic chrome-plated tubular steel frame with black leather straps forming the seat and backrest. Soft warm lighting at 2700K highlights the gleaming metal curves and rich leather texture. Clean minimal background with subtle era-appropriate architectural elements...

**Simple (better for Gemini):**
> Wassily Chair, three-quarter view, chrome tubular steel frame, black leather straps, warm lighting, clean background

### Reference Images

- Use different references for different detail shots
- Rotate between available images for variety
- Check the batch file for suggested reference mappings

### Image Formats

- Gemini generates PNGs by default ✓
- Scripts support PNG, JPG, JPEG, WEBP
- Use consistent format across all images

### Error Handling

If generation fails for some slots:

```bash
# Check which images exist
python update_mdx_images.py wassily-chair --dry-run

# Generate only missing slots
python generate_images.py wassily-chair \
  --slots detail-material detail-structure
```

## Examples

See these example files:
- `example-custom-prompts.json` - Simple prompt examples
- `example-reference-images.json` - Reference URL mappings
- `wassily-chair-fal-prompt.md` - Complete FAL prompts for comparison

## Troubleshooting

**"No prompts found"**
```bash
# Check prompts directory exists
ls public/images/generated-prompts/wassily-chair/
```

**"MDX file not found"**
```bash
# Check content directory
ls src/content/blog/wassily-chair.*
```

**"No images found"**
```bash
# Check images directory
ls public/images/wassily-chair-*
```

**API errors**
- Verify `GOOGLE_API_KEY` in `.env`
- Check API quotas at console.cloud.google.com
- Try `--simple` flag for shorter prompts
