import os
import html
import json
import urllib.request
import urllib.error
from pathlib import Path
from datetime import date, timedelta
from collections import Counter


# ============================================================
# CONFIG
# ============================================================

USER = os.getenv("GITHUB_USERNAME", "adityakumar-ara")
TOKEN = os.getenv("GITHUB_TOKEN")

OUT = Path("assets/github-dashboard.svg")
OUT.parent.mkdir(parents=True, exist_ok=True)


# ============================================================
# GITHUB GRAPHQL
# ============================================================

QUERY = """
query($login:String!) {
  user(login:$login) {
    login
    name
    bio
    avatarUrl
    followers {
      totalCount
    }
    following {
      totalCount
    }

    repositories(
      first: 100
      ownerAffiliations: OWNER
      privacy: PUBLIC
      orderBy: {field: UPDATED_AT, direction: DESC}
    ) {
      totalCount
      nodes {
        name
        stargazerCount
        forkCount
        primaryLanguage {
          name
          color
        }
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
            color
          }
        }
      }
    }
  }
}
"""


def github_graphql():
    if not TOKEN:
        raise RuntimeError("GITHUB_TOKEN is missing.")

    payload = json.dumps({
        "query": QUERY,
        "variables": {
            "login": USER
        }
    }).encode("utf-8")

    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "github-profile-dashboard"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"GitHub API error {e.code}: {body}")

    if result.get("errors"):
        raise RuntimeError(
            "GitHub GraphQL error: " +
            json.dumps(result["errors"])
        )

    return result["data"]["user"]


# ============================================================
# HELPERS
# ============================================================

def esc(value):
    return html.escape(str(value or ""), quote=True)


def safe_int(value):
    try:
        return int(value)
    except Exception:
        return 0


def shorten(text, length=48):
    text = str(text or "")
    if len(text) <= length:
        return text
    return text[:length - 3] + "..."


# ============================================================
# CONTRIBUTION CALCULATIONS
# ============================================================

def get_contribution_days(user):
    days = []

    weeks = (
        user
        .get("contributionsCollection", {})
        .get("contributionCalendar", {})
        .get("weeks", [])
    )

    for week in weeks:
        for day in week.get("contributionDays", []):
            days.append({
                "date": day.get("date"),
                "count": safe_int(day.get("contributionCount")),
                "color": day.get("color", "#161b22")
            })

    days.sort(key=lambda x: x["date"] or "")
    return days


def calculate_streak(days):
    if not days:
        return 0, 0

    contribution_dates = {
        d["date"]
        for d in days
        if d["count"] > 0
    }

    if not contribution_dates:
        return 0, 0

    today = date.today()

    # Current streak
    current = 0
    cursor = today

    # If today has no contribution, start from yesterday.
    if cursor.isoformat() not in contribution_dates:
        cursor -= timedelta(days=1)

    while cursor.isoformat() in contribution_dates:
        current += 1
        cursor -= timedelta(days=1)

    # Best streak
    best = 0
    running = 0
    previous = None

    for item in days:
        if item["count"] <= 0:
            running = 0
            previous = None
            continue

        current_date = date.fromisoformat(item["date"])

        if previous and current_date == previous + timedelta(days=1):
            running += 1
        else:
            running = 1

        best = max(best, running)
        previous = current_date

    return current, best


def weekly_activity(days):
    result = []

    for i in range(0, len(days), 7):
        week = days[i:i + 7]
        total = sum(d["count"] for d in week)

        if week:
            result.append({
                "label": week[-1]["date"][5:],
                "value": total
            })

    return result[-12:]


def activity_by_weekday(days):
    counts = [0] * 7

    for item in days:
        try:
            d = date.fromisoformat(item["date"])
            counts[d.weekday()] += item["count"]
        except Exception:
            pass

    return counts


# ============================================================
# SVG BUILDING BLOCKS
# ============================================================

SVG_WIDTH = 1200
SVG_HEIGHT = 2050

