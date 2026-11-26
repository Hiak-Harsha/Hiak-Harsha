"""Sync public repositories and generate animated OpenCode SVGs for Hiak-Harsha."""
from datetime import date, timedelta
import html
import json
import os
from pathlib import Path
import re
import urllib.request

USERNAME = "Hiak-Harsha"
ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = ROOT / "assets"
README_PATH = ROOT / "README.md"

TOP_MENTIONS = {
    "Hiak-Harsha",
    "Quant-Alpha-Engine",
    "dynamic-dual-model",
    "custom-avatar-studio",
}

FALLBACK_DESCRIPTIONS = {
    "Project-Graph": "codebase dependency audit dashboard across files, modules, APIs & databases",
    "Workspace-Navigator": "multi-project workspace navigation utility",
    "Cli-Setup": "automated CLI environment setup tool",
    "omnipolish": "Python workflow & polish utilities",
    "RAIL_OPT": "real-time railway traffic optimization & operations control center (`OR-Tools`, `Three.js`)",
    "ChainSentinal": "air-gapped Bitcoin transaction forensics & taint-tracing platform (`DuckDB`, `SHAP`)",
    "BharatSR": "4× Sentinel-2 satellite image super-resolution pipeline (`PyTorch`, `GDAL`)",
    "Sentinel-Flow-AI-Demo": "real-time AI network intrusion & anomaly detection (`Scikit-learn`, `FastAPI`)",
    "Society-Vault": "auditable financial & loan management platform (`TypeScript`, `Prisma`, `Razorpay/Stripe`)",
    "kee-crochet-shop": "full-stack e-commerce platform with Razorpay checkout",
    "Table-Tennis-Academy": "multi-role academy management & Zod-validated billing platform",
    "Career-Graph": "interactive visualization of projects, skills & credentials (`D3.js`, `FastAPI`)",
    "Sahaaya": "Kotlin mobile application",
    "Movie-Recommendation": "movie recommendation engine in Python",
    "Fake-News-Detector": "fake news classification pipeline in Python",
    "Start---Up-Market-Research-Analysis": "startup funding & market research analysis",
}

# Exact OpenCode 4x8 pixel glyph patterns (0=empty, 1=solid, 2=inset shadow)
BG = "#0A0A0A"
GRAY = "#808080"
GRAY_SHADOW = "#282828"
WHITE = "#EEEEEE"
WHITE_SHADOW = "#434343"
AMBER = "#d97706"

GLYPHS = {
    "a": [[0,0,0,0],[0,0,0,0],[0,1,1,1],[0,0,0,1],[0,1,1,1],[1,2,2,1],[0,1,1,1],[0,0,0,0]],
    "b": [[1,0,0,0],[1,0,0,0],[1,1,1,0],[1,0,0,1],[1,2,2,1],[1,2,2,1],[1,1,1,0],[0,0,0,0]],
    "c": [[0,0,0,0],[0,0,0,0],[0,1,1,1],[1,0,0,0],[1,2,0,0],[1,2,0,0],[0,1,1,1],[0,0,0,0]],
    "d": [[0,0,0,1],[0,0,0,1],[0,1,1,1],[1,0,0,1],[1,2,2,1],[1,2,2,1],[0,1,1,1],[0,0,0,0]],
    "e": [[0,0,0,0],[0,0,0,0],[0,1,1,0],[1,0,0,1],[1,1,1,1],[1,2,0,0],[0,1,1,1],[0,0,0,0]],
    "h": [[1,0,0,0],[1,0,0,0],[1,1,1,0],[1,0,0,1],[1,2,2,1],[1,2,2,1],[1,0,0,1],[0,0,0,0]],
    "i": [[0,0,0,0],[0,1,1,0],[0,0,0,0],[0,1,1,0],[0,1,1,0],[0,2,2,0],[0,1,1,0],[0,0,0,0]],
    "k": [[1,0,0,0],[1,0,0,0],[1,0,0,1],[1,0,1,0],[1,1,0,0],[1,2,1,0],[1,0,0,1],[0,0,0,0]],
    "l": [[1,1,0,0],[0,1,0,0],[0,1,0,0],[0,1,0,0],[0,1,0,0],[0,2,0,0],[0,1,1,1],[0,0,0,0]],
    "o": [[0,0,0,0],[0,0,0,0],[0,1,1,0],[1,0,0,1],[1,2,2,1],[1,2,2,1],[0,1,1,0],[0,0,0,0]],
    "r": [[0,0,0,0],[0,0,0,0],[1,1,1,0],[1,0,0,1],[1,2,0,0],[1,2,0,0],[1,0,0,0],[0,0,0,0]],
    "s": [[0,0,0,0],[0,0,0,0],[0,1,1,1],[1,0,0,0],[0,1,1,0],[0,0,2,1],[1,1,1,0],[0,0,0,0]],
    "t": [[0,1,0,0],[0,1,0,0],[1,1,1,0],[0,1,0,0],[0,1,0,0],[0,2,0,0],[0,0,1,1],[0,0,0,0]],
    "u": [[0,0,0,0],[0,0,0,0],[1,0,0,1],[1,0,0,1],[1,2,2,1],[1,2,2,1],[0,1,1,1],[0,0,0,0]],
    " ": [[0,0,0,0]] * 8,
}

