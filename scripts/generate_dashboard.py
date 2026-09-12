#!/usr/bin/env python3
import os
import json
import html
import urllib.request
from pathlib import Path
from datetime import datetime, timedelta

USER = os.getenv("GITHUB_USERNAME", "adityakumar-ara")
TOKEN = os.getenv("GITHUB_TOKEN")
OUT = Path("assets/github-dashboard.svg")
OUT.parent.mkdir(parents=True, exist_ok=True)

QUERY = """
query($login:String!) {
  user(login:$login) {
    name
    login
    followers { totalCount }
    following { totalCount }
    repositories(first:100, ownerAffiliations:OWNER, privacy:PUBLIC) {
      totalCount
      nodes {
        stargazerCount
        forkCount
        primaryLanguage { name }
      }
    }
    contributionsCollection {
      totalCommitContributions
      totalIssueContributions
      totalPullRequestContributions
      totalPullRequestReviewContributions
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
          }
        }
      }
    }
  }
}
"""

def get_user():
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({
            "query": QUERY,
            "variables": {"login": USER}
        }).encode(),
        headers={
            "Authorization": "bearer " + TOKEN,
            "Content-Type": "application/json",
            "User-Agent": "github-dashboard"
        }
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if data.get("errors"):
        raise RuntimeError(str(data["errors"]))
    return data["data"]["user"]

def esc(x):
    return html.escape(str(x))

u = get_user()
name = u.get("name") or USER
login = u.get("login") or USER
followers = u["followers"]["totalCount"]
following = u["following"]["totalCount"]
repo_count = u["repositories"]["totalCount"]

cc = u["contributionsCollection"]
commits = cc["totalCommitContributions"]
issues = cc["totalIssueContributions"]
prs = cc["totalPullRequestContributions"]
reviews = cc["totalPullRequestReviewContributions"]
total = cc["contributionCalendar"]["totalContributions"]

repos = u["repositories"]["nodes"]
stars = sum(r["stargazerCount"] for r in repos)
forks = sum(r["forkCount"] for r in repos)

lang_counts = {}
for r in repos:
    p = r.get("primaryLanguage")
    if p:
        lang_counts[p["name"]] = lang_counts.get(p["name"], 0) + 1
langs = sorted(lang_counts.items(), key=lambda x: x[1], reverse=True)[:5]

days = []
for week in cc["contributionCalendar"]["weeks"]:
    days.extend(week["contributionDays"])
days.sort(key=lambda x: x["date"])

daymap = {d["date"]: d["contributionCount"] for d in days}
today = datetime.utcnow().date()
cursor = today
current = 0
if daymap.get(str(cursor), 0) == 0:
    cursor -= timedelta(days=1)
while daymap.get(str(cursor), 0) > 0:
    current += 1
    cursor -= timedelta(days=1)

longest = 0
run = 0
previous = None
for d in days:
    if d["contributionCount"] > 0:
        if previous:
            a = datetime.fromisoformat(previous)
            b = datetime.fromisoformat(d["date"])
            run = run + 1 if (b - a).days == 1 else 1
        else:
            run = 1
        longest = max(longest, run)
        previous = d["date"]
    else:
        run = 0
        previous = None

months = {}
for d in days:
    key = d["date"][:7]
    months[key] = months.get(key, 0) + d["contributionCount"]
month_items = list(months.items())[-12:]
month_max = max([v for _, v in month_items] or [1])

dow = [0] * 7
for d in days:
    dow[datetime.fromisoformat(d["date"]).weekday()] += d["contributionCount"]
dow_max = max(dow or [1])

W, H = 1000, 1450
bg = "#07111b"
panel = "#091a27"
panel2 = "#0b2030"
border = "#12384e"
white = "#eaf5f9"
muted = "#8ca8b6"
cyan = "#16d8ff"
green = "#18d98a"
orange = "#f2a14a"
purple = "#b77cff"
pink = "#ff5f91"

s = []
s.append('<svg xmlns="http://www.w3.org/2000/svg" width="' + str(W) + '" height="' + str(H) + '" viewBox="0 0 ' + str(W) + ' ' + str(H) + '">')
s.append('<rect width="100%" height="100%" rx="22" fill="' + bg + '"/>')
s.append('<style>.t{font-family:Segoe UI,Arial,sans-serif;fill:' + white + '}.m{font-family:Segoe UI,Arial,sans-serif;fill:' + muted + '}.h{font-family:Segoe UI,Arial,sans-serif;fill:' + white + ';font-size:17px;font-weight:700}</style>')

# Top dashboard card
s.append(f'<rect x="18" y="18" width="964" height="760" rx="18" fill="{panel}" stroke="{border}"/>')

