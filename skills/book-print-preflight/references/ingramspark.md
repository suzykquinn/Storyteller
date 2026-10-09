# IngramSpark print specs

IngramSpark is stricter than KDP and runs automated validation. Specs drift; when
a pass/fail call is tight, tell the user to check Ingram's current File Creation
Guide and say so in the report.

## Cover

- **Template first**: Ingram's cover template generator produces the exact
  dimensions, spine width and barcode for the ISBN, trim, paper and binding.
  Spine width depends on paper stock (crème vs white vs groundwood, colour
  options) and Ingram's own caliper numbers can differ slightly from KDP's, so
  a cover built for KDP is NOT automatically right for Ingram. Ask the user for
  the template PDF (or its stated dimensions) and compare.
- **Format**: PDF/X-1a:2001 is the safe choice (Ingram also accepts newer PDF/X
  versions in recent guides). X-1a means: CMYK only, fonts embedded, no live
  transparency, no layers.
- **Colour**: CMYK only. RGB, Lab and spot colours are rejected or
  force-converted. Convert spot colours to process.
- **Total ink limit**: 240%. This is enforced. Large black areas should be a
  rich black of 60C 40M 40Y 100K (= 240%) or less, not 4x100.
- **Text black**: 100K only. Small text in rich black prints fuzzy because the
  four plates never land exactly on top of each other.
- **Images**: 300 ppi minimum.
- **Bleed**: 0.125in all round.
- **Safe area**: keep text 0.125in inside the trim; spine text 0.0625in from
  each fold (more for thick books is safer, as spines can drift 1/16in).
- **Barcode**: from the template (it encodes the ISBN and optional price add-on).
  It must stay 100K on a white box, at 100% size, not stretched or recoloured.
- **No** crop marks, slug, colour bars, annotations or comments.

## Interior

- **Format**: PDF/X-1a (or accepted newer PDF/X), single pages, fonts embedded.
- **Page count**: must be even.
- **B&W interior**: everything must be greyscale/100K. Any RGB or CMYK colour
  object can trigger a rejection or a muddy conversion. Grey tints below ~10%
  can drop out and above ~90% can fill in on uncoated stock.
- **Colour interior**: CMYK, 240% TAC.
- **Bleed**: 0.125in on top, bottom and outside edges only.
- **Margins**: Ingram recommends at least 0.5in all round, with more in the
  gutter for thicker books (the KDP gutter table is a sensible minimum).
- **Images**: 300 ppi; line art 600-1200 ppi.
- **Blank pages**: fine, but keep the final page count even.

## Common Ingram validation rejections

Spot colours present, RGB images, TAC over 240%, live transparency in an X-1a
file, fonts not embedded, spine width not matching the template, barcode
missing/altered, odd page count, page size not matching trim (+ bleed).
