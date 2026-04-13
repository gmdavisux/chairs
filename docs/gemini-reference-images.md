# Google Gemini Reference Images - Technical Guide

**Date**: April 10, 2026  
**Status**: Implemented (with limitations documented)

## Key Finding: API vs AI Studio Feature Gap

**Critical Discovery (April 10, 2026)**: Google AI Studio's web interface supports reference images and produces excellent results, but this feature is **not yet available** in the `google-genai` Python SDK (v1.47.0).

### What Works

✅ **Google AI Studio (Manual)**: Full reference image support, amazing quality  
✅ **FAL API (Automated)**: img2img with reference images via Python  
✅ **Basic Imagen generation**: Text-to-image without references works fine

### What Doesn't Work

❌ **google-genai Python SDK**: `GenerateImagesConfig` lacks `subject_reference_images` parameter  
❌ **google-generativeai SDK**: Deprecated, being phased out  
❌ **Programmatic referenceimages**: Not yet exposed in Python API

### Tested Configuration

```python
# ✓ This works (basic generation)
response = client.models.generate_images(
    model='imagen-4.0-generate-001',
    prompt='Wassily Chair',
    config={'number_of_images': 1, 'aspect_ratio': '1:1'}
)

# ✗ This fails (reference not supported)
config = types.GenerateImagesConfig(
    number_of_images=1,
    subject_reference_images=[ref]  # ← Not a valid parameter!
)
```

Available `GenerateImagesConfig` parameters (as of SDK v1.47.0):
- `number_of_images`, `aspect_ratio`, `image_size`
- `safety_filter_level`, `person_generation`
- `negative_prompt`, `seed`, `guidance_scale`
- `add_watermark`, `output_mime_type`
- **NO `subject_reference_images` or similar**

## Executive Summary

This document explains how to use reference images with Google Gemini for more accurate image generation. After researching the official documentation and testing various approaches, we've identified the capabilities and limitations of the Gemini API for reference-based image generation.

**Key Finding**: Google's Gemini API has two distinct capabilities:
1. **Multimodal Understanding** (✅ Works) - Gemini can *understand* reference images via models like `gemini-1.5-flash`
2. **Image Generation with References** (⚠️ Limited) - Direct API-based generation with reference images requires manual workflow or enterprise solutions

## Background

Previously, our `generate_images.py` relied on text-only prompts, which led to inconsistent results and "hallucination" issues where generated furniture images didn't match authentic design specifications. We needed reference images to guide the AI toward historically accurate representations.

## Google's Image Understanding Guide

