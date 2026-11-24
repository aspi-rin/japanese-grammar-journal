#!/usr/bin/env python3
"""Render a standalone interactive Japanese grammar daily journal HTML page.

Combines the warm hand-journal layout (4 color-coded grammar sections, non-sticky
control bar, bedtime review + interactive quiz + 0.85x playlist, FishAudio proxy +
Web Speech fallback) with the minimalist dot-to-wave pronunciation indicator.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path
from typing import Any

THEME_ORDER = ["indigo", "emerald", "orange", "purple"]

THEMES: dict[str, dict[str, str]] = {
    "indigo": {
        "section_border": "border-indigo-100",
        "banner_bg": "from-indigo-600 to-indigo-500",
        "banner_sub": "text-indigo-100",
        "formula_box": "bg-indigo-50/70 border-indigo-200/70",
        "formula_label": "text-indigo-600",
        "formula_tip": "text-indigo-800/80",
        "bar": "bg-indigo-500",
        "title": "text-indigo-700",
        "accent_box": "bg-indigo-50/60 border-indigo-200/70",
        "accent_title": "text-indigo-800",
        "phrase_card": "bg-indigo-50/65 hover:bg-indigo-100/70 border-indigo-200/90",
        "phrase_tag": "bg-indigo-200/75 text-indigo-800",
        "tag_theme": "bg-indigo-100 text-indigo-800 border-indigo-200",
        "mnemonic_border": "border-indigo-500",
        "mnemonic_title": "text-indigo-700",
        "table_text": "text-indigo-300",
        "playlist_text": "text-indigo-300",
        "note_badge": "text-indigo-700 bg-indigo-50/90 border-indigo-200/70",
    },
    "emerald": {
        "section_border": "border-emerald-100",
        "banner_bg": "from-emerald-600 to-teal-600",
        "banner_sub": "text-emerald-100",
        "formula_box": "bg-emerald-50/70 border-emerald-200/70",
        "formula_label": "text-emerald-700",
        "formula_tip": "text-emerald-900/80",
        "bar": "bg-emerald-600",
        "title": "text-emerald-700",
        "accent_box": "bg-emerald-50/60 border-emerald-200/70",
        "accent_title": "text-emerald-800",
        "phrase_card": "bg-emerald-50/65 hover:bg-emerald-100/70 border-emerald-200/90",
        "phrase_tag": "bg-emerald-200/75 text-emerald-800",
        "tag_theme": "bg-emerald-100 text-emerald-800 border-emerald-200",
        "mnemonic_border": "border-emerald-500",
        "mnemonic_title": "text-emerald-700",
        "table_text": "text-emerald-300",
        "playlist_text": "text-emerald-300",
        "note_badge": "text-emerald-800 bg-emerald-50/90 border-emerald-200/70",
    },
    "orange": {
        "section_border": "border-orange-100",
        "banner_bg": "from-orange-500 to-amber-500",
        "banner_sub": "text-orange-50",
        "formula_box": "bg-orange-50/70 border-orange-200/70",
        "formula_label": "text-orange-700",
        "formula_tip": "text-orange-900/80",
        "bar": "bg-orange-500",
        "title": "text-orange-700",
        "accent_box": "bg-orange-50/60 border-orange-200/70",
        "accent_title": "text-orange-800",
        "phrase_card": "bg-orange-50/65 hover:bg-orange-100/70 border-orange-200/90",
        "phrase_tag": "bg-orange-200/75 text-orange-800",
        "tag_theme": "bg-orange-100 text-orange-800 border-orange-200",
        "mnemonic_border": "border-orange-500",
        "mnemonic_title": "text-orange-700",
        "table_text": "text-orange-300",
        "playlist_text": "text-orange-300",
        "note_badge": "text-orange-800 bg-orange-50/90 border-orange-200/70",
    },
    "purple": {
        "section_border": "border-purple-100",
        "banner_bg": "from-purple-600 to-violet-500",
        "banner_sub": "text-purple-100",
        "formula_box": "bg-purple-50/70 border-purple-200/70",
        "formula_label": "text-purple-700",
        "formula_tip": "text-purple-900/80",
        "bar": "bg-purple-600",
        "title": "text-purple-700",
        "accent_box": "bg-purple-50/60 border-purple-200/70",
        "accent_title": "text-purple-800",
        "phrase_card": "bg-purple-50/65 hover:bg-purple-100/70 border-purple-200/90",
        "phrase_tag": "bg-purple-200/75 text-purple-800",
        "tag_theme": "bg-purple-100 text-purple-800 border-purple-200",
        "mnemonic_border": "border-purple-500",
        "mnemonic_title": "text-purple-700",
        "table_text": "text-purple-300",
        "playlist_text": "text-purple-300",
        "note_badge": "text-purple-800 bg-purple-50/90 border-purple-200/70",
    },
}

TAG_KIND_STYLES = {
    "screenshot": "bg-sky-100 text-sky-800 border-sky-200",
    "daily": "bg-amber-100 text-amber-800 border-amber-200",
    "contrast": "bg-teal-100 text-teal-800 border-teal-200",
}

DATE_RE = re.compile(r"^\d{4}\.\d{2}\.\d{2}$")


def esc(text: str) -> str:
    return html.escape(str(text), quote=True)


def check_balanced_ruby(fragment: str, label: str, errors: list[str]) -> None:
    if fragment.count("<ruby>") != fragment.count("</ruby>"):
        errors.append(f"{label}: unbalanced <ruby> tags")
    if fragment.count("<rt>") != fragment.count("</rt>"):
        errors.append(f"{label}: unbalanced <rt> tags")


def validate_data(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    date_str = data.get("date", "")
    if not isinstance(date_str, str) or not DATE_RE.match(date_str):
        errors.append(f"date must match YYYY.MM.DD, got: {date_str!r}")

    grammars = data.get("grammars")
    if not isinstance(grammars, list) or not grammars:
        errors.append("grammars must be a non-empty list")
        return errors

    seen_ids: set[str] = set()
    for idx, g in enumerate(grammars):
        gid = g.get("id", f"g{idx + 1}")
        if gid in seen_ids:
            errors.append(f"duplicate grammar id: {gid}")
        seen_ids.add(gid)

        theme = g.get("theme", THEME_ORDER[idx % len(THEME_ORDER)])
        if theme not in THEMES:
            errors.append(f"grammar {gid}: unsupported theme {theme!r}")

        for req in ("pattern", "meaning", "keywords", "formulaHtml"):
            if not g.get(req):
                errors.append(f"grammar {gid}: missing required field {req}")

        check_balanced_ruby(g.get("patternHtml", g.get("pattern", "")), f"{gid}.patternHtml", errors)

        examples = g.get("examples")
        if not isinstance(examples, list) or not examples:
            errors.append(f"grammar {gid}: examples must be a non-empty list")
        else:
            for ex_idx, ex in enumerate(examples):
                for req in ("tag", "jpHtml", "plainText", "cn"):
                    if not ex.get(req):
                        errors.append(f"grammar {gid}.examples[{ex_idx}]: missing {req}")
                check_balanced_ruby(ex.get("jpHtml", ""), f"{gid}.examples[{ex_idx}].jpHtml", errors)

        for p_idx, ph in enumerate(g.get("phrases") or []):
            for req in ("tag", "jpHtml", "plainText", "cn"):
                if not ph.get(req):
                    errors.append(f"grammar {gid}.phrases[{p_idx}]: missing {req}")
            check_balanced_ruby(ph.get("jpHtml", ""), f"{gid}.phrases[{p_idx}].jpHtml", errors)

    bedtime = data.get("bedtime")
    if not isinstance(bedtime, dict):
        errors.append("bedtime must be an object")
        return errors

    for key in ("mnemonics", "table", "quiz", "playlist"):
        if not isinstance(bedtime.get(key), list) or not bedtime[key]:
            errors.append(f"bedtime.{key} must be a non-empty list")

    for q_idx, q in enumerate(bedtime.get("quiz") or []):
        opts = q.get("options")
        ans = q.get("answer")
        if not isinstance(opts, list) or len(opts) < 2:
            errors.append(f"bedtime.quiz[{q_idx}]: options must have at least 2 items")
        elif not isinstance(ans, int) or not (0 <= ans < len(opts)):
            errors.append(f"bedtime.quiz[{q_idx}]: answer index {ans!r} out of range")
        check_balanced_ruby(q.get("questionHtml", ""), f"bedtime.quiz[{q_idx}].questionHtml", errors)

    for pl_idx, item in enumerate(bedtime.get("playlist") or []):
        for req in ("label", "jpHtml", "plainText", "cn"):
            if not item.get(req):
                errors.append(f"bedtime.playlist[{pl_idx}]: missing {req}")
        check_balanced_ruby(item.get("jpHtml", ""), f"bedtime.playlist[{pl_idx}].jpHtml", errors)

    return errors


def render_dot_indicator() -> str:
    return (
        '<div class="play-indicator shrink-0 flex items-center justify-center w-6 h-6 mt-0.5" aria-hidden="true">'
        '<span class="idle-dot"></span>'
        '<span class="loading-dots">'
        '<span class="loading-dot"></span>'
        '<span class="loading-dot"></span>'
        '<span class="loading-dot"></span>'
        "</span>"
        '<span class="wave-bars">'
        '<span class="wave-bar"></span>'
        '<span class="wave-bar"></span>'
        '<span class="wave-bar"></span>'
        "</span>"
        "</div>"
    )


def render_analysis_card(item: dict[str, Any], theme: dict[str, str]) -> str:
    variant = item.get("variant", "neutral")
    if variant == "warning":
        box_cls = "bg-rose-50/60 rounded-2xl p-3.5 border border-rose-200/70"
        title_cls = "font-bold text-rose-700 mb-1"
    elif variant == "accent":
        box_cls = f"{theme['accent_box']} rounded-2xl p-3.5 border"
        title_cls = f"font-bold {theme['accent_title']} mb-1"
    else:
        box_cls = "bg-stone-50 rounded-2xl p-3.5 border border-stone-200/70"
        title_cls = f"font-bold {theme['title']} mb-1"

    parts = [f'<div class="{box_cls}">', f'<div class="{title_cls}">{esc(item["title"])}</div>']

    if item.get("bodyHtml"):
        parts.append(f'<p>{item["bodyHtml"]}</p>')

    if item.get("bulletsHtml"):
        li_html = "".join(f"<li>• {b}</li>" for b in item["bulletsHtml"])
        parts.append(f'<ul class="space-y-1 ml-1">{li_html}</ul>')

    if item.get("gridHtml"):
        grid_cards = "".join(
            f'<div class="bg-white p-2.5 rounded-xl border border-stone-200/70">{cell}</div>'
            for cell in item["gridHtml"]
        )
        parts.append(f'<div class="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-1.5">{grid_cards}</div>')

    parts.append("</div>")
    return "\n".join(parts)


def render_phrases_block(g: dict[str, Any], theme: dict[str, str]) -> str:
    phrases = g.get("phrases") or []
    if not phrases:
        return ""

    heading = g.get("phrasesTitle") or "高频词组与对比小卡（点击即可发音）"
    cols_cls = "sm:grid-cols-2" if len(phrases) == 2 else "sm:grid-cols-3"
    cards_html: list[str] = []

    for idx, ph in enumerate(phrases):
        is_contrast = bool(ph.get("isContrast"))
        card_cls = (
            "bg-teal-50/60 hover:bg-teal-100/60 border-dashed border-teal-200/90"
            if is_contrast
            else theme["phrase_card"]
        )
        tag_cls = "bg-teal-100 text-teal-800" if is_contrast else theme["phrase_tag"]
        card_id = f"{g['id']}-phrase-{idx}"
        cards_html.append(
            f"""
            <div id="{esc(card_id)}" role="button" tabindex="0"
              data-text="{esc(ph['plainText'])}"
              onclick="speakCard(this)"
              onkeydown="if(event.key==='Enter'||event.key===' '){{event.preventDefault();speakCard(this);}}"
              aria-label="点击词组卡片播放日语发音"
              class="playable-card group cursor-pointer select-none text-left {card_cls} border rounded-2xl p-3.5 transition duration-200">
              <div class="flex items-start justify-between gap-2">
                <div class="min-w-0 flex-1">
                  <span class="inline-block text-[11px] font-bold px-2 py-0.5 rounded-md {tag_cls}">{esc(ph['tag'])}</span>
                  <div class="jp-speech-target font-jp text-lg font-bold text-stone-800 mt-1.5 leading-[1.9]">{ph['jpHtml']}</div>
                </div>
                {render_dot_indicator()}
              </div>
              <div class="translation-text text-xs text-stone-600 mt-1" onclick="handleTranslationClick(event, this)">{esc(ph['cn'])}</div>
            </div>"""
        )

    return f"""
        <!-- 核心词组 / 对比小卡 -->
        <div>
          <h3 class="font-maru text-base font-bold text-stone-800 flex items-center gap-2 mb-3">
            <span class="w-1.5 h-5 rounded-full {theme['bar']}"></span>
            <span>{esc(heading)}</span>
          </h3>
          <div class="grid grid-cols-1 {cols_cls} gap-3">
            {''.join(cards_html)}
          </div>
        </div>"""


def render_grammar_section(g: dict[str, Any], index: int) -> str:
    theme_name = g.get("theme", THEME_ORDER[index % len(THEME_ORDER)])
    theme = THEMES[theme_name]
    num_str = f"{index + 1:02d}"
    pattern_html = g.get("patternHtml") or esc(g["pattern"])
    heading_size = "text-lg sm:text-2xl" if len(g["pattern"]) > 16 else "text-xl sm:text-2xl"

    formula_tip = (
        f'<p class="text-xs sm:text-sm {theme["formula_tip"]} mt-2">💡 提示：{g["formulaTipHtml"]}</p>'
        if g.get("formulaTipHtml")
        else ""
    )

    analysis_html = "\n".join(render_analysis_card(item, theme) for item in g.get("analysis") or [])
    phrases_html = render_phrases_block(g, theme)

    return f"""
    <!-- 文法 {index + 1}：{esc(g['pattern'])}（主题色：{theme_name}） -->
    <section id="grammar-{index + 1}" data-theme="{theme_name}" class="grammar-section bg-white rounded-3xl border {theme['section_border']} journal-card overflow-hidden">
      <div class="bg-gradient-to-r {theme['banner_bg']} px-5 py-4 sm:px-7 sm:py-5 text-white">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <div class="flex items-center gap-3">
            <span class="w-9 h-9 rounded-2xl bg-white/20 backdrop-blur-sm flex items-center justify-center font-maru font-bold text-lg shrink-0">{num_str}</span>
            <div>
              <h2 class="font-maru {heading_size} font-bold tracking-wide">{pattern_html}</h2>
              <p class="{theme['banner_sub']} text-xs sm:text-sm mt-0.5">{esc(g['meaning'])}</p>
            </div>
          </div>
          <span class="px-3 py-1 rounded-full bg-white/15 text-xs font-medium">{esc(g['keywords'])}</span>
        </div>
      </div>

      <div class="p-5 sm:p-7 space-y-6">
        <!-- 接续公式 -->
        <div class="{theme['formula_box']} border rounded-2xl p-4">
          <div class="text-xs font-bold uppercase tracking-wider {theme['formula_label']} mb-1.5">📐 接续公式</div>
          <p class="font-jp text-sm sm:text-base font-bold text-stone-800 leading-relaxed">
            {g['formulaHtml']}
          </p>
          {formula_tip}
        </div>

        <!-- 延伸用法与避坑辨析 -->
        <div>
          <h3 class="font-maru text-base font-bold text-stone-800 flex items-center gap-2 mb-3">
            <span class="w-1.5 h-5 rounded-full {theme['bar']}"></span>
            <span>延伸用法与避坑辨析</span>
          </h3>
          <div class="grid grid-cols-1 gap-3 text-sm leading-relaxed text-stone-700">
            {analysis_html}
          </div>
        </div>
        {phrases_html}

        <!-- 例句列表 -->
        <div>
          <h3 class="font-maru text-base font-bold text-stone-800 flex items-center gap-2 mb-3">
            <span class="w-1.5 h-5 rounded-full {theme['bar']}"></span>
            <span>精选例句（点击任意卡片即可发音）</span>
          </h3>
          <div class="space-y-3" id="examples-{esc(g['id'])}"></div>
        </div>
      </div>
    </section>"""


def render_mnemonics(bedtime: dict[str, Any], grammars: list[dict[str, Any]]) -> str:
    cards: list[str] = []
    for idx, m in enumerate(bedtime["mnemonics"]):
        theme_name = (
            grammars[idx].get("theme", THEME_ORDER[idx % len(THEME_ORDER)])
            if idx < len(grammars)
            else THEME_ORDER[idx % len(THEME_ORDER)]
        )
        theme = THEMES[theme_name]
        anchor = (
            f'<span class="text-xs text-stone-500 block mt-1">📌 锚点：{m["anchorHtml"]}</span>'
            if m.get("anchorHtml")
            else ""
        )
        cards.append(
            f"""
          <div class="bg-[#FAF7F2] text-stone-800 rounded-2xl p-4 border-l-4 {theme['mnemonic_border']}">
            <div class="font-jp font-bold {theme['mnemonic_title']} text-base">{esc(m['title'])}</div>
            <p class="text-sm mt-1 leading-relaxed">{esc(m['text'])}{anchor}</p>
          </div>"""
        )
    return "".join(cards)


def render_table_rows(bedtime: dict[str, Any], grammars: list[dict[str, Any]]) -> str:
    rows: list[str] = []
    for idx, row in enumerate(bedtime["table"]):
        theme_name = (
            grammars[idx].get("theme", THEME_ORDER[idx % len(THEME_ORDER)])
            if idx < len(grammars)
            else THEME_ORDER[idx % len(THEME_ORDER)]
        )
        theme = THEMES[theme_name]
        rows.append(
            f"""
              <tr class="hover:bg-slate-700/30">
                <td class="py-3 px-4 font-jp font-bold {theme['table_text']} whitespace-nowrap">{esc(row['pattern'])}</td>
                <td class="py-3 px-4 font-jp">{esc(row['connection'])}</td>
                <td class="py-3 px-4">{esc(row['pitfall'])}</td>
              </tr>"""
        )
    return "".join(rows)


def build_js_payloads(data: dict[str, Any]) -> tuple[str, str, str]:
    grammars = data["grammars"]
    examples_map: dict[str, list[dict[str, Any]]] = {}

    for idx, g in enumerate(grammars):
        theme_name = g.get("theme", THEME_ORDER[idx % len(THEME_ORDER)])
        theme = THEMES[theme_name]
        items: list[dict[str, Any]] = []
        for ex in g["examples"]:
            kind = ex.get("tagKind", "theme")
            tag_style = TAG_KIND_STYLES.get(kind, theme["tag_theme"])
            entry: dict[str, Any] = {
                "tag": ex["tag"],
                "tagStyle": tag_style,
                "noteStyle": theme["note_badge"],
                "isContrast": bool(ex.get("isContrast", False)),
                "jpHtml": ex["jpHtml"],
                "plainText": ex["plainText"],
                "cn": ex["cn"],
            }
            if ex.get("note"):
                entry["note"] = ex["note"]
            items.append(entry)
        examples_map[g["id"]] = items

    quiz_list: list[dict[str, Any]] = []
    for idx, q in enumerate(data["bedtime"]["quiz"]):
        quiz_list.append(
            {
                "id": q.get("id", idx + 1),
                "grammar": q["grammar"],
                "questionHtml": q["questionHtml"],
                "options": q["options"],
                "answer": q["answer"],
                "explanation": q["explanation"],
            }
        )

    playlist_list: list[dict[str, Any]] = []
    for idx, item in enumerate(data["bedtime"]["playlist"]):
        theme_name = (
            grammars[idx].get("theme", THEME_ORDER[idx % len(THEME_ORDER)])
            if idx < len(grammars)
            else THEME_ORDER[idx % len(THEME_ORDER)]
        )
        theme = THEMES[theme_name]
        playlist_list.append(
            {
                "label": item["label"],
                "color": theme["playlist_text"],
                "jpHtml": item["jpHtml"],
                "plainText": item["plainText"],
                "cn": item["cn"],
            }
        )

    def safe_json(obj: Any) -> str:
        # Prevent closing </script> tags inside embedded JSON
        return json.dumps(obj, ensure_ascii=False, indent=2).replace("</", "<\\/")

    return safe_json(examples_map), safe_json(quiz_list), safe_json(playlist_list)


def render_html(data: dict[str, Any], index_href: str | None = None) -> str:
    date_str = data["date"]
    level_badge = data.get("levelBadge") or "N2 / N3 核心精讲"
    subtitle = data.get("subtitle") or (
        "收录全部课堂板书与截图例句，搭配延伸辨析、高频日常口语、逐句日语发音与睡前复习。"
    )
    grammars = data["grammars"]
    count = len(grammars)
    bedtime = data["bedtime"]

    back_link_html = (
        f'<a href="{esc(index_href)}" class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-stone-100/90 hover:bg-amber-50 border border-stone-200/80 text-stone-600 hover:text-amber-800 text-xs font-medium transition">← 返回手账目录</a>'
        if index_href
        else ""
    )

    pattern_summary_html = '<span class="text-amber-400/80 select-none">／</span>'.join(
        f'<span class="inline-block">{esc(g["pattern"])}</span>' for g in grammars
    )
    grammar_sections_html = "\n".join(render_grammar_section(g, i) for i, g in enumerate(grammars))
    mnemonics_html = render_mnemonics(bedtime, grammars)
    table_rows_html = render_table_rows(bedtime, grammars)
    examples_json, quiz_json, playlist_json = build_js_payloads(data)
    quiz_count = len(bedtime["quiz"])
    playlist_count = len(bedtime["playlist"])

    return f"""<!DOCTYPE html>
