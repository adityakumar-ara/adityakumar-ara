import os
import json
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from html import escape


# ============================================================
# CONFIGURATION
# ============================================================

USERNAME = os.environ.get("GITHUB_USERNAME", "adityakumar-ara")
TOKEN = os.environ.get("GITHUB_TOKEN")

OUTPUT = "assets/github-dashboard.svg"

if not TOKEN:
    raise RuntimeError("GITHUB_TOKEN is not set.")


# ============================================================
# GITHUB GRAPHQL API
# ============================================================

def github_graphql(query, variables=None):
    if variables is None:
        variables = {}

    payload = json.dumps({
        "query": query,
        "variables": variables
    }).encode("utf-8")

    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "github-dashboard"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(request) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"GitHub API error {error.code}: {body}"
        )

    if "errors" in data:
        raise RuntimeError(
            "GitHub GraphQL error: " +
            json.dumps(data["errors"], indent=2)
        )

    return data["data"]


# ============================================================
# GRAPHQL QUERY
# ============================================================

QUERY = """
query($username: String!) {
  user(login: $username) {

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
      orderBy: {
        field: UPDATED_AT
        direction: DESC
      }
    ) {
      totalCount

      nodes {
        name
        description
        url
        stargazerCount
        forkCount
        primaryLanguage {
          name
        }

        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges {
            size
            node {
              name
            }
          }
        }
      }
    }

    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      totalRepositoryContributions
      restrictedContributionsCount

      contributionCalendar {
        totalContributions

        weeks {
          contributionDays {
            contributionCount
            date
            weekday
          }
        }
      }
    }
  }
}
"""


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def esc(value):
    return escape(str(value if value is not None else ""), quote=True)


def shorten(text, length):
    if not text:
        return ""

    text = str(text).replace("\n", " ").strip()

    if len(text) <= length:
        return text

    return text[:length - 3] + "..."


def format_number(number):
    number = int(number or 0)

    if number >= 1_000_000:
        return f"{number / 1_000_000:.1f}M"

    if number >= 1_000:
        return f"{number / 1_000:.1f}K"

    return str(number)


def contribution_color(count):
    if count == 0:
        return "#161b22"

    if count <= 2:
        return "#0e4429"

    if count <= 5:
        return "#006d32"

    if count <= 9:
        return "#26a641"

    return "#39d353"


def language_color(language):
    colors = {
        "Python": "#3572A5",
        "JavaScript": "#f1e05a",
        "TypeScript": "#3178c6",
        "Java": "#b07219",
        "C++": "#f34b7d",
        "C": "#555555",
        "C#": "#178600",
        "HTML": "#e34c26",
        "CSS": "#563d7c",
        "PHP": "#4F5D95",
        "Go": "#00ADD8",
        "Rust": "#dea584",
        "Kotlin": "#A97BFF",
        "Swift": "#F05138",
        "Dart": "#00B4AB",
        "Shell": "#89e051",
        "Jupyter Notebook": "#DA5B0B",
    }

    return colors.get(language, "#8b949e")


def xml_text(text, x, y, size=14, fill="#c9d1d9",
             weight="400", anchor="start"):
    return (
        f'<text x="{x}" y="{y}" '
        f'font-family="Arial, Helvetica, sans-serif" '
        f'font-size="{size}px" '
        f'font-weight="{weight}" '
        f'fill="{fill}" '
        f'text-anchor="{anchor}">'
        f'{esc(text)}</text>'
    )


def rounded_rect(x, y, width, height, radius=16,
                 fill="#161b22", stroke="#30363d"):
    return (
        f'<rect x="{x}" y="{y}" width="{width}" height="{height}" '
        f'rx="{radius}" fill="{fill}" stroke="{stroke}" '
        f'stroke-width="1"/>'
    )


# ============================================================
# FETCH GITHUB DATA
# ============================================================

def get_github_data():
    data = github_graphql(
        QUERY,
        {"username": USERNAME}
    )

    user = data["user"]

    if not user:
        raise RuntimeError(
            f"GitHub user '{USERNAME}' was not found."
        )

    return user


# ============================================================
# LANGUAGE STATISTICS
# ============================================================

def calculate_languages(repositories):
    language_sizes = {}

    for repo in repositories:
        languages = repo.get("languages") or {}

        for edge in languages.get("edges", []):
            language = edge.get("node", {}).get("name")
            size = edge.get("size", 0)

            if language:
                language_sizes[language] = (
                    language_sizes.get(language, 0) + size
                )

    total = sum(language_sizes.values())

    if total == 0:
        return []

    result = []

    for language, size in sorted(
        language_sizes.items(),
        key=lambda item: item[1],
        reverse=True
    ):
        percentage = (size / total) * 100

        result.append({
            "name": language,
            "size": size,
            "percentage": percentage
        })

    return result


