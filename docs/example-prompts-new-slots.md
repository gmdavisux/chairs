# Example Image Prompts for New Slot Strategy

## Hero Slot (hero.txt)

**Barcelona Chair Example:**
```
Barcelona Chair by Ludwig Mies van der Rohe, three-quarter view showing 
polished stainless steel X-frame base with tufted leather cushions. Soft 
warm museum lighting at 2700K, clean minimal white background. Sharp focus 
on the chair's iconic crossed-leg frame and quilted upholstery pattern. 
Natural shadows emphasize materials and form. Match exact chrome finish 
and cognac leather color from reference images.
```

**Wassily Chair Example:**
```
Wassily Chair by Marcel Breuer, three-quarter view showing chrome tubular 
steel frame with black leather straps forming seat and backrest. Warm 
museum lighting highlights gleaming metal curves and leather texture. 
Clean background with subtle Bauhaus-era architectural elements. Focus 
on revolutionary cantilevered structure and geometric form. Match exact 
chrome steel and black leather from reference images.
```

## Silhouette Slot (silhouette.txt)

**Barcelona Chair Example:**
```
Industrial design marker rendering of Barcelona Chair. Technical drawing 
style on white paper showing side profile with precise proportions. 
1970s design studio aesthetic using black markers for frame, subtle 
gray tones for leather cushion volume. Clean linework emphasizing the 
iconic X-shaped scissor frame and floating cushion geometry. No 
photorealistic shading - pure design sketch showing essential form.
```

**Wassily Chair Example:**
```
Industrial design marker rendering of Wassily Chair. Clean technical 
drawing on kraft paper showing side profile. Use black markers for 
tubular steel frame with precise line weight, subtle brown tones for 
leather straps. 1970s Bauhaus design sketch aesthetic. Emphasize the 
distinctive cantilevered geometry and suspended seat construction. 
Pure linework, no photorealistic details.
```

**Eames Lounge Example:**
```
Industrial design marker rendering of Eames Lounge Chair and Ottoman. 
Side elevation view on white paper. Black markers for shell structure, 
warm brown tones for leather cushions, clean gray shadows. 1960s 
industrial design sketch style with precise proportions and elegant 
curves. Show the iconic reclined angle and three-part shell composition.
```

## Context Slot (context.txt)

**Barcelona Chair Example:**
```
Barcelona Chair in 1929 International Exposition Barcelona Pavilion-style 
interior. Minimal modernist architecture with travertine floor, onyx wall 
panels, natural daylight through floor-to-ceiling glass. Chair as focal 
point in authentic Mies van der Rohe architectural setting. Period-appropriate 
1920s-1930s aesthetic, no modern furnishings. Clean composition, warm 
natural light.
```

**Wassily Chair Example:**
```
Wassily Chair in 1925 Bauhaus Dessau faculty apartment interior. Clean 
white walls, geometric window detail, polished wood floor. Minimal 
period-appropriate styling with subtle Bauhaus color accents (primary 
colors). Natural warm lighting, chair positioned near window. Focus on 
chair while showing authentic 1920s modernist context. No anachronisms.
```

**Eames Lounge Example:**
```
Eames Lounge Chair and Ottoman in mid-century modern living room, late 
1950s aesthetic. Walnut wood paneling, floor-to-ceiling windows with 
garden view, clean modernist interior. Natural afternoon light, minimal 
styling with period-appropriate ceramics or books. Chair positioned for 
reading. Authentic 1950s-1960s setting without contemporary elements.
```

## Designer Slot (designer.txt)

**Marcel Breuer Example:**
```
Black and white archival portrait photograph of Marcel Breuer from 1920s 
Bauhaus period. Professional studio quality showing clear facial features 
and expression. Style matches historical photography conventions of the 
era - sharp focus, controlled lighting, formal composition. Period-appropriate 
clothing and hairstyle. No modern photographic techniques or anachronistic 
elements.
```

**Mies van der Rohe Example:**
```
Black and white archival portrait of Ludwig Mies van der Rohe from 1920s-1930s. 
Professional architectural photographer style of the period. Clear, dignified 
composition typical of modernist architect portraits. Period clothing, 
natural lighting. Historical photography aesthetic matching the Barcelona 
Chair's design era.
```

**Charles & Ray Eames Example:**
```
Black and white archival photograph of Charles and Ray Eames in their design 
studio, mid-1950s. Natural documentary style showing both designers at work. 
Period-appropriate 1950s clothing and studio environment. Clear focus, 
authentic mid-century photography aesthetic. May include furniture prototypes 
or design materials in background for context.
```

## Prompt Writing Tips

### Hero
- Specify exact viewing angle (3/4, front, side)
- Mention key materials and finishes explicitly
- Reference lighting color temperature (2700-3000K warm)
- Always include "Match exact [materials] from reference images"

### Silhouette
- Specify "marker rendering" or "technical drawing" style
- Mention background type (white paper, kraft paper)
- Reference design era for sketch style (1960s-1980s)
- Emphasize "clean linework" and "no photorealistic details"
- Focus on proportions and iconic geometry

### Context
- Specify interior style matching furniture's design era
- Name architectural elements (floor type, walls, windows)
- Keep styling minimal - "period-appropriate" not "decorated"
- Include time period explicitly (1920s, 1950s, etc.)
- "No anachronisms" is critical

### Designer
- Specify photograph era (1920s, 1950s, etc.)
- Mention "archival" or "historical" for authentic feel
- Black & white unless original was actually color
- "Period-appropriate" clothing and setting
- Can include studio/workspace for context

## Anti-Hallucination Strategy

**What NOT to prompt for:**
- ❌ Close-up of joinery/screws/hardware
- ❌ Detail of attachment mechanisms
- ❌ Specific construction techniques
- ❌ Invented finishes or materials

**What WORKS well:**
- ✅ Overall form and silhouette
- ✅ General material types (leather, steel, wood)
- ✅ Composition and styling
- ✅ Historical context and era
- ✅ Design sketches (abstracts away details)