BG = "#0d1117"
CARD = "#161b22"
CARD2 = "#11161d"
BORDER = "#30363d"
TEXT = "#f0f6fc"
MUTED = "#8b949e"
GREEN = "#39d353"
GREEN2 = "#26a641"
BLUE = "#58a6ff"
PURPLE = "#bc8cff"
ORANGE = "#f0883e"


def rect(x, y, w, h, fill=CARD, stroke=BORDER, radius=14):
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" '
        f'rx="{radius}" fill="{fill}" stroke="{stroke}" />'
    )


def text(x, y, value, size=16, fill=TEXT, weight="400",
         anchor="start"):
    return (
        f'<text x="{x}" y="{y}" font-family="Arial, sans-serif" '
        f'font-size="{size}px" font-weight="{weight}" '
        f'fill="{fill}" text-anchor="{anchor}">'
        f'{esc(value)}</text>'
    )


def line(x1, y1, x2, y2, stroke=BORDER, width=1):
    return (
        f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
        f'stroke="{stroke}" stroke-width="{width}" />'
    )


def circle(cx, cy, r, fill, stroke="none"):
    return (
        f'<circle cx="{cx}" cy="{cy}" r="{r}" '
        f'fill="{fill}" stroke="{stroke}" />'
    )


# ============================================================
# HEADER
# ============================================================

def build_header(user):
    name = user.get("name") or user.get("login") or USER
    login = user.get("login") or USER
    bio = user.get("bio") or "Full-Stack Developer | Python | Django | React"

    return f"""
    {text(45, 58, "Hi, I'm " + name, 34, TEXT, "700")}
    {text(45, 88, "@" + login, 16, MUTED)}
    {text(45, 116, shorten(bio, 105), 15, MUTED)}

    {rect(955, 30, 190, 70, CARD2, BORDER, 12)}
    {text(1050, 58, "GITHUB", 11, MUTED, "700", "middle")}
    {text(1050, 84, "PROFILE", 17, TEXT, "700", "middle")}
    """


# ============================================================
# STAT CARDS
# ============================================================

def build_stat_cards(user, days):
    repos = user.get("repositories", {})
    total_repos = safe_int(repos.get("totalCount"))

    followers = safe_int(user.get("followers", {}).get("totalCount"))
    following = safe_int(user.get("following", {}).get("totalCount"))

    contrib = user.get("contributionsCollection", {})

    commits = safe_int(contrib.get("totalCommitContributions"))
    prs = safe_int(contrib.get("totalPullRequestContributions"))
    issues = safe_int(contrib.get("totalIssueContributions"))

    total_contributions = sum(d["count"] for d in days)

    stats = [
        ("Repositories", total_repos),
        ("Contributions", total_contributions),
        ("Commits", commits),
        ("Pull Requests", prs),
        ("Issues", issues),
        ("Followers", followers),
    ]

    output = ""

    x_positions = [45, 230, 415, 600, 785, 970]

    for x, (label, value) in zip(x_positions, stats):
        output += rect(x, 145, 165, 95, CARD, BORDER, 12)
        output += text(x + 15, 175, label, 12, MUTED, "600")
        output += text(x + 15, 212, f"{value:,}", 26, TEXT, "700")

    return output


# ============================================================
# CONTRIBUTION HEATMAP
# ============================================================

def build_heatmap(days):
    output = ""

    output += text(
        45, 285,
        "GitHub Overview",
        22,
        TEXT,
        "700"
    )

    output += text(
        45, 310,
        f"{sum(d['count'] for d in days):,} contributions in the last year",
        13,
        MUTED
    )

    # Last 371 days
    days = days[-371:]

    start_x = 45
    start_y = 335
    cell = 13
    gap = 4

    # Arrange 53 columns x 7 rows
    for index, item in enumerate(days):
        col = index // 7
        row = index % 7

        x = start_x + col * (cell + gap)
        y = start_y + row * (cell + gap)

        count = item["count"]

        if count == 0:
            fill = "#161b22"
        elif count <= 2:
            fill = "#0e4429"
        elif count <= 5:
            fill = "#006d32"
        elif count <= 9:
            fill = "#26a641"
        else:
            fill = "#39d353"

        output += (
            f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" '
            f'rx="3" fill="{fill}" />'
        )

    return output


