# Photographic Style Guide - Classic Furniture Archives

## Intent

A single, consistent visual language for generated and normalized images that feels museum-caliber, warm, and historically faithful.

## Core Requirements

### Lighting
- Soft, diffused warm illumination at approximately 2700-3000 K.
- Gentle highlights with well-defined but not harsh shadows.
- Fuller tonal range utilizing both shadow detail and highlight clarity.
- Avoid cool daylight, fluorescent cast, and artificial dramatic high-contrast styling.

### Color and Mood
- Restrained warmth and natural color rendering.
- Rich contrast with full tonal range from true blacks to clean whites.
- Preserve shadow detail and highlight texture to enhance material depth.
- No artificial oversaturation, synthetic HDR appearance, or overprocessed edges.

### Composition
- Furniture is the clear focal subject.
- Target subject occupancy: roughly 60-75 percent of frame.
- Preferred viewpoint: three-quarter or slight low-angle with minimal distortion.
- Keep clean negative space and avoid visual crowding.

### Environmental Context
- Use only when needed to anchor period authenticity.
- Context should be minimal, architectural, and subordinate to object readability.
- Limit context descriptions to one clause and no more than three structural features.

### Forbidden Elements
- People
- Decorative clutter and props (rugs, lamps, books, artwork, vases)
- Text overlays, logos, and watermarks
- Cartoonish or painterly rendering styles

## Historical Fidelity Rules

Generated or transformed images must preserve:
- signature silhouette and geometry
- plausible materials and finish
- visible joinery/hardware logic
- era-appropriate setting

Reject outputs that violate any of the above.

## Master Prompt Template

Use this structure for text-to-image generation:

Photorealistic museum-catalog photograph of [precise furniture description with designer, model, materials, colorway, and viewing angle]. The scene is lit with soft, diffused warm incandescent light at dusk (about 2800 K), producing gentle amber warmth with well-defined natural shadows and rich tonal depth. [Optional minimal context clause with era-appropriate architecture and no more than three structural features.] Full tonal range from deep shadows to clean highlights; shallow depth of field with sharp texture detail on material grain, stitching, and hardware; enhanced contrast preserving shadow and highlight detail; natural color grading; clean negative space; zero extraneous props or distractions.

## Negative Prompt Baseline

harsh shadows, cool lighting, daylight, fluorescent, oversaturated colors, blown highlights, crushed blacks, muddy mid-tones, flat lighting, cluttered background, people, rugs, lamps, artwork, books, decorative props, text, logos, watermark, modern anachronistic elements, cartoonish, painterly, synthetic HDR halos, overprocessed, low resolution, blur, motion blur

## Refinement Prompt Template

Refine this image to the Classic Furniture Archives style: soft diffused warm illumination (2700-3000 K), natural color balance with rich tonal depth, enhanced material texture realism with visible grain and surface detail, and well-defined dimensional shadows that preserve both shadow and highlight detail without altering object structure. Increase contrast to achieve fuller tonal range while maintaining warm museum aesthetic. If background replacement is requested, use a minimalist era-appropriate architectural setting and remove all extraneous objects. Preserve historical accuracy and signature geometry.

## Image-to-Image Parameter Guidance

Preferred strength/denoise range: 0.35-0.55.

- 0.35-0.42: conservative cleanup, highest structural preservation
- 0.43-0.50: balanced normalization and style alignment
- 0.51-0.55: stronger restyling, use only when source image quality is poor

## Slot-Specific Intent

### Photorealistic Slots
- Hero: full object readability and iconic silhouette
- Detail Material: grain, leather, textile, or finish authenticity
- Detail Structure: joints, frame transitions, hardware logic
- Context: era-appropriate environmental anchoring
- Designer: portrait or archival photograph

### Sketch Slot - Marker Rendering Style

The sketch slot uses professional industrial design marker rendering technique instead of photorealism.

**PROVIDER NOTE:** 
- **Google AI Studio (Manual)**: Best quality with full multi-reference support - produces amazing results when using reference URLs manually in the web interface
- **FAL (FLUX) (Automated)**: Good quality for automation but limited to ONE reference image per generation. Increased inference steps (50+) provides good quality while maintaining accuracy to the actual chair design
- **Trade-off**: AI Studio (manual) = best quality with multiple references; FAL (automated) = good quality, single reference, fully scriptable

**Reference Image Limitations:**
- FAL img2img: Single `image_url` parameter only
- Google AI Studio: Multiple reference URLs supported (but Python SDK doesn't expose this yet)
- Workaround: Choose the best single reference per slot for FAL automation

**Additional Style Refrences for sketching**
- https://media.licdn.com/dms/image/v2/C5622AQEsWIESc2lxXA/feedshare-shrink_8192/feedshare-shrink_8192/0/1547756609958?e=1777507200&v=beta&t=nOHIpJChD4qrQLIvoyYaAefHxR3caB007sifJ2i9slk
- https://media.licdn.com/dms/image/v2/C4E22AQFXGn2GGhnvzw/feedshare-shrink_2048_1536/feedshare-shrink_2048_1536/0/1578258065899?e=1777507200&v=beta&t=kb1AhRuWln-3uFCiTIBQrASb-5lNCMz_4wsSreqNZCs
- https://media.licdn.com/dms/image/v2/C5622AQG5elUIxPCUcg/feedshare-shrink_8192/feedshare-shrink_8192/0/1563128324286?e=1777507200&v=beta&t=Ew0bYt9FqCXzLGLhzeMYLpZDvUTBRKYvjHca4NIoMOo

**CRITICAL: NOT A SILHOUETTE** - Avoid flat side-profile views. Use dynamic three-quarter or perspective angles that show sculptural form and dimensional depth.

**Visual Characteristics:**
- Bold, generous color application is the primary visual driver — colors drawn from the subject's own palette and era applied to key forms, not saved as a small accent
- Gray Prismacolor or Copic markers (20%, 30%, 50%) used only for secondary shadow tones; gray must NOT dominate
- Confident, sketchy black ink construction lines that extend beyond the form with skeletal quality
- Multiple overlapping line strokes showing drawing process - not tight technical drawing
- Lines can overshoot corners and edges, emphasizing gesture and construction over precision
- White or subtly tinted paper background (pale blue, warm beige, or neutral tone)
- Dynamic three-quarter or perspective view emphasizing sculptural geometry (NOT flat profile)

**Background Treatment (REQUIRED — not optional):**
- Abstract geometric shapes, color blocks, or marker splashes behind subject are mandatory
- Color washes drawn from the subject's palette as design presentation accents
- Construction lines and gestural marks that extend beyond the object form
- Background energy gives the rendering life and professional presentation quality
- Background adds visual interest without competing with the subject

**Core Requirements:**
- No signature, text, annotations, or dimension lines
- Sketchy, loose linework showing drawing confidence and process
- Color and background are as important as the linework — do not produce a gray-toned outline drawing
- Balance between technical precision and hand-drawn spontaneity