<html lang="zh-CN" class="scroll-smooth">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>日语文法手账 · {esc(date_str)}（{count}个核心文法）</title>
  <!-- Tailwind CSS CDN -->
  <script src="https://cdn.tailwindcss.com"></script>
  <!-- 日式手账感字体：Noto Sans JP / Noto Sans SC / Zen Maru Gothic -->
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700&family=Noto+Sans+SC:wght@400;500;700&family=Zen+Maru+Gothic:wght@500;700&display=swap" rel="stylesheet" />

  <script>
    tailwind.config = {{
      theme: {{
        extend: {{
          fontFamily: {{
            sans: ['"Noto Sans SC"', '"Noto Sans JP"', 'Inter', 'system-ui', 'sans-serif'],
            jp: ['"Noto Sans JP"', '"Noto Sans SC"', 'sans-serif'],
            maru: ['"Zen Maru Gothic"', '"Noto Sans SC"', 'sans-serif'],
          }},
          colors: {{
            paper: '#FAF7F2',
            ink: '#2D2A26',
            muted: '#6E675F',
          }}
        }}
      }}
    }};
  </script>

  <style>
    /* 日式方格/点阵手账纸张背景 */
    body {{
      background-color: #FAF7F2;
      background-image: radial-gradient(#E2DACD 1px, transparent 1px);
      background-size: 22px 22px;
      color: #2D2A26;
      -webkit-tap-highlight-color: transparent;
    }}

    /* Ruby 振假名排版优化 */
    ruby {{
      ruby-align: center;
      ruby-position: over;
    }}
    rt {{
      font-size: 0.62em;
      color: #78716C;
      font-weight: 400;
      user-select: none;
      transition: opacity 0.2s ease;
    }}
    #bedtime-review rt {{
      color: #A7B6D2;
    }}
    .grammar-section h2 rt {{
      color: rgba(255, 255, 255, 0.85);
    }}

    /* 隐藏假名开关生效时 */
    body.hide-furigana rt {{
      visibility: hidden;
      opacity: 0;
    }}

    /* 目标文法主题高亮（自动随章节配色） */
    .hl-theme {{
      font-weight: 700;
      padding: 0 4px;
      border-radius: 5px;
    }}
    [data-theme="indigo"] .hl-theme {{
      background-color: #E0E7FF;
      color: #312E81;
    }}
    [data-theme="emerald"] .hl-theme {{
      background-color: #D1FAE5;
      color: #064E3B;
    }}
    [data-theme="orange"] .hl-theme {{
      background-color: #FFEDD5;
      color: #7C2D12;
    }}
    [data-theme="purple"] .hl-theme {{
      background-color: #F3E8FF;
      color: #581C87;
    }}
    .hl-contrast {{
      background-color: #CCFBF1;
      color: #115E59;
      font-weight: 700;
      padding: 0 4px;
      border-radius: 5px;
    }}
    #bedtime-review .hl-theme {{
      background: linear-gradient(transparent 62%, rgba(252, 211, 77, 0.32) 62%);
      color: #FDE68A;
      padding: 0 2px;
    }}

    /* 隐藏中文翻译开关生效时（支持点击/悬停偷看） */
    body.hide-translation .translation-text {{
      filter: blur(6px);
      opacity: 0.38;
      cursor: pointer;
      transition: filter 0.22s ease, opacity 0.22s ease;
      user-select: none;
    }}
    body.hide-translation .translation-text:hover,
    body.hide-translation .translation-text.peeked {{
      filter: blur(0);
      opacity: 1;
    }}

    /* 滚动跳转时保留清爽顶部间距 */
    section[id] {{
      scroll-margin-top: 24px;
    }}

    /* 手账柔和纸张阴影 */
    .journal-card {{
      box-shadow: 0 4px 20px -2px rgba(92, 76, 56, 0.07), 0 1px 3px rgba(92, 76, 56, 0.05);
    }}

    /* 整卡点击发音交互态（极简小圆点与声波反馈） */
    .playable-card {{
      transition: border-color 0.2s ease, background-color 0.2s ease, transform 0.12s ease, box-shadow 0.2s ease;
    }}
    .playable-card:active {{
      transform: scale(0.992);
    }}
    .playable-card.loading {{
      border-color: #FCD34D !important;
      background-color: #FFFDF5 !important;
    }}
    .playable-card.playing {{
      border-color: #F59E0B !important;
      border-style: solid !important;
      background-color: #FFFBEB !important;
      box-shadow: 0 0 0 3px rgba(245, 158, 11, 0.16), 0 4px 16px -2px rgba(245, 158, 11, 0.14);
    }}

    /* 夜间模式下的卡片加载与播放态 */
    #bedtime-review .playable-card.loading {{
      border-color: rgba(252, 211, 77, 0.5) !important;
      background-color: rgba(252, 211, 77, 0.08) !important;
    }}
    #bedtime-review .playable-card.playing {{
      border-color: rgba(252, 211, 77, 0.72) !important;
      background-color: rgba(252, 211, 77, 0.15) !important;
      box-shadow: 0 0 0 2px rgba(252, 211, 77, 0.24);
    }}

    /* 极简小圆点指示器：待机圆点 → 加载呼吸点 → 播放声波 */
    .idle-dot {{
      display: inline-block;
      width: 8px;
      height: 8px;
      border-radius: 9999px;
      background-color: rgba(217, 119, 6, 0.32);
      transition: background-color 0.2s ease, transform 0.2s ease;
    }}
    .playable-card:hover .idle-dot {{
      background-color: rgba(217, 119, 6, 0.72);
      transform: scale(1.22);
    }}
    #bedtime-review .idle-dot {{
      background-color: rgba(252, 211, 77, 0.38);
    }}
    #bedtime-review .playable-card:hover .idle-dot {{
      background-color: rgba(252, 211, 77, 0.85);
    }}

    .loading-dots {{
      display: none;
      align-items: center;
      gap: 3px;
    }}
    .loading-dot {{
      width: 4px;
      height: 4px;
      border-radius: 9999px;
      background-color: #D97706;
      animation: dotPulse 0.9s ease-in-out infinite;
    }}
    #bedtime-review .loading-dot {{
      background-color: #FCD34D;
    }}
    .loading-dot:nth-child(2) {{ animation-delay: 0.15s; }}
    .loading-dot:nth-child(3) {{ animation-delay: 0.3s; }}

    @keyframes dotPulse {{
      0%, 80%, 100% {{ opacity: 0.3; transform: scale(0.8); }}
      40% {{ opacity: 1; transform: scale(1.25); }}
    }}

    .wave-bars {{
      display: none;
      align-items: flex-end;
      gap: 2.5px;
      height: 14px;
    }}
    .wave-bar {{
      display: inline-block;
      width: 3px;
      border-radius: 999px;
      background-color: #D97706;
      animation: soundWave 0.72s ease-in-out infinite;
    }}
    #bedtime-review .wave-bar {{
      background-color: #FCD34D;
    }}
    .wave-bar:nth-child(1) {{ height: 6px; animation-delay: 0s; }}
    .wave-bar:nth-child(2) {{ height: 13px; animation-delay: 0.16s; }}
    .wave-bar:nth-child(3) {{ height: 8px; animation-delay: 0.32s; }}

    @keyframes soundWave {{
      0%, 100% {{ transform: scaleY(0.45); }}
      50% {{ transform: scaleY(1.15); }}
    }}

    .playable-card.loading .idle-dot,
    .playable-card.playing .idle-dot {{
      display: none;
    }}
    .playable-card.loading .loading-dots {{
      display: inline-flex;
    }}
    .playable-card.playing .wave-bars {{
      display: inline-flex;
    }}

    /* 弹窗试听加载转圈动画 */
    @keyframes ttsSpin {{
      to {{ transform: rotate(360deg); }}
    }}
    .tts-spinner {{
      display: inline-block;
      width: 14px;
      height: 14px;
      border: 2px solid currentColor;
      border-right-color: transparent;
      border-radius: 999px;
      animation: ttsSpin 0.7s linear infinite;
    }}
  </style>
