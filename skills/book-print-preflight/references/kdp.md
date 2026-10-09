# Amazon KDP print specs (paperback focus)

Specs drift. These were compiled from KDP's published guidance as known in 2025-26.
If a number here decides pass/fail and the margin is tight, tell the user to confirm
it in KDP's current help pages or the KDP cover calculator, and say so in the report.

## Paperback cover

- **File**: single PDF, one page: back cover + spine + front cover, with bleed. No crop marks.
- **Size**: width = 0.125 bleed + back trim + spine + front trim + 0.125 bleed.
  Height = trim height + 0.25.
- **Spine width** = page count x paper factor:
  | Paper | inches per page |
  |---|---|
  | Black & white, white paper | 0.002252 |
  | Black & white, cream paper | 0.0025 |
  | Standard colour, white | 0.002252 |
  | Premium colour, white | 0.002347 |
  The PDF can be off by a hair (KDP tolerates tiny rounding), but anything over
  ~0.01in difference is a reupload, and a wrong page count is the usual cause.
- **Spine text** is only allowed when the book has more than 79 pages. Keep spine
  text 0.0625in away from each fold.
- **Safe area**: keep text and important image content 0.125in in from the trim
  on all outer edges. Extend backgrounds fully to the bleed edge.
- **Barcode**: KDP prints its barcode in a 2in x 1.2in area at the bottom right
  of the back cover (towards the spine). Keep that box free of text and busy
  detail, or supply your own barcode in that spot. Never let anything important
  hide under it.
- **Images**: 300 ppi minimum at placed size.
- **Colour**: KDP accepts RGB or CMYK covers and converts on its side. CMYK
  gives the designer control; RGB images can shift (bright blues, greens,
  oranges dull down). Either way, aim for total ink under ~240-260% in large
  dark areas so they dry properly and don't mottle.
- **Fonts**: embedded.
- **Rejections we see most**: wrong spine width (page count changed after the
  cover was made), text in the barcode box, text too near the trim, spine text
  on a sub-80-page book, low-res images, cover file size/page size not matching
  the selected trim.

## Paperback interior

- **Page size**: no bleed = exact trim. With bleed = trim width + 0.125in,
  trim height + 0.25in (bleed is on the top, bottom and outside edge only, never
  the gutter).
- **Minimum page count**: 24.
- **Inside (gutter) margin** depends on page count:
  | Pages | Gutter |
  |---|---|
  | 24-150 | 0.375in |
  | 151-300 | 0.5in |
  | 301-500 | 0.625in |
  | 501-700 | 0.75in |
  | 701-828 | 0.875in |
- **Outside, top and bottom margins**: at least 0.25in without bleed, 0.375in
  with bleed.
- **Single pages**, not spreads. Page 1 is a right-hand (recto) page.
- **Blank pages**: KDP flags long runs of blank pages (more than a couple in the
  middle, more than ~10 at the end). A few intentional blanks are fine.
- **B&W interiors** are printed in greyscale. Colour text or RGB black will
  just become grey, so set body text in 100K/greyscale black for crispness.
- **Images**: 300 ppi. Line art (maps, diagrams) ideally 600+.
- **Fonts** embedded, no crop marks, no annotations/comments, no form fields.

## Hardcover (case laminate)

Different cover maths (hinge and wrap). Do not reuse paperback numbers: ask the
user for the KDP hardcover template for their trim and page count and check
against that.
