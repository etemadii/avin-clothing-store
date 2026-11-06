#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ساخت اطلس PDF حاشیه نویسی شدهٔ فصل ۳ «دستگاه حرکتی» (زیست یازدهم).

خروجی ها:
  Atlas_Dastgah_Harekaty.pdf   اطلس کامل: تصاویر استخراج شده + درج ریز اطلاعات
                                روی تصویر + تکمیل دانشگاهی + نکات پنهان + ۵۲ تست
  Question_Bank_Challenge.pdf  بانک تست و پاسخنامه به صورت جداگانه
"""
import json
import os
import sys

import pymupdf
import arabic_reshaper
from bidi.algorithm import get_display
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from content_a import BONE_UNITS
from content_b import JOINT_UNITS
from content_c import MUSCLE_UNITS, INTEGRATED_QUESTIONS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSET = os.path.join(ROOT, "assets")
FONT_DIR = os.path.join(ASSET, "fonts")
OUT_FULL = os.path.join(ROOT, "Atlas_Dastgah_Harekaty.pdf")
OUT_QUESTIONS = os.path.join(ROOT, "Question_Bank_Challenge.pdf")

W, H = 595.0, 842.0          # A4
M = 34.0
BOTTOM = H - 48

INK = (0.12, 0.17, 0.21)
MUTED = (0.42, 0.48, 0.53)
LIGHT = (0.87, 0.91, 0.93)
PAPER = (1, 1, 1)
BONE = (0.05, 0.42, 0.40)
JOINT = (0.36, 0.24, 0.55)
MUSCLE = (0.72, 0.18, 0.24)
COMPARE = (0.12, 0.38, 0.62)
GOLD = (0.72, 0.52, 0.13)

FONT_FILES = {
    "r": os.path.join(FONT_DIR, "Vazirmatn-Regular.ttf"),
    "m": os.path.join(FONT_DIR, "Vazirmatn-Medium.ttf"),
    "b": os.path.join(FONT_DIR, "Vazirmatn-Bold.ttf"),
}
FONT_NAMES = {"r": "vz", "m": "vzm", "b": "vzb"}
FONTS = {k: pymupdf.Font(fontfile=v) for k, v in FONT_FILES.items()}

RESHAPER = arabic_reshaper.ArabicReshaper(
    configuration={"delete_harakat": False, "support_ligatures": True}
)


def sh(text):
    """Shape Persian/Arabic text and apply the bidi visual-order algorithm."""
    return get_display(RESHAPER.reshape(str(text)))


def tw(text, fkey="r", size=10):
    return FONTS[fkey].text_length(sh(text), fontsize=size)


def fa(n):
    """Latin digits -> Persian digits (for RTL-safe numbering)."""
    return str(n).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))


def register_fonts(page):
    for k, name in FONT_NAMES.items():
        page.insert_font(fontname=name, fontfile=FONT_FILES[k])


def text(page, x_right, y, s, size=10, fkey="r", color=INK):
    t = sh(s)
    w = FONTS[fkey].text_length(t, fontsize=size)
    page.insert_text((x_right - w, y), t, fontname=FONT_NAMES[fkey],
                     fontsize=size, color=color)


def text_left(page, x_left, y, s, size=10, fkey="r", color=INK):
    page.insert_text((x_left, y), sh(s), fontname=FONT_NAMES[fkey],
                     fontsize=size, color=color)


def wrap(s, fkey, size, maxw):
    out = []
    for part in str(s).split("\n"):
        words, cur = part.split(), ""
        for word in words:
            cand = (cur + " " + word) if cur else word
            if tw(cand, fkey, size) <= maxw or not cur:
                cur = cand
            else:
                out.append(cur)
                cur = word
        if cur:
            out.append(cur)
    return out


def para(page, x_right, y, s, maxw, size=10, fkey="r", color=INK, leading=None):
    leading = leading or size * 1.45
    for line in wrap(s, fkey, size, maxw):
        text(page, x_right, y, line, size, fkey, color)
        y += leading
    return y


def badge(page, cx, cy, n, color, r=9, size=8.5):
    page.draw_circle((cx, cy), r, color=color, fill=color, width=0.6)
    d = str(n)
    dw = FONTS["b"].text_length(d, fontsize=size)
    page.insert_text((cx - dw / 2, cy + size * 0.34), d, fontname=FONT_NAMES["b"],
                     fontsize=size, color=(1, 1, 1))


def header(page, title, subtitle, accent, kicker=None):
    page.draw_rect(pymupdf.Rect(0, 0, W, 7), color=None, fill=accent)
    page.draw_rect(pymupdf.Rect(M, 20, W - M, 66), color=None, fill=(0.95, 0.97, 0.98))
    page.draw_rect(pymupdf.Rect(M, 20, M + 4, 66), color=None, fill=accent)
    if kicker:
        text(page, W - M - 10, 35, kicker, 8, "m", accent)
    text(page, W - M - 10, 54, title, 13.5, "b", INK)
    text_left(page, M + 10, 54, subtitle, 8, "r", MUTED)
    page.draw_line((M, 72), (W - M, 72), color=LIGHT, width=0.7)


def footer(page, number, label):
    page.draw_line((M, H - 40), (W - M, H - 40), color=LIGHT, width=0.7)
    text(page, W - M, H - 24, label, 7.6, "r", MUTED)
    text_left(page, M, H - 24, "ص " + fa(number), 7.6, "r", MUTED)


def new_page(doc, title, subtitle, accent, kicker=None):
    page = doc.new_page(width=W, height=H)
    register_fonts(page)
    header(page, title, subtitle, accent, kicker)
    return page


class Story:
    """Simple RTL vertical flow with automatic page breaks."""

    def __init__(self, doc, title, accent, kicker=None, start=88):
        self.doc, self.title, self.accent, self.kicker = doc, title, accent, kicker
        self.page = None
        self.y = start
        self.new_page()

    def new_page(self):
        self.page = new_page(self.doc, self.title, "اطلس تشریحی دستگاه حرکتی • زیست یازدهم، فصل ۳",
                             self.accent, self.kicker)
        self.y = 88

    def ensure(self, h):
        if self.y + h > BOTTOM:
            self.new_page()

    def heading(self, s, size=11.5, gap=8):
        self.ensure(30)
        self.y += gap
        page = self.page
        page.draw_rect(pymupdf.Rect(M, self.y - 12, W - M, self.y + 10),
                       color=None, fill=(0.94, 0.96, 0.97))
        page.draw_rect(pymupdf.Rect(M, self.y - 12, M + 3, self.y + 10),
                       color=None, fill=self.accent)
        text(page, W - M - 10, self.y + 3, s, size, "b", self.accent)
        self.y += 24

    def bullet(self, s, size=9.6, leading=13.2, color=INK, maxw=None):
        maxw = maxw or (W - 2 * M - 26)
        lines = wrap(s, "r", size, maxw)
        self.ensure(len(lines) * leading + 6)
        self.page.draw_circle((W - M - 4, self.y - 3), 2.3,
                              color=self.accent, fill=self.accent)
        self.y = para(self.page, W - M - 14, self.y, lines_text(lines), maxw,
                      size, "r", color, leading)
        self.y += 3

    def plain(self, s, size=9.6, leading=13.4, color=INK, fkey="r", maxw=None):
        maxw = maxw or (W - 2 * M - 16)
        lines = wrap(s, fkey, size, maxw)
        self.ensure(len(lines) * leading + 4)
        self.y = para(self.page, W - M - 8, self.y, "\n".join(lines), maxw,
                      size, fkey, color, leading)
        self.y += 4

    def box(self, items, heading, fill=(0.97, 0.98, 0.99), size=9.4):
        lines = [ln for it in items for ln in wrap(it, "r", size, W - 2 * M - 46)]
        h = 34 + len(lines) * 12.8 + len(items) * 4
        self.ensure(h + 10)
        page = self.page
        y0 = self.y
        page.draw_rect(pymupdf.Rect(M, y0, W - M, y0 + h), color=LIGHT,
                       fill=fill, width=0.8)
        page.draw_rect(pymupdf.Rect(M, y0, M + 3, y0 + h), color=None, fill=self.accent)
        text(page, W - M - 12, y0 + 18, heading, 10.5, "b", self.accent)
        yy = y0 + 34
        for it in items:
            ls = wrap(it, "r", size, W - 2 * M - 46)
            page.draw_circle((W - M - 14, yy - 3), 2.1, color=self.accent, fill=self.accent)
            yy = para(page, W - M - 24, yy, "\n".join(ls), W - 2 * M - 46,
                      size, "r", INK, 12.8)
            yy += 4
        self.y = y0 + h + 10


def lines_text(lines):
    return "\n".join(lines)


# ---------------------------------------------------------------------------
UNITS = BONE_UNITS + JOINT_UNITS + MUSCLE_UNITS
SECTION_OF = {}
for i, u in enumerate(UNITS):
    if i <= 6:
        SECTION_OF[u["key"]] = BONE
    elif i <= 11:
        SECTION_OF[u["key"]] = JOINT
    elif i <= 20:
        SECTION_OF[u["key"]] = MUSCLE
    else:
        SECTION_OF[u["key"]] = COMPARE

QNUM = {}
counter = 1
for u in UNITS:
    QNUM[u["key"]] = list(range(counter, counter + len(u["questions"])))
    counter += len(u["questions"])
INTEGRATED_NUMS = list(range(counter, counter + len(INTEGRATED_QUESTIONS)))
TOTAL_Q = counter + len(INTEGRATED_QUESTIONS) - 1


def draw_callouts(page, unit, rect, accent, tall=False):
    x0, y0, x1, y1 = rect.x0, rect.y0, rect.x1, rect.y1
    dw, dh = x1 - x0, y1 - y0
    # For very wide/short strips, spread the numbered labels into a taller
    # band around the image so the callout boxes do not overlap each other.
    if dh < 220 and not tall:
        label_y0, label_h = y0 - 60, dh + 120
    else:
        label_y0, label_h = y0, dh
    size = 7.4 if tall else 8.4
    for i, (tx, ty, lx, ly, side, label) in enumerate(unit["callouts"], 1):
        T = pymupdf.Point(x0 + tx * dw, y0 + ty * dh)
        L = pymupdf.Point(x0 + lx * dw, label_y0 + ly * label_h)
        lw = tw(label, "m", size) + 14
        if side == "R":
            left, right = L.x + 12, L.x + 12 + lw
        else:
            right, left = L.x - 12, L.x - 12 - lw
        dx = 0.0
        if right > W - 6:
            dx = (W - 6) - right
        if left < 6:
            dx = 6 - left
        left += dx
        right += dx
        B = pymupdf.Point(L.x + dx, L.y)
        page.draw_line(T, B, color=accent, width=0.9)
        page.draw_circle(T, 2.6, color=(1, 1, 1), fill=accent, width=0.8)
        page.draw_rect(pymupdf.Rect(left, B.y - 10, right, B.y + 10),
                       color=accent, fill=(1, 1, 1), width=0.6, fill_opacity=0.92)
        text(page, right - 6, B.y + size * 0.34, label, size, "m", INK)
        badge(page, B.x, B.y, i, accent, r=8.5, size=8)


def legend(page, unit, x_right, colw, y, accent):
    text(page, x_right, y, "راهنمای شماره ها؛ ریزنگاشت های درج شده روی تصویر", 10.5, "b", accent)
    y += 18
    size, lead = 9.1, 12.6
    for i, item in enumerate(unit["legend"], 1):
        ls = wrap(item, "r", size, colw - 26)
        badge(page, x_right - 7, y + 2, i, accent, r=7.5, size=7.4)
        y = para(page, x_right - 22, y, "\n".join(ls), colw - 26, size, "r", INK, lead)
        y += 6
    return y


def plate_page(doc, unit, idx, accent):
    page = new_page(doc, unit["title"], unit["src"], accent,
                    kicker="لوح " + fa(idx) + "  |  " + unit["no"])
    path = os.path.join(ROOT, unit["img"])
    iw, ih = Image.open(path).size
    tall = unit["layout"] == "tall"
    if tall:
        scale = min(215.0 / iw, 645.0 / ih)
        dw, dh = iw * scale, ih * scale
        x0, y0 = W - M - dw, 88.0
    else:
        scale = min((W - 2 * M) / iw, 392.0 / ih)
        dw, dh = iw * scale, ih * scale
        x0, y0 = (W - dw) / 2, (150.0 if dh < 220 else 84.0)
    rect = pymupdf.Rect(x0, y0, x0 + dw, y0 + dh)
    page.insert_image(rect, filename=path, keep_proportion=False)
    page.draw_rect(rect, color=LIGHT, width=0.8)
    draw_callouts(page, unit, rect, accent, tall)

    if tall:
        col_right, colw = M + 320, 320
        y = 98
    else:
        col_right, colw = W - M, W - 2 * M
        y = max(y0 + dh + 22, (y0 - 60 + dh + 120 + 16) if dh < 220 else 0)
    y = legend(page, unit, col_right, colw, y, accent)
    # source strip: right-aligned lines only, so nothing can collide.
    # On tall plates it goes below the image, never across it.
    ref_lines = wrap("منابع تکمیل: " + unit["refs"], "r", 7.8, W - 2 * M - 20)
    strip_h = 12 + len(ref_lines) * 11 + 15
    if tall:
        strip_y = max(y0 + dh + 8, H - 52 - strip_h)
    else:
        strip_y = min(y + 6, H - 52 - strip_h)
    page.draw_rect(pymupdf.Rect(M, strip_y, W - M, strip_y + strip_h),
                   color=None, fill=(0.96, 0.975, 0.985))
    page.draw_rect(pymupdf.Rect(M, strip_y, M + 3, strip_y + strip_h),
                   color=None, fill=accent)
    yy = strip_y + 12
    for ln in ref_lines:
        text(page, W - M - 8, yy, ln, 7.8, "r", MUTED)
        yy += 11
    text(page, W - M - 8, yy + 2,
         "تصویر استخراج شده از متن + حاشیه نویسی اختصاصی", 7.4, "m", accent)
    return page


def notes_page(doc, unit, accent, idx):
    title = "تکمیل پیشرفته و نکات پنهان | " + unit["no"]
    st = Story(doc, title, accent, kicker="برگهٔ تکمیلی لوح " + fa(idx), start=88)
    st.heading("۱  تکمیل از کتاب های پیشرفتهٔ زیستی و پزشکی")
    for b in unit["advanced"]:
        st.bullet(b, size=9.5)
    st.heading("۲  نکات پیدا و پنهان شکل و متن کتاب")
    st.box(unit["hidden"], "آنچه در تصویر/متن پنهان است", fill=(0.985, 0.97, 0.95))
    st.heading("۳  پیوند بالینی")
    st.box([unit["clinical"]], "کاربرد در پزشکی", fill=(0.95, 0.97, 0.99))
    st.heading("۴  پیوند با بانک تست")
    nums = " و ".join(fa(n) for n in QNUM[unit["key"]])
    st.plain("پرسش های چالشی وابسته به این لوح، شماره های " + nums + " در بانک تست",
             size=9.6, color=accent, fkey="m")
    st.plain("پاسخ تشریحی همهٔ پرسش ها در بخش پاسخنامه آمده است.", size=9.2, color=MUTED)
    return st.page


def cover(doc):
    page = doc.new_page(width=W, height=H)
    register_fonts(page)
    hero = os.path.join(ROOT, "figure_crops", "F00_prosthesis.jpg")
    page.insert_image(pymupdf.Rect(0, 0, W, 330), filename=hero, keep_proportion=False)
    page.draw_rect(pymupdf.Rect(0, 0, W, 330), color=None, fill=(0.04, 0.13, 0.18),
                   fill_opacity=0.58)
    page.draw_rect(pymupdf.Rect(0, 320, W, 338), color=None, fill=BONE)
    text(page, W - 40, 128, "اطلس تشریحی و تکمیلی", 25, "b", (1, 1, 1))
    text(page, W - 40, 166, "دستگاه حرکتی", 30, "b", (1, 1, 1))
    text(page, W - 40, 202, "استخوان • مفصل • ماهیچه • اسکلت جانوران", 13, "m", (0.92, 0.96, 0.97))
    text(page, W - 40, 246, "بر پایهٔ فصل سوم کتاب زیست شناسی یازدهم (صفحات ۳۷ تا ۵۲)", 10.5, "r", (0.9, 0.94, 0.96))
    text(page, W - 40, 272, "استخراج تمام تصاویر • درج ریز اطلاعات روی تصویر • تکمیل دانشگاهی • تست های چالشی", 9.5, "r", (0.9, 0.94, 0.96))

    y = 370
    page.draw_rect(pymupdf.Rect(M, y, W - M, y + 62), color=None, fill=(0.94, 0.97, 0.97))
    page.draw_rect(pymupdf.Rect(M, y, M + 4, y + 62), color=None, fill=BONE)
    text(page, W - M - 14, y + 24, "پیشگفتار", 12, "b", BONE)
    y = para(page, W - M - 14, y + 44,
             "این اطلس با نگاه یک زیست شناس تنظیم شده است: نخست تک تک تصاویر جاسازی شده در پروندهٔ PDF از متن جدا شد، سپس هر شکل با جزئیاتی که کتاب درسی نگفته (بافت شناسی، فیزیولوژی، ژنتیک مولکولی و پزشکی بالینی) کامل و همان اطلاعات به صورت شماره دار روی خود تصویر درج گردید. در پایان، از نکات آشکار و پنهان شکل ها، پرسش های دشوار و تحلیلی طرح شده است.",
             W - 2 * M - 28, 9.6, "r", INK, 14)

    stats = [
        (fa(28), "عکس جاسازی شده استخراج شد"),
        (fa(22), "لوح تشریحی و تکمیلی"),
        (fa(TOTAL_Q), "تست چالشی با پاسخ تشریحی"),
        (fa(132), "ریزنگاشت روی تصاویر"),
    ]
    yy = y + 24
    for i, (n, lab) in enumerate(stats):
        x = M + (i % 2) * 265
        ry = yy + (i // 2) * 66
        page.draw_rect(pymupdf.Rect(x, ry, x + 255, ry + 56), color=LIGHT,
                       fill=(0.97, 0.985, 0.99), width=0.8)
        text(page, x + 245, ry + 30, n, 19, "b", BONE)
        text(page, x + 225 - tw(n, "b", 19) - 6, ry + 30, lab, 9.2, "r", INK)

    yy += 150
    page.draw_rect(pymupdf.Rect(M, yy, W - M, yy + 96), color=None, fill=(0.99, 0.97, 0.94))
    page.draw_rect(pymupdf.Rect(M, yy, M + 4, yy + 96), color=None, fill=GOLD)
    text(page, W - M - 14, yy + 24, "یادداشت روش شناسی", 11, "b", GOLD)
    yy = para(page, W - M - 14, yy + 44,
              "پرسش های مربوط به شکل های ۱ و ۹ و اعداد جدول فعّالیت ۲، که کتاب درسی طرح پرسش حفظی از آن ها را در آزمون های سراسری منع کرده، در این اطلس به صورت تحلیلی و مبتنی بر سازوکار طرح شده اند؛ یعنی به جای حفظ جانمایی برچسب و عدد خام، استدلال، مقایسهٔ روندها و پیامد علّی سنجیده می شود. منابع دانشگاهی در پایان کتاب آمده اند.",
              W - 2 * M - 28, 9.3, "r", INK, 13.6)
    return page


def guide_page(doc):
    page = new_page(doc, "راهنمای استفاده و نقشهٔ اطلس", "ساختار پرونده و شیوهٔ مطالعه", BONE,
                    kicker="پیش از آغاز")
    y = 96
    sections = [
        ("۱  لوح های تصویری (Plate)",
         "هر لوح، تصویر استخراج شدهٔ کتاب به همراه برچسب های اصلی خود کتاب است. شماره های درون دایره های رنگی، با پیکان به ساختمان مورد نظر اشاره می کنند و عنوان کوتاه کنارشان «روی خود تصویر» درج شده است. «راهنمای شماره ها» زیر یا کنار تصویر، همان شماره ها را با اطلاعات ریز (ابعاد، مولکول ها، سازوکار، آمار بالینی) باز می کند."),
        ("۲  برگهٔ تکمیلی",
         "چهار بخش دارد: تکمیل از منابع دانشگاهی و پزشکی، نکات پیدا و پنهان شکل و متن کتاب، پیوند بالینی، و شمارهٔ تست های وابسته به همان لوح. اینجا جایی است که ساده سازی های کتاب درسی (مثلاً نقش ATP در کندن پل های میوزین، یا نقش لاکتات در درد عضلانی) با دقت علمی اصلاح می شود."),
        ("۳  بانک تست های چالشی",
         "۵۲ پرسش چهارگزینه ای در سه سطح «دشوار»، «بسیار دشوار» و «المپیادی». ۴۴ پرسش به ترتیب لوح ها و ۸ پرسش یکپارچه در پایان آمده اند. پرسش ها ترکیبی از داده کاوی جدول، تحلیل پیکان های شکل، مقایسهٔ بافت ها، زنجیرهٔ علّی مولکولی و نکات پنهان اند."),
        ("۴  پاسخنامه",
         "نخست یک جدول فشرده از کلید پاسخ ها، سپس پاسخ تشریحی تک تک پرسش ها با ذکر دلیل نادرستی گزینه های دیگر و ارجاع به شکل مربوطه."),
        ("۵  پرونده های همراه",
         "پوشهٔ extracted_images حاوی ۲۸ شیء تصویری جدا شده از PDF اصلی (بدون دخل و تصرف در پیکسل ها)، پوشهٔ figure_crops حاوی برش های با کیفیت بالای شکل ها به همراه برچسب های چاپی، وQuestion_Bank_Challenge.pdf نسخهٔ جداگانهٔ تست ها و پاسخنامه است."),
    ]
    for head, body in sections:
        page.draw_rect(pymupdf.Rect(M, y, W - M, y + 24), color=None, fill=(0.94, 0.97, 0.97))
        page.draw_rect(pymupdf.Rect(M, y, M + 3, y + 24), color=None, fill=BONE)
        text(page, W - M - 10, y + 16, head, 10.5, "b", BONE)
        y += 30
        y = para(page, W - M - 10, y, body, W - 2 * M - 20, 9.5, "r", INK, 13.4)
        y += 12
    return page


def inventory_page(doc):
    page = new_page(doc, "فهرست کامل تصاویر استخراج شده", "۲۸ شیء تصویری جاسازی شده در PDF منبع", BONE,
                    kicker="پیوست الف")
    inv = json.load(open(os.path.join(ASSET, "image_inventory.json"), encoding="utf-8"))
    cols = [W - M, W - M - 55, W - M - 125, W - M - 210, W - M - 350]
    heads = ["ردیف", "صفحه", "xref", "ابعاد px", "پروندهٔ استخراج شده"]
    y = 96
    page.draw_rect(pymupdf.Rect(M, y, W - M, y + 24), color=None, fill=BONE)
    for x, h in zip(cols, heads):
        text(page, x - 6, y + 16, h, 8.8, "b", (1, 1, 1))
    y += 24
    for i, e in enumerate(inv, 1):
        if i % 2 == 0:
            page.draw_rect(pymupdf.Rect(M, y, W - M, y + 19), color=None, fill=(0.97, 0.98, 0.985))
        vals = [fa(i), fa(e["page"]), str(e["xref"]),
                "%d×%d" % (e["width"], e["height"]), e["file"]]
        for j, (x, v) in enumerate(zip(cols, vals)):
            text(page, x - 6, y + 13, v, 8.0, "r", INK)
        y += 19
        page.draw_line((M, y), (W - M, y), color=LIGHT, width=0.4)
    y += 12
    y = para(page, W - M - 8, y,
             "توضیح: تصویر p01_xref224 همان کد QR صفحهٔ آغازین فصل است و محتوای زیستی ندارد؛ با این حال برای «استخراج همهٔ تصاویر» در فهرست و پوشهٔ extracted_images نگه داشته شده است. صفحهٔ ۵۲ کتاب فاقد شیء تصویری است، بنابراین لوح تطبیقی مربوط به آن از روی متن و منابع دانشگاهی بازسازی شده است.",
             W - 2 * M - 16, 9.1, "r", MUTED, 13)
    return page


def question_card(st, q, num, accent, tag=None):
    stem, options, ans, explain, level = q
    size, lead = 9.5, 13.2
    ls = wrap(stem, "m", size, W - 2 * M - 30)
    opt_lines = [wrap("(" + fa(k + 1) + ")  " + o, "r", 9.0, W - 2 * M - 36)
                 for k, o in enumerate(options)]
    n_opt_lines = sum(len(o) for o in opt_lines)
    h = 24 + len(ls) * lead + n_opt_lines * 12.4 + 4 * 2.6 + 12
    st.ensure(h + 12)
    page = st.page
    y0 = st.y
    page.draw_rect(pymupdf.Rect(M, y0, W - M, y0 + h), color=LIGHT,
                   fill=(0.985, 0.99, 0.995), width=0.7)
    page.draw_rect(pymupdf.Rect(M, y0, M + 3, y0 + h), color=None, fill=accent)
    text(page, W - M - 12, y0 + 16, "سؤال " + fa(num), 10, "b", accent)
    text_left(page, M + 12, y0 + 16, "سطح: " + level + ("  |  " + tag if tag else ""),
              7.8, "r", MUTED)
    yy = y0 + 32
    yy = para(page, W - M - 14, yy, "\n".join(ls), W - 2 * M - 30,
              size, "m", INK, lead)
    yy += 4
    for k, ols in enumerate(opt_lines):
        for j, line in enumerate(ols):
            text(page, W - M - 20, yy, line, 9.0, "r", INK if j == 0 else MUTED)
            yy += 12.4
        yy += 2.6
    st.y = y0 + h + 10


def build_question_section(doc):
    st = Story(doc, "بانک تست های چالشی", MUSCLE,
               kicker="بخش نخست: ۵۲ پرسش چهارگزینه ای", start=88)
    st.heading("پرسش های وابسته به لوح ها (۴۴ پرسش)")
    n = 1
    for u in UNITS:
        accent = SECTION_OF[u["key"]]
        st.ensure(30)
        st.page.draw_rect(pymupdf.Rect(M, st.y, W - M, st.y + 20),
                          color=None, fill=(0.95, 0.97, 0.98))
        text(st.page, W - M - 10, st.y + 14, u["no"] + "  |  " + u["title"],
             9.2, "b", accent)
        st.y += 26
        for q in u["questions"]:
            question_card(st, q, n, accent)
            n += 1
    st.heading("آزمون یکپارچهٔ سطح برتر (۸ پرسش ترکیبی)", size=11.5)
    st.plain("این پرسش ها میان چند شکل و چند بخش فصل پل می زنند و برای سنجش انتقال مفاهیم طراحی شده اند.",
             size=9.4, color=MUTED)
    for q in INTEGRATED_QUESTIONS:
        question_card(st, q, n, GOLD, tag="یکپارچه")
        n += 1
    return st


def answer_section(doc, all_questions):
    start_page = doc.page_count
    # compact key sheet
    page = new_page(doc, "کلید فشردهٔ پاسخ ها", "همهٔ ۵۲ پرسش در یک نگاه", GOLD,
                    kicker="پاسخنامه")
    page.draw_rect(pymupdf.Rect(M, 92, W - M, 116), color=None, fill=BONE)
    text(page, W - M - 10, 108, "شمارهٔ سؤال ← شمارهٔ گزینهٔ درست", 10, "b", (1, 1, 1))
    y = 132
    per_row = 10
    for i in range(0, len(all_questions), per_row):
        chunk = all_questions[i:i + per_row]
        page.draw_rect(pymupdf.Rect(M, y, W - M, y + 40), color=LIGHT,
                       fill=(0.98, 0.99, 0.99), width=0.6)
        for j, q in enumerate(chunk):
            x = W - M - 12 - j * 52
            text(page, x, y + 16, fa(i + j + 1), 8.6, "r", MUTED)
            text(page, x, y + 32, fa(q[2] + 1), 11, "b", GOLD)
        y += 46
    y += 10
    y = para(page, W - M - 10, y,
             "راهنمایی: پاسخ های «بسیار دشوار» و «المپیادی» معمولاً با یک واسطهٔ مولکولی یا یک مقایسهٔ کمی به دست می آیند؛ در پاسخ تشریحی، دلیل رد گزینه های دیگر هم آمده است.",
             W - 2 * M - 20, 9.3, "r", INK, 13.5)

    st = Story(doc, "پاسخنامهٔ تشریحی", GOLD, kicker="بخش دوم: تحلیل گزینه به گزینه", start=88)
    for i, q in enumerate(all_questions, 1):
        stem, options, ans, explain, level = q
        st.ensure(96)
        page = st.page
        y0 = st.y
        page.draw_rect(pymupdf.Rect(M, y0, W - M, y0 + 22), color=None, fill=(0.97, 0.96, 0.92))
        text(page, W - M - 10, y0 + 15, "سؤال " + fa(i), 10, "b", GOLD)
        text(page, W - M - 110, y0 + 15, "گزینهٔ درست: " + fa(ans + 1), 9.5, "b", BONE)
        text_left(page, M + 10, y0 + 15, level, 8, "r", MUTED)
        st.y = y0 + 30
        st.plain(explain, size=9.4, leading=13.2)
        st.y += 8
    return start_page


def references_page(doc):
    page = new_page(doc, "منابع تکمیلی و یادداشت پایانی", "کتاب های دانشگاهی مورد استناد در حاشیه نویسی ها", COMPARE,
                    kicker="پیوست ب")
    y = 96
    refs = [
        "Junqueira's Basic Histology: Text & Atlas — بافت استخوان، غضروف، بافت پیوندی و ماهیچه؛ سامانهٔ هاورس، لایه های پریوستئوم و انواع تارها.",
        "Ross & Pawlina, Histology — اوستئون، استئوسیت/کانالیکول، انتزیس، کندروسیت و پردهٔ سینوویال.",
        "Guyton & Hall, Textbook of Medical Physiology — واحد حرکتی، جفت شدن برانگیختگی-انقباض، انرژی عضله، هورمون های کلسیم.",
        "Boron & Boulpaep, Medical Physiology — DHPR/RyR1، چرخهٔ اتصال متقابل، ایزوفرم های میوزین، بازتاب های نخاعی.",
        "Alberts et al., Molecular Biology of the Cell — اکتین/میوزین، تیتین، ماتریس برون سلولی، کوستامرها و مولکول های چسبندگی.",
        "Gray's Anatomy / Netter's Atlas — کالبدشناسی اسکلت محوری و جانبی، درزها، مفاصل، رباط صلیبی و خونرسانی سر ران.",
        "Robbins & Cotran, Pathologic Basis of Disease — ترمیم شکستگی، پوکی استخوان، روماتیسم مفصلی و استخوان سازی نابجا.",
        "Harrison's Principles of Internal Medicine — T-score/DXA، FRAX، درمان های ضدپوکی، هیپرترمی بدخیم و میاستنی.",
        "Rockwood & Green's Fractures in Adults； Nordin & Frankel, Basic Biomechanics — شکستگی گردن ران، ACL و اهرم بندی مفاصل.",
        "Schmidt-Nielsen, Animal Physiology； Brusca & Brusca, Invertebrates — اسکلت هیدرواستاتیک، بیرونی و درونی، مقیاس بندی و تکانه.",
        "کتاب درسی زیست شناسی یازدهم، فصل ۳ «دستگاه حرکتی» (صفحات ۳۷ تا ۵۲) — منبع همهٔ تصاویر و متن پایه.",
    ]
    for r in refs:
        ls = wrap(r, "r", 9.3, W - 2 * M - 26)
        page.draw_circle((W - M - 4, y), 2.2, color=COMPARE, fill=COMPARE)
        y = para(page, W - M - 14, y + 3, "\n".join(ls), W - 2 * M - 26, 9.3, "r", INK, 13.2)
        y += 7
    y += 12
    page.draw_rect(pymupdf.Rect(M, y, W - M, y + 74), color=None, fill=(0.96, 0.97, 0.98))
    page.draw_rect(pymupdf.Rect(M, y, M + 3, y + 74), color=None, fill=COMPARE)
    y = para(page, W - M - 14, y + 20,
             "یادداشت پایانی: این پرونده یک ابزار آموزشی تکمیلی است؛ اعداد بالینی و نام داروها برای درک سازوکارها آورده شده و نباید به عنوان توصیهٔ درمانی تلقی شوند. تصاویر پایه از پروندهٔ بارگذاری شده استخراج شده و تمام حاشیه نویسی ها، نمودارها و پرسش ها به طور اختصاصی برای این اطلس تولید شده اند.",
             W - 2 * M - 28, 9.2, "r", MUTED, 13.4)
    return page


def main():
    doc = pymupdf.open()
    cover(doc)
    guide_page(doc)
    inventory_page(doc)
    for idx, u in enumerate(UNITS, 1):
        accent = SECTION_OF[u["key"]]
        plate_page(doc, u, idx, accent)
        notes_page(doc, u, accent, idx)
    q_start = doc.page_count
    build_question_section(doc)
    all_q = []
    for u in UNITS:
        all_q.extend(u["questions"])
    all_q.extend(INTEGRATED_QUESTIONS)
    answer_start = doc.page_count
    answer_section(doc, all_q)
    references_page(doc)
    for i, page in enumerate(doc, 1):
        footer(page, i, "اطلس تشریحی و تکمیلی دستگاه حرکتی | زیست یازدهم، فصل ۳ | " + fa(len(UNITS)) + " لوح")
    try:
        doc.subset_fonts()
    except Exception as exc:
        print("font subsetting skipped:", exc)
    doc.save(OUT_FULL, garbage=4, deflate=True, clean=True)
    print("saved", OUT_FULL, "pages", doc.page_count, "size",
          round(os.path.getsize(OUT_FULL) / 1024 / 1024, 2), "MB")

    qdoc = pymupdf.open()
    c = qdoc.new_page(width=W, height=H)
    register_fonts(c)
    c.draw_rect(pymupdf.Rect(0, 0, W, 10), color=None, fill=MUSCLE)
    c.draw_rect(pymupdf.Rect(M, 150, W - M, 430), color=LIGHT,
                fill=(0.985, 0.96, 0.96), width=0.8)
    c.draw_rect(pymupdf.Rect(M, 150, M + 5, 430), color=None, fill=MUSCLE)
    text(c, W - M - 20, 210, "بانک تست های چالشی", 24, "b", MUSCLE)
    text(c, W - M - 20, 246, "و پاسخنامهٔ تشریحی", 18, "b", INK)
    c.draw_line((M + 20, 268), (W - M - 20, 268), color=LIGHT, width=0.8)
    y = para(c, W - M - 20, 296,
             "نسخهٔ مستقل از بخش تست اطلس تشریحی دستگاه حرکتی (زیست یازدهم، فصل ۳). "
             "۵۲ پرسش چهارگزینه ای در سطوح دشوار، بسیار دشوار و المپیادی، همراه با کلید فشرده و پاسخنامهٔ تحلیلی. "
             "منبع تصویری پرسش ها، ۲۲ لوح حاشیه نویسی شده در Atlas_Dastgah_Harekaty.pdf است.",
             W - 2 * M - 40, 10.5, "r", INK, 16)
    text(c, W - M - 20, 374, "چهل و چهار پرسش وابسته به لوح های تصویری", 10, "m", MUSCLE)
    text(c, W - M - 20, 396, "هشت پرسش یکپارچهٔ سطح برتر", 10, "m", MUSCLE)
    qdoc.insert_pdf(doc, from_page=q_start, to_page=doc.page_count - 1)
    original_names = dict(FONT_NAMES)
    FONT_NAMES.update({"r": "qvz", "m": "qvzm", "b": "qvzb"})
    for j in range(1, qdoc.page_count):
        pg = qdoc[j]
        for k, name in FONT_NAMES.items():
            pg.insert_font(fontname=name, fontfile=FONT_FILES[k])
        pg.draw_rect(pymupdf.Rect(0, H - 46, W, H), color=None, fill=(1, 1, 1))
        footer(pg, j + 1, "بانک تست های چالشی | دستگاه حرکتی | زیست یازدهم، فصل ۳")
    FONT_NAMES.clear()
    FONT_NAMES.update(original_names)
    qdoc.save(OUT_QUESTIONS, garbage=4, deflate=True)
    print("saved", OUT_QUESTIONS, "pages", qdoc.page_count,
          "size", round(os.path.getsize(OUT_QUESTIONS) / 1024 / 1024, 2), "MB")
    doc.close()
    qdoc.close()
    return q_start, answer_start


if __name__ == "__main__":
    main()