</head>
<body class="font-sans antialiased selection:bg-amber-200/70">

  <!-- =========================================================
       顶部手账封面页眉
  ========================================================== -->
  <header class="max-w-4xl mx-auto px-4 pt-6 pb-4 sm:pt-8">
    <div class="bg-white/90 backdrop-blur-sm border border-stone-200/80 rounded-3xl p-5 sm:p-7 journal-card relative overflow-hidden">
      <!-- 装饰性手账纸胶带 -->
      <div class="absolute -top-2 right-8 w-20 h-6 bg-amber-200/70 rotate-3 rounded-sm pointer-events-none"></div>
      <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <div class="flex flex-wrap items-center gap-2 mb-2.5">
            {back_link_html}
            <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-amber-50 border border-amber-200/80 text-amber-800 text-xs font-medium">
              <span>📓 日语文法每日手账</span>
              <span class="text-amber-400">•</span>
              <span>{esc(level_badge)}</span>
            </div>
          </div>
          <h1 class="font-maru text-2xl sm:text-3xl font-bold text-stone-800 tracking-tight">
            日语文法手账 · {esc(date_str)}<span class="text-stone-400 font-normal text-lg sm:text-xl ml-1.5">（{count}个核心文法）</span>
          </h1>
          <p class="font-jp text-xs sm:text-sm font-medium text-amber-800/85 mt-1.5 flex flex-wrap items-center gap-x-1.5 gap-y-0.5">
            {pattern_summary_html}
          </p>
          <p class="text-sm text-stone-500 mt-1">
            {esc(subtitle)}
          </p>
        </div>
        <!-- 语音引擎状态小标签 -->
        <button id="voice-status" type="button" onclick="openVoiceModal()"
          class="self-start sm:self-end inline-flex items-center gap-1.5 text-xs text-stone-600 bg-stone-100/90 hover:bg-amber-50 px-3 py-1.5 rounded-xl border border-stone-200/70 transition shrink-0">
          <span class="w-2 h-2 rounded-full bg-amber-500"></span>
          <span>🐟 FishAudio 代理已就绪</span>
        </button>
      </div>
    </div>
  </header>

  <!-- =========================================================
       全局学习控制卡片（随页面正常滚动，不吸顶遮挡）
  ========================================================== -->
  <section aria-label="全局学习控制" class="max-w-4xl mx-auto px-4 pt-1 pb-1">
    <div class="bg-white/90 backdrop-blur-sm border border-stone-200/80 rounded-3xl p-4 sm:px-6 sm:py-4 journal-card flex flex-wrap items-center justify-between gap-2">
      <div class="flex flex-wrap items-center gap-2">
        <!-- 语速切换 -->
        <button id="btn-speed" type="button"
          class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs sm:text-sm font-medium bg-[#FAF7F2] border border-stone-200 text-stone-700 hover:bg-stone-100 active:scale-95 transition">
          <span>🔊</span>
          <span id="speed-label">正常 1.0x</span>
        </button>

        <!-- 假名注音开关 -->
        <button id="btn-furigana" type="button" aria-pressed="true"
          class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs sm:text-sm font-medium bg-indigo-50 border border-indigo-200 text-indigo-700 hover:bg-indigo-100/70 active:scale-95 transition">
          <span class="w-2 h-2 rounded-full bg-indigo-500"></span>
          <span>假名注音：开</span>
        </button>

        <!-- 中文翻译开关 -->
        <button id="btn-translation" type="button" aria-pressed="true"
          class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs sm:text-sm font-medium bg-emerald-50 border border-emerald-200 text-emerald-700 hover:bg-emerald-100/70 active:scale-95 transition">
          <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
          <span>中文翻译：开</span>
        </button>

        <!-- 语音设置与引擎切换入口 -->
        <button id="btn-voice-settings" type="button" onclick="openVoiceModal()"
          class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs sm:text-sm font-medium bg-amber-50 border border-amber-200 text-amber-800 hover:bg-amber-100/80 active:scale-95 transition">
          <span>⚙️ 语音设置</span>
          <span id="engine-badge" class="px-1.5 py-0.5 rounded-md bg-amber-100/90 border border-amber-300 text-[11px] font-bold text-amber-900">🐟 FishAudio</span>
        </button>
      </div>

      <!-- 停止当前朗读按钮（仅播放时显现） -->
      <button id="btn-stop-all" type="button"
        class="hidden inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs sm:text-sm font-medium bg-rose-50 border border-rose-200 text-rose-700 hover:bg-rose-100 active:scale-95 transition">
        <span>⏹</span>
        <span>停止朗读</span>
      </button>
    </div>
  </section>

  <!-- =========================================================
       主内容区：{count} 个文法卡片 + 睡前复习模块
  ========================================================== -->
  <main class="max-w-4xl mx-auto px-4 py-6 sm:py-8 space-y-8">
    {grammar_sections_html}

    <!-- =======================================================
         🌙 睡前复习专属模块（柔和夜间护眼深蓝 + 暖米卡片）
    ======================================================== -->
    <section id="bedtime-review" class="rounded-3xl bg-gradient-to-br from-[#1E293B] via-[#23314A] to-[#1A2438] text-stone-100 p-5 sm:p-8 shadow-xl border border-slate-700/80 space-y-8">
      <!-- 标题 -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-700/80 pb-5">
        <div>
          <div class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-300/15 border border-amber-300/30 text-amber-200 text-xs font-medium mb-2">
            <span>🌙 睡前黄金记忆 3 分钟</span>
          </div>
          <h2 class="font-maru text-2xl sm:text-3xl font-bold text-amber-50">睡前复习小笔记</h2>
          <p class="text-slate-300 text-sm mt-1">睡前快速过一遍口诀、做{quiz_count}道小题、听一遍核心例句，让大脑在睡眠中自动巩固。</p>
        </div>
      </div>

      <!-- ① 一句话秒记口诀 -->
      <div>
        <h3 class="font-maru text-lg font-bold text-amber-200 mb-3 flex items-center gap-2">
          <span>✨</span><span>① 一句话秒记口诀</span>
        </h3>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
          {mnemonics_html}
        </div>
      </div>

      <!-- ② 接续与易错点速查表 -->
      <div>
        <h3 class="font-maru text-lg font-bold text-amber-200 mb-3 flex items-center gap-2">
          <span>📋</span><span>② 接续与易错点速查表</span>
        </h3>
        <div class="overflow-x-auto rounded-2xl border border-slate-700 bg-slate-800/70">
          <table class="w-full text-left text-xs sm:text-sm border-collapse min-w-[540px]">
            <thead>
              <tr class="bg-slate-900/70 text-amber-200 border-b border-slate-700">
                <th class="py-3 px-4 font-bold">文法</th>
                <th class="py-3 px-4 font-bold">核心接续</th>
                <th class="py-3 px-4 font-bold">最大避坑点</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-700/70 text-slate-200">
              {table_rows_html}
            </tbody>
          </table>
        </div>
      </div>

      <!-- ③ 睡前3分钟小自测 -->
      <div>
        <div class="flex flex-wrap items-center justify-between gap-2 mb-3">
          <h3 class="font-maru text-lg font-bold text-amber-200 flex items-center gap-2">
            <span>📝</span><span>③ 睡前3分钟小自测（{quiz_count}题）</span>
          </h3>
          <div class="flex items-center gap-2">
            <span id="quiz-score-badge" class="text-xs px-3 py-1 rounded-full bg-slate-800 border border-slate-600 text-amber-200">
              已完成 0 / {quiz_count}
            </span>
            <button type="button" onclick="resetQuiz()" class="text-xs px-3 py-1 rounded-full bg-slate-700 hover:bg-slate-600 text-slate-200 transition">
              重新自测
            </button>
          </div>
        </div>
        <div id="quiz-container" class="space-y-4"></div>
        <!-- 完成后显示的掌握度总结卡 -->
        <div id="quiz-summary" class="hidden mt-4 p-4 rounded-2xl bg-amber-300/15 border border-amber-300/40 text-amber-100 text-sm flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div id="quiz-summary-text" class="font-medium"></div>
          <button type="button" onclick="resetQuiz()" class="shrink-0 px-4 py-1.5 rounded-xl bg-amber-300 text-slate-900 font-bold text-xs hover:bg-amber-200 transition">
            再刷一遍巩固
          </button>
        </div>
      </div>

      <!-- ④ 睡前磨耳朵一键连播 -->
      <div class="bg-slate-900/60 border border-slate-700/90 rounded-2xl p-4 sm:p-5">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
          <div>
            <h3 class="font-maru text-lg font-bold text-amber-200 flex items-center gap-2">
              <span>🎧</span><span>④ 睡前磨耳朵一键连播</span>
            </h3>
            <p class="text-xs text-slate-400 mt-0.5">以柔和语速（0.85x）依次自动朗读今日{playlist_count}个文法的代表例句，闭眼听也能记住。</p>
          </div>
          <button id="btn-bedtime-play" type="button" onclick="toggleBedtimePlaylist()"
            class="inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-amber-300 hover:bg-amber-200 text-slate-900 font-bold text-sm transition active:scale-95 shadow-md shrink-0">
            <span id="bedtime-play-icon">🎧</span>
            <span id="bedtime-play-text">连播今日{playlist_count}句核心例句</span>
          </button>
        </div>

        <div id="bedtime-playlist" class="space-y-2.5"></div>
      </div>
    </section>

  </main>

  <!-- 底部温和鼓励语 -->
  <footer class="max-w-4xl mx-auto px-4 pb-10 pt-2 text-center text-xs text-stone-400">
    <p>毎日コツコツ、積み重ねが力になる。{esc(date_str)} 打卡完成！✨</p>
  </footer>

  <!-- =========================================================
       语音引擎设置弹窗（FishAudio API / 浏览器原生语音）
  ========================================================== -->
  <div id="voice-settings-modal" class="fixed inset-0 z-50 hidden items-center justify-center p-4 bg-stone-900/50 backdrop-blur-sm" role="dialog" aria-modal="true" aria-labelledby="voice-modal-title">
    <div class="bg-[#FAF7F2] w-full max-w-md rounded-3xl border border-stone-200 shadow-2xl overflow-hidden">
      <!-- 弹窗顶部 -->
      <div class="bg-white px-5 py-4 border-b border-stone-200/80 flex items-center justify-between">
        <div class="flex items-center gap-2">
          <span class="text-lg">⚙️</span>
          <h3 id="voice-modal-title" class="font-maru text-lg font-bold text-stone-800">语音引擎设置</h3>
        </div>
        <button type="button" onclick="closeVoiceModal()" aria-label="关闭弹窗"
          class="w-8 h-8 rounded-xl bg-stone-100 hover:bg-stone-200 text-stone-600 flex items-center justify-center transition">
          ✕
        </button>
      </div>

      <!-- 弹窗内容 -->
      <div class="p-5 space-y-4 max-h-[78vh] overflow-y-auto">
        <!-- 引擎选择 -->
        <div>
          <label class="block text-xs font-bold text-stone-600 mb-2">选择朗读引擎</label>
          <div class="grid grid-cols-2 gap-2.5">
            <label class="cursor-pointer">
              <input type="radio" name="tts-engine" value="fish" class="peer sr-only" onchange="onEngineRadioChange()" />
              <div class="p-3 rounded-2xl border-2 border-stone-200 bg-white peer-checked:border-amber-500 peer-checked:bg-amber-50/70 transition text-center">
                <div class="text-lg mb-0.5">🐟</div>
                <div class="text-sm font-bold text-stone-800">FishAudio API</div>
                <div class="text-[11px] text-stone-500 mt-0.5">真人级 AI 音色</div>
              </div>
            </label>
            <label class="cursor-pointer">
              <input type="radio" name="tts-engine" value="browser" class="peer sr-only" onchange="onEngineRadioChange()" />
              <div class="p-3 rounded-2xl border-2 border-stone-200 bg-white peer-checked:border-emerald-500 peer-checked:bg-emerald-50/70 transition text-center">
                <div class="text-lg mb-0.5">🔊</div>
                <div class="text-sm font-bold text-stone-800">浏览器原生</div>
                <div class="text-[11px] text-stone-500 mt-0.5">免费免配置</div>
              </div>
            </label>
          </div>
        </div>

        <!-- FishAudio 专属配置区 -->
        <div id="fish-config-fields" class="space-y-3.5 bg-white p-4 rounded-2xl border border-stone-200/80">
          <!-- API Key -->
          <div>
            <label for="input-fish-key" class="block text-xs font-bold text-stone-700 mb-1">FishAudio API Key（使用自建代理时可留空）</label>
            <div class="relative">
              <input id="input-fish-key" type="password" autocomplete="off" placeholder="直连需填 Key；若代理已配置环境变量可留空"
                class="w-full pr-10 pl-3 py-2.5 text-sm rounded-xl border border-stone-300 bg-[#FCFBF9] focus:outline-none focus:ring-2 focus:ring-amber-400 focus:border-amber-400" />
              <button type="button" onclick="toggleKeyVisibility()" aria-label="显示或隐藏密钥"
                class="absolute right-2 top-1/2 -translate-y-1/2 w-8 h-8 rounded-lg hover:bg-stone-100 text-stone-500 flex items-center justify-center text-sm">
                <span id="eye-icon">👁️</span>
              </button>
            </div>
            <p class="text-[11px] text-stone-500 mt-1">🔒 若在 Cloudflare Worker 后台配置了密钥，这里可直接留空（若设置了访问口令则填口令）。</p>
          </div>

          <!-- Model / Voice ID -->
          <div>
            <label for="input-fish-model" class="block text-xs font-bold text-stone-700 mb-1">模型 / 音色 ID（reference_id）</label>
            <input id="input-fish-model" type="text" autocomplete="off"
              class="w-full px-3 py-2 text-xs sm:text-sm font-mono rounded-xl border border-stone-300 bg-[#FCFBF9] focus:outline-none focus:ring-2 focus:ring-amber-400 focus:border-amber-400" />
          </div>

          <!-- Endpoint / Proxy URL -->
          <div>
            <label for="input-fish-endpoint" class="block text-xs font-bold text-stone-700 mb-1">API 地址 / 跨域代理 URL</label>
            <input id="input-fish-endpoint" type="url" autocomplete="off"
              class="w-full px-3 py-2 text-xs sm:text-sm font-mono rounded-xl border border-stone-300 bg-[#FCFBF9] focus:outline-none focus:ring-2 focus:ring-amber-400 focus:border-amber-400" />
            <p class="text-[11px] text-stone-500 mt-1 leading-relaxed">
              因 FishAudio 官方接口禁止浏览器直接跨域（CORS），建议填入你的 Cloudflare Worker 代理地址（如 <code class="bg-stone-100 px-1 rounded">https://xxx.workers.dev</code>）。请求失败时会自动回退浏览器原生语音。
            </p>
          </div>
        </div>

        <!-- 操作按钮组 -->
        <div class="flex flex-wrap items-center gap-2 pt-1">
          <button type="button" onclick="saveVoiceSettings()"
            class="flex-1 py-2.5 px-4 rounded-xl bg-amber-500 hover:bg-amber-600 text-white font-bold text-sm transition active:scale-95 shadow-sm">
            💾 保存到浏览器
          </button>
          <button id="btn-test-voice" type="button" onclick="testVoiceSettings()"
            class="py-2.5 px-4 rounded-xl bg-indigo-50 hover:bg-indigo-100 text-indigo-700 border border-indigo-200 font-bold text-sm transition active:scale-95">
            🎵 试听语音
          </button>
        </div>

        <div class="flex items-center justify-between pt-2 border-t border-stone-200/80 text-xs">
          <span id="storage-status-hint" class="text-stone-500">同一句重播会自动命中本地内存缓存，不重复扣费</span>
          <button type="button" onclick="clearSavedFishKey()"
            class="text-rose-600 hover:text-rose-700 font-medium underline underline-offset-2 shrink-0 ml-2">
            清除已存 Key
          </button>
        </div>
      </div>
    </div>
  </div>

  <!-- 轻提示 Toast（替代 alert） -->
  <div id="toast" class="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 px-4 py-2.5 rounded-2xl bg-stone-900/90 text-white text-xs sm:text-sm shadow-lg opacity-0 pointer-events-none transition-opacity duration-300 max-w-[90vw] text-center"></div>

  <!-- =========================================================
       核心数据与交互逻辑
  ========================================================== -->
  <script>
    /* -----------------------------------------------------------
       1. 文法完整例句数据
    ----------------------------------------------------------- */
    const GRAMMAR_EXAMPLES = {examples_json};

    /* -----------------------------------------------------------
       2. 睡前小自测题目数据
    ----------------------------------------------------------- */
    const QUIZ_DATA = {quiz_json};

    /* -----------------------------------------------------------
       3. 睡前磨耳朵一键连播数据
    ----------------------------------------------------------- */
    const BEDTIME_PLAYLIST = {playlist_json};

    /* -----------------------------------------------------------
       4. 全局状态 & 双引擎 TTS（FishAudio API + Web Speech API）
    ----------------------------------------------------------- */
    const FISH_DEFAULT_MODEL_ID = '14073a8ffcad4c2297ee567777b18d23';
    const FISH_OFFICIAL_ENDPOINT = 'https://api.fish.audio/v1/tts';
    const FISH_DEFAULT_ENDPOINT = 'https://fish-tts.yexin-liu.workers.dev/';
    const STORAGE_KEY = 'jp_grammar_tts_settings_v2';
    const LEGACY_STORAGE_KEY = 'jp_grammar_tts_config_v2';

    let ttsSettings = {{
      engine: 'fish',
      apiKey: '',
      referenceId: FISH_DEFAULT_MODEL_ID,
      endpoint: FISH_DEFAULT_ENDPOINT
    }};

    let globalRate = 1.0;             // 1.0 正常 / 0.75 慢速
    let jaVoice = null;               // 优先选中的浏览器日语语音
    let activeCardEl = null;          // 当前正在加载或播放的卡片
    let activeBtnEl = null;           // 弹窗试听按钮
    let activeAudio = null;           // 当前正在播放的 HTML5 Audio 对象
    let activeFetchController = null; // 用于取消进行中的 FishAudio 请求
    let isBedtimePlaying = false;     // 是否正在进行睡前连播
    let bedtimeTimer = null;          // 连播间隔定时器
    let playSessionId = 0;            // 防止并发回调错乱

    const fishAudioCache = new Map();
    const synth = 'speechSynthesis' in window ? window.speechSynthesis : null;

    function escapeAttr(str) {{
      return String(str)
        .replace(/&/g, '&amp;')
        .replace(/"/g, '&quot;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
    }}

    function renderDotIndicatorHtml() {{
      return `
        <div class="play-indicator shrink-0 flex items-center justify-center w-6 h-6 mt-0.5" aria-hidden="true">
          <span class="idle-dot"></span>
          <span class="loading-dots">
            <span class="loading-dot"></span>
            <span class="loading-dot"></span>
            <span class="loading-dot"></span>
          </span>
          <span class="wave-bars">
            <span class="wave-bar"></span>
            <span class="wave-bar"></span>
            <span class="wave-bar"></span>
          </span>
        </div>
      `;
    }}

    function loadVoiceSettings() {{
      try {{
        const raw = window.localStorage.getItem(STORAGE_KEY);
        if (raw) {{
          const parsed = JSON.parse(raw);
          ttsSettings = {{
            engine: parsed.engine === 'browser' ? 'browser' : 'fish',
            apiKey: typeof parsed.apiKey === 'string' ? parsed.apiKey : '',
            referenceId: parsed.referenceId || FISH_DEFAULT_MODEL_ID,
            endpoint: parsed.endpoint || FISH_DEFAULT_ENDPOINT
          }};
        }} else {{
          const legacyRaw = window.localStorage.getItem(LEGACY_STORAGE_KEY);
          if (legacyRaw) {{
            const legacy = JSON.parse(legacyRaw);
            ttsSettings = {{
              engine: legacy.engine === 'browser' ? 'browser' : 'fish',
              apiKey: typeof legacy.fishKey === 'string' ? legacy.fishKey : '',
              referenceId: legacy.fishModel || FISH_DEFAULT_MODEL_ID,
              endpoint: legacy.fishUrl || FISH_DEFAULT_ENDPOINT
            }};
          }}
        }}
      }} catch (e) {{
        // 受限 iframe 环境无法访问 localStorage 时静默降级为内存态
      }}
      refreshEngineBadges();
    }}

    function persistVoiceSettings() {{
      try {{
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify(ttsSettings));
        return true;
      }} catch (e) {{
        return false;
      }}
    }}

    function refreshEngineBadges() {{
      const badge = document.getElementById('engine-badge');
      const statusEl = document.getElementById('voice-status');
      const endpoint = (ttsSettings.endpoint || '').trim();
      const isProxyEndpoint = endpoint.length > 0 && !endpoint.includes('api.fish.audio');
      const useFish = ttsSettings.engine === 'fish' && (ttsSettings.apiKey.trim().length > 0 || isProxyEndpoint);

      if (badge) {{
        if (ttsSettings.engine === 'fish') {{
          badge.textContent = useFish ? '🐟 FishAudio' : '🐟 FishAudio(需配置)';
          badge.className = 'px-1.5 py-0.5 rounded-md bg-amber-100/90 border border-amber-300 text-[11px] font-bold text-amber-900';
        }} else {{
          badge.textContent = '🔊 浏览器语音';
          badge.className = 'px-1.5 py-0.5 rounded-md bg-white/90 border border-amber-200/80 text-[11px] font-bold text-stone-700';
        }}
      }}

      if (statusEl) {{
        if (useFish) {{
          statusEl.innerHTML = `<span class="w-2 h-2 rounded-full bg-amber-500"></span><span>🐟 FishAudio ${{isProxyEndpoint ? '代理已就绪' : '已配置'}}</span>`;
        }} else if (ttsSettings.engine === 'fish') {{
          statusEl.innerHTML = `<span class="w-2 h-2 rounded-full bg-amber-400"></span><span>🐟 待配置代理/Key（自动回退浏览器）</span>`;
        }} else if (synth) {{
          statusEl.innerHTML = `<span class="w-2 h-2 rounded-full bg-emerald-500"></span><span>🔊 浏览器日语语音就绪</span>`;
        }} else {{
          statusEl.innerHTML = `<span class="w-2 h-2 rounded-full bg-rose-400"></span><span>浏览器不支持语音朗读</span>`;
        }}
      }}
    }}

    function loadJapaneseVoice() {{
      if (!synth) {{
        refreshEngineBadges();
        return;
      }}
      const voices = synth.getVoices();
      if (!voices.length) return;

      const jaVoices = voices.filter(v => v.lang && v.lang.toLowerCase().startsWith('ja'));
      if (jaVoices.length > 0) {{
        jaVoice =
          jaVoices.find(v => /Google|Nanami|Kyoko|Haruka|O-Ren|Otoya/i.test(v.name)) ||
          jaVoices[0];
      }}
      refreshEngineBadges();
    }}

    if (synth) {{
      loadJapaneseVoice();
      if (typeof synth.onvoiceschanged !== 'undefined') {{
        synth.onvoiceschanged = loadJapaneseVoice;
      }}
    }}

    function openVoiceModal() {{
      const modal = document.getElementById('voice-settings-modal');
      document.querySelectorAll('input[name="tts-engine"]').forEach(r => {{
        r.checked = (r.value === ttsSettings.engine);
      }});
      document.getElementById('input-fish-key').value = ttsSettings.apiKey || '';
      document.getElementById('input-fish-model').value = ttsSettings.referenceId || FISH_DEFAULT_MODEL_ID;
      document.getElementById('input-fish-endpoint').value = ttsSettings.endpoint || FISH_DEFAULT_ENDPOINT;
      onEngineRadioChange();
      modal.classList.remove('hidden');
      modal.classList.add('flex');
    }}

    function closeVoiceModal() {{
      const modal = document.getElementById('voice-settings-modal');
      modal.classList.add('hidden');
      modal.classList.remove('flex');
    }}

    function onEngineRadioChange() {{
      const selected = document.querySelector('input[name="tts-engine"]:checked')?.value || 'browser';
      const fishFields = document.getElementById('fish-config-fields');
      fishFields.classList.toggle('opacity-60', selected !== 'fish');
    }}

    function toggleKeyVisibility() {{
      const input = document.getElementById('input-fish-key');
      const icon = document.getElementById('eye-icon');
      if (input.type === 'password') {{
        input.type = 'text';
        icon.textContent = '🙈';
      }} else {{
        input.type = 'password';
        icon.textContent = '👁️';
      }}
    }}

    function applyModalInputsToState() {{
      const selected = document.querySelector('input[name="tts-engine"]:checked')?.value || 'browser';
      const apiKey = document.getElementById('input-fish-key').value.trim();
      const referenceId = document.getElementById('input-fish-model').value.trim() || FISH_DEFAULT_MODEL_ID;
      const endpoint = document.getElementById('input-fish-endpoint').value.trim() || FISH_DEFAULT_ENDPOINT;
      ttsSettings = {{ engine: selected, apiKey, referenceId, endpoint }};
      refreshEngineBadges();
    }}

    function saveVoiceSettings() {{
      applyModalInputsToState();
      const saved = persistVoiceSettings();
      closeVoiceModal();
      if (saved) {{
        showToast(ttsSettings.engine === 'fish'
          ? '🐟 已保存 FishAudio 配置到浏览器缓存'
          : '🔊 已切换并保存为浏览器原生语音');
      }} else {{
        showToast('已应用设置（当前沙箱环境不支持持久缓存，仅本次有效）');
      }}
    }}

    function clearSavedFishKey() {{
      document.getElementById('input-fish-key').value = '';
      ttsSettings.apiKey = '';
      try {{
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify(ttsSettings));
      }} catch (e) {{}}
      refreshEngineBadges();
      showToast('已清除浏览器中缓存的 FishAudio API Key');
    }}

    function testVoiceSettings() {{
      applyModalInputsToState();
      const btn = document.getElementById('btn-test-voice');
      stopAllSpeech();
      playUnifiedTTS({{
        text: 'こんにちは、今日も一緒に日本語を勉強しましょう。',
        rate: globalRate,
        btn
      }});
    }}

    /**
     * 核心工具：获取不含 <rt>/<rp> 振假名的纯净日语文本
     */
    function extractCleanJapaneseText(cardEl) {{
      const attrText = cardEl.getAttribute('data-text');
      if (attrText && attrText.trim()) return attrText.trim();
      const target = cardEl.querySelector('.jp-speech-target') || cardEl;
      const clone = target.cloneNode(true);
      clone.querySelectorAll('rt, rp').forEach(node => node.remove());
      return (clone.textContent || '').replace(/\\s+/g, '').trim();
    }}

    let toastTimeout = null;
    function showToast(msg, duration = 2600) {{
      const toast = document.getElementById('toast');
      toast.textContent = msg;
      toast.classList.remove('opacity-0');
      toast.classList.add('opacity-100');
      clearTimeout(toastTimeout);
      toastTimeout = setTimeout(() => {{
        toast.classList.remove('opacity-100');
        toast.classList.add('opacity-0');
      }}, duration);
    }}

    function setCardState(cardEl, state) {{
      if (!cardEl) return;
      cardEl.classList.remove('loading', 'playing');
      if (state === 'loading') cardEl.classList.add('loading');
      if (state === 'playing') cardEl.classList.add('playing');
    }}

    function setTestBtnState(btn, state) {{
      if (!btn) return;
      if (state === 'loading') {{
        btn.innerHTML = '<span class="tts-spinner"></span> <span>加载中…</span>';
      }} else if (state === 'playing') {{
        btn.innerHTML = '<span>🔊 正在试听…</span>';
      }} else {{
        btn.innerHTML = '🎵 试听语音';
      }}
    }}

    function resetActiveUI() {{
      if (activeCardEl) {{
        setCardState(activeCardEl, 'idle');
        activeCardEl = null;
      }}
      if (activeBtnEl) {{
        setTestBtnState(activeBtnEl, 'idle');
        activeBtnEl = null;
      }}
      document.getElementById('btn-stop-all').classList.add('hidden');
    }}

    function stopAllSpeech() {{
      playSessionId++;
      clearTimeout(bedtimeTimer);
      bedtimeTimer = null;

      if (isBedtimePlaying) {{
        isBedtimePlaying = false;
        updateBedtimePlayUI(false);
      }}

      if (activeFetchController) {{
        try {{ activeFetchController.abort(); }} catch (e) {{}}
        activeFetchController = null;
      }}

      if (activeAudio) {{
        try {{
          activeAudio.onended = null;
          activeAudio.onerror = null;
          activeAudio.pause();
          activeAudio.currentTime = 0;
        }} catch (e) {{}}
        activeAudio = null;
      }}

      if (synth) {{
        try {{ synth.cancel(); }} catch (e) {{}}
      }}

      resetActiveUI();
    }}

    function playUnifiedTTS({{ text, rate = globalRate, cardEl = null, btn = null, onDone = null }}) {{
      if (!text) {{
        if (onDone) onDone(false);
        return;
      }}

      const sessionId = ++playSessionId;
      if (activeCardEl && activeCardEl !== cardEl) {{
        setCardState(activeCardEl, 'idle');
      }}
      if (activeBtnEl && activeBtnEl !== btn) {{
        setTestBtnState(activeBtnEl, 'idle');
      }}

      activeCardEl = cardEl;
      activeBtnEl = btn;
      document.getElementById('btn-stop-all').classList.remove('hidden');

      const endpoint = (ttsSettings.endpoint || '').trim();
      const isProxyEndpoint = endpoint.length > 0 && !endpoint.includes('api.fish.audio');
      const canUseFish = ttsSettings.engine === 'fish' && (ttsSettings.apiKey.trim().length > 0 || isProxyEndpoint);

      if (canUseFish) {{
        playWithFishAudio({{ text, rate, cardEl, btn, sessionId, onDone }});
      }} else {{
        playWithBrowserTTS({{ text, rate, cardEl, btn, sessionId, onDone }});
      }}
    }}

    async function playWithFishAudio({{ text, rate, cardEl, btn, sessionId, onDone }}) {{
      const endpoint = (ttsSettings.endpoint || FISH_DEFAULT_ENDPOINT).trim();
      const referenceId = (ttsSettings.referenceId || FISH_DEFAULT_MODEL_ID).trim();
      const cacheKey = `${{endpoint}}::${{referenceId}}::${{text}}`;

      const playAudioFromUrl = (url) => {{
        if (sessionId !== playSessionId) return;
        const audio = new Audio(url);
        audio.playbackRate = rate;
        activeAudio = audio;
        setCardState(cardEl, 'playing');
        setTestBtnState(btn, 'playing');

        audio.onended = () => {{
          if (activeAudio === audio) activeAudio = null;
          if (sessionId !== playSessionId) return;
          if (!isBedtimePlaying) resetActiveUI();
          else setCardState(cardEl, 'idle');
          if (onDone) onDone(true);
        }};

        audio.onerror = () => {{
          if (activeAudio === audio) activeAudio = null;
          if (sessionId !== playSessionId) return;
          showToast('音频播放失败，已切换浏览器原生日语朗读');
          playWithBrowserTTS({{ text, rate, cardEl, btn, sessionId, onDone }});
        }};

        audio.play().catch(() => {{
          if (activeAudio === audio) activeAudio = null;
          if (sessionId !== playSessionId) return;
          showToast('浏览器拦截自动播放，已切换原生日语语音');
          playWithBrowserTTS({{ text, rate, cardEl, btn, sessionId, onDone }});
        }});
      }};

      if (fishAudioCache.has(cacheKey)) {{
        playAudioFromUrl(fishAudioCache.get(cacheKey));
        return;
      }}

      setCardState(cardEl, 'loading');
      setTestBtnState(btn, 'loading');
      const controller = new AbortController();
      activeFetchController = controller;

      try {{
        const headers = {{
          'Content-Type': 'application/json',
          'model': 's2.1-pro'
        }};
        if (ttsSettings.apiKey && ttsSettings.apiKey.trim()) {{
          headers['Authorization'] = `Bearer ${{ttsSettings.apiKey.trim()}}`;
        }}

        const res = await fetch(endpoint, {{
          method: 'POST',
          headers,
          body: JSON.stringify({{
            text,
            reference_id: referenceId,
            format: 'mp3'
          }}),
          signal: controller.signal
        }});

        if (activeFetchController === controller) activeFetchController = null;
        if (sessionId !== playSessionId) return;

        if (!res.ok) throw new Error(`HTTP ${{res.status}}`);

        const blob = await res.blob();
        if (!blob || blob.size === 0) throw new Error('Empty audio response');

        const audioUrl = URL.createObjectURL(blob);
        fishAudioCache.set(cacheKey, audioUrl);
        playAudioFromUrl(audioUrl);
      }} catch (err) {{
        if (activeFetchController === controller) activeFetchController = null;
        if ((err && err.name === 'AbortError') || sessionId !== playSessionId) return;
        const statusMsg = err && err.message ? err.message : '网络异常';
        showToast(`FishAudio 请求失败（${{statusMsg}}），已自动回退浏览器语音`, 3000);
        playWithBrowserTTS({{ text, rate, cardEl, btn, sessionId, onDone }});
      }}
    }}

    function playWithBrowserTTS({{ text, rate, cardEl, btn, sessionId, onDone }}) {{
      if (sessionId !== playSessionId) return;
      if (!synth) {{
        showToast('当前浏览器不支持语音合成，请配置 FishAudio 代理');
        resetActiveUI();
        if (onDone) onDone(false);
        return;
      }}

      try {{
        synth.cancel();
        const utter = new SpeechSynthesisUtterance(text);
        utter.lang = 'ja-JP';
        utter.rate = rate;
        if (jaVoice) utter.voice = jaVoice;

        setCardState(cardEl, 'playing');
        setTestBtnState(btn, 'playing');

        utter.onstart = () => {{
          if (sessionId !== playSessionId) return;
          setCardState(cardEl, 'playing');
          setTestBtnState(btn, 'playing');
        }};

        utter.onend = () => {{
          if (sessionId !== playSessionId) return;
          if (!isBedtimePlaying) resetActiveUI();
          else setCardState(cardEl, 'idle');
          if (onDone) onDone(true);
        }};

        utter.onerror = (e) => {{
          if (sessionId !== playSessionId) return;
          if (e && (e.error === 'interrupted' || e.error === 'canceled')) return;
          if (!isBedtimePlaying) resetActiveUI();
          else setCardState(cardEl, 'idle');
          if (onDone) onDone(false);
        }};

        synth.speak(utter);
      }} catch (e) {{
        resetActiveUI();
        if (onDone) onDone(false);
      }}
    }}

    /**
     * 点击整张例句 / 词组 / 睡前卡片朗读（再次点击同一卡片停止）
     */
    function speakCard(cardEl) {{
      const isSameCardActive = activeCardEl === cardEl && !isBedtimePlaying;
      stopAllSpeech();
      if (isSameCardActive) return;

      const text = extractCleanJapaneseText(cardEl);
      if (!text) return;
      playUnifiedTTS({{ text, rate: globalRate, cardEl }});
    }}

    /**
     * 中文翻译点击处理：隐藏翻译模式下仅偷看翻译，不误触发音
     */
    function handleTranslationClick(event, el) {{
      if (document.body.classList.contains('hide-translation')) {{
        event.stopPropagation();
        el.classList.toggle('peeked');
      }}
    }}

    /* -----------------------------------------------------------
       5. 渲染例句卡片（整卡点击发音 + 极简小圆点状态指示）
    ----------------------------------------------------------- */
    function renderExamples() {{
      Object.keys(GRAMMAR_EXAMPLES).forEach(groupKey => {{
        const container = document.getElementById(`examples-${{groupKey}}`);
        if (!container) return;

        const items = GRAMMAR_EXAMPLES[groupKey];
        container.innerHTML = items.map((item, idx) => {{
          const textId = `jp-${{groupKey}}-${{idx}}`;
          const cardStyle = item.isContrast
            ? 'bg-teal-50/40 hover:bg-teal-50/80 border-dashed border-teal-200 hover:border-teal-300'
            : 'bg-[#FCFBF9] hover:bg-white border-stone-200/80 hover:border-amber-300';
          const noteHtml = item.note
            ? `<div class="mt-1.5 inline-flex items-center gap-1 text-xs ${{item.noteStyle}} border px-2.5 py-0.5 rounded-lg">📌 ${{item.note}}</div>`
            : '';

          return `
            <div role="button" tabindex="0"
              data-text="${{escapeAttr(item.plainText)}}"
              onclick="speakCard(this)"
              onkeydown="if(event.key==='Enter'||event.key===' '){{event.preventDefault();speakCard(this);}}"
              aria-label="点击卡片播放日语例句"
              class="playable-card group cursor-pointer select-none ${{cardStyle}} border rounded-2xl p-4">
              <div class="flex items-start justify-between gap-3">
                <div class="flex-1 min-w-0">
                  <div class="flex flex-wrap items-center gap-2 mb-2">
                    <span class="text-[11px] font-bold px-2.5 py-0.5 rounded-full border ${{item.tagStyle}}">${{item.tag}}</span>
                  </div>
                  <p id="${{textId}}" class="jp-speech-target font-jp text-base sm:text-[17px] leading-[2.15] text-stone-800 tracking-wide break-words">
                    ${{item.jpHtml}}
                  </p>
                  <p class="translation-text text-sm text-stone-500 mt-1.5 leading-relaxed" title="隐藏翻译时点击可临时查看" onclick="handleTranslationClick(event, this)">
                    ${{item.cn}}
                  </p>
                  ${{noteHtml}}
                </div>
                ${{renderDotIndicatorHtml()}}
              </div>
            </div>
          `;
        }}).join('');
      }});
    }}

    /* -----------------------------------------------------------
       6. 渲染睡前 3 分钟互动小自测
    ----------------------------------------------------------- */
    const quizAnswers = {{}};

    function renderQuiz() {{
      const container = document.getElementById('quiz-container');
      container.innerHTML = QUIZ_DATA.map((q, qIndex) => {{
        const optionsHtml = q.options.map((opt, optIdx) => `
          <button type="button"
            data-q="${{q.id}}" data-opt="${{optIdx}}"
            onclick="handleQuizChoice(${{q.id}}, ${{optIdx}})"
            class="quiz-opt-${{q.id}} text-left px-3.5 py-2.5 rounded-xl border border-stone-200 bg-white hover:bg-amber-50 hover:border-amber-300 text-stone-800 font-jp text-sm transition active:scale-[0.98]">
            <span class="inline-block w-5 h-5 rounded-full bg-stone-100 text-stone-500 text-xs font-bold text-center leading-5 mr-2">${{String.fromCharCode(65 + optIdx)}}</span>
            <span>${{opt}}</span>
          </button>
        `).join('');

        return `
          <div class="bg-[#FAF7F2] text-stone-800 rounded-2xl p-4 sm:p-5 border border-stone-200/80">
            <div class="flex items-center justify-between gap-2 mb-2">
              <span class="text-xs font-bold px-2.5 py-0.5 rounded-full bg-slate-800 text-amber-200">Q${{qIndex + 1}} · ${{q.grammar}}</span>
              <span id="quiz-status-${{q.id}}" class="text-xs font-bold"></span>
            </div>
            <p class="font-jp text-sm sm:text-base font-medium text-stone-800 leading-[1.95] mb-3.5">${{q.questionHtml}}</p>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              ${{optionsHtml}}
            </div>
            <div id="quiz-exp-${{q.id}}" class="hidden mt-3 text-xs sm:text-sm p-3 rounded-xl leading-relaxed"></div>
          </div>
        `;
      }}).join('');
    }}

    function handleQuizChoice(qId, chosenIdx) {{
      const q = QUIZ_DATA.find(item => item.id === qId);
      if (!q) return;

      const isCorrect = chosenIdx === q.answer;
      quizAnswers[qId] = isCorrect;

      document.querySelectorAll(`.quiz-opt-${{qId}}`).forEach((btn, idx) => {{
        btn.disabled = true;
        btn.classList.remove('hover:bg-amber-50', 'hover:border-amber-300', 'bg-white', 'border-stone-200');
        if (idx === q.answer) {{
          btn.classList.add('bg-emerald-50', 'border-emerald-500', 'text-emerald-900', 'font-bold');
        }} else if (idx === chosenIdx && !isCorrect) {{
          btn.classList.add('bg-rose-50', 'border-rose-400', 'text-rose-800');
        }} else {{
          btn.classList.add('bg-stone-50', 'border-stone-200', 'opacity-60');
        }}
      }});

      const statusEl = document.getElementById(`quiz-status-${{qId}}`);
      statusEl.textContent = isCorrect ? '✅ 回答正确' : '❌ 再记一下';
      statusEl.className = `text-xs font-bold ${{isCorrect ? 'text-emerald-600' : 'text-rose-600'}}`;

      const expEl = document.getElementById(`quiz-exp-${{qId}}`);
      expEl.classList.remove('hidden');
      expEl.className = `mt-3 text-xs sm:text-sm p-3 rounded-xl leading-relaxed border ${{
        isCorrect ? 'bg-emerald-50/80 border-emerald-200 text-emerald-900' : 'bg-rose-50/80 border-rose-200 text-rose-900'
      }}`;
      expEl.innerHTML = `<strong>解析：</strong>${{q.explanation}}`;

      updateQuizProgress();
    }}

    function updateQuizProgress() {{
      const total = QUIZ_DATA.length;
      const answeredCount = Object.keys(quizAnswers).length;
      const correctCount = Object.values(quizAnswers).filter(Boolean).length;
      const badge = document.getElementById('quiz-score-badge');
      badge.textContent = `已完成 ${{answeredCount}} / ${{total}}（对 ${{correctCount}} 题）`;

      const summary = document.getElementById('quiz-summary');
      const summaryText = document.getElementById('quiz-summary-text');

      if (answeredCount === total) {{
        summary.classList.remove('hidden');
        const rate = Math.round((correctCount / total) * 100);
        let comment = '';
        if (correctCount === total) {{
          comment = `🎉 今日掌握度 100%（${{total}}/${{total}} 全对）！四个文法已经牢牢刻进脑海啦，安心睡个好觉吧！`;
        }} else if (correctCount >= total - 1) {{
          comment = `🌟 今日掌握度 ${{rate}}%（${{correctCount}}/${{total}}）！表现很棒，睡前再听一遍连播巩固错题就完美了。`;
        }} else {{
          comment = `💪 今日掌握度 ${{rate}}%（${{correctCount}}/${{total}}）。别着急，把上面的口诀和避坑点再看一眼，明天会更顺手！`;
        }}
        summaryText.textContent = comment;
      }}
    }}

    function resetQuiz() {{
      Object.keys(quizAnswers).forEach(k => delete quizAnswers[k]);
      document.getElementById('quiz-score-badge').textContent = `已完成 0 / ${{QUIZ_DATA.length}}`;
      document.getElementById('quiz-summary').classList.add('hidden');
      renderQuiz();
    }}

    /* -----------------------------------------------------------
       7. 睡前磨耳朵一键连播（单卡可点 + 极简小圆点指示）
    ----------------------------------------------------------- */
    function renderBedtimePlaylist() {{
      const container = document.getElementById('bedtime-playlist');
      container.innerHTML = BEDTIME_PLAYLIST.map((item, idx) => `
        <div id="bedtime-item-${{idx}}" role="button" tabindex="0"
          data-text="${{escapeAttr(item.plainText)}}"
          onclick="speakCard(this)"
          onkeydown="if(event.key==='Enter'||event.key===' '){{event.preventDefault();speakCard(this);}}"
          aria-label="点击播放睡前核心例句"
          class="playable-card group cursor-pointer select-none rounded-xl p-3.5 bg-slate-800/70 hover:bg-slate-800 border border-slate-700/80 hover:border-amber-300/50 flex items-start justify-between gap-3">
          <div class="flex-1 min-w-0">
            <div class="text-xs font-bold ${{item.color}} mb-1">${{item.label}}</div>
            <p id="bedtime-jp-${{idx}}" class="jp-speech-target font-jp text-sm sm:text-base leading-[2.05] text-stone-100">${{item.jpHtml}}</p>
            <p class="translation-text text-xs text-slate-400 mt-1" onclick="handleTranslationClick(event, this)">${{item.cn}}</p>
          </div>
          ${{renderDotIndicatorHtml()}}
        </div>
      `).join('');
    }}

    function updateBedtimePlayUI(playing) {{
      const icon = document.getElementById('bedtime-play-icon');
      const text = document.getElementById('bedtime-play-text');
      icon.textContent = playing ? '⏹' : '🎧';
      text.textContent = playing ? '停止连播' : `连播今日${{BEDTIME_PLAYLIST.length}}句核心例句`;
    }}

    function toggleBedtimePlaylist() {{
      if (isBedtimePlaying) {{
        stopAllSpeech();
        return;
      }}
      stopAllSpeech();
      isBedtimePlaying = true;
      updateBedtimePlayUI(true);
      document.getElementById('btn-stop-all').classList.remove('hidden');
      playBedtimeIndex(0);
    }}

    function playBedtimeIndex(index) {{
      if (!isBedtimePlaying) return;
      if (index >= BEDTIME_PLAYLIST.length) {{
        isBedtimePlaying = false;
        updateBedtimePlayUI(false);
        resetActiveUI();
        showToast(`🌙 睡前 ${{BEDTIME_PLAYLIST.length}} 句核心例句连播完成，晚安！`);
        return;
      }}

      const cardEl = document.getElementById(`bedtime-item-${{index}}`);
      if (!cardEl) return;
      cardEl.scrollIntoView({{ behavior: 'smooth', block: 'nearest' }});

      const text = extractCleanJapaneseText(cardEl);
      playUnifiedTTS({{
        text,
        rate: 0.85,
        cardEl,
        onDone: (ok) => {{
          if (!isBedtimePlaying) return;
          if (!ok) {{
            stopAllSpeech();
            return;
          }}
          bedtimeTimer = setTimeout(() => {{
            playBedtimeIndex(index + 1);
          }}, 680);
        }}
      }});
    }}

    /* -----------------------------------------------------------
       8. 顶部控制栏事件绑定
    ----------------------------------------------------------- */
    function initGlobalControls() {{
      const btnSpeed = document.getElementById('btn-speed');
      const speedLabel = document.getElementById('speed-label');
      btnSpeed.addEventListener('click', () => {{
        if (globalRate === 1.0) {{
          globalRate = 0.75;
          speedLabel.textContent = '慢速 0.75x';
          btnSpeed.classList.add('bg-amber-50', 'border-amber-300', 'text-amber-800');
          btnSpeed.classList.remove('bg-[#FAF7F2]', 'border-stone-200', 'text-stone-700');
          showToast('全局朗读语速已切换为：慢速 0.75x');
        }} else {{
          globalRate = 1.0;
          speedLabel.textContent = '正常 1.0x';
          btnSpeed.classList.remove('bg-amber-50', 'border-amber-300', 'text-amber-800');
          btnSpeed.classList.add('bg-[#FAF7F2]', 'border-stone-200', 'text-stone-700');
          showToast('全局朗读语速已切换为：正常 1.0x');
        }}
        if (activeAudio && !activeAudio.paused && !isBedtimePlaying) {{
          activeAudio.playbackRate = globalRate;
        }}
      }});

      const btnFurigana = document.getElementById('btn-furigana');
      btnFurigana.addEventListener('click', () => {{
        const isHidden = document.body.classList.toggle('hide-furigana');
        btnFurigana.setAttribute('aria-pressed', String(!isHidden));
        btnFurigana.innerHTML = isHidden
          ? `<span class="w-2 h-2 rounded-full bg-stone-400"></span><span>假名注音：关</span>`
          : `<span class="w-2 h-2 rounded-full bg-indigo-500"></span><span>假名注音：开</span>`;
        btnFurigana.classList.toggle('bg-indigo-50', !isHidden);
        btnFurigana.classList.toggle('border-indigo-200', !isHidden);
        btnFurigana.classList.toggle('text-indigo-700', !isHidden);
        btnFurigana.classList.toggle('bg-white', isHidden);
        btnFurigana.classList.toggle('border-stone-200', isHidden);
        btnFurigana.classList.toggle('text-stone-500', isHidden);
      }});

      const btnTranslation = document.getElementById('btn-translation');
      btnTranslation.addEventListener('click', () => {{
        const isHidden = document.body.classList.toggle('hide-translation');
        document.querySelectorAll('.translation-text.peeked').forEach(el => el.classList.remove('peeked'));
        btnTranslation.setAttribute('aria-pressed', String(!isHidden));
        btnTranslation.innerHTML = isHidden
          ? `<span class="w-2 h-2 rounded-full bg-stone-400"></span><span>中文翻译：关</span>`
          : `<span class="w-2 h-2 rounded-full bg-emerald-500"></span><span>中文翻译：开</span>`;
        btnTranslation.classList.toggle('bg-emerald-50', !isHidden);
        btnTranslation.classList.toggle('border-emerald-200', !isHidden);
        btnTranslation.classList.toggle('text-emerald-700', !isHidden);
        btnTranslation.classList.toggle('bg-white', isHidden);
        btnTranslation.classList.toggle('border-stone-200', isHidden);
        btnTranslation.classList.toggle('text-stone-500', isHidden);
        if (isHidden) {{
          showToast('已隐藏中文翻译，点击模糊区域可单独偷看');
        }}
      }});

      document.getElementById('btn-stop-all').addEventListener('click', stopAllSpeech);

      const modal = document.getElementById('voice-settings-modal');
      modal.addEventListener('click', (e) => {{
        if (e.target === modal) closeVoiceModal();
      }});

      document.addEventListener('keydown', (e) => {{
        if (e.key === 'Escape' && !modal.classList.contains('hidden')) {{
          closeVoiceModal();
        }}
      }});
    }}

    window.addEventListener('beforeunload', () => {{
      stopAllSpeech();
    }});

    document.addEventListener('DOMContentLoaded', () => {{
      loadVoiceSettings();
      renderExamples();
      renderQuiz();
      renderBedtimePlaylist();
      initGlobalControls();
    }});
  </script>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Render Japanese grammar daily journal HTML from JSON.")
    parser.add_argument("input_json", type=Path, help="Path to daily grammar JSON file")
    parser.add_argument("--output", "-o", type=Path, help="Output HTML path (default: 日语文法-YYYY.MM.DD.html in cwd)")
    parser.add_argument("--index-href", type=str, default=None, help="Optional relative href back to index.html (e.g. ../index.html)")
    args = parser.parse_args()

    try:
        data = json.loads(args.input_json.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"ERROR: failed to read JSON {args.input_json}: {exc}", file=sys.stderr)
        return 1

    errors = validate_data(data)
    if errors:
        print("Validation failed:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    out_path = args.output or Path(f"日语文法-{data['date']}.html")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    rendered = render_html(data, index_href=args.index_href)
    out_path.write_text(rendered, encoding="utf-8")
    print(f"Rendered {out_path} ({len(rendered.encode('utf-8'))} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