# ============================================================
# CONTRIBUTION DATA
# ============================================================

def get_contribution_days(user):
    calendar = (
        user["contributionsCollection"]
        ["contributionCalendar"]
    )

    days = []

    for week in calendar["weeks"]:
        for day in week["contributionDays"]:
            days.append({
                "date": day["date"],
                "count": day["contributionCount"],
                "weekday": day["weekday"]
            })

    return days


def calculate_streaks(days):
    if not days:
        return 0, 0

    dates = {}

    for day in days:
        dates[day["date"]] = day["count"]

    sorted_dates = sorted(dates.keys())

    longest = 0
    current = 0
    running = 0

    previous_date = None

    for date_string in sorted_dates:
        current_date = datetime.strptime(
            date_string,
            "%Y-%m-%d"
        ).date()

        count = dates[date_string]

        if count > 0:
            if (
                previous_date is not None
                and current_date == previous_date + timedelta(days=1)
            ):
                running += 1
            else:
                running = 1

            longest = max(longest, running)
        else:
            running = 0

        previous_date = current_date

    today = datetime.now().date()

    check_date = today

    if dates.get(check_date.strftime("%Y-%m-%d"), 0) == 0:
        check_date -= timedelta(days=1)

    while True:
        key = check_date.strftime("%Y-%m-%d")

        if dates.get(key, 0) <= 0:
            break

        current += 1
        check_date -= timedelta(days=1)

    return current, longest


# ============================================================
# WEEKLY ACTIVITY
# ============================================================

def weekly_activity(days):
    weeks = []

    if not days:
        return weeks

    current_week = []
    previous_weekday = None

    for day in days:
        weekday = day["weekday"]

        if previous_weekday is not None and weekday < previous_weekday:
            weeks.append(current_week)
            current_week = []

        current_week.append(day)
        previous_weekday = weekday

    if current_week:
        weeks.append(current_week)

    return weeks[-12:]


# ============================================================
# SVG HEADER
# ============================================================

def svg_header(width, height):
    return f'''<svg xmlns="http://www.w3.org/2000/svg"
    width="{width}"
    height="{height}"
    viewBox="0 0 {width} {height}">
    <rect width="{width}" height="{height}" fill="#0d1117"/>
'''


def svg_footer():
    return "</svg>"


# ============================================================
# TOP HEADER
# ============================================================

def render_header(user, total_contributions):
    name = user.get("name") or USERNAME
    login = user.get("login") or USERNAME

    avatar = user.get("avatarUrl", "")

    output = []

    output.append(
        f'<image href="{esc(avatar)}" x="45" y="35" '
        f'width="90" height="90" preserveAspectRatio="xMidYMid slice"/>'
    )

    output.append(
        xml_text(
            name,
            160,
            65,
            30,
            "#f0f6fc",
            "700"
        )
    )

    output.append(
        xml_text(
            f"@{login}",
            160,
            95,
            16,
            "#8b949e"
        )
    )

    output.append(
        xml_text(
            f"{format_number(total_contributions)} contributions",
            160,
            120,
            15,
            "#3fb950",
            "600"
        )
    )

    return "\n".join(output)


# ============================================================
# STAT CARDS
# ============================================================

def render_stat_cards(user):
    followers = user["followers"]["totalCount"]
    following = user["following"]["totalCount"]

    repos = user["repositories"]["totalCount"]

    contributions = (
        user["contributionsCollection"]
        ["contributionCalendar"]
        ["totalContributions"]
    )

    cards = [
        ("Repositories", format_number(repos)),
        ("Followers", format_number(followers)),
        ("Following", format_number(following)),
        ("Contributions", format_number(contributions)),
    ]

    output = []

    start_x = 45
    y = 155
    width = 245
    height = 105
    gap = 20

    for index, (title, value) in enumerate(cards):
        x = start_x + index * (width + gap)

        output.append(
            rounded_rect(
                x,
                y,
                width,
                height
            )
        )

        output.append(
            xml_text(
                title,
                x + 20,
                y + 35,
                15,
                "#8b949e"
            )
        )

        output.append(
            xml_text(
                value,
                x + 20,
                y + 75,
                28,
                "#f0f6fc",
                "700"
            )
        )

    return "\n".join(output)


