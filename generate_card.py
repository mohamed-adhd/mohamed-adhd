#!/usr/bin/env python3
"""Generates card.svg (dark stats card) for a GitHub user.
Usage:  GH_TOKEN=xxx python generate_card.py mohamed-adhd [--title "bruh"]
        python generate_card.py mohamed-adhd --demo     (fake numbers, no token needed)
"""
import os, sys, json, math, argparse, datetime as dt
import urllib.request

HOURS_PER_COMMIT = 0.5  # heuristic: "estimated coding hours" = commits * this

def gql(token, query, variables):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as r:
        data = json.load(r)
    if "errors" in data:
        raise SystemExit(data["errors"])
    return data["data"]

def fetch(login, token):
    base = gql(token, """query($l:String!){user(login:$l){createdAt
      pullRequests{totalCount}}}""", {"l": login})["user"]
    created = dt.datetime.fromisoformat(base["createdAt"].replace("Z", "+00:00"))
    prs = base["pullRequests"]["totalCount"]

    # stars on owned, non-fork repos
    stars, cursor = 0, None
    while True:
        d = gql(token, """query($l:String!,$c:String){user(login:$l){
          repositories(ownerAffiliations:OWNER,isFork:false,first:100,after:$c){
          nodes{stargazerCount} pageInfo{hasNextPage endCursor}}}}""",
          {"l": login, "c": cursor})["user"]["repositories"]
        stars += sum(n["stargazerCount"] for n in d["nodes"])
        if not d["pageInfo"]["hasNextPage"]:
            break
        cursor = d["pageInfo"]["endCursor"]

    # total commits, year by year since account creation
    now = dt.datetime.now(dt.timezone.utc)
    commits, year_contrib = 0, 0
    for y in range(created.year, now.year + 1):
        a = dt.datetime(y, 1, 1, tzinfo=dt.timezone.utc)
        b = min(dt.datetime(y, 12, 31, 23, 59, 59, tzinfo=dt.timezone.utc), now)
        c = gql(token, """query($l:String!,$f:DateTime!,$t:DateTime!){user(login:$l){
          contributionsCollection(from:$f,to:$t){totalCommitContributions
          restrictedContributionsCount}}}""",
          {"l": login, "f": a.isoformat(), "t": b.isoformat()})["user"]["contributionsCollection"]
        commits += c["totalCommitContributions"] + c["restrictedContributionsCount"]

    # weekly trend: last 7 days vs previous 7 days (contribution counts)
    cal = gql(token, """query($l:String!){user(login:$l){contributionsCollection{
      contributionCalendar{totalContributions weeks{contributionDays{contributionCount}}}}}}""",
      {"l": login})["user"]["contributionsCollection"]["contributionCalendar"]
    days = [d["contributionCount"] for w in cal["weeks"] for d in w["contributionDays"]]
    this_w, prev_w = sum(days[-7:]), sum(days[-14:-7])
    return dict(commits=commits, prs=prs, stars=stars, this_w=this_w, prev_w=prev_w,
                year=cal["totalContributions"])

def grade(year_contrib):
    score = min(100, round(year_contrib / 25))
    for g, m in [("S", 95), ("A+", 85), ("A", 75), ("B+", 65), ("B", 55), ("C", 0)]:
        if score >= m:
            return g, score

