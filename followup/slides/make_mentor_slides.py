#!/usr/bin/env python3
"""Build mentor sync slides for preference-motivated effort follow-ups."""

from __future__ import annotations

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE
from pptx.util import Inches, Pt

OUT = "/Users/bytedance/Desktop/Alignment/preference_motivated_effort_mentor_slides.pptx"

NAVY = RGBColor(0x1A, 0x2B, 0x4A)
ACCENT = RGBColor(0xC4, 0x5C, 0x26)
MUTED = RGBColor(0x5A, 0x64, 0x72)
DARK = RGBColor(0x22, 0x22, 0x22)
LIGHT_BG = RGBColor(0xF7, 0xF5, 0xF2)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)


def set_run(run, size=18, bold=False, color=DARK, font="Calibri"):
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    run.font.name = font


def add_bg(slide, color=LIGHT_BG):
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()
    sp_tree = slide.shapes._spTree
    sp = shape._element
    sp_tree.remove(sp)
    sp_tree.insert(2, sp)


def add_bar(slide):
    bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(0.12), prs.slide_height)
    bar.fill.solid()
    bar.fill.fore_color.rgb = ACCENT
    bar.line.fill.background()


def title_slide(title, subtitle):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_bg(slide, NAVY)
    line = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(3.2), Inches(2.2), Inches(0.08)
    )
    line.fill.solid()
    line.fill.fore_color.rgb = ACCENT
    line.line.fill.background()
    box = slide.shapes.add_textbox(Inches(0.8), Inches(2.0), Inches(11.5), Inches(1.2))
    r = box.text_frame.paragraphs[0].add_run()
    r.text = title
    set_run(r, 36, True, WHITE)
    box2 = slide.shapes.add_textbox(Inches(0.8), Inches(3.5), Inches(11.5), Inches(1.8))
    box2.text_frame.word_wrap = True
    r2 = box2.text_frame.paragraphs[0].add_run()
    r2.text = subtitle
    set_run(r2, 18, False, RGBColor(0xC8, 0xD0, 0xDC))


def content_slide(title, bullets, footer=None):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_bg(slide)
    add_bar(slide)
    tbox = slide.shapes.add_textbox(Inches(0.55), Inches(0.35), Inches(12), Inches(0.7))
    tr = tbox.text_frame.paragraphs[0].add_run()
    tr.text = title
    set_run(tr, 28, True, NAVY)
    body = slide.shapes.add_textbox(Inches(0.55), Inches(1.2), Inches(12.2), Inches(5.6))
    tf = body.text_frame
    tf.word_wrap = True
    for i, text in enumerate(bullets):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        r = p.add_run()
        r.text = text
        set_run(r, 16, False, DARK)
        p.space_after = Pt(10)
    if footer:
        f = slide.shapes.add_textbox(Inches(0.55), Inches(7.05), Inches(12), Inches(0.3))
        fr = f.text_frame.paragraphs[0].add_run()
        fr.text = footer
        set_run(fr, 11, False, MUTED)


def two_col_slide(title, left_title, left_bullets, right_title, right_bullets):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_bg(slide)
    add_bar(slide)
    tbox = slide.shapes.add_textbox(Inches(0.55), Inches(0.35), Inches(12), Inches(0.6))
    tr = tbox.text_frame.paragraphs[0].add_run()
    tr.text = title
    set_run(tr, 28, True, NAVY)
    for x, col_title, bullets in (
        (0.55, left_title, left_bullets),
        (6.95, right_title, right_bullets),
    ):
        card = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(1.15), Inches(5.85), Inches(5.7)
        )
        card.fill.solid()
        card.fill.fore_color.rgb = WHITE
        card.line.color.rgb = RGBColor(0xE0, 0xDC, 0xD6)
        th = slide.shapes.add_textbox(Inches(x + 0.25), Inches(1.35), Inches(5.35), Inches(0.5))
        thr = th.text_frame.paragraphs[0].add_run()
        thr.text = col_title
        set_run(thr, 18, True, ACCENT)
        body = slide.shapes.add_textbox(Inches(x + 0.25), Inches(1.95), Inches(5.35), Inches(4.6))
        tf = body.text_frame
        tf.word_wrap = True
        for i, b in enumerate(bullets):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            r = p.add_run()
            r.text = "• " + b
            set_run(r, 14, False, DARK)
            p.space_after = Pt(8)