# ============================================================
# CONTRIBUTION HEATMAP
# ============================================================

def render_heatmap(days):
    x = 45
    y = 315

    width = 1010
    height = 390

    output = []

    output.append(
        rounded_rect(
            x,
            y,
            width,
            height
        )
    )

    output.append(
        xml_text(
            "Contribution Activity",
            x + 20,
            y + 35,
            20,
            "#f0f6fc",
            "700"
        )
    )

    output.append(
        xml_text(
            "Last 365 days",
            x + 20,
            y + 60,
            13,
            "#8b949e"
        )
    )

    # Use last ~53 weeks
    recent_days = days[-371:]

    cell = 12
    gap = 4

    start_x = x + 25
    start_y = y + 85

    day_map = {}

    for day in recent_days:
        day_map[day["date"]] = day

    if recent_days:
        first_date = datetime.strptime(
            recent_days[0]["date"],
            "%Y-%m-%d"
        ).date()

        # Align to Sunday
        first_date -= timedelta(
            days=(first_date.weekday() + 1) % 7
        )

        current_date = first_date

        for column in range(53):
            for row in range(7):
                date_string = current_date.strftime("%Y-%m-%d")

                count = day_map.get(
                    date_string,
                    {}
                ).get("count", 0)

                rect_x = start_x + column * (cell + gap)
                rect_y = start_y + row * (cell + gap)

                output.append(
                    f'<rect x="{rect_x}" y="{rect_y}" '
                    f'width="{cell}" height="{cell}" '
                    f'rx="2" '
                    f'fill="{contribution_color(count)}">'
                    f'<title>{esc(date_string)}: '
                    f'{count} contributions</title>'
                    f'</rect>'
                )

                current_date += timedelta(days=1)

            # Reset date after 7-day column
            current_date = first_date + timedelta(
                days=column * 7 + 7
            )

    return "\n".join(output)


# ============================================================
# WEEKLY ACTIVITY CHART
# ============================================================

def render_activity_chart(days):
    x = 45
    y = 730

    width = 495
    height = 300

    output = []

    output.append(
        rounded_rect(
            x,
            y,
            width,
            height
        )
    )

    output.append(
        xml_text(
            "Weekly Activity",
            x + 20,
            y + 35,
            20,
            "#f0f6fc",
            "700"
        )
    )

    weeks = weekly_activity(days)

    totals = []

    for week in weeks:
        totals.append(
            sum(day["count"] for day in week)
        )

    if not totals:
        totals = [0]

    max_value = max(totals) or 1

    chart_x = x + 25
    chart_y = y + 75

    chart_width = width - 50
    chart_height = 175

    bar_gap = 7

    bar_width = max(
        5,
        (chart_width - bar_gap * len(totals))
        / len(totals)
    )

    for index, value in enumerate(totals):
        bar_height = (
            value / max_value
        ) * chart_height

        bar_x = (
            chart_x
            + index * (bar_width + bar_gap)
        )

        bar_y = (
            chart_y
            + chart_height
            - bar_height
        )

        output.append(
            f'<rect x="{bar_x:.2f}" '
            f'y="{bar_y:.2f}" '
            f'width="{bar_width:.2f}" '
            f'height="{bar_height:.2f}" '
            f'rx="3" fill="#26a641">'
            f'<title>{value} contributions</title>'
            f'</rect>'
        )

    output.append(
        xml_text(
            f"Max: {max(totals)}",
            x + 20,
            y + height - 20,
            13,
            "#8b949e"
        )
    )

    return "\n".join(output)


# ============================================================
# STREAK CARD
# ============================================================

def render_streak_card(days):
    x = 560
    y = 730

    width = 495
    height = 300

    current, longest = calculate_streaks(days)

    output = []

    output.append(
        rounded_rect(
            x,
            y,
            width,
            height
        )
    )

    output.append(
        xml_text(
            "Contribution Streak",
            x + 20,
            y + 35,
            20,
            "#f0f6fc",
            "700"
        )
    )

    output.append(
        xml_text(
            "Current streak",
            x + 25,
            y + 95,
            15,
            "#8b949e"
        )
    )

    output.append(
        xml_text(
            f"{current} days",
            x + 25,
            y + 140,
            34,
            "#3fb950",
            "700"
        )
    )

    output.append(
        xml_text(
            "Longest streak",
            x + 250,
            y + 95,
            15,
            "#8b949e"
        )
    )

    output.append(
        xml_text(
            f"{longest} days",
            x + 250,
            y + 140,
            34,
            "#f0f6fc",
            "700"
        )
    )

    output.append(
        xml_text(
            "Keep building consistently 🚀",
            x + 25,
            y + 205,
            16,
            "#8b949e"
        )
    )

    return "\n".join(output)


