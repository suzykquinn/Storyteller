"""Build sample PDFs with known faults, for testing the preflight skill."""
import pymupdf, io, sys
from PIL import Image, ImageDraw, ImageFilter
PT=72
out=sys.argv[1]

def photo(w,h,seed=1,blur=0):
    import random; random.seed(seed)
    im=Image.new("RGB",(w,h),(40,60,120)); d=ImageDraw.Draw(im)
    for _ in range(400):
        x,y=random.randrange(w),random.randrange(h); r=random.randrange(2,max(3,w//15))
        d.ellipse([x,y,x+r,y+r],fill=(random.randrange(256),random.randrange(256),random.randrange(256)))
    if blur: im=im.filter(ImageFilter.GaussianBlur(blur))
    b=io.BytesIO(); im.save(b,"JPEG",quality=92); return b.getvalue()

def upscaled(w,h):
    small=Image.open(io.BytesIO(photo(w//4,h//4,seed=3))).resize((w,h),Image.BICUBIC)
    b=io.BytesIO(); small.save(b,"JPEG",quality=92); return b.getvalue()

# ---- BAD COVER: 5x8, 300 pages cream on KDP => spine 0.75in; we build spine 0.6in
tw,th,b=5,8,0.125; spine=0.6
W=(2*tw+spine+2*b)*PT; H=(th+2*b)*PT
doc=pymupdf.open(); pg=doc.new_page(width=W,height=H)
sl=(b+tw)*PT; sr=sl+spine*PT
# front: full-bleed photo at low res (approx 150ppi)
pg.insert_image(pymupdf.Rect(sr,0,W,H),stream=photo(780,1240))
# back: upscaled image region (300ppi nominal but upscaled)
pg.insert_image(pymupdf.Rect(0,0,sl,H*0.5),stream=upscaled(1590,1260))
# back solid with 4x100 rich black = 400% TAC
pg.draw_rect(pymupdf.Rect(0,H*0.5,sl,H),color=None,fill=(1,1,1,1))
# spine: background
pg.draw_rect(pymupdf.Rect(sl,0,sr,H),color=None,fill=(0,0,0,1))
# title text in RGB, near trim on front
pg.insert_text((sr+0.15*PT,(b+0.08)*PT+20),"THE VICARAGE MURDERS",fontsize=24,color=(0.9,0.1,0.1))
# small rich black text body on back (on white box)
pg.draw_rect(pymupdf.Rect(0.5*PT,H*0.52,sl-0.5*PT,H*0.75),color=None,fill=(0,0,0,0))
pg.insert_text((0.6*PT,H*0.55),"Bob and Shirley are back, and this time it's personal.",fontsize=8,color=(0.6,0.4,0.4,1))
# tiny reversed white text on black
pg.insert_text((0.6*PT,H*0.8),"Cover design by Somebody. Printed in the UK.",fontsize=6,color=(0,0,0,0))
# spine text crossing fold
pg.insert_text((sl-0.1*PT,H*0.5),"SUZY K QUINN",fontsize=14,color=(0,0,0,0),rotate=90)
# hairline rule
pg.draw_line((0.6*PT,H*0.6),(sl-0.6*PT,H*0.6),color=(0,0,0,1),width=0.1)
# ISBN text
pg.insert_text((0.6*PT,H*0.7),"ISBN 978-1-23456-789-7",fontsize=9,color=(0,0,0,1))
doc.save(f"{out}/bad_cover.pdf")

# ---- GOOD COVER: 5x8, 300 pages cream, spine 0.75
spine=0.75; W=(2*tw+spine+2*b)*PT
doc=pymupdf.open(); pg=doc.new_page(width=W,height=H)
sl=(b+tw)*PT; sr=sl+spine*PT
img=Image.open(io.BytesIO(photo(1580,2475,seed=5))).convert("CMYK")
bb=io.BytesIO(); img.save(bb,"JPEG",quality=92)
pg.insert_image(pymupdf.Rect(sr,0,W,H),stream=bb.getvalue())
pg.draw_rect(pymupdf.Rect(0,0,sr,H),color=None,fill=(0.6,0.4,0.4,1))
pg.draw_rect(pymupdf.Rect(0.5*PT,H*0.2,sl-0.5*PT,H*0.6),color=None,fill=(0,0,0,0))
pg.insert_text((0.7*PT,H*0.25),"Bob and Shirley are back.",fontsize=11,color=(0,0,0,1))
pg.insert_text((sr+0.6*PT,1.5*PT),"THE VICARAGE MURDERS",fontsize=22,color=(0,0,0,0))
pg.insert_text((sl+0.45*PT,H*0.35),"SUZY K QUINN",fontsize=12,color=(0,0,0,0),rotate=90)
pg.insert_text((0.7*PT,H*0.3),"ISBN 978-1-23456-789-7",fontsize=9,color=(0,0,0,1))
doc.save(f"{out}/good_cover.pdf")

# ---- BAD INTERIOR: 5x8 no bleed, 40 pages, text into gutter, RGB image, colour text
doc=pymupdf.open()
for i in range(40):
    pg=doc.new_page(width=5*PT,height=8*PT)
    if i in (2,3): continue  # blanks
    recto = i%2==0
    x = 0.2*PT if recto else 0.75*PT  # gutter far too small on recto pages
    tb=pymupdf.Rect(x,0.75*PT,x+4*PT,7.3*PT)
    pg.insert_textbox(tb,("Shirley put the kettle on. "*60),fontsize=10.5,color=(0,0,0))
    pg.insert_text((2.4*PT,7.7*PT),str(i+1),fontsize=9,color=(0,0,0))
    if i==10:
        pg.insert_image(pymupdf.Rect(1*PT,2*PT,4*PT,4*PT),stream=photo(300,200))
    if i==12:
        pg.insert_text((1*PT,0.5*PT),"Chapter Five",fontsize=16,color=(0.7,0.1,0.1))
doc.save(f"{out}/bad_interior.pdf")
print("ok")
