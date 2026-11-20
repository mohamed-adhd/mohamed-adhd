#!/usr/bin/env python3
"""Rebuilds assets/project-queue.svg with live commit counts. No dependencies."""
import html
import json
import os
import re
import time
import urllib.error
import urllib.request

# ---------------- config: edit these ----------------
OWNER = "mohamed-adhd"
CURRENT = "Oscuola"
QUEUE = ["ADHDewey", "packrat", "spinit"]
OUT = "assets/project-queue.svg"
# ----------------------------------------------------

TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
FALLBACK_BARS = [3, 4, 3, 6, 5, 8, 6, 10, 8, 12, 10, 14]


def api(path):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "project-queue-widget",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    req = urllib.request.Request(f"https://api.github.com{path}", headers=headers)
    return urllib.request.urlopen(req, timeout=30)


def commit_count(repo):
    """Total commits on the default branch (reads the last page number)."""
    try:
        with api(f"/repos/{OWNER}/{repo}/commits?per_page=1") as r:
            link = r.headers.get("Link", "")
            m = re.search(r'[?&]page=(\d+)>; rel="last"', link)
            if m:
                return int(m.group(1))
            return len(json.loads(r.read()))
    except urllib.error.HTTPError as e:
        print(f"warn: {repo} commits -> HTTP {e.code}")
        return 0 if e.code == 409 else None  # 409 = empty repo


def weekly_activity(repo, weeks=12):
    """Commits per week for the last N weeks (GitHub may need a moment to compute)."""
    for _ in range(4):
        try:
            with api(f"/repos/{OWNER}/{repo}/stats/commit_activity") as r:
                if r.status == 200:
                    data = json.loads(r.read())
                    if data:
                        return [w["total"] for w in data][-weeks:]
        except urllib.error.HTTPError as e:
            print(f"warn: {repo} activity -> HTTP {e.code}")
            break
        time.sleep(3)
    return None


def fmt(n):
    if n is None:
        return "--"
    return f"{n / 1000:.1f}k".replace(".0k", "k") if n >= 1000 else str(n)


def bars_svg(values):
    values = (values or FALLBACK_BARS)[-12:]
    values = [0] * (12 - len(values)) + values
    top = max(values) or 1
    out = []
    for i, v in enumerate(values):
        h = 6 + round((v / top) * 36)
        op = 0.35 + 0.6 * (i / 11)
        out.append(
            f'<rect x="{38 + i * 10}" y="{182 - h}" width="6" height="{h}" rx="2" opacity="{op:.2f}"/>'
        )
    return "\n    ".join(out)


def queue_card(i, name, count):
    x = 340 + i * 160
    w = 150
    fills = ["#161a36", "#141831", "#121630"]
    strokes = ["#2a3055", "#262b4a", "#222744"]
    divs = ["#262b4a", "#222744", "#1e2340"]
    names = ["#e6e9ff", "#d5d9f5", "#c3c8ea"]
    fade = [1, 0.88, 0.75]
    tx = x + 18
    nxt = (
        f'<text x="{x + w - 16}" y="50" fill="#4b5380" font-size="9" letter-spacing="1.4" text-anchor="end">NEXT</text>'
        if i == 0
        else ""
    )
    return f"""
  <g>
    <rect x="{x}" y="20" width="{w}" height="190" rx="14" fill="{fills[i]}"/>
    <rect x="{x + 0.5}" y="20.5" width="{w - 1}" height="189" rx="13.5" stroke="{strokes[i]}"/>
    <text x="{tx}" y="50" fill="#7aa2f7" font-size="11" font-weight="700" letter-spacing="1.6" opacity="{fade[i]}">0{i + 1}</text>
    {nxt}
    <line x1="{tx}" y1="62" x2="{x + w - 18}" y2="62" stroke="{divs[i]}"/>
    <text x="{tx}" y="108" fill="{names[i]}" font-size="17" font-weight="800">{html.escape(name)}</text>
    <text x="{tx}" y="126" fill="#6c749c" font-size="10">{html.escape(OWNER)}</text>
    <text x="{tx}" y="182" fill="#2dd4bf" font-size="28" font-weight="800" opacity="{fade[i]}">{fmt(count)}</text>
    <text x="{tx}" y="198" fill="#6c749c" font-size="9" letter-spacing="1.6">COMMITS</text>
  </g>"""