FONT_MONO = "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace"


def build_text_grid(text: str, split_index: int | None = None) -> list[list[str | None]]:
    if split_index is None:
        split_index = len(text) // 2
    colored_chars = []
    for idx, ch in enumerate(text):
        glyph = GLYPHS.get(ch.lower(), GLYPHS[" "])
        c_main = GRAY if idx < split_index else WHITE
        c_shadow = GRAY_SHADOW if idx < split_index else WHITE_SHADOW
        char_grid = []
        for r in range(8):
            row = []
            for val in glyph[r]:
                if val == 0:
                    row.append(None)
                elif val == 1:
                    row.append(c_main)
                else:
                    row.append(c_shadow)
            char_grid.append(row)
        colored_chars.append(char_grid)

    grid: list[list[str | None]] = []
    for r in range(8):
        row: list[str | None] = []
        for idx, ch_grid in enumerate(colored_chars):
            if idx > 0:
                row.append(None)
            row.extend(ch_grid[r])
        grid.append(row)
    return grid


def render_animated_pixel_runs(
    grid: list[list[str | None]],
    ox: int,
    oy: int,
    scale: int,
    base_delay: float = 0.08,
    step: float = 0.025,
) -> str:
    """Render merged horizontal pixel runs that materialize in a clean pixel-wave."""
    rects = []
    cols = len(grid[0]) if grid else 0
    for r, row in enumerate(grid):
        c = 0
        while c < cols:
            col = row[c]
            if col is None:
                c += 1
                continue
            start = c
            while c < cols and row[c] == col:
                c += 1
            width = (c - start) * scale
            # Deterministic pixel-storm stagger based on column & row
            delay = base_delay + ((start * 3 + r * 2) % 14) * step
            rects.append(
                f'<rect x="{ox + start * scale}" y="{oy + r * scale}" '
                f'width="{width}" height="{scale}" fill="{col}" opacity="0">'
                f'<animate attributeName="opacity" from="0" to="1" '
                f'begin="{delay:.2f}s" dur="0.20s" fill="freeze"/>'
                f'</rect>'
            )
    return "\n    ".join(rects)


