# 日语文法每日手账 (Japanese Grammar Journal)

每天 4 个日语文法的交互式复习手账静态站：
- `index.html`：按日期倒序展示全部每日手账，支持关键词筛选。
- `pages/日语文法-YYYY.MM.DD.html`：每日独立静态网页（假名开关、翻译偷看、小圆点发音、睡前复习与自测）。
- `data/YYYY.MM.DD.json`：每日结构化文法数据。
- `scripts/render_journal.py` & `scripts/build_index.py`：渲染每日手账页面并重建导航主页。

## 添加新一天的手账

```bash
python3 scripts/render_journal.py data/YYYY.MM.DD.json \
  --output pages/日语文法-YYYY.MM.DD.html \
  --index-href ../index.html
python3 scripts/build_index.py
```
