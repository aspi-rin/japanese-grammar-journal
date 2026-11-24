#!/usr/bin/env python3
"""Build index.html navigation homepage for the Japanese grammar journal site."""

from __future__ import annotations

import html
import json
from pathlib import Path
from urllib.parse import quote

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
OUT_INDEX = REPO_ROOT / "index.html"

PILL_STYLES = [
    "bg-indigo-50 text-indigo-800 border-indigo-200/80",
    "bg-emerald-50 text-emerald-800 border-emerald-200/80",
    "bg-orange-50 text-orange-800 border-orange-200/80",
    "bg-purple-50 text-purple-800 border-purple-200/80",
]


def esc(text: str) -> str:
    return html.escape(str(text), quote=True)


def build_index() -> None:
    entries: list[dict] = []
    for json_path in sorted(DATA_DIR.glob("*.json"), reverse=True):
        data = json.loads(json_path.read_text(encoding="utf-8"))
        date_str = data["date"]
        filename = f"日语文法-{date_str}.html"
        grammars = data.get("grammars") or []
        example_count = sum(len(g.get("examples") or []) for g in grammars)
        phrase_count = sum(len(g.get("phrases") or []) for g in grammars)
        entries.append(
            {
                "date": date_str,
                "filename": filename,
                "href": f"./pages/{quote(filename)}",
                "level": data.get("levelBadge") or "N2 / N3 核心精讲",
                "subtitle": data.get("subtitle") or "",
                "grammars": [
                    {
                        "pattern": g["pattern"],
                        "meaning": g["meaning"],
                        "keywords": g.get("keywords", ""),
                    }
                    for g in grammars
                ],
                "exampleCount": example_count,
                "phraseCount": phrase_count,
            }
        )

    entries.sort(key=lambda e: e["date"], reverse=True)
    total_days = len(entries)
    total_grammars = sum(len(e["grammars"]) for e in entries)
    total_examples = sum(e["exampleCount"] for e in entries)
    latest_date = entries[0]["date"] if entries else "—"

    cards_html: list[str] = []
    for idx, entry in enumerate(entries):
        is_latest = idx == 0
        latest_badge = (
            '<span class="px-2 py-0.5 rounded-full bg-amber-100 border border-amber-300/80 text-amber-900 text-[11px] font-bold">最新</span>'
            if is_latest
            else ""
        )
        pills = []
        search_terms = [entry["date"], entry["level"]]
        for g_idx, g in enumerate(entry["grammars"]):
            style = PILL_STYLES[g_idx % len(PILL_STYLES)]
            search_terms.extend([g["pattern"], g["meaning"], g["keywords"]])
            pills.append(
                f"""
                <div class="rounded-2xl border {style} px-3 py-2">
                  <div class="font-jp text-sm font-bold leading-snug">{esc(g['pattern'])}</div>
                  <div class="text-xs opacity-80 mt-0.5 line-clamp-1">{esc(g['meaning'])}</div>
                </div>"""
            )

        search_blob = esc(" ".join(search_terms).lower())
        stats_text = f"{len(entry['grammars'])} 个文法 · {entry['exampleCount']} 条例句"
        if entry["phraseCount"]:
            stats_text += f" · {entry['phraseCount']} 组对比小卡"

        cards_html.append(
            f"""
      <a href="{entry['href']}" data-search="{search_blob}"
        class="day-card group block bg-white/95 hover:bg-white rounded-3xl border border-stone-200/80 hover:border-amber-300 p-5 sm:p-6 journal-card transition duration-200 hover:-translate-y-0.5">
        <div class="flex flex-wrap items-center justify-between gap-2 mb-3.5">
          <div class="flex items-center gap-2.5">
            <span class="font-maru text-xl sm:text-2xl font-bold text-stone-800 group-hover:text-amber-700 transition">{esc(entry['date'])}</span>
            {latest_badge}
          </div>
          <div class="flex items-center gap-2 text-xs text-stone-500">
            <span>{esc(stats_text)}</span>
            <span class="w-7 h-7 rounded-xl bg-stone-100 group-hover:bg-amber-100 text-stone-500 group-hover:text-amber-800 flex items-center justify-center transition">→</span>
          </div>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
          {''.join(pills)}
        </div>
      </a>"""
        )

    page_html = f"""<!DOCTYPE html>
<html lang="zh-CN" class="scroll-smooth">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>日语文法每日手账 · 目录</title>
  <script src="https://cdn.tailwindcss.com"></script>
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
          }}
        }}
      }}
    }};
  </script>
  <style>
    body {{
      background-color: #FAF7F2;
      background-image: radial-gradient(#E2DACD 1px, transparent 1px);
      background-size: 22px 22px;
      color: #2D2A26;
      -webkit-tap-highlight-color: transparent;
    }}
    .journal-card {{
      box-shadow: 0 4px 20px -2px rgba(92, 76, 56, 0.07), 0 1px 3px rgba(92, 76, 56, 0.05);
    }}
  </style>
</head>
<body class="font-sans antialiased min-h-screen selection:bg-amber-200/70">
  <header class="max-w-4xl mx-auto px-4 pt-7 pb-4 sm:pt-10">
    <div class="bg-white/90 backdrop-blur-sm border border-stone-200/80 rounded-3xl p-6 sm:p-8 journal-card relative overflow-hidden">
      <div class="absolute -top-2 right-8 w-20 h-6 bg-amber-200/70 rotate-3 rounded-sm pointer-events-none"></div>
      <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-amber-50 border border-amber-200/80 text-amber-800 text-xs font-medium mb-3">
        <span>📓 日语文法每日手账</span>
        <span class="text-amber-400">•</span>
        <span>每日 4 个核心文法</span>
      </div>
      <h1 class="font-maru text-2xl sm:text-3xl font-bold text-stone-800 tracking-tight">
        日语文法手账目录
      </h1>
      <p class="text-sm text-stone-500 mt-1.5">
        按日期倒序收录每日 YouTube 文法教学手账，支持点击卡片朗读、假名/翻译开关与睡前复习。
      </p>

      <div class="mt-5 grid grid-cols-3 gap-2.5 sm:gap-3">
        <div class="rounded-2xl bg-[#FAF7F2] border border-stone-200/80 px-3.5 py-2.5">
          <div class="text-[11px] text-stone-500">已打卡天数</div>
          <div class="font-maru text-xl sm:text-2xl font-bold text-stone-800 mt-0.5">{total_days}</div>
        </div>
        <div class="rounded-2xl bg-[#FAF7F2] border border-stone-200/80 px-3.5 py-2.5">
          <div class="text-[11px] text-stone-500">累计文法点</div>
          <div class="font-maru text-xl sm:text-2xl font-bold text-amber-700 mt-0.5">{total_grammars}</div>
        </div>
        <div class="rounded-2xl bg-[#FAF7F2] border border-stone-200/80 px-3.5 py-2.5">
          <div class="text-[11px] text-stone-500">最近更新</div>
          <div class="font-maru text-base sm:text-xl font-bold text-stone-800 mt-1">{esc(latest_date)}</div>
        </div>
      </div>
    </div>
  </header>

  <section aria-label="筛选文法" class="max-w-4xl mx-auto px-4 pt-1 pb-2">
    <div class="relative">
      <input id="filter-input" type="search" placeholder="搜索日期、文法（如 からには / うちに / おかげで）或中文意思…"
        class="w-full pl-10 pr-4 py-3 rounded-2xl bg-white/95 border border-stone-200/90 text-sm text-stone-800 placeholder:text-stone-400 focus:outline-none focus:ring-2 focus:ring-amber-400/70 focus:border-amber-400 journal-card transition" />
      <span class="absolute left-3.5 top-1/2 -translate-y-1/2 text-stone-400 text-sm pointer-events-none">🔍</span>
    </div>
  </section>

  <main class="max-w-4xl mx-auto px-4 py-4 pb-14 space-y-4">
    <div id="day-list" class="space-y-4">
      {''.join(cards_html)}
    </div>
    <div id="empty-state" class="hidden text-center py-12 rounded-3xl bg-white/80 border border-dashed border-stone-300 text-sm text-stone-500">
      没有找到匹配的文法记录，换个关键词试试吧。
    </div>
  </main>

  <footer class="max-w-4xl mx-auto px-4 pb-10 text-center text-xs text-stone-400">
    <p>毎日コツコツ、積み重ねが力になる。共收录 {total_grammars} 个文法 · {total_examples} 条例句 ✨</p>
  </footer>

  <script>
    const input = document.getElementById('filter-input');
    const cards = Array.from(document.querySelectorAll('.day-card'));
    const emptyState = document.getElementById('empty-state');

    input.addEventListener('input', () => {{
      const q = input.value.trim().toLowerCase();
      let visible = 0;
      cards.forEach((card) => {{
        const hit = !q || (card.dataset.search || '').includes(q);
        card.classList.toggle('hidden', !hit);
        if (hit) visible++;
      }});
      emptyState.classList.toggle('hidden', visible > 0);
    }});
  </script>
</body>
</html>
"""
    OUT_INDEX.write_text(page_html, encoding="utf-8")
    print(f"Built {OUT_INDEX} ({total_days} days, {total_grammars} grammars)")


if __name__ == "__main__":
    build_index()
