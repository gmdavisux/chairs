# New Image Slot Strategy

## The Problem with Detail Photos

AI-generated close-up detail shots tend to **hallucinate non-existent structural details** - inventing screws, joinery, hardware, and finishes that don't match the actual furniture piece. This is historically inaccurate for a furniture archive.

## The Solution: Alternative Slot Types

Instead of risky detail shots, we now use four complementary image types:

### 1. **Hero** (Photorealistic)
Standard museum-catalog view of the complete chair.
- **Style**: Photorealistic product photography
- **Goal**: Show overall form, materials, and proportions
- **Hallucination risk**: Low (full view is harder to fake)

### 2. **Silhouette** (Technical Rendering)
Industrial design marker rendering showing pure form.
- **Style**: 1960s-1980s design sketch with markers/pencil on white/kraft paper
- **Goal**: Emphasize iconic silhouette and geometry without photorealistic details
- **Hallucination risk**: Very low (no structural details to invent)
- **Reference**: Designer sketches, archival drawings

### 3. **Context** (Lifestyle/Interior)
Chair placed in period-appropriate home setting.
- **Style**: 3/4 view in authentic interior matching design era
- **Goal**: Show how chair lives in real space, historical context
- **Hallucination risk**: Low (focus on composition, not details)
- **Reference**: Period catalog photos, interior photos from design era

### 4. **Designer** (Portrait Photo - Optional)
Archival portrait of the designer from their active period.
- **Style**: Black & white or period-appropriate archival photography
- **Goal**: Connect piece to its creator, historical context
- **Hallucination risk**: None (based on actual archival photos)
- **Reference**: Historical portraits, design archives

## Example Prompts

### Hero
```
Wassily Chair by Marcel Breuer, three-quarter view showing chrome-plated 
tubular steel frame with black leather straps. Soft warm museum lighting, 
clean minimal background. Match exact materials from reference image.
```

### Silhouette
```
Industrial design marker rendering of Wassily Chair. Clean technical drawing 
style with precise lines on white paper. 1970s design sketch aesthetic with 
markers and pencil. Show accurate proportions and iconic cantilevered form. 
No photorealistic shading, pure linework showing distinctive profile.
```

### Context
```
Wassily Chair in 1920s Bauhaus-era interior. Period-appropriate room with 
clean modernist architecture, minimal styling. Natural warm lighting. Chair 
as focal point in authentic historical setting. No modern anachronisms.
```

### Designer
```
Black and white archival portrait photograph of Marcel Breuer from 1920s-1930s. 
Professional quality, clear focus. Style matches historical photography 
conventions of the Bauhaus period. No modern elements.
```

## Configuration

Generate all four slots:
```bash
FURNITURE_IMAGE_MAX_PER_PAGE=4
```

Generate hero + silhouette + context (skip designer):
```bash
FURNITURE_IMAGE_MAX_PER_PAGE=3
```

Hero only:
```bash
FURNITURE_IMAGE_MAX_PER_PAGE=1
```

## Benefits

✅ **No hallucinated details** - Silhouette/context don't require close-up structural accuracy  
✅ **Visual variety** - Technical, photorealistic, lifestyle, and historical perspectives  
✅ **Historical authenticity** - Designer portraits and period interiors add context  
✅ **Better storytelling** - Shows the chair's design intent, real-world use, and creator  
✅ **Flexible** - Can skip designer slot if no good reference exists  

## Migration from Old Slots

Old slots are aliased for backward compatibility:
- `detail-silhouette` → `silhouette`
- `detail-context` → `context`
- `detail-material` ❌ (deprecated, causes hallucinations)
- `detail-structure` ❌ (deprecated, causes hallucinations)

Existing projects will continue to work, but new prompts should use the new slot names and styles.