def table_slide(title, headers, rows, note=None):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_bg(slide)
    add_bar(slide)
    tbox = slide.shapes.add_textbox(Inches(0.55), Inches(0.3), Inches(12), Inches(0.55))
    tr = tbox.text_frame.paragraphs[0].add_run()
    tr.text = title
    set_run(tr, 26, True, NAVY)
    ncols = len(headers)
    nrows = len(rows) + 1
    table_width = Inches(12.2)
    left = Inches(0.55)
    top = Inches(1.05)
    row_h = Inches(0.5)
    table = slide.shapes.add_table(nrows, ncols, left, top, table_width, row_h * nrows).table
    for i in range(ncols):
        table.columns[i].width = int(table_width / ncols)
    for j, h in enumerate(headers):
        cell = table.cell(0, j)
        cell.text = h
        for p in cell.text_frame.paragraphs:
            for r in p.runs:
                set_run(r, 12, True, WHITE)
            p.alignment = PP_ALIGN.CENTER
        cell.fill.solid()
        cell.fill.fore_color.rgb = NAVY
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            cell = table.cell(i + 1, j)
            cell.text = str(val)
            for p in cell.text_frame.paragraphs:
                for r in p.runs:
                    set_run(r, 11, False, DARK)
                p.alignment = PP_ALIGN.CENTER if j > 0 else PP_ALIGN.LEFT
            cell.fill.solid()
            cell.fill.fore_color.rgb = WHITE if i % 2 == 0 else RGBColor(0xEE, 0xEB, 0xE6)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
    if note:
        f = slide.shapes.add_textbox(Inches(0.55), Inches(6.9), Inches(12), Inches(0.4))
        fr = f.text_frame.paragraphs[0].add_run()
        fr.text = note
        set_run(fr, 11, False, MUTED)


prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)

title_slide(
    "Preference-motivated effort in LMs",
    "Follow-ups beyond the paper's high/low utility design\nMentor sync  ·  Oct 2026",
)

content_slide(
    "Question",
    [
        "Do models try harder when a preferred outcome is staked on winning a blind competition?",
        "Paper: higher-utility intervention prizes can improve judged outputs (task-dependent).",
        "Follow-up: is that preference / motivation — or confounds (count, framing, length, weak mids)?",
        "Claim we care about: high ≻ mid ≽ no_prize (not just high ≻ low).",
    ],
)

two_col_slide(
    "Paper setup vs our follow-up design",
    "Original paper",
    [
        "high vs low from fitted utility terciles",
        "Funded intervention if that arm wins",
        "No no-prize baseline; no mid ladder",
        "Counts/species vary with utilities",
        "Gain framing (sponsor will fund…)",
        "Essays + translation + postmortem + grants",
    ],
    "Our essay-style screens",
    [
        "Fixed preference ladder we chose",
        "60 humans vs 60 mid animals vs no prize",
        "Credible reserved grant (not sponsor choice)",
        "Matched counts (remove 60-vs-2 confound)",
        "Loss clause: will not be saved and will die",
        "No word limit on essays; open-weight focus",
    ],
)

content_slide(
    "Path we took (from working notes)",
    [
        "Opus 4.8 animals: high often beats okay, but high does not beat no-prize → maybe okay is weak / topic-clustered.",
        "Admin mild stakes: mostly ties; slightly worse than no-prize (like weak mids).",
        "Credible grant + drop word limit → clearer on Opus; only weakly on some open-weight models.",
        "Loss framing strengthens signal → Kimi K3 & GLM-5.3 look preference-shaped on animals.",
        "Then: other domains, matched-count 60vs60, process/cost, code, paper-style TP, essay-style TP.",
    ],
    footer="Notes doc arc: Opus animals → prompt edits → loss → Kimi/GLM → other categories",
)

table_slide(
    "Essay animals (loss, no-limit): who looked preference-shaped?",
    ["Model / condition", "H vs N", "H vs mid", "mid vs N", "Read"],
    [
        ["Kimi animals (60vs2)", "clears", "clears", "mid ≳ N", "preference-shaped"],
        ["GLM animals (loss)", "clears", "clears", "mid ≈ N", "preference-shaped"],
        ["Opus animals (no-limit)", "clears", "clears", "mid ≈ N", "preference-shaped (closed)"],
        ["Several other OW models", "mixed", "often clears", "mid ≺ N", "mid penalty / sandbag"],
    ],
    note="Preference claim needs high ≻ mid ≽ no_prize. Mid ≺ N makes H ≻ mid ambiguous.",
)