def mini_mascot_svg(x: int, y: int) -> str:
    """Crisp animated mini vector pixel orange brick mascot."""
    return f'''<g transform="translate({x}, {y})">
    <g>
      <animateTransform attributeName="transform" type="translate" values="0,0; 0,-3; 0,0; 0,0" keyTimes="0;0.25;0.5;1" dur="2.2s" repeatCount="indefinite"/>
      <!-- Left & right arms -->
      <rect x="0" y="13" width="5" height="5" fill="#C4684D" stroke="#111111" stroke-width="1"/>
      <rect x="37" y="13" width="5" height="5" fill="#C4684D" stroke="#111111" stroke-width="1"/>
      <!-- 4 little legs -->
      <rect x="8" y="25" width="4" height="6" fill="#8E422E" stroke="#111111" stroke-width="1"/>
      <rect x="14" y="25" width="4" height="6" fill="#8E422E" stroke="#111111" stroke-width="1"/>
      <rect x="24" y="25" width="4" height="6" fill="#8E422E" stroke="#111111" stroke-width="1"/>
      <rect x="30" y="25" width="4" height="6" fill="#8E422E" stroke="#111111" stroke-width="1"/>
      <!-- Body -->
      <rect x="5" y="4" width="32" height="21" rx="1.5" fill="#CF6D50" stroke="#111111" stroke-width="1.5"/>
      <!-- Subtle top highlight -->
      <rect x="7" y="6" width="28" height="2" fill="#DE8368" opacity="0.65"/>
      <!-- Eyes + periodic blink -->
      <g>
        <animate attributeName="opacity" values="1;1;0;1;1" keyTimes="0;0.90;0.94;0.98;1" dur="3.6s" repeatCount="indefinite"/>
        <rect x="12" y="10" width="4" height="7" fill="#181210"/>
        <rect x="26" y="10" width="4" height="7" fill="#181210"/>
        <rect x="13" y="11" width="1.5" height="1.5" fill="#EEEEEE"/>
        <rect x="27" y="11" width="1.5" height="1.5" fill="#EEEEEE"/>
      </g>
    </g>
  </g>'''


def http_get(url: str, accept: str = "application/vnd.github+json") -> str:
    headers = {"Accept": accept, "User-Agent": f"{USERNAME}-profile-updater"}
    token = os.environ.get("GITHUB_TOKEN")
    if token and "api.github.com" in url:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8")


def fetch_profile_data() -> dict:
    user = json.loads(http_get(f"https://api.github.com/users/{USERNAME}"))
    repos: list[dict] = []
    page = 1
    while True:
        batch = json.loads(
            http_get(
                f"https://api.github.com/users/{USERNAME}/repos"
                f"?type=owner&sort=pushed&direction=desc&per_page=100&page={page}"
            )
        )
        if not batch:
            break
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1

    owned_public = [r for r in repos if not r.get("fork") and not r.get("private")]
    listed_repos = [r for r in owned_public if r["name"] not in TOP_MENTIONS]

    # Latest active non-profile repo
    active_repos = [r for r in owned_public if r["name"] != USERNAME]
    latest_repo = active_repos[0]["name"] if active_repos else "custom-avatar-studio"

    # Language distribution across owned public repos (weighted by repo size)
    lang_weights: dict[str, int] = {}
    total_stars = 0
    for r in owned_public:
        total_stars += int(r.get("stargazers_count", 0))
        lang = r.get("language")
        if lang:
            lang_weights[lang] = lang_weights.get(lang, 0) + max(1, int(r.get("size", 1)))

    # Contributions calendar (last year)
    contrib_html = http_get(f"https://github.com/users/{USERNAME}/contributions", accept="text/html")
    raw_days = re.findall(r'data-date="(\d{4}-\d{2}-\d{2})"[^>]*data-level="(\d)"', contrib_html)
    day_map = {d: int(lvl) for d, lvl in raw_days}
    total_match = re.search(r"([\d,]+)\s+contributions\s+in\s+the\s+last\s+year", contrib_html)
    total_contribs = total_match.group(1) if total_match else str(sum(1 for v in day_map.values() if v > 0))

    def fmt_range(start_iso: str | None, end_iso: str | None) -> str:
        if not start_iso or not end_iso:
            return "—"
        s_dt = date.fromisoformat(start_iso)
        e_dt = date.fromisoformat(end_iso)
        if s_dt == e_dt:
            return s_dt.strftime("%b %d").replace(" 0", " ")
        s_str = s_dt.strftime("%b %d").replace(" 0", " ")
        e_str = e_dt.strftime("%b %d" if s_dt.month != e_dt.month else "%d").replace(" 0", " ")
        return f"{s_str}–{e_str}"

    # Compute current & longest active-day streaks with date ranges from day_map
    sorted_dates = sorted(day_map.keys())
    longest_streak = 0
    longest_start = longest_end = None
    run = 0
    run_start = None
    for d in sorted_dates:
        if day_map[d] > 0:
            if run == 0:
                run_start = d
            run += 1
            if run >= longest_streak:
                longest_streak = run
                longest_start = run_start
                longest_end = d
        else:
            run = 0
            run_start = None

    current_streak = 0
    cur_start = cur_end = None
    if sorted_dates:
        idx = len(sorted_dates) - 1
        # Allow today to be 0 if yesterday had activity
        if day_map[sorted_dates[idx]] == 0 and idx > 0 and day_map[sorted_dates[idx - 1]] > 0:
            idx -= 1
        if day_map[sorted_dates[idx]] > 0:
            cur_end = sorted_dates[idx]
        while idx >= 0 and day_map[sorted_dates[idx]] > 0:
            cur_start = sorted_dates[idx]
            current_streak += 1
            idx -= 1

    total_prs = 0
    total_issues = 0
    try:
        pr_res = json.loads(http_get(f"https://api.github.com/search/issues?q=author:{USERNAME}+type:pr"))
        total_prs = int(pr_res.get("total_count", 0))
        iss_res = json.loads(http_get(f"https://api.github.com/search/issues?q=author:{USERNAME}+type:issue"))
        total_issues = int(iss_res.get("total_count", 0))
    except Exception:
        pass

    return {
        "public_repos": int(user.get("public_repos", len(owned_public))),
        "total_stars": total_stars,
        "total_prs": total_prs,
        "total_issues": total_issues,
        "latest_repo": latest_repo,
        "listed_repos": listed_repos,
        "lang_weights": lang_weights,
        "day_map": day_map,
        "total_contribs": total_contribs,
        "current_streak": current_streak,
        "current_streak_range": fmt_range(cur_start, cur_end),
        "longest_streak": longest_streak,
        "longest_streak_range": fmt_range(longest_start, longest_end),
    }


