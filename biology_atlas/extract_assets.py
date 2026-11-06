#!/usr/bin/env python3
"""
Extract every embedded raster object from the uploaded textbook PDF
(C111216(2).PDF = فصل ۳ «دستگاه حرکتی»، زیست‌یازدهم) and also cut out
high-resolution "figure plates" (artwork + the labels/captions printed
around it).  The plates are the canvases that build_atlas.py annotates.

Outputs (all inside the repository):
  extracted_images/  : 28 original embedded image objects, verbatim pixels
  figure_crops/      : 22 high-res figure plates (JPEG, 3x render)
  figure_crops/preview_*.png : downscaled copies used while authoring
  assets/density_chart.png   : reconstructed graph for فعّالیت ۲ (p. 42)
  assets/skeleton_types.png  : comparative plate for p. 52 (no image there)
"""
import json
import os
import sys

import pymupdf
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = "/tmp/arena-coding-uploads/C111216(2).PDF"
if not os.path.exists(SRC):
    SRC = os.path.join(ROOT, "C111216(2).PDF")

RAW_DIR = os.path.join(ROOT, "extracted_images")
CROP_DIR = os.path.join(ROOT, "figure_crops")
ASSET_DIR = os.path.join(ROOT, "assets")
os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(CROP_DIR, exist_ok=True)
os.makedirs(ASSET_DIR, exist_ok=True)

FONT_R = os.path.join(ASSET_DIR, "fonts", "Vazirmatn-Regular.ttf")
FONT_B = os.path.join(ASSET_DIR, "fonts", "Vazirmatn-Bold.ttf")

# ---------------------------------------------------------------------------
# Figure plate definitions: (key, source page (1-based), crop rect in PDF pt)
# Crop rects deliberately include the textbook's own blue labels and green
# caption, so the extracted figure remains faithful to the printed page.
# ---------------------------------------------------------------------------
PLATES = [
    ("F00_prosthesis", 1, (62, 62, 540, 422)),       # عکس آغازین فصل
    ("F01_skeleton", 2, (58, 247, 413, 638)),       # شکل ۱
    ("F02_bone_types", 3, (55, 110, 186, 730)),     # شکل ۲ (چهار تصویر)
    ("F03_osteon", 4, (55, 125, 545, 425)),         # شکل ۳
    ("F04_fracture", 5, (52, 115, 545, 402)),       # شکل ۴
    ("F05_osteoporosis", 5, (52, 558, 545, 705)),   # شکل ۵
    ("F06_density_table", 6, (145, 120, 460, 335)),  # جدول فعّالیت ۲
    ("F07_suture", 6, (55, 530, 425, 745)),          # شکل ۶
    ("F08_synovial", 7, (235, 172, 550, 428)),       # شکل ۷
    ("F09_joint_types", 7, (190, 580, 550, 750)),    # شکل ۸
    ("F10_acl", 7, (55, 355, 190, 690)),             # بدانید بیشتر: رباط صلیبی
    ("F11_arthritis", 8, (85, 510, 395, 705)),       # بدانید بیشتر: روماتیسم
    ("F12_muscles", 9, (55, 185, 548, 570)),         # شکل ۹
    ("F13_antagonist", 10, (55, 55, 550, 300)),      # شکل ۱۰
    ("F14_muscle_structure", 11, (55, 185, 550, 425)),  # شکل ۱۱
    ("F15_fiber_myofibril", 12, (52, 52, 550, 435)),    # شکل ۱۲
    ("F16_micro_sarcomere", 12, (52, 455, 550, 535)),   # شکل ۱۳
    ("F17_myosin", 12, (52, 545, 550, 625)),            # شکل ۱۴
    ("F18_sliding", 13, (55, 195, 550, 410)),           # شکل ۱۵
    ("F19_crossbridge", 14, (52, 55, 550, 320)),        # شکل ۱۶
    ("F20_fiber_types", 15, (55, 240, 550, 575)),       # شکل ۱۷
]