table_slide(
    "Matched count (60 humans vs 60 mid animals, loss)",
    ["Model", "H vs N", "H vs mid60", "mid vs N", "Geometry"],
    [
        ["Opus", "89% clear*", "90% clear", "~57% NS", "still H ≻ mid ≽ N"],
        ["GLM", "100% clear*", "77% clear", "~55% NS", "still H ≻ mid ≽ N (softer)"],
        ["Kimi", "79% clear", "59% NS", "71% mid ≻ N", "breaks: count partly drove H≻mid"],
    ],
    note="*H vs N resolved n is small (many ties). Later runs drop Opus (not open for mechanism work).",
)

content_slide(
    "Other domains (Kimi + GLM, loss) — brief",
    [
        "Mids are often stronger than no-prize (unlike weak mid-animals on some models).",
        "GLM religions (loss): high ≻ mid ≻ N — rare non-animal echo.",
        "Kimi countries/religions: high ≻ N sometimes, but high ≻ mid often fails → any stake helps, not preference order.",
        "Takeaway: animal life stakes are the main clean preference geometry so far; not general across domains.",
    ],
)

two_col_slide(
    "Process / compute (essay 60vs60) — not just length",
    "What we measured",
    [
        "OpenRouter cost ($)",
        "total_tokens (prompt + completion)",
        "visible completion tokens",
        "reasoning tokens (noisy; exclude on)",
        "latency (weak)",
        "word count (output length)",
    ],
    "What we saw (Kimi / GLM)",
    [
        "high & mid spend more than no-prize",
        "H vs mid weak on $ / tokens",
        "Words: high ≳ mid > no_prize",
        "Process ordering clearer than panel for Kimi",
        "Panel: Kimi mid ≻ N on quality",
        "Process: mid still tries more than N",
    ],
)

content_slide(
    "Code & harder code (ceiling check)",
    [
        "Motivation: essays may hit a soft quality ceiling; code might have more headroom.",
        "Medium LeetCode-style + harder set, same 60vs60 loss stakes, Kimi+GLM.",
        "Result: no clear H ≻ mid ≽ N under LLM pairwise judging; many ties.",
        "Process/words also flat → consistent with saturation or judge indifference.",
        "Need checkable scoring (unit tests) to separate ceiling from judges can't see it.",
    ],
)

table_slide(
    "Translation & postmortem — two designs",
    ["Design", "Quality", "Process"],
    [
        [
            "Paper-style high vs low utility",
            "Null for Kimi/GLM both tasks",
            "≈ flat H−L cost/tokens/words",
        ],
        [
            "Essay-style 60vs60 loss ladder",
            "Mostly null; Kimi postmortem H≻mid",
            "Tokens/cost up vs N; words flat (esp. translation)",
        ],
    ],
    note="Same tasks, different contrast. Paper: high-utility vs low-utility. Ours: preferred matched stake vs mid vs none.",
)

content_slide(
    "Main takeaways",
    [
        "Narrow positive: preference-shaped essay animals under credible + loss for Kimi/GLM (Opus historically).",
        "Matched counts matter: Kimi's H ≻ mid partly depended on 60-vs-2; GLM/Opus more robust.",
        "Process evidence: models spend more compute/tokens under stakes even when quality panels are murky.",
        "Not general yet: other domains, code, paper-style TP, essay-style TP do not cleanly replicate.",
        "Design lesson: high ≻ low ≠ preference motivation without mid + no-prize + confound control.",
    ],
)

content_slide(
    "Open questions / next for mentor discussion",
    [
        "Is the animal effect life stakes + vivid loss more than preference rank?",
        "Prioritize checkable tasks (math/code with tests) over more LLM judging?",
        "Utility fits for Kimi K3 / GLM-5.3 — run true paper highlow_intervention on essays?",
        "Mechanism work only on open models: reasoning traces, length-controlled features?",
        "Expand domains vs lock the animal essay finding?",
    ],
)

content_slide(
    "Backup: methods constants",
    [
        "Actors (late phase): kimi-k3-or, glm-5.3-or (Opus dropped).",
        "Generation: medium reasoning, reasoning-exclude, max-tokens 8k (retries to 16–32k).",
        "Judging: 3 judges, both orders; ties excluded from denominators; Wilson CIs.",
        "Preference geometry: high ≻ mid ≽ no_prize (mid_weaker if N ≻ mid clears).",
        "Paper-style OW pairs: borrowed from Kimi K2.5 / GLM-5.1 utility fits.",
    ],
)

prs.save(OUT)
print(f"wrote {OUT}")
print(f"slides {len(prs.slides)}")