def format_repo_line(repo: dict) -> str:
    name = repo["name"]
    url = repo["html_url"]
    desc = (repo.get("description") or "").strip()
    if not desc:
        desc = FALLBACK_DESCRIPTIONS.get(name, "").strip()
    if not desc:
        lang = repo.get("language")
        desc = f"`{lang}` repository" if lang else "GitHub repository"
    return f"- [`{name}`]({url}) — {desc}"


def write_terminal_card(latest_repo: str) -> None:
    grid = build_text_grid("harsha", split_index=3)
    scale = 11
    grid_w = len(grid[0]) * scale
    ox, oy = 32, 56
    w, h = 760, 172
    meta_x = ox + grid_w + 38
    safe_latest = html.escape(latest_repo[:34] + ("…" if len(latest_repo) > 34 else ""))
    active_line = (
        f'active: <tspan fill="{WHITE}">{safe_latest}</tspan>'
        if len(latest_repo) > 20
        else f'active: <tspan fill="{WHITE}">{safe_latest}</tspan> · Python &amp; TS'
    )

    rects_svg = render_animated_pixel_runs(grid, ox, oy, scale, base_delay=0.10, step=0.03)
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="hiak / harsha animated terminal identity card">
  <defs>
    <clipPath id="tc-l1"><rect x="{meta_x}" y="48" width="0" height="28"><animate attributeName="width" from="0" to="350" begin="0.40s" dur="0.35s" fill="freeze"/></rect></clipPath>
    <clipPath id="tc-l2"><rect x="{meta_x}" y="76" width="0" height="24"><animate attributeName="width" from="0" to="350" begin="0.72s" dur="0.45s" fill="freeze"/></rect></clipPath>
    <clipPath id="tc-l3"><rect x="{meta_x}" y="100" width="0" height="24"><animate attributeName="width" from="0" to="350" begin="1.12s" dur="0.45s" fill="freeze"/></rect></clipPath>
    <clipPath id="tc-l4"><rect x="{meta_x}" y="124" width="0" height="26"><animate attributeName="width" from="0" to="330" begin="1.50s" dur="0.55s" fill="freeze"/></rect></clipPath>
  </defs>

  <rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="12" fill="{BG}" stroke="#282828"/>
  <rect x="1" y="1" width="{w - 2}" height="30" rx="11" fill="#111111"/>
  <rect x="1" y="20" width="{w - 2}" height="11" fill="#111111"/>
  <line x1="1" y1="31" x2="{w - 1}" y2="31" stroke="#282828" stroke-width="1"/>
  <circle cx="20" cy="16" r="4.5" fill="#282828"/>
  <circle cx="35" cy="16" r="4.5" fill="#434343"/>
  <circle cx="50" cy="16" r="4.5" fill="{AMBER}">
    <animate attributeName="opacity" values="1;0.45;1" dur="2.4s" repeatCount="indefinite"/>
  </circle>
  <text x="68" y="20" font-family="{FONT_MONO}" font-size="11.5" fill="{GRAY}">hiak@github:~/Hiak-Harsha</text>

  <g shape-rendering="crispEdges">
    {rects_svg}
  </g>

  <line x1="{meta_x - 20}" y1="48" x2="{meta_x - 20}" y2="48" stroke="#282828" stroke-width="1">
    <animate attributeName="y2" from="48" to="148" begin="0.30s" dur="0.35s" fill="freeze"/>
  </line>

  <text x="{meta_x}" y="68" clip-path="url(#tc-l1)" font-family="{FONT_MONO}" font-size="15" font-weight="700" fill="{WHITE}">hiak <tspan fill="{AMBER}">/</tspan> harsha</text>
  <text x="{meta_x}" y="93" clip-path="url(#tc-l2)" font-family="{FONT_MONO}" font-size="12.5" fill="{GRAY}">ai systems · developer tools · full-stack</text>
  <g clip-path="url(#tc-l3)">
    <circle cx="{meta_x + 5}" cy="114" r="3.5" fill="{AMBER}"/>
    <text x="{meta_x + 16}" y="118" font-family="{FONT_MONO}" font-size="12" fill="{GRAY}">{active_line}</text>
  </g>
  <text x="{meta_x}" y="142" clip-path="url(#tc-l4)" font-family="{FONT_MONO}" font-size="12" fill="#666666">$ echo "shipping clean tools &amp; ai systems"</text>
  <rect x="{meta_x + 298}" y="131" width="7" height="13" fill="{AMBER}" opacity="0">
    <animate attributeName="opacity" values="0;0;1;1;0;0;1" keyTimes="0;0.45;0.46;0.70;0.71;0.95;1" dur="2.2s" begin="1.45s" repeatCount="indefinite"/>
  </rect>