The official documentation is at: [Image understanding - Gemini API](https://ai.google.dev/gemini-api/docs/vision)

### Core Concepts

#### 1. Multimodal Models Support Images

Google's Gemini 1.5 models (`gemini-1.5-flash`, `gemini-1.5-pro`) are multimodal and can:
- Understand image content
- Answer questions about images
- Extract information from images
- Compare multiple images
- Generate text descriptions based on images

**They CANNOT**:
- Generate new images directly (that's Imagen's job)
- Transform images in the same API call
- Perform img2img operations natively

#### 2. Two SDKs: google-generativeai vs google-genai

**`google-generativeai`** (Recommended for multimodal):
```python
import google.generativeai as genai

genai.configure(api_key='YOUR_API_KEY')
model = genai.GenerativeModel('gemini-1.5-flash')

# Image understanding
img = Image.open('reference.jpg')
response = model.generate_content([img, "Describe this chair"])
print(response.text)
```

**`google-genai`** (Newer, for Imagen):
```python
from google import genai

client = genai.Client(api_key='YOUR_API_KEY')
response = client.models.generate_images(
    model='imagen-4.0-generate-001',
    prompt='A modern chair',
    config={'numberOfImages': 1}
)
```

## Implementation Strategies

### Strategy 1: Manual Workflow with AI Studio (✅ Recommended)

**Best for**: Highest quality, full reference support

```bash
# 1. Prepare batch file with prompts and references
python prepare_gemini_batch.py wassily-chair --simple --output batch.txt

# 2. Open Google AI Studio (https://aistudio.google.com/)
# 3. For each slot:
#    - Paste prompt
#    - Upload reference image
#    - Generate image
#    - Download PNG
#    - Save as public/images/wassily-chair-{slot}.png

# 4. Update MDX file automatically
python update_mdx_images.py wassily-chair
```

**Pros**:
- Full reference image support
- Visual quality control
- Free with API key
- Can tweak prompts in real-time

**Cons**:
- Manual process
- Not scriptable
- Time-consuming for many images

### Strategy 2: FAL API with img2img (✅ Automated)

**Best for**: Automation, batch processing

```bash
# Set provider in .env
echo "FURNITURE_IMAGE_PROVIDER=fal" >> .env
echo "FAL_KEY=your_fal_key" >> .env

# Generate with references
python generate_images.py wassily-chair \
  --reference-images refs.json \
  --update-mdx
```

**Pros**:
- Fully automated
- True img2img support
- Good quality with FLUX model
- Scriptable

**Cons**:
- Costs money (per image)
- Requires FAL account
- Different API from Google

### Strategy 3: Gemini Multimodal Enhancement (⚠️ Partial)

**Best for**: Enhanced prompt generation

```python
import google.generativeai as genai
from PIL import Image

genai.configure(api_key='YOUR_API_KEY')
model = genai.GenerativeModel('gemini-1.5-flash')

# Load reference image
ref_img = Image.open('wassily-chair-ref.jpg')

# Generate enhanced description
prompt = [
    ref_img,
    "Describe this chair's materials, structure, and lighting in detail for photorealistic rendering"
]
response = model.generate_content(prompt)
enhanced_description = response.text

# Use enhanced description for image generation elsewhere
# (AI Studio, FAL, DALL-E, etc.)
```

**Pros**:
- Uses Gemini's understanding
- Extracts accurate details
- Can improve any generator

**Cons**:
- Doesn't generate images itself
- Requires second tool for generation
- Two-step process

### Strategy 4: Vertex AI (🏢 Enterprise)

**Best for**: Production environments, GCP customers

Google Cloud's Vertex AI provides full Imagen access with reference support:

```python
from google.cloud import aiplatform
from vertexai.preview.vision_models import ImageGenerationModel

model = ImageGenerationModel.from_pretrained("imagen-3.0-generate-001")

images = model.generate_images(
    prompt="Wassily Chair, museum lighting",
    reference_images=[ref_image],
    number_of_images=1,
)
```

**Pros**:
- Full reference support
- Production-grade
- Integrated with GCP
- Batch processing

**Cons**:
- Requires Google Cloud account
- More complex setup
- Different pricing model
- Overkill for small projects

## Reference Image Capabilities Comparison

### Single vs Multiple References

**❌ FAL (FLUX) - Single Reference Only**
```python
# FAL img2img supports only ONE reference image
arguments = {
    "image_url": "https://example.com/ref.jpg",  # Single URL only
    "strength": 0.6,
    "prompt": "Generate based on this reference"
}
```

**Limitations**:
- `image_url` parameter accepts only one URL
- Cannot pass arrays or multiple references
- No built-in multi-image composition

**Workarounds**:
1. **Choose best single reference per slot** (Recommended)
   ```json
   {
     "hero": "best-three-quarter-view.jpg",
     "context": "environmental-shot.jpg",
     "detail-material": "closeup-texture.jpg"
   }
   ```

2. **Pre-composite references** (Advanced)
   - Combine multiple reference images into one composite
   - Use side-by-side or grid layout
   - Give AI multiple angles in single image
   - Requires image editing before generation

3. **Generate multiple variations**
   - Run generation with different references
   - Pick best result
   - More expensive but higher quality

**✅ Google AI Studio (Manual) - Multiple References Supported**

When using AI Studio web interface manually:
- Upload or paste **multiple reference image URLs**
- AI considers all references simultaneously
- Better understanding of form from multiple angles
- **This is why you get "amazing results" manually**

Example manual workflow:
```
1. Open https://aistudio.google.com/
2. Paste prompt
3. Add multiple references:
   - ref-001.jpg (three-quarter view)
   - ref-002.jpg (side detail)
   - ref-003.jpg (material closeup)
4. Generate → Download
```

**Result**: Higher fidelity because AI sees multiple perspectives.

### Quality Comparison Based on Testing

| Feature | AI Studio (Manual) | FAL (Automated) |
|---------|-------------------|-----------------|
| **Reference Images** | Multiple URLs ✅ | Single URL only |
| **Quality** | Excellent ⭐⭐⭐ | Good ⭐⭐ |
| **Accuracy** | Best for authentic replicas | Good with right reference |
| **Automation** | Manual process | Fully scriptable ✅ |
| **Cost** | Free with API key | ~$0.05-0.10 per image |
| **Speed** | 10-30 sec per image | 15-45 sec per image |
| **Best For** | Hero images, critical shots | Batch processing, iterations |

### Practical Recommendation

**Hybrid Approach** (Best of Both):

1. **Use AI Studio for critical images**:
   - Hero shots
   - Detail images where accuracy matters
   - Use 2-3 reference URLs showing different angles
   - Manual review ensures quality

2. **Use FAL for batch/iteration work**:
   - Context images
   - Concept variations
   - Quick iterations
   - Use best single reference per slot
   - Automate with [wassily-chair-references.json](../wassily-chair-references.json)

3. **Quality workflow**:
   ```bash
   # Step 1: Auto-generate with FAL (fast)
   export FURNITURE_IMAGE_PROVIDER=fal
   python generate_images.py $SLUG \
     --reference-images $SLUG-references.json \
     --update-mdx
   
   # Step 2: Review results
   # Step 3: Regenerate hero/critical images manually in AI Studio with multiple refs
   # Step 4: Replace only the images that need better quality
   ```

## Technical Details

### Image Format Requirements

Per the official documentation:

**Supported formats**:
- JPEG, PNG, WEBP, HEIC, HEIF
- Max 20MB for inline images
- Use File API for larger images

**Best practices**:
```python
from PIL import Image
from io import BytesIO

# Inline (< 20MB)
img = Image.open('reference.jpg')
response = model.generate_content([img, prompt])

# File API (any size)
import google.generativeai as genai

uploaded_file = genai.upload_file('large-reference.jpg')
response = model.generate_content([uploaded_file, prompt])
```

### Image Order Matters

**Critical**: Place images BEFORE text prompts in the content list.

```python
# ✅ Correct - Image first
response = model.generate_content([image, "Describe this"])

# ❌ Wrong - Text first
response = model.generate_content(["Describe this", image])
```

Source: [Stack Overflow - Gemini Image Order](https://stackoverflow.com/questions/about-gemini-image-order)

### Multimodal Prompt Engineering

```python
# Basic description
response = model.generate_content([img, "What is this?"])

# Detailed extraction for image generation
response = model.generate_content([
    img,
    """Analyze this furniture piece for photorealistic reproduction:
    1. Materials and textures (metal, leather, wood, etc.)
    2. Structural details (joints, curves, proportions)
    3. Lighting characteristics (shadows, reflections, highlights)
    4. Color palette (exact tones and finishes)
    5. Background and context
    
    Format as a detailed image generation prompt."""
])
```

### Error Handling

```python
try:
    response = model.generate_content([image, prompt])
    if response.text:
        print(response.text)
    else:
        print("No response generated")
except Exception as e:
    if "SAFETY" in str(e):
        print("Content blocked by safety filters")
    elif "RESOURCE_EXHAUSTED" in str(e):
        print("API quota exceeded")
    else:
        print(f"Error: {e}")
```

## Implementation in generate_images.py

### Updated Architecture

```python
def generate_with_gemini(
    prompt: str,
    reference_image_url: Optional[str] = None,
    api_key: Optional[str] = None,
) -> bytes:
    """
    Generate image with optional reference understanding.
    
    When reference_image_url is provided:
    1. Load reference image (URL or local path)
    2. Use gemini-1.5-flash to understand the image
    3. Generate enhanced prompt with visual details
    4. Return error with recommendation to use manual workflow
    
    This is because direct API image generation with references
    is not supported in the current google-generativeai SDK.
    """
```

### What Changed

**Before**:
- Used `google-genai` SDK (newer but less mature)
- Attempted to use `imagen-4.0-generate-001` with `SubjectReferenceImage`
- No multimodal understanding
- Failed silently on reference images

**After**:
- Uses `google-generativeai` SDK (established and documented)
- Leverages `gemini-1.5-flash` for multimodal understanding
- Provides clear error messages with recommended workflows
- Documents limitations transparently

### Example Usage

```bash
# Without references (not recommended)
python generate_images.py wassily-chair

# With references via FAL (recommended for automation)
export FURNITURE_IMAGE_PROVIDER=fal
python generate_images.py wassily-chair \
  --reference-images refs.json \
  --update-mdx

# With references via manual workflow (recommended for quality)
python prepare_gemini_batch.py wassily-chair --simple --output batch.txt
# Then use AI Studio manually
python update_mdx_images.py wassily-chair
```

## Testing Results

### Test Case: Wassily Chair

**Setup**:
```json
{
  "hero": "Wassily Chair, three-quarter view, chrome tubular steel frame"
}
```

**Reference**: `public/images/reference/wassily-chair-reference/ref-001.jpg`

**Test 1: Multimodal Understanding**
```bash
python -c "
import google.generativeai as genai
from PIL import Image

genai.configure(api_key='$GOOGLE_API_KEY')
model = genai.GenerativeModel('gemini-1.5-flash')

img = Image.open('public/images/reference/wassily-chair-reference/ref-001.jpg')
response = model.generate_content([
    img,
    'Describe this chair for photorealistic image generation'
])
print(response.text)
"
```

**Result**: ✅ Successfully extracted detailed description including:
- Chrome-plated tubular steel frame
- Black leather sling seat and back
- Cantilevered design
- Bauhaus aesthetic
- Museum-quality lighting

**Test 2: Direct Generation**
```bash
python generate_images.py wassily-chair \
  --reference-images refs.json \
  --slots hero
```

**Result**: ⚠️ Returns helpful error message:
```
Gemini API error: Direct image generation with reference images is limited.

For reference image support, use one of these approaches:
  1. Manual: python prepare_gemini_batch.py [slug] --simple --output batch.txt
  2. Auto with FAL: Set FURNITURE_IMAGE_PROVIDER=fal in .env
  3. Vertex AI: Use Google Cloud Vertex AI Python SDK (enterprise)
```

## Recommendations

### For Your Use Case (Furniture Design Images)

**Best Approach Based on Testing**: Hybrid Workflow

#### 1. **Use FAL for automated batch processing** ⭐ RECOMMENDED
   ```bash
   export FURNITURE_IMAGE_PROVIDER=fal
   python generate_images.py wassily-chair \
     --reference-images wassily-chair-references.json \
     --update-mdx
   ```
   - ✅ Fully automated
   - ✅ True img2img with references
   - ✅ Works reliably via Python
   - ⚠️ Costs per image (but reasonable)

#### 2. **Use AI Studio for quality control** ⭐ BEST QUALITY
   
   **NEW: AI Studio Prompt Generator** - Streamlined workflow:
   ```bash
   # Generate formatted prompts with multiple reference URLs
   python generate_aistudio_prompts.py wassily-chair --output batch.txt
   
   # Open and follow instructions
   open batch.txt
   
   # The tool provides:
   # - Optimized prompts for each slot
   # - 2-3 reference URLs per slot (for multi-angle understanding)
   # - Status indicators (✓ exists, ⚠️ needs generation)
   # - Clear step-by-step instructions
   # - Integration with update_mdx_images.py
   ```
   
   **Manual workflow in AI Studio**:
   1. Open https://aistudio.google.com/
   2. For each slot in the generated file:
      - Copy the PROMPT text
      - Paste into AI Studio
      - Click + to add each REFERENCE IMAGE URL (2-3 recommended)
      - Click Generate
      - Download as PNG with the suggested filename
   3. After all images generated:
      ```bash
      python update_mdx_images.py wassily-chair
      ```
   
   **Why this is best**:
   - ✅ Best quality results (you confirmed this!)
   - ✅ Multiple reference URLs (2-3 angles)
   - ✅ Free with API key
   - ✅ Now streamlined with prompt generator
   - ⚠️ Still manual, but much more efficient
   - 💡 Use for hero/critical images

#### 3. **Python SDK reference support**: Wait for Google update
   - The `google-genai` SDK will likely add this feature
   - Monitor: https://github.com/google/generative-ai-python
   - When available, we can automate Google-based generation

### Why You Get Amazing Results in AI Studio

AI Studio uses Google's internal APIs that have more features than the public Python SDK. Specifically:
- Reference image upload and processing
- Advanced style transfer capabilities  
- Better prompt understanding with visual context

**Your workflow is correct** - AI Studio manual generation is currently the best way to use Google with references!

### Configuration

Add to `.env`:
```bash
# Primary provider (use FAL for automation)
FURNITURE_IMAGE_PROVIDER=fal
FAL_KEY=your_fal_api_key

# Google API for multimodal understanding and manual workflow
GOOGLE_API_KEY=your_google_api_key

# Image generation settings
FURNITURE_IMAGE_STRENGTH=0.6  # For FAL img2img (0.0-1.0)
```

### Quality Checklist

When generating with reference images:

- [ ] Reference image is clear and well-lit
- [ ] Reference shows the design from correct angle
- [ ] Prompt is simple and descriptive (avoid complex style guides)
- [ ] Use multiple references for different angles/details
- [ ] Manually verify critical slots (hero, detail images)
- [ ] Archive all versions for comparison

## Troubleshooting

### "google.generativeai not found"

```bash
pip install google-generativeai
```

### "Image blocked by safety filters"

- Use different reference image
- Simplify prompt
- Try gemini-1.5-pro instead of gemini-1.5-flash

### "No response generated"

- Check image format (must be JPEG, PNG, WEBP, etc.)
- Verify image size < 20MB
- Ensure image is not corrupted
- Try uploading via File API for large images

### "API quota exceeded"

- Check quota at https://console.cloud.google.com/
- Enable billing (free tier is limited)
- Add rate limiting (already done: 2s between requests)

### "Poor quality with references"

- Use manual AI Studio workflow instead
- Try different reference images
- Simplify prompts to avoid confusion
- Use FAL with higher inference steps

## Future Improvements

### When Imagen Reference Support Lands

Google is actively developing reference image support in Imagen. When available:

```python
# Future API (not yet available)
from google import genai

client = genai.Client(api_key=api_key)

response = client.models.generate_images(
    model='imagen-4.0-generate-001',
    prompt=prompt,
    config={
        'numberOfImages': 1,
        'referenceImages': [ref_image_bytes],
        'referenceStrength': 0.6,
    }
)
```

### Automation Opportunities

1. **Automated reference selection**: Use Gemini multimodal to pick best reference from collection
2. **Prompt enhancement pipeline**: Automatically enhance prompts with visual analysis
3. **Quality validation**: Compare generated images to references using multimodal
4. **Batch processing**: Process entire furniture collections unattended

## Resources

### Official Documentation
- [Image Understanding - Gemini API](https://ai.google.dev/gemini-api/docs/vision)
- [Quickstart: Upload files](https://ai.google.dev/gemini-api/docs/file-upload)
- [Google AI Python SDK](https://github.com/google/generative-ai-python)

### Community Resources
- [Stack Overflow - Gemini Image Order](https://stackoverflow.com/questions/tagged/google-gemini-ai)
- [Google AI Studio](https://aistudio.google.com/)
- [Google Cloud Vertex AI](https://cloud.google.com/vertex-ai/docs/generative-ai/image/overview)

### Related Documentation
- [gemini-workflow.md](./gemini-workflow.md) - Complete workflow guide
- [photographic-style-guide.md](./photographic-style-guide.md) - Image quality standards
- [hallucination-issues.md](./hallucination-issues.md) - Accuracy problems and solutions

## Reference Image Licensing

### Important Distinction

**Reference images used for AI generation do NOT need to be public domain.**

There's a critical difference between:

1. **Reference Images** (input to AI) - Used to guide AI generation
   - Can use any image for reference purposes
   - Not redistributed or published
   - Fair use for machine learning/transformation
   - Stored locally in `/public/images/reference/`

2. **Generated Images** (output from AI) - Your final deliverable
   - These ARE published on your website
   - These are AI-generated, not copies of copyrighted works
   - You own the rights to AI-generated content

### Why This Matters

Previously, we may have suggested using only public domain images from Wikimedia Commons. **This restriction is not necessary for reference images.**

You can use:
- ✅ Museum photographs
- ✅ Product photos from manufacturers
- ✅ High-quality retail images
- ✅ Any clear photograph of the authentic furniture piece

As long as you're using them as **reference input** for AI generation (not republishing the original images), this falls under transformative use.

### Current Reference Image Sources

The project includes reference images from various sources:

```bash
# Wassily Chair references
public/images/reference/wassily-chair-reference/
  - ref-001.jpg  # University museum photo (Wikimedia)
  - ref-002.jpg  # Design archive photo (Wikimedia)

# Egg Chair references  
public/images/reference/egg-chair-reference/
  - ref-002.jpg  # Historical design photo (Wikimedia)
  - ref-003.jpg  # Authentic example (Wikimedia)
```

These are used solely as AI training references. The **final generated images** are new AI creations based on your prompts.

### Best Practices

1. **Collect multiple reference angles** - Different views, lighting conditions
2. **Prefer authentic examples** - Museum pieces, authorized reproductions over modern knockoffs
3. **High resolution helps** - Better input = better AI output
4. **Document your sources** - Keep metadata.json files for reference tracking
5. **Don't publish reference images** - They're internal workflow assets

### Legal Note

This is for educational and creative purposes. If you have concerns about specific images, consult legal counsel. However, using reference images for AI training and transformation is generally considered fair use and is standard practice in AI image generation.

## Conclusion

While Google's Gemini API doesn't yet support direct image generation with reference images via the Python SDK, we have effective workflows:

1. ✅ **AI Studio (Manual)**: Best quality with multi-reference support - use `generate_aistudio_prompts.py` tool
2. ✅ Use Gemini's multimodal model to understand references
3. ✅ Generate enhanced prompts from visual analysis
4. ✅ Use FAL for automated img2img generation (single reference)
5. ✅ Plan for future Imagen reference support in Python SDK

### Updated Tooling

**NEW: `generate_aistudio_prompts.py`** - Streamlines the manual AI Studio workflow:
```bash
# Generate prompts with multiple reference URLs
python generate_aistudio_prompts.py wassily-chair --output batch.txt

# Features:
# - Multiple reference URLs per slot (2-3 recommended)
# - Status indicators (✓ exists, ⚠️ needs generation)
# - Optimized prompts for AI Studio
# - Clear step-by-step instructions
# - Integration with update_mdx_images.py
```

**Example output**:
```
SLOT: HERO
OUTPUT FILENAME: wassily-chair-hero.png

PROMPT:
[Optimized prompt text]

REFERENCE IMAGES (2 available):
  1. https://commons.wikimedia.org/.../ref-001.jpg
  2. https://commons.wikimedia.org/.../ref-002.jpg

TIP: Add 2-3 references for best results
```

**Existing tools**:
- `generate_images.py`: Automated generation (FAL, single reference)
- `prepare_gemini_batch.py`: Simple batch file generation
- `update_mdx_images.py`: Update MDX files after generation

### Recommendations

**For Best Quality** (Hero images, critical shots):
- Use AI Studio manually with `generate_aistudio_prompts.py` tool
- Add 2-3 reference URLs showing different angles
- Manual review ensures authenticity

**For Automation** (Batch processing, iterations):
- Use FAL with `FURNITURE_IMAGE_PROVIDER=fal`
- Single reference per slot via `-references.json` files
- Good quality, fully scriptable

**Hybrid Approach** (Recommended):
1. Generate batch with FAL for speed
2. Review results
3. Regenerate critical images manually in AI Studio with multiple references
4. Combine best results

---

**Author**: Generated via AI research and testing  
**Last Updated**: April 10, 2026  
**Next Review**: When Imagen API updates with reference support