def main():
    doc = pymupdf.open(SRC)
    inventory = []
    for pno, page in enumerate(doc, start=1):
        for im in page.get_images(full=True):
            xref = im[0]
            pix = pymupdf.Pixmap(doc, xref)
            if pix.colorspace is not None and pix.colorspace.n > 3:
                pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
            name = "p%02d_xref%d_%dx%d.png" % (pno, xref, im[2], im[3])
            pix.save(os.path.join(RAW_DIR, name))
            inventory.append({
                "page": pno, "xref": xref, "width": im[2], "height": im[3],
                "colorspace": str(im[5]), "rect": [round(v, 1) for v in page.get_image_rects(xref)[0]],
                "file": name,
            })
    with open(os.path.join(ROOT, "assets", "image_inventory.json"), "w", encoding="utf-8") as fh:
        json.dump(inventory, fh, ensure_ascii=False, indent=1)
    print("embedded rasters extracted:", len(inventory))

    sizes = {}
    for key, pno, rect in PLATES:
        page = doc[pno - 1]
        pix = page.get_pixmap(matrix=pymupdf.Matrix(3, 3),
                             clip=pymupdf.Rect(*rect), alpha=False)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        out = os.path.join(CROP_DIR, key + ".jpg")
        img.save(out, "JPEG", quality=91, subsampling=0, optimize=True)
        w, h = img.size
        sizes[key] = [w, h]
        thumb = img.copy()
        thumb.thumbnail((900, 900))
        thumb.save(os.path.join(CROP_DIR, "preview_" + key + ".png"))
    with open(os.path.join(ROOT, "assets", "plate_sizes.json"), "w") as fh:
        json.dump(sizes, fh, indent=1)
    print("figure plates cut:", len(sizes))
    make_density_chart()
    make_skeleton_types_plate()
    doc.close()


def rtl(text, font):
    import arabic_reshaper
    from bidi.algorithm import get_display
    return get_display(arabic_reshaper.reshape(text))


def rtl(text, font=None):
    import arabic_reshaper
    from bidi.algorithm import get_display
    return get_display(arabic_reshaper.reshape(text))


def tw(dr, text, font):
    return dr.textlength(rtl(text), font=font)