</svg>
'''
    (ASSETS_DIR / "terminal_card.svg").write_text(svg, encoding="utf-8")


def write_section_header(filename: str, label: str, tag: str, base_delay: float) -> None:
    grid = build_text_grid(label)
    scale = 4
    grid_w = len(grid[0]) * scale
    ox, oy = 36, 7
    pill_w = ox + grid_w + 18
    total_w, h = 760, 44
    line_x1 = pill_w + 14
    line_x2 = total_w - 8

    rects_svg = render_animated_pixel_runs(grid, ox, oy, scale, base_delay=base_delay, step=0.025)
    line_delay = base_delay + 0.18
    tag_delay = base_delay + 0.35

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{total_w}" height="{h}" viewBox="0 0 {total_w} {h}" role="img" aria-label="{html.escape(label)}">
  <rect x="0.5" y="0.5" width="{pill_w}" height="{h - 1}" rx="8" fill="{BG}" stroke="#282828"/>
  <g>
    <animate attributeName="opacity" values="0.35;1;0.35" dur="2.6s" begin="{base_delay:.2f}s" repeatCount="indefinite"/>
    <rect x="14" y="14" width="5" height="5" fill="{AMBER}"/>
    <rect x="19" y="19" width="5" height="5" fill="{AMBER}"/>
    <rect x="14" y="24" width="5" height="5" fill="{AMBER}"/>
  </g>
  <g shape-rendering="crispEdges">
    {rects_svg}
  </g>
  <line x1="{line_x1}" y1="22" x2="{line_x1}" y2="22" stroke="#282828" stroke-width="1">
    <animate attributeName="x2" from="{line_x1}" to="{line_x2}" begin="{line_delay:.2f}s" dur="0.40s" fill="freeze"/>
  </line>
  <text x="{line_x2}" y="16" text-anchor="end" font-family="{FONT_MONO}" font-size="10.5" fill="{GRAY}" opacity="0">
    {html.escape(tag)}
    <animate attributeName="opacity" from="0" to="1" begin="{tag_delay:.2f}s" dur="0.25s" fill="freeze"/>
  </text>
</svg>
'''
    (ASSETS_DIR / filename).write_text(svg, encoding="utf-8")