# Header
s.append(f'<circle cx="70" cy="68" r="30" fill="#0d2c40" stroke="{cyan}" stroke-width="2"/>')
s.append(f'<text x="70" y="76" text-anchor="middle" font-family="Segoe UI" font-size="18" font-weight="700" fill="{cyan}">AK</text>')
s.append(f'<text x="115" y="48" class="t" font-size="18" font-weight="700">Hi, I&apos;m {esc(name)}</text>')
s.append(f'<text x="115" y="67" class="m" font-size="9">BCA Student | Full-Stack Developer | Python &amp; Django Developer</text>')
s.append(f'<text x="115" y="84" class="m" font-size="8">Learning React, REST APIs, DSA &amp; AI/ML</text>')
s.append(f'<text x="940" y="52" text-anchor="end" class="m" font-size="8">Followers</text>')
s.append(f'<text x="940" y="70" text-anchor="end" class="t" font-size="14" font-weight="700">{followers}</text>')
s.append(f'<text x="940" y="88" text-anchor="end" class="m" font-size="8">Following {following}</text>')

# Stat cards
stats = [
    ("Public Repos", repo_count),
    ("Contributions", total),
    ("Commits", commits),
    ("Issues", issues),
    ("Pull Requests", prs),
]
for i, (label, value) in enumerate(stats):
    x = 32 + i * 190
    s.append(f'<rect x="{x}" y="105" width="174" height="67" rx="10" fill="{panel2}" stroke="{border}"/>')
    s.append(f'<text x="{x+12}" y="126" class="m" font-size="8">{esc(label)}</text>')
    s.append(f'<text x="{x+12}" y="153" class="t" font-size="18" font-weight="700">{value}</text>')

# Contribution heatmap
s.append(f'<text x="34" y="198" class="h">🟩 Contribution Activity</text>')
s.append(f'<rect x="32" y="210" width="936" height="184" rx="11" fill="#071722" stroke="{border}"/>')
heat = days[-371:]
cell = 10
gap = 3
for idx, d in enumerate(heat):
    col = idx // 7
    row = idx % 7
    x = 43 + col * (cell + gap)
    y = 228 + row * (cell + gap)
    n = d["contributionCount"]
    fill = "#102938" if n == 0 else "#075a47" if n < 3 else "#0a8e68" if n < 6 else "#12c987"
    s.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2" fill="{fill}"/>')
s.append(f'<text x="44" y="376" class="m" font-size="7">Less</text>')
for i, c in enumerate(["#102938", "#075a47", "#0a8e68", "#12c987"]):
    s.append(f'<rect x="{77+i*16}" y="369" width="10" height="10" rx="2" fill="{c}"/>')
s.append(f'<text x="146" y="376" class="m" font-size="7">More</text>')

# Coding Activity
s.append(f'<rect x="32" y="412" width="456" height="210" rx="12" fill="{panel2}" stroke="{border}"/>')
s.append(f'<text x="48" y="439" class="h">📊 Coding Activity</text>')
s.append(f'<text x="48" y="458" class="m" font-size="8">Commits • Pull Requests • Issues • Reviews</text>')
for i, (m, v) in enumerate(month_items):
    x = 50 + i * 33
    bh = int(105 * v / month_max)
    y = 574 - bh
    s.append(f'<rect x="{x}" y="{y}" width="18" height="{bh}" rx="3" fill="{cyan}"/>')
    s.append(f'<text x="{x+9}" y="592" text-anchor="middle" class="m" font-size="6">{m[5:]}</text>')

# Languages
s.append(f'<rect x="512" y="412" width="456" height="210" rx="12" fill="{panel2}" stroke="{border}"/>')
s.append(f'<text x="528" y="439" class="h">◉ Most Used Languages</text>')
cx, cy, r = 600, 520, 55
circ = 2 * 3.14159265 * r
offset = 0
lang_colors = [cyan, green, orange, purple, pink]
lang_total = sum(v for _, v in langs) or 1
for i, (lang, count) in enumerate(langs):
    dash = circ * count / lang_total
    s.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{lang_colors[i%5]}" stroke-width="19" stroke-dasharray="{dash} {circ-dash}" stroke-dashoffset="{-offset}" transform="rotate(-90 {cx} {cy})"/>')
    offset += dash
    yy = 463 + i * 25
    s.append(f'<circle cx="685" cy="{yy}" r="4" fill="{lang_colors[i%5]}"/>')
    s.append(f'<text x="696" y="{yy+3}" class="m" font-size="8">{esc(lang)} {count}</text>')
s.append(f'<text x="{cx}" y="{cy+5}" text-anchor="middle" class="t" font-size="15" font-weight="700">{len(langs)}</text>')