def build_svg(title, s):
    hours = s["commits"] * HOURS_PER_COMMIT
    if s["prev_w"]:
        pct = round((s["this_w"] - s["prev_w"]) / s["prev_w"] * 100)
    else:
        pct = 100 if s["this_w"] else 0
    up = pct >= 0
    g, score = grade(s["year"])
    C = 2 * math.pi * 32
    dash = C * score / 100
    arrow_col = "#4ade80" if up else "#f87171"
    arrow = "M4 0 L8 5 H5.2 V9 H2.8 V5 H0 Z" if up else "M4 9 L8 4 H5.2 V0 H2.8 V4 H0 Z"
    f = lambda n: f"{n:,}"
    rows = [
        ("Estimated Coding Hours:", f"{hours:,.1f}h"),
        ("Weekly Trend:", f"{f(s['this_w'])} commits"),
        ("Total Commits:", f(s["commits"])),
        ("Total PRs:", f(s["prs"])),
        ("Total Stars Earned:", f(s["stars"])),
    ]
    ys = [72, 94.5, 117, 139.5, 162]
    icons = [
        # clock
        '<circle cx="7" cy="0" r="7" fill="#2dd4bf"/><path d="M7 -4 V0 L10 2" stroke="#1a1b27" stroke-width="1.6" fill="none" stroke-linecap="round"/>',
        # signal bars
        '<g fill="#34d399"><rect x="0" y="-1" width="2" height="7"/><rect x="4" y="-4" width="2" height="10"/><rect x="8" y="-7" width="2" height="13"/><rect x="12" y="-3" width="2" height="9"/></g>',
        # commit
        '<g stroke="#fb923c" stroke-width="1.8" fill="none" stroke-linecap="round"><circle cx="7" cy="0" r="3.2"/><path d="M0 0 H3.8 M10.2 0 H14"/></g>',
        # pull request
        '<g stroke="#facc15" stroke-width="1.7" fill="none" stroke-linecap="round"><circle cx="3" cy="-5" r="1.9"/><circle cx="3" cy="5" r="1.9"/><circle cx="11" cy="5" r="1.9"/><path d="M3 -3 V3 M11 3 V-3 C11 -5 9.5 -5.5 8 -5.5 H6.5"/></g>',
        # star
        '<path d="M7 -7 L9 -2.2 L14.2 -1.8 L10.2 1.6 L11.5 6.6 L7 3.9 L2.5 6.6 L3.8 1.6 L-0.2 -1.8 L5 -2.2 Z" fill="#fbbf24"/>',
    ]
    out = []
    for i, ((label, val), y, ic) in enumerate(zip(rows, ys, icons)):
        out.append(f'<g transform="translate(41,{y-4})">{ic}</g>')
        out.append(f'<text x="64" y="{y}" class="l">{label}</text>')
        out.append(f'<text x="332" y="{y}" class="v" text-anchor="end">{val}</text>')
        if i == 1:
            out.append(f'<g transform="translate(205,{y-9})"><path d="{arrow}" fill="{arrow_col}" transform="scale(.9)"/></g>'
                       f'<text x="217" y="{y-1}" class="s" fill="{arrow_col}">{"+" if up else ""}{pct}%</text>')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="484" height="200" viewBox="0 0 484 200" role="img" aria-label="GitHub stats">
<style>
text{{font-family:'Segoe UI','Ubuntu','Helvetica Neue',Arial,sans-serif}}
.t{{font-size:18px;font-weight:700;fill:#c792ea}}
.l{{font-size:13px;fill:#7aa2f7}}
.v{{font-size:13px;font-weight:700;fill:#7aa2f7}}
.s{{font-size:9px;font-weight:700}}
.g{{font-size:21px;font-weight:700;fill:#c792ea}}
.p{{font-size:11px;fill:#7aa2f7}}
</style>
<rect x="18" y="12" width="444" height="178" rx="30" fill="#1a1b27" stroke="#5b7fd6" stroke-width="1.2"/>
<text x="41" y="45" class="t">{title}</text>
{chr(10).join(out)}
<g transform="translate(412,100)">
  <circle r="32" fill="none" stroke="#3b4268" stroke-width="4"/>
  <circle r="32" fill="none" stroke="#c792ea" stroke-width="4" stroke-linecap="round"
          stroke-dasharray="{dash:.1f} {C:.1f}" transform="rotate(-90)"/>
  <text y="3" class="g" text-anchor="middle">{g}</text>
  <text y="19" class="p" text-anchor="middle">{score}%</text>
</g>
</svg>'''

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("login")
    ap.add_argument("--title", default=None)
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--out", default="card.svg")
    a = ap.parse_args()
    if a.demo:
        stats = dict(commits=2314, prs=48, stars=127, this_w=53, prev_w=24, year=2244)
    else:
        stats = fetch(a.login, os.environ["GH_TOKEN"])
    open(a.out, "w").write(build_svg(a.title or a.login, stats))
    print("wrote", a.out, stats)