def write_about_card() -> None:
    w, h = 760, 146
    mascot = mini_mascot_svg(692, 96)
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="about hiak / harsha">
  <defs>
    <clipPath id="ab-1"><rect x="24" y="20" width="0" height="22"><animate attributeName="width" from="0" to="640" begin="0.75s" dur="0.35s" fill="freeze"/></rect></clipPath>
    <clipPath id="ab-2"><rect x="24" y="42" width="0" height="24"><animate attributeName="width" from="0" to="640" begin="1.05s" dur="0.45s" fill="freeze"/></rect></clipPath>
    <clipPath id="ab-3"><rect x="24" y="74" width="0" height="22"><animate attributeName="width" from="0" to="640" begin="1.45s" dur="0.35s" fill="freeze"/></rect></clipPath>
    <clipPath id="ab-4"><rect x="24" y="96" width="0" height="22"><animate attributeName="width" from="0" to="640" begin="1.75s" dur="0.45s" fill="freeze"/></rect></clipPath>
    <clipPath id="ab-5"><rect x="24" y="116" width="0" height="22"><animate attributeName="width" from="0" to="640" begin="2.10s" dur="0.45s" fill="freeze"/></rect></clipPath>
  </defs>

  <rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="10" fill="{BG}" stroke="#282828"/>
  <text x="24" y="36" clip-path="url(#ab-1)" font-family="{FONT_MONO}" font-size="12.5" font-weight="700" fill="{AMBER}">&gt; whoami</text>
  <text x="38" y="57" clip-path="url(#ab-2)" font-family="{FONT_MONO}" font-size="13" fill="{WHITE}">hiak / harsha — developer &amp; systems tinkerer</text>

  <text x="24" y="89" clip-path="url(#ab-3)" font-family="{FONT_MONO}" font-size="12.5" font-weight="700" fill="{AMBER}">&gt; focus</text>
  <text x="38" y="110" clip-path="url(#ab-4)" font-family="{FONT_MONO}" font-size="12.5" fill="{GRAY}">building agentic AI workflows, quantitative pipelines,</text>
  <text x="38" y="129" clip-path="url(#ab-5)" font-family="{FONT_MONO}" font-size="12.5" fill="{GRAY}">terminal-first developer tools, and full-stack software.</text>

  {mascot}