# Streak
s.append(f'<rect x="32" y="640" width="456" height="120" rx="12" fill="{panel2}" stroke="{border}"/>')
s.append(f'<text x="48" y="667" class="h">🔥 Coding Streak</text>')
s.append(f'<text x="48" y="710" class="t" font-size="28" font-weight="700">{current} days</text>')
s.append(f'<text x="48" y="728" class="m" font-size="8">Current Streak</text>')
s.append(f'<text x="260" y="710" class="t" font-size="28" font-weight="700">{longest} days</text>')
s.append(f'<text x="260" y="728" class="m" font-size="8">Longest Streak</text>')
s.append(f'<rect x="48" y="742" width="410" height="10" rx="4" fill="#073b32"/>')

# Developer profile
s.append(f'<rect x="512" y="640" width="456" height="120" rx="12" fill="{panel2}" stroke="{border}"/>')
s.append(f'<text x="528" y="667" class="h">👨‍💻 Developer Profile</text>')
items = [("Python", "Django / Backend"), ("Web Development", "HTML / CSS / JS"), ("Programming", "Python / Java / C"), ("Database", "PostgreSQL / MySQL")]
for i, (a, b) in enumerate(items):
    x = 528 + (i % 2) * 215
    y = 686 + (i // 2) * 35
    s.append(f'<rect x="{x}" y="{y}" width="198" height="28" rx="7" fill="#071722" stroke="{border}"/>')
    s.append(f'<text x="{x+9}" y="{y+12}" class="t" font-size="8" font-weight="700">{esc(a)}</text>')
    s.append(f'<text x="{x+9}" y="{y+22}" class="m" font-size="6">{esc(b)}</text>')

# Live metrics
s.append(f'<text x="34" y="795" class="h">⚡ Live GitHub Metrics</text>')
s.append(f'<text x="34" y="817" class="m" font-size="8">Stars {stars} • Forks {forks} • Reviews {reviews} • Public repositories {repo_count}</text>')

# Activity section
s.append(f'<rect x="18" y="840" width="964" height="300" rx="18" fill="{panel}" stroke="{border}"/>')
s.append(f'<text x="500" y="872" text-anchor="middle" class="t" font-size="20" font-weight="700">GitHub Activity</text>')

s.append(f'<rect x="32" y="892" width="456" height="210" rx="12" fill="{panel2}" stroke="{border}"/>')
s.append(f'<text x="48" y="918" class="h">Repository Activity</text>')
recent = month_items[-10:]
recent_max = max([v for _, v in recent] or [1])
for i, (m, v) in enumerate(recent):
    x = 50 + i * 39
    bh = int(120 * v / recent_max)
    y = 1060 - bh
    s.append(f'<rect x="{x}" y="{y}" width="22" height="{bh}" rx="3" fill="{cyan}"/>')
    s.append(f'<text x="{x+11}" y="1080" text-anchor="middle" class="m" font-size="6">{m[5:]}</text>')

s.append(f'<rect x="512" y="892" width="456" height="210" rx="12" fill="{panel2}" stroke="{border}"/>')
s.append(f'<text x="528" y="918" class="h">📅 Activity by Day of Week</text>')
colors = [cyan, green, orange, purple, pink, cyan, green]
labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
for i, v in enumerate(dow):
    x = 532 + i * 57
    bh = int(120 * v / dow_max)
    y = 1060 - bh
    s.append(f'<rect x="{x}" y="{y}" width="34" height="{bh}" rx="4" fill="{colors[i]}"/>')
    s.append(f'<text x="{x+17}" y="1080" text-anchor="middle" class="m" font-size="6">{labels[i]}</text>')

s.append(f'<text x="500" y="1175" text-anchor="middle" class="m" font-size="8">Updated automatically from public GitHub activity</text>')
s.append(f'<text x="500" y="1193" text-anchor="middle" class="m" font-size="8">github.com/{esc(login)}</text>')
s.append(f'<rect x="18" y="1215" width="964" height="1" fill="{border}"/>')
s.append(f'<text x="500" y="1248" text-anchor="middle" class="t" font-size="15" font-weight="700">Aditya Kumar • Full-Stack Developer</text>')
s.append(f'<text x="500" y="1270" text-anchor="middle" class="m" font-size="8">Python • Django • JavaScript • React • PostgreSQL • Git</text>')
s.append(f'<text x="500" y="1292" text-anchor="middle" class="m" font-size="8">Code • Learn • Build • Repeat</text>')
s.append('</svg>')

OUT.write_text("\n".join(s), encoding="utf-8")
print("Dashboard generated:", OUT)