# ============================================================
# LANGUAGE CARD
# ============================================================

def render_language_card(languages):
    x = 45
    y = 1055

    width = 495
    height = 380

    output = []

    output.append(
        rounded_rect(
            x,
            y,
            width,
            height
        )
    )

    output.append(
        xml_text(
            "Top Languages",
            x + 20,
            y + 35,
            20,
            "#f0f6fc",
            "700"
        )
    )

    top_languages = languages[:7]

    if not top_languages:
        output.append(
            xml_text(
                "No language data available.",
                x + 20,
                y + 80,
                14,
                "#8b949e"
            )
        )
        return "\n".join(output)

    start_y = y + 75

    for index, language in enumerate(top_languages):
        row_y = start_y + index * 40

        name = language["name"]
        percentage = language["percentage"]

        output.append(
            f'<circle cx="{x + 27}" cy="{row_y - 5}" '
            f'r="5" fill="{language_color(name)}"/>'
        )

        output.append(
            xml_text(
                name,
                x + 42,
                row_y,
                14,
                "#c9d1d9"
            )
        )

        bar_x = x + 150
        bar_width = 240
        bar_height = 8

        output.append(
            f'<rect x="{bar_x}" y="{row_y - 12}" '
            f'width="{bar_width}" height="{bar_height}" '
            f'rx="4" fill="#21262d"/>'
        )

        output.append(
            f'<rect x="{bar_x}" y="{row_y - 12}" '
            f'width="{bar_width * percentage / 100:.2f}" '
            f'height="{bar_height}" '
            f'rx="4" fill="{language_color(name)}"/>'
        )

        output.append(
            xml_text(
                f"{percentage:.1f}%",
                x + 405,
                row_y,
                13,
                "#8b949e",
                "600",
                "end"
            )
        )

    return "\n".join(output)


# ============================================================
# PROFILE CARD
# ============================================================

def render_profile_card(user):
    x = 560
    y = 1055

    width = 495
    height = 380

    output = []

    output.append(
        rounded_rect(
            x,
            y,
            width,
            height
        )
    )

    output.append(
        xml_text(
            "About Me",
            x + 20,
            y + 35,
            20,
            "#f0f6fc",
            "700"
        )
    )

    bio = user.get("bio")

    if bio:
        lines = []

        words = bio.split()
        current = ""

        for word in words:
            test = (
                current + " " + word
            ).strip()

            if len(test) > 42:
                lines.append(current)
                current = word
            else:
                current = test

        if current:
            lines.append(current)

        for index, line in enumerate(lines[:5]):
            output.append(
                xml_text(
                    line,
                    x + 20,
                    y + 75 + index * 25,
                    14,
                    "#c9d1d9"
                )
            )
    else:
        output.append(
            xml_text(
                "GitHub developer",
                x + 20,
                y + 75,
                14,
                "#c9d1d9"
            )
        )

    output.append(
        xml_text(
            f"Followers: {user['followers']['totalCount']}",
            x + 20,
            y + 220,
            15,
            "#8b949e"
        )
    )

    output.append(
        xml_text(
            f"Following: {user['following']['totalCount']}",
            x + 20,
            y + 250,
            15,
            "#8b949e"
        )
    )

    output.append(
        xml_text(
            f"Public repositories: "
            f"{user['repositories']['totalCount']}",
            x + 20,
            y + 280,
            15,
            "#8b949e"
        )
    )

    return "\n".join(output)


# ============================================================
# REPOSITORY CARD
# ============================================================

def render_repo_card(repo, x, y, width=495, height=135):
    output = []

    output.append(
        rounded_rect(
            x,
            y,
            width,
            height
        )
    )

    name = repo.get("name", "")
    description = repo.get("description") or "No description"

    language = repo.get("primaryLanguage")

    if language:
        language_name = language.get("name", "")
    else:
        language_name = ""

    stars = repo.get("stargazerCount", 0)
    forks = repo.get("forkCount", 0)

    output.append(
        xml_text(
            shorten(name, 30),
            x + 20,
            y + 32,
            17,
            "#58a6ff",
            "700"
        )
    )

    description = shorten(
        description,
        48
    )

    output.append(
        xml_text(
            description,
            x + 20,
            y + 60,
            13,
            "#8b949e"
        )
    )

    if language_name:
        output.append(
            f'<circle cx="{x + 27}" cy="{y + 95}" '
            f'r="5" fill="{language_color(language_name)}"/>'
        )

        output.append(
            xml_text(
                language_name,
                x + 40,
                y + 100,
                12,
                "#8b949e"
            )
        )

    output.append(
        xml_text(
            f"★ {stars}",
            x + 180,
            y + 100,
            12,
            "#8b949e"
        )
    )

    output.append(
        xml_text(
            f"⑂ {forks}",
            x + 250,
            y + 100,
            12,
            "#8b949e"
        )
    )

    return "\n".join(output)