</svg>
'''
    (ASSETS_DIR / "about_card.svg").write_text(svg, encoding="utf-8")


def write_stats_card(data: dict) -> None:
    w, h = 760, 204
    lang_weights: dict[str, int] = data["lang_weights"]
    total_w = max(1, sum(lang_weights.values()))
    top_langs = sorted(lang_weights.items(), key=lambda kv: kv[1], reverse=True)[:5]

    bar_colors = [AMBER, WHITE, GRAY, "#525252", "#3A3A3A"]
    bar_x, bar_y, bar_w = 398, 48, 330

    # Build animated stacked bar + individual language rows
    lang_rows = []
    stacked_segs = []
    cur_x = float(bar_x)
    for idx, (lang, weight) in enumerate(top_langs):
        pct = (weight / total_w) * 100.0
        seg_w = max(4.0, (weight / total_w) * bar_w)
        col = bar_colors[idx % len(bar_colors)]
        delay = 1.85 + idx * 0.10

        stacked_segs.append(
            f'<rect x="{cur_x:.1f}" y="{bar_y}" width="0" height="8" fill="{col}">'
            f'<animate attributeName="width" from="0" to="{seg_w:.1f}" begin="{delay:.2f}s" dur="0.45s" fill="freeze"/>'
            f'</rect>'
        )
        cur_x += seg_w

        ry = 74 + idx * 18
        lang_rows.append(
            f'<circle cx="{bar_x + 5}" cy="{ry - 4}" r="3.5" fill="{col}"/>'
            f'<text x="{bar_x + 16}" y="{ry}" font-family="{FONT_MONO}" font-size="11.5" fill="{WHITE}">{html.escape(lang)}</text>'
            f'<text x="{bar_x + bar_w}" y="{ry}" text-anchor="end" font-family="{FONT_MONO}" font-size="11.5" fill="{GRAY}">{pct:.1f}%</text>'
        )

    metrics = [
        ("contributions (1y)", str(data["total_contribs"]), AMBER, 1.80),
        ("total stars", str(data["total_stars"]), WHITE, 1.90),
        ("public repos", str(data["public_repos"]), WHITE, 2.00),
        ("pull requests", str(data["total_prs"]), GRAY, 2.10),
        ("issues", str(data["total_issues"]), GRAY, 2.20),
    ]
    metric_lines = []
    for idx, (label, val, val_col, delay) in enumerate(metrics):
        my = 58 + idx * 28
        metric_lines.append(
            f'<g opacity="0">'
            f'<animate attributeName="opacity" from="0" to="1" begin="{delay:.2f}s" dur="0.28s" fill="freeze"/>'
            f'<text x="26" y="{my}" font-family="{FONT_MONO}" font-size="12" fill="{GRAY}">{label}</text>'
            f'<text x="342" y="{my}" text-anchor="end" font-family="{FONT_MONO}" font-size="13.5" font-weight="700" fill="{val_col}">{html.escape(val)}</text>'
            f'<line x1="26" y1="{my + 8}" x2="342" y2="{my + 8}" stroke="#191919" stroke-width="1"/>'
            f'</g>'
        )

    cur_str = f"{data['current_streak']}d ({data['current_streak_range']})"
    best_str = f"{data['longest_streak']}d ({data['longest_streak_range']})"

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="Hiak-Harsha GitHub telemetry">
  <rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="12" fill="{BG}" stroke="#282828"/>
  <text x="26" y="28" font-family="{FONT_MONO}" font-size="11.5" font-weight="700" fill="{GRAY}">GITHUB TELEMETRY</text>
  <text x="{bar_x}" y="28" font-family="{FONT_MONO}" font-size="11.5" font-weight="700" fill="{GRAY}">TOP LANGUAGES</text>
  <circle cx="732" cy="24" r="3.5" fill="{AMBER}">
    <animate attributeName="opacity" values="1;0.3;1" dur="2s" repeatCount="indefinite"/>
  </circle>

  {"".join(metric_lines)}

  <line x1="370" y1="22" x2="370" y2="{h - 20}" stroke="#282828" stroke-width="1"/>

  <rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="8" rx="4" fill="#171717"/>
  <g>
    {"".join(stacked_segs)}
  </g>
  {"".join(lang_rows)}

  <line x1="{bar_x}" y1="160" x2="{bar_x + bar_w}" y2="160" stroke="#282828" stroke-width="1"/>
  <g opacity="0">
    <animate attributeName="opacity" from="0" to="1" begin="2.25s" dur="0.30s" fill="freeze"/>
    <text x="{bar_x}" y="179" font-family="{FONT_MONO}" font-size="11.5" fill="{GRAY}">active streak <tspan fill="{AMBER}" font-weight="700">{html.escape(cur_str)}</tspan></text>
    <text x="{bar_x}" y="195" font-family="{FONT_MONO}" font-size="11.5" fill="{GRAY}">longest streak <tspan fill="{WHITE}" font-weight="700">{html.escape(best_str)}</tspan></text>
  </g>
</svg>
'''
    (ASSETS_DIR / "stats_card.svg").write_text(svg, encoding="utf-8")