def wrap_rtl(dr, text, font, maxw):
    """Greedy RTL-aware word wrap; shaping is applied per rendered line."""
    words = text.split()
    lines, cur = [], ""
    for w in words:
        cand = (cur + " " + w).strip()
        if tw(dr, cand, font) <= maxw or not cur:
            cur = cand
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def make_density_chart():
    """Reconstructed line graph of the bone-density table on page 42."""
    ages = [20, 30, 40, 50, 60, 70, 80]
    women = [0.895, 0.886, 0.850, 0.797, 0.733, 0.667, 0.607]
    men = [0.979, 0.936, 0.894, 0.851, 0.809, 0.766, 0.724]
    W, H = 1500, 900
    im = Image.new("RGB", (W, H), "#ffffff")
    dr = ImageDraw.Draw(im)
    f_reg = ImageFont.truetype(FONT_R, 29)
    f_bold = ImageFont.truetype(FONT_B, 38)
    f_sm = ImageFont.truetype(FONT_R, 23)
    x0, x1, y0, y1 = 170, 1390, 140, 700
    dr.rectangle((x0, y0, x1, y1), outline="#c9d6df", width=2)
    for v in [0.55, 0.65, 0.75, 0.85, 0.95, 1.05]:
        y = y1 - (v - 0.55) / 0.5 * (y1 - y0)
        dr.line((x0, y, x1, y), fill="#e7edf2", width=2)
        dr.text((x0 - 22, y - 16), "%.2f" % v, font=f_sm, fill="#5b6b78", anchor="ra")
    for i, a in enumerate(ages):
        x = x0 + i * (x1 - x0) / (len(ages) - 1)
        dr.line((x, y1, x, y1 + 8), fill="#5b6b78", width=3)
        dr.text((x, y1 + 18), str(a), font=f_sm, fill="#3c4a55", anchor="ma")

    def series(vals, color):
        pts = [(x0 + i * (x1 - x0) / (len(vals) - 1),
                y1 - (v - 0.55) / 0.5 * (y1 - y0)) for i, v in enumerate(vals)]
        dr.line(pts, fill=color, width=7, joint="curve")
        for p in pts:
            dr.ellipse((p[0] - 10, p[1] - 10, p[0] + 10, p[1] + 10), fill=color,
                       outline="white", width=3)
        return pts
    series(men, "#1769aa")
    series(women, "#c2185b")
    dr.text((W // 2, 30), rtl("نمودار بازسازی‌شدهٔ فعّالیت ۲: تغییر میانگین تراکم تودهٔ استخوانی با سن"),
            font=f_bold, fill="#123a54", anchor="ma")
    dr.text((W // 2, y1 + 62), rtl("سن (سال)"), font=f_reg, fill="#3c4a55", anchor="ma")
    dr.text((x1 - 10, 92), rtl("تراکم استخوان، واحد تقریبی g/cm²"), font=f_sm,
            fill="#3c4a55", anchor="ra")
    # legend (top-left, above the curves)
    dr.rounded_rectangle((x0 + 20, 160, x0 + 330, 270), radius=12, fill="#ffffff",
                         outline="#dbe5ec", width=2)
    dr.line((x0 + 40, 195, x0 + 130, 195), fill="#c2185b", width=7)
    dr.ellipse((x0 + 78, 188, x0 + 92, 202), fill="#c2185b")
    dr.text((x0 + 310, 178), rtl("زنان"), font=f_reg, fill="#7a1640", anchor="ra")
    dr.line((x0 + 40, 240, x0 + 130, 240), fill="#1769aa", width=7)
    dr.ellipse((x0 + 78, 233, x0 + 92, 247), fill="#1769aa")
    dr.text((x0 + 310, 223), rtl("مردان"), font=f_reg, fill="#12456f", anchor="ra")
    dr.text((x1, 820), rtl("نکتهٔ پنهان: شیب افت تراکم پس از ۵۰ سالگی در زنان تندتر است؛ اختلاف دو جنس از ۰٫۰۸۴ به ۰٫۱۱۷ می رسد"),
            font=f_sm, fill="#7a1640", anchor="ra")
    im.save(os.path.join(ASSET_DIR, "density_chart.png"))


def make_skeleton_types_plate():
    """Page 52 has no picture; this plate is the advanced comparative figure."""
    W, H = 1500, 900
    im = Image.new("RGB", (W, H), "#f7fbfd")
    dr = ImageDraw.Draw(im)
    f_bold = ImageFont.truetype(FONT_B, 32)
    f_reg = ImageFont.truetype(FONT_R, 25)
    f_sm = ImageFont.truetype(FONT_R, 22)
    cols = [
        ("#e8f5e9", "#2e7d32", "اسکلت ایستایی-آب (Hydrostatic)",
         ["عروس دریایی و کرم خاکی", "مایع درونی تحت فشار در برابر ماهیچه های حلقوی و طولی",
          "بدون سطح سخت اتکا؛ حرکت با نیروی عکس العمل محیط", "محدودیت: وابستگی به محیط آبی یا مرطوب"]),
        ("#fff3e0", "#ef6c00", "اسکلت بیرونی (Exoskeleton)",
         ["حشرات و سخت پوستان؛ کیتین و کلسیم کربنات", "ماهیچه ها به سطح درونی پوسته متصل می شوند",
          "رشد تنها با پوست اندازی (ecdysis) ممکن است", "محدودیت: جرم با توان سوم طول افزایش می یابد"]),
        ("#e3f2fd", "#1565c0", "اسکلت درونی (Endoskeleton)",
         ["مهره داران؛ نوع غضروفی در کوسه ماهیان", "استخوان زنده، رگ دار و پیوسته بازسازی شونده",
          "رشد بدون پوست اندازی و اهرم بندی کارآمد", "محدودیت: آسیب پذیری در ضربه و وابستگی به کلسیم"]),
    ]
    x, cw = 25, 480
    for bg, accent, title, rows in cols:
        dr.rounded_rectangle((x, 115, x + cw, 850), radius=22, fill=bg, outline=accent, width=3)
        dr.rounded_rectangle((x, 115, x + cw, 195), radius=22, fill=accent)
        dr.rectangle((x, 170, x + cw, 195), fill=accent)
        for j, ln in enumerate(wrap_rtl(dr, title, f_bold, cw - 30)):
            dr.text((x + cw // 2, 128 + j * 34), rtl(ln), font=f_bold, fill="white", anchor="ma")
        yy = 220
        for r in rows:
            dr.ellipse((x + cw - 34, yy + 9, x + cw - 22, yy + 21), fill=accent)
            for ln in wrap_rtl(dr, r, f_reg, cw - 80):
                dr.text((x + cw - 52, yy), rtl(ln), font=f_reg, fill="#20313c", anchor="ra")
                yy += 36
            yy += 26
        dr.text((x + cw // 2, 795), rtl("سازوکار مشترک: وارد کردن نیروی مخالف جهت حرکت"),
                font=f_sm, fill=accent, anchor="ma")
        x += cw + 10
    dr.text((W // 2, 38), rtl("لوح تطبیقی تکمیلی: سه نوع اسکلت در جانوران (بر پایهٔ متن ص ۵۲ و منابع دانشگاهی)"),
            font=f_bold, fill="#123a54", anchor="ma")
    im.save(os.path.join(ASSET_DIR, "skeleton_types.png"))


if __name__ == "__main__":
    main()