# ============================================================
# CODING ACTIVITY
# ============================================================

def build_activity(days):
    output = ""

    output += text(45, 480, "Coding Activity", 22, TEXT, "700")
    output += text(
        45,
        505,
        "Recent contribution activity",
        13,
        MUTED
    )

    activity = weekly_activity(days)

    if not activity:
        return output

    max_value = max([a["value"] for a in activity] + [1])

    chart_x = 55
    chart_y = 625
    chart_h = 85
    bar_w = 50
    gap = 25

    for i, item in enumerate(activity):
        value = item["value"]

        height = max(5, (value / max_value) * chart_h)

        x = chart_x + i * (bar_w + gap)
        y = chart_y - height

        output += (
            f'<rect x="{x}" y="{y}" width="{bar_w}" '
            f'height="{height}" rx="6" fill="{GREEN2}" />'
        )

        output += text(
            x + bar_w / 2,
            chart_y + 25,
            item["label"],
            10,
            MUTED,
            "400",
            "middle"
        )

    return output


# ============================================================
# LANGUAGE DONUT
# ============================================================

def build_languages(user):
    languages = Counter()

    for repo in user.get("repositories", {}).get("nodes", []):
        language = repo.get("primaryLanguage")

        if language and language.get("name"):
            languages[language["name"]] += 1

    if not languages:
        languages["Other"] = 1

    top = languages.most_common(6)
    total = sum(v for _, v in top)

    output = ""

    output += text(
        700,
        480,
        "Most Used Languages",
        22,
        TEXT,
        "700"
    )

    output += text(
        700,
        505,
        "Based on public repositories",
        13,
        MUTED
    )

    # SVG donut
    cx = 820
    cy = 595
    radius = 78
    circumference = 2 * 3.1415926535 * radius

    colors = [
        "#58a6ff",
        "#f1e05a",
        "#3572A5",
        "#e34c26",
        "#563d7c",
        "#89e051"
    ]

    offset = 0

    for i, (language, count) in enumerate(top):
        percent = count / total
        dash = percent * circumference

        output += (
            f'<circle cx="{cx}" cy="{cy}" r="{radius}" '
            f'fill="none" stroke="{colors[i % len(colors)]}" '
            f'stroke-width="18" '
            f'stroke-dasharray="{dash} {circumference - dash}" '
            f'stroke-dashoffset="{-offset}" '
            f'transform="rotate(-90 {cx} {cy})" />'
        )

        offset += dash

    output += circle(cx, cy, 56, CARD)
    output += text(cx, cy - 5, f"{total}", 25, TEXT, "700", "middle")
    output += text(cx, cy + 17, "repos", 11, MUTED, "400", "middle")

    legend_x = 945
    legend_y = 550

    for i, (language, count) in enumerate(top):
        y = legend_y + i * 30

        output += circle(
            legend_x,
            y - 4,
            5,
            colors[i % len(colors)]
        )

        percent = (count / total) * 100

        output += text(
            legend_x + 14,
            y,
            f"{language}  {percent:.0f}%",
            12,
            TEXT
        )

    return output


# ============================================================
# STREAK
# ============================================================