def write_contrib_graph(data: dict) -> None:
    day_map: dict[str, int] = data["day_map"]
    w, h = 760, 150
    cell = 10
    gap = 3
    step = cell + gap
    ox, oy = 36, 40

    level_colors = {
        0: "#151515",
        1: "#3D2710",
        2: "#7A4512",
        3: "#B45E0B",
        4: AMBER,
    }

    sorted_dates = sorted(day_map.keys())
    if sorted_dates:
        end_dt = date.fromisoformat(sorted_dates[-1])
    else:
        end_dt = date.today()

    # Align grid to 53 Sunday-start columns ending on end_dt's week
    days_since_sun = (end_dt.weekday() + 1) % 7
    last_sunday = end_dt - timedelta(days=days_since_sun)
    first_sunday = last_sunday - timedelta(weeks=52)

    cols_svg = []
    for week in range(53):
        col_delay = 1.95 + week * 0.018
        week_rects = []
        for dow in range(7):
            cur_dt = first_sunday + timedelta(weeks=week, days=dow)
            if cur_dt > end_dt:
                continue
            lvl = day_map.get(cur_dt.isoformat(), 0)
            col = level_colors.get(lvl, level_colors[0])
            cx = ox + week * step
            cy = oy + dow * step
            week_rects.append(
                f'<rect x="{cx}" y="{cy}" width="{cell}" height="{cell}" rx="2" fill="{col}"/>'
            )
        if week_rects:
            cols_svg.append(
                f'<g opacity="0">'
                f'<animate attributeName="opacity" from="0" to="1" begin="{col_delay:.2f}s" dur="0.22s" fill="freeze"/>'
                f'{"".join(week_rects)}'
                f'</g>'
            )

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="Hiak-Harsha contribution heatmap">
  <rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="12" fill="{BG}" stroke="#282828"/>
  <text x="36" y="25" font-family="{FONT_MONO}" font-size="11.5" fill="{GRAY}"><tspan fill="{WHITE}" font-weight="700">{html.escape(data["total_contribs"])}</tspan> contributions in the last year</text>
  <text x="{w - 110}" y="25" font-family="{FONT_MONO}" font-size="10.5" fill="#666666">less</text>
  <rect x="{w - 82}" y="16" width="9" height="9" rx="2" fill="#151515"/>
  <rect x="{w - 70}" y="16" width="9" height="9" rx="2" fill="#3D2710"/>
  <rect x="{w - 58}" y="16" width="9" height="9" rx="2" fill="#7A4512"/>
  <rect x="{w - 46}" y="16" width="9" height="9" rx="2" fill="#B45E0B"/>
  <rect x="{w - 34}" y="16" width="9" height="9" rx="2" fill="{AMBER}"/>
  <text x="{w - 20}" y="25" font-family="{FONT_MONO}" font-size="10.5" fill="#666666">more</text>

  {"".join(cols_svg)}
</svg>
'''
    (ASSETS_DIR / "contrib_graph.svg").write_text(svg, encoding="utf-8")


def main() -> None:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    data = fetch_profile_data()

    # Regenerate all animated SVGs
    write_terminal_card(data["latest_repo"])
    write_section_header("header_about.svg", "about", "01 // profile", base_delay=0.55)
    write_about_card()
    write_section_header("header_builds.svg", "builds", "02 // mentions", base_delay=1.10)
    write_section_header("header_stack.svg", "stack", "03 // toolkit", base_delay=1.45)
    write_section_header("header_stats.svg", "stats", "04 // telemetry", base_delay=1.75)
    write_stats_card(data)
    write_contrib_graph(data)

    # Update expandable repo list inside README.md
    readme = README_PATH.read_text(encoding="utf-8")
    pattern = re.compile(r"<!-- REPOS_START -->.*?<!-- REPOS_END -->", re.DOTALL)
    if not pattern.search(readme):
        raise RuntimeError("Missing <!-- REPOS_START --> ... <!-- REPOS_END --> markers in README.md")

    lines = "\n".join(format_repo_line(r) for r in data["listed_repos"])
    replacement = f"<!-- REPOS_START -->\n{lines}\n<!-- REPOS_END -->"
    updated = pattern.sub(replacement, readme, count=1)
    if updated != readme:
        README_PATH.write_text(updated, encoding="utf-8")

    print(
        f"Synced {len(data['listed_repos'])} repos, latest={data['latest_repo']}, "
        f"contribs={data['total_contribs']}, streak={data['current_streak']}d/{data['longest_streak']}d"
    )


if __name__ == "__main__":
    main()
