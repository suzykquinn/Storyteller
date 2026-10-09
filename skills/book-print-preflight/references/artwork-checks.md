# The senior artworker's rulebook

Everything below is what an experienced pre-press artworker checks on a book
cover or interior, with why it matters and how to fix it. Use the "why" when
explaining to the user: they want to understand, not just be told.

Contents: 1 Geometry | 2 Resolution & image quality | 3 Colour & ink |
4 Black | 5 Overprint & knockout | 6 Fine detail | 7 Transparency & effects |
8 Fonts & text | 9 Content accuracy | 10 Cover design sense | 11 Interior layout |
12 File hygiene | 13 Fix-it cheat sheet by app

## 1. Geometry

- **Page size matches the spec exactly** (trim + bleed). A cover that is 0.15in
  narrow means the spine is wrong, which means the page count or paper changed.
- **Spine width matches page count x paper**. Recompute it every time; it is the
  most common rejection.
- **Spine content centred on the spine**, not drifting towards one fold.
- **Backgrounds reach the bleed edge** on every side (look at the guides render:
  a white sliver between the art and the red trim line on the outside is a fault).
- **Nothing important in the 0.125in safe margin**, including the bottom of
  descenders, award badges and author photos. Text that crosses a spine fold will
  wrap around the book.
- **Spine text direction**: US/UK convention is top-to-bottom (readable when the
  book lies face up). Bottom-to-top is the European convention; flag it, don't
  fail it.

## 2. Resolution & image quality

- **300 ppi at placed size** for photos and painted art. 200-299 is a risk
  (soft), under 200 is a blocker on anything larger than a thumbnail.
- **Line art / flat graphics / maps** as bitmaps want 600-1200 ppi or, better,
  vector.
- **Upscaled images**: an image enlarged in Photoshop to hit "300 ppi" has the
  numbers but not the detail. The script flags suspects; confirm on the zoom
  tiles (smeary edges, plastic skin, fuzzy text inside the image).
- **AI-generated art**: often 1024-2048px natively and upscaled. Look closely at
  hands, lettering inside the image, repeated textures, and seams.
- **JPEG artefacts**: blocky 8x8 squares in skies and flat areas, ringing
  round text. Show up much worse in print than on screen.
- **Banding** in gradients and skies (visible steps). Fix with a touch of noise
  or a 16-bit source.
- **Moiré**: tiny repeating patterns (fabric, screens) can clash with the print
  screen.
- **Text baked into images** (title lettering as part of a JPEG) prints at image
  resolution, not vector sharpness. Recommend live text or a 600ppi+ image.

## 3. Colour & ink

- **RGB vs CMYK**: what the printer wants (Ingram: CMYK only). RGB objects get
  converted by the printer's software, and bright RGB colours (electric blue,
  neon green, vivid orange, hot pink) are outside what CMYK ink can print, so
  they go dull. Warn the user specifically about any such colour in a key spot
  (title, brand colour). Note: the TAC heat map for RGB content uses a generic
  conversion, so treat its numbers as indicative only.
- **Total ink coverage (TAC)**: the sum of C+M+Y+K in any spot. Over ~240-260%
  on uncoated or digital stock causes mottling, scuffing, set-off onto the
  facing page/cover, and long dry times. Ingram rejects over 240%. Look at the
  *_tac.png: red zones are over the limit.
- **Spot colours** (Pantone) on a digitally printed POD book: must be converted
  to CMYK. Two names for the same Pantone make two plates. "All"/Registration
  used as a colour prints on every plate (solid muddy black).