def build_streak(days):
    current, best = calculate_streak(days)

    output = ""

    output += text(
        45,
        770,
        "Coding Streak",
        22,
        TEXT,
        "700"
    )

    output += text(
        45,
        795,
        "Consistency matters more than perfection",
        13,
        MUTED
    )

    output += rect(45, 820, 340, 105, CARD, BORDER, 12)

    output += text(
        65,
        855,
        "Current Streak",
        12,
        MUTED
    )

    output += text(
        65,
        895,
        f"{current} days",
        27,
        GREEN,
        "700"
    )

    output += rect(405, 820, 340, 105, CARD, BORDER, 12)

    output += text(
        425,
        855,
        "Best Streak",
        12,
        MUTED
    )

    output += text(
        425,
        895,
        f"{best} days",
        27,
        PURPLE,
        "700"
    )

    return output


# ============================================================
# DEVELOPER PROFILE
# ============================================================

def build_profile(user):
    name = user.get("name") or USER
    login = user.get("login") or USER
    bio = user.get("bio") or "Full-Stack Developer"

    followers = safe_int(
        user.get("followers", {}).get("totalCount")
    )

    following = safe_int(
        user.get("following", {}).get("totalCount")
    )

    output = ""

    output += text(
        45,
        980,
        "Developer Profile",
        22,
        TEXT,
        "700"
    )

    output += rect(45, 1010, 1110, 155, CARD, BORDER, 14)

    output += circle(105, 1085, 45, "#21262d")

    # Simple avatar-style icon
    output += circle(105, 1072, 16, "#8b949e")
    output += (
        '<path d="M75 1120 Q105 1085 135 1120" '
        'fill="#8b949e" />'
    )

    output += text(
        170,
        1055,
        name,
        22,
        TEXT,
        "700"
    )

    output += text(
        170,
        1082,
        "@" + login,
        14,
        MUTED
    )

    output += text(
        170,
        1110,
        shorten(bio, 75),
        13,
        MUTED
    )

    output += text(
        850,
        1055,
        "Followers",
        12,
        MUTED
    )

    output += text(
        850,
        1083,
        str(followers),
        21,
        TEXT,
        "700"
    )

    output += text(
        1000,
        1055,
        "Following",
        12,
        MUTED
    )

    output += text(
        1000,
        1083,
        str(following),
        21,
        TEXT,
        "700"
    )

    output += text(
        850,
        1120,
        "github.com/" + login,
        12,
        BLUE
    )

    return output


# ============================================================
# LIVE METRICS
# ============================================================

def build_metrics(user, days):
    repos = user.get("repositories", {}).get("nodes", [])

    stars = sum(
        safe_int(repo.get("stargazerCount"))
        for repo in repos
    )

    forks = sum(
        safe_int(repo.get("forkCount"))
        for repo in repos
    )

    contributions = sum(
        d["count"] for d in days
    )

    output = ""

    output += text(
        45,
        1220,
        "Live GitHub Metrics",
        22,
        TEXT,
        "700"
    )

    output += rect(45, 1250, 1110, 125, CARD, BORDER, 14)

    metrics = [
        ("Public Repositories", len(repos)),
        ("Total Stars", stars),
        ("Total Forks", forks),
        ("Contributions", contributions),
    ]

    positions = [70, 340, 610, 880]

    for x, (label, value) in zip(positions, metrics):
        output += text(
            x,
            1285,
            label,
            12,
            MUTED
        )

        output += text(
            x,
            1320,
            f"{value:,}",
            25,
            TEXT,
            "700"
        )

    return output


# ============================================================
# ACTIVITY BY DAY
# ============================================================

def build_weekday_chart(days):
    counts = activity_by_weekday(days)

    labels = [
        "Mon",
        "Tue",
        "Wed",
        "Thu",
        "Fri",
        "Sat",
        "Sun"
    ]

    output = ""

    output += text(
        45,
        1435,
        "GitHub Activity",
        22,
        TEXT,
        "700"
    )

    output += text(
        45,
        1460,
        "Activity by Day of Week",
        13,
        MUTED
    )

    chart_x = 55
    chart_y = 1585
    chart_h = 90
    bar_w = 85
    gap = 48

    max_value = max(counts + [1])

    for i, (label, value) in enumerate(zip(labels, counts)):
        height = max(5, (value / max_value) * chart_h)

        x = chart_x + i * (bar_w + gap)
        y = chart_y - height

        output += (
            f'<rect x="{x}" y="{y}" width="{bar_w}" '
            f'height="{height}" rx="7" fill="{BLUE}" />'
        )

        output += text(
            x + bar_w / 2,
            chart_y + 25,
            label,
            11,
            MUTED,
            "400",
            "middle"
        )

        output += text(
            x + bar_w / 2,
            y - 8,
            str(value),
            10,
            MUTED,
            "400",
            "middle"
        )

    return output