def build():
    cur_count = commit_count(CURRENT)
    cur_bars = weekly_activity(CURRENT)
    q_counts = [commit_count(r) for r in QUEUE]
    print("counts:", CURRENT, cur_count, dict(zip(QUEUE, q_counts)))

    cards = "".join(queue_card(i, n, c) for i, (n, c) in enumerate(zip(QUEUE, q_counts)))

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="830" height="230" viewBox="0 0 830 230" fill="none" font-family="'SF Mono','JetBrains Mono',Consolas,'Courier New',monospace">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="830" y2="230" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#12162e"/>
      <stop offset="1" stop-color="#0b0e1f"/>
    </linearGradient>
    <linearGradient id="purple" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#c084fc"/>
      <stop offset="1" stop-color="#7aa2f7"/>
    </linearGradient>
    <linearGradient id="mainfill" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#c084fc" stop-opacity="0.18"/>
      <stop offset="1" stop-color="#7aa2f7" stop-opacity="0.04"/>
    </linearGradient>
    <radialGradient id="glow" cx="0.2" cy="0.1" r="0.9">
      <stop offset="0" stop-color="#c084fc" stop-opacity="0.25"/>
      <stop offset="1" stop-color="#c084fc" stop-opacity="0"/>
    </radialGradient>
  </defs>

  <rect x="0.5" y="0.5" width="829" height="229" rx="18" fill="url(#bg)" stroke="#262b4a"/>

  <!-- current project -->
  <rect x="20" y="20" width="300" height="190" rx="14" fill="url(#mainfill)"/>
  <rect x="20" y="20" width="300" height="190" rx="14" fill="url(#glow)"/>
  <rect x="20.75" y="20.75" width="298.5" height="188.5" rx="13.5" stroke="url(#purple)" stroke-opacity="0.7" stroke-width="1.5"/>

  <rect x="38" y="38" width="112" height="24" rx="12" fill="#c084fc" fill-opacity="0.15"/>
  <circle cx="53" cy="50" r="4" fill="#c084fc">
    <animate attributeName="opacity" values="1;0.25;1" dur="1.8s" repeatCount="indefinite"/>
  </circle>
  <circle cx="53" cy="50" r="4" fill="none" stroke="#c084fc">
    <animate attributeName="r" values="4;10" dur="1.8s" repeatCount="indefinite"/>
    <animate attributeName="opacity" values="0.7;0" dur="1.8s" repeatCount="indefinite"/>
  </circle>
  <text x="65" y="54.5" fill="#d8b4fe" font-size="10.5" font-weight="700" letter-spacing="1.6">BUILDING NOW</text>

  <text x="38" y="106" fill="#ffffff" font-size="30" font-weight="800" letter-spacing="-0.5">{html.escape(CURRENT)}</text>
  <text x="38" y="126" fill="#8890b5" font-size="11" letter-spacing="0.5">{html.escape(OWNER)} / {html.escape(CURRENT.lower())}</text>

  <g fill="url(#purple)">
    {bars_svg(cur_bars)}
  </g>

  <text x="282" y="166" fill="#ffffff" font-size="34" font-weight="800" text-anchor="end">{fmt(cur_count)}</text>
  <text x="282" y="184" fill="#8890b5" font-size="10" letter-spacing="1.6" text-anchor="end">COMMITS</text>

  <!-- queue -->{cards}
</svg>
"""


if __name__ == "__main__":
    svg = build()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"wrote {OUT}")