- **ICC profile / output intent**: for PDF/X the output intent should be a CMYK
  print profile (e.g. FOGRA39, GRACoL/SWOP, or Ingram's recommended). An RGB
  output intent in an "X" file is a contradiction worth flagging.
- **Skin tones and greys made of CMY** can shift colour on press. Neutral greys
  in text/graphics are safer as K only.
- **Cream paper** yellows everything, especially pale blues and whites in
  interior images. Mention it if a cream interior has colour-critical images.

## 4. Black

- **Small text (under ~14pt) must be 100K only.** Rich black or 4-colour text
  shows coloured fringes when plates are a hair out of register. RGB black
  (0,0,0) converts to a 4-colour rich black, so it's the same problem in disguise.
- **Large black areas** look weak in 100K alone (dark grey). Use a controlled
  rich black, Ingram's 60/40/40/100 is the standard. 100/100/100/100 (400%) is
  a blocker.
- **Mixed blacks next to each other** (a 100K box butting a rich black box)
  show up as two visibly different blacks.
- **White/reversed text on rich black**: small reversed text can fill in if
  the black has heavy ink. Keep reversed text 9pt+, bold-ish, and preferably out
  of K-only or a light rich black.

## 5. Overprint & knockout

- **White set to overprint** disappears completely on press (the scripts flag
  it, and it is always a blocker).
- **Black text should usually overprint** coloured backgrounds (prevents white
  halos if registration slips). 100K text knocking out is a minor risk, not a
  blocker, on POD.
- **Coloured objects set to overprint** by accident mix with what's under them
  and change colour. If the overprint graphics state count is non-zero and it
  isn't just black text, inspect.

## 6. Fine detail

- **Hairlines under 0.25pt** can vanish or break up. Reversed (white) lines want
  0.5pt+.
- **Minimum type**: 7pt for positive text, 9pt for reversed text, and serif
  fonts with thin strokes need more. Copyright/legal lines on covers often
  breach this.
- **Thin serifs or script fonts in 4 colours** fall apart; keep them in a single
  ink.

## 7. Transparency & effects

- Drop shadows, glows, blend modes and opacity are fine in PDF/X-4 but must be
  flattened for PDF/X-1a. Flattening can produce visible boxes/stitching lines,
  especially over spot colours or with text: inspect the zooms around shadows.
- Shadows made of rich black on a coloured background can push TAC over the
  limit locally.

## 8. Fonts & text

- **All fonts embedded.** Non-embedded fonts get substituted (often Courier or
  Arial) and reflow.
- Check faux bold/italic (fake styles from Word/Canva can look smeary).
- Check for missing glyphs (boxes or ?), curly vs straight quotes, and
  apostrophes facing the wrong way at the start of words ('Til, 'em, '90s).

## 9. Content accuracy (proofread like it costs money, because it does)

- **Title, subtitle, author name spelled identically** on front, spine, back,
  interior title page, and the metadata the user gives you.
- **ISBN**: valid check digit; same number in the barcode human-readable line,
  the text on the back, and the interior copyright page; the right ISBN for the
  format (paperback vs hardcover have different ISBNs).
- **Price** on the cover/barcode (if any) matches the intended price and
  currency, or omit it.
- **Series name and number** correct and consistent.
- **Back cover copy**: spelling, grammar, widows (single word on the last line),
  straight quotes, double spaces.
- **Publisher/imprint logo and name** correct.

## 10. Cover design sense (the eye of a pro, not just the measuring tape)

- **Thumbnail test**: shrink the front to ~150px wide (Amazon search size).
  Is the title readable? Author name? Most sales decisions happen at this size.
- **Genre signals**: does it look like the books readers of this genre buy?
  (Cosy mystery: bright, illustrated, warm, playful title type.)
- **Contrast**: title against background in greyscale; if it vanishes in
  greyscale it is weak.
- **Visual hierarchy**: one dominant element; nothing fighting the title.
- **Spine works on a shelf**: author and title readable at a distance; series
  branding consistent across books.
- **Optical centring** and kerning of the title (awkward gaps like "A V", "T o").
Frame these as opinions, separate from technical faults.

## 11. Interior layout

- **Gutter/outside margins** per printer table.
- **Chapter openers** consistent (all recto if that's the style), drop caps aligned.
- **Running heads**: correct book/author/chapter names, none on chapter opening
  pages or blank pages.
- **Page numbers**: present, sequential, none on blank pages; front matter roman
  numerals if used.
- **Front matter order**: half title, (ad card), title, copyright, dedication,
  contents, etc. Copyright page details correct.
- **Typography**: widows/orphans, stacks of hyphens (3+ lines ending in hyphens),
  rivers of white in justified text, a lone line of a chapter on its own page,
  inconsistent scene-break markers, double spaces.
- **Images**: inside the margins (or deliberately to the bleed), not crossing
  the gutter unless it's a planned spread.

## 12. File hygiene

- No layers/optional content (hidden layers can print), no annotations, form
  fields, JavaScript, or crop marks/slug for POD.
- Single PDF, correct page count, no blank page 1 by accident, pages in order.
- PDF/X standard declared when the printer asks for it.
- No encryption/password.

## 13. Fix-it cheat sheet by app

Give fixes in the app the user actually uses. Ask if unsure.

- **InDesign**: Export > Adobe PDF (Print) > preset "PDF/X-1a:2001", Marks and
  Bleeds: tick "Use Document Bleed Settings", untick all marks. Window > Output >
  Separations Preview (ink coverage, set 240%) and Flattener Preview. Swatches:
  convert spot to process. Text to [Black] swatch (100K) not [Registration].
  Links panel shows effective ppi.
- **Affinity Publisher/Designer**: Document Setup > Colour: CMYK/8 with a
  print profile. Export PDF > preset "PDF/X-1a" or "PDF (press ready)", tick
  "Include bleed", untick marks. Use a 0,0,0,100 swatch for text.
- **Photoshop**: Image > Image Size (Resample off) to see true ppi.
  View > Proof Setup > Working CMYK + View > Gamut Warning for out-of-gamut
  colours.
- **Canva**: Download > PDF Print, tick "Crop marks and bleed" only if asked
  (KDP: bleed yes, crop marks no), "Flatten PDF", Colour profile CMYK (Pro).
  Canva black text is RGB-derived rich black; acceptable for KDP, risky for
  Ingram.
- **Vellum**: interiors are generally well-formed; check trim, gutter and that
  images are 300 ppi before importing.
- **Atticus / Word**: export PDF with fonts embedded (Word: Options > "Embed fonts",
  "ISO 19005-1 compliant (PDF/A)" helps), check page size isn't Letter/A4.