# ============================================================
# TOP REPOSITORIES
# ============================================================

def render_repositories(repositories):
    x = 45
    y = 1475

    output = []

    output.append(
        xml_text(
            "Repositories",
            x,
            y,
            24,
            "#f0f6fc",
            "700"
        )
    )

    repos = sorted(
        repositories,
        key=lambda repo: (
            repo.get("stargazerCount", 0),
            repo.get("forkCount", 0)
        ),
        reverse=True
    )

    repos = repos[:6]

    start_y = y + 25

    for index, repo in enumerate(repos):
        column = index % 2
        row = index // 2

        card_x = 45 + column * 510
        card_y = start_y + row * 155

        output.append(
            render_repo_card(
                repo,
                card_x,
                card_y
            )
        )

    return "\n".join(output)


# ============================================================
# TECHNOLOGIES
# ============================================================

def render_technologies(languages):
    x = 45
    y = 2005

    output = []

    output.append(
        xml_text(
            "Technology Stack",
            x,
            y,
            24,
            "#f0f6fc",
            "700"
        )
    )

    techs = [
        language["name"]
        for language in languages[:12]
    ]

    if not techs:
        techs = [
            "Python",
            "JavaScript",
            "Git",
            "GitHub"
        ]

    pill_x = x
    pill_y = y + 30

    for tech in techs:
        pill_width = max(
            90,
            len(tech) * 8 + 30
        )

        if pill_x + pill_width > 1030:
            pill_x = x
            pill_y += 42

        output.append(
            f'<rect x="{pill_x}" y="{pill_y}" '
            f'width="{pill_width}" height="30" '
            f'rx="15" fill="#161b22" '
            f'stroke="#30363d"/>'
        )

        output.append(
            xml_text(
                tech,
                pill_x + pill_width / 2,
                pill_y + 20,
                12,
                "#c9d1d9",
                "600",
                "middle"
            )
        )

        pill_x += pill_width + 12

    return "\n".join(output)


# ============================================================
# FOOTER
# ============================================================

def render_footer():
    return "\n".join([
        xml_text(
            f"Generated automatically from GitHub • "
            f"{datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
            550,
            2185,
            12,
            "#6e7681",
            "400",
            "middle"
        )
    ])


# ============================================================
# COMPLETE SVG
# ============================================================

def generate_svg(user):
    width = 1100
    height = 2220

    contributions = (
        user["contributionsCollection"]
        ["contributionCalendar"]
        ["totalContributions"]
    )

    days = get_contribution_days(user)

    repositories = user["repositories"]["nodes"]

    languages = calculate_languages(
        repositories
    )

    parts = []

    parts.append(
        svg_header(width, height)
    )

    parts.append(
        render_header(
            user,
            contributions
        )
    )

    parts.append(
        render_stat_cards(user)
    )

    parts.append(
        render_heatmap(days)
    )

    parts.append(
        render_activity_chart(days)
    )

    parts.append(
        render_streak_card(days)
    )

    parts.append(
        render_language_card(languages)
    )

    parts.append(
        render_profile_card(user)
    )

    parts.append(
        render_repositories(repositories)
    )

    parts.append(
        render_technologies(languages)
    )

    parts.append(
        render_footer()
    )

    parts.append(
        svg_footer()
    )

    return "\n".join(parts)


# ============================================================
# MAIN
# ============================================================

def main():
    print("Fetching GitHub data...")
    print(f"Username: {USERNAME}")

    user = get_github_data()

    print("Generating dashboard...")

    svg = generate_svg(user)

    os.makedirs(
        os.path.dirname(OUTPUT),
        exist_ok=True
    )

    with open(
        OUTPUT,
        "w",
        encoding="utf-8"
    ) as file:
        file.write(svg)

    print(
        f"Dashboard generated successfully: {OUTPUT}"
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("Dashboard generation failed:")
        print(error)
        raise