# ============================================================
# REPOSITORY ACTIVITY
# ============================================================

def build_repositories(user):
    repos = user.get("repositories", {}).get("nodes", [])

    repos = sorted(
        repos,
        key=lambda r: (
            safe_int(r.get("stargazerCount")) +
            safe_int(r.get("forkCount"))
        ),
        reverse=True
    )[:5]

    output = ""

    output += text(
        45,
        1725,
        "Repository Activity",
        22,
        TEXT,
        "700"
    )

    y = 1765

    for repo in repos:
        name = shorten(repo.get("name"), 35)

        stars = safe_int(repo.get("stargazerCount"))
        forks = safe_int(repo.get("forkCount"))

        language = repo.get("primaryLanguage") or {}
        lang_name = language.get("name") or "Other"

        output += text(
            55,
            y,
            name,
            14,
            TEXT,
            "600"
        )

        output += text(
            600,
            y,
            f"★ {stars}",
            12,
            MUTED
        )

        output += text(
            700,
            y,
            f"⑂ {forks}",
            12,
            MUTED
        )

        output += text(
            850,
            y,
            lang_name,
            12,
            BLUE
        )

        y += 42

    return output


# ============================================================
# BUILD COMPLETE SVG
# ============================================================

def build_svg(user):
    days = get_contribution_days(user)

    content = []

    content.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{SVG_WIDTH}" height="{SVG_HEIGHT}" '
        f'viewBox="0 0 {SVG_WIDTH} {SVG_HEIGHT}">'
    )

    content.append(
        f'<rect width="{SVG_WIDTH}" height="{SVG_HEIGHT}" '
        f'fill="{BG}" />'
    )

    # Header
    content.append(build_header(user))

    # Stats
    content.append(build_stat_cards(user, days))

    # Main cards
    content.append(
        rect(30, 260, 1140, 200, CARD2, BORDER, 16)
    )

    content.append(
        rect(30, 520, 625, 220, CARD2, BORDER, 16)
    )

    content.append(
        rect(675, 520, 495, 220, CARD2, BORDER, 16)
    )

    # Streak cards
    content.append(
        rect(30, 750, 760, 200, CARD2, BORDER, 16)
    )

    # Developer profile
    content.append(build_heatmap(days))
    content.append(build_activity(days))
    content.append(build_languages(user))
    content.append(build_streak(days))
    content.append(build_profile(user))
    content.append(build_metrics(user, days))

    # Activity
    content.append(
        rect(30, 1390, 1140, 315, CARD2, BORDER, 16)
    )

    content.append(build_weekday_chart(days))
    content.append(build_repositories(user))

    content.append(
        text(
            600,
            2020,
            f"Generated automatically from GitHub • @{USER}",
            11,
            MUTED,
            "400",
            "middle"
        )
    )

    content.append("</svg>")

    return "\n".join(content)


# ============================================================
# MAIN
# ============================================================

def main():
    print(f"Generating GitHub dashboard for @{USER}")

    user = github_graphql()

    if not user:
        raise RuntimeError(
            f"GitHub user '{USER}' was not found."
        )

    svg = build_svg(user)

    OUT.write_text(
        svg,
        encoding="utf-8"
    )

    print(f"Dashboard generated successfully: {OUT}")
    print(f"File size: {OUT.stat().st_size} bytes")


if __name__ == "__main__":
    main()
