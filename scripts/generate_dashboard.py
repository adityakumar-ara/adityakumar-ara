import os
import json
import urllib.request
from datetime import datetime

# Environment Variables se token aur username lena
TOKEN = os.getenv("GITHUB_TOKEN")
USERNAME = os.getenv("GITHUB_USERNAME", "adityakumar-ara")

if not TOKEN:
    raise ValueError("GITHUB_TOKEN is missing! GitHub Actions me token ensure karein.")

def fetch_github_data():
    url = "https://api.github.com/graphql"
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    
    # GraphQL query to get real user stats
    query = """
    {
      user(login: "%s") {
        repositories(first: 100, ownerAffiliations: OWNER, orderBy: {field: STARGAZERS, direction: DESC}) {
          totalCount
          nodes {
            stargazerCount
            primaryLanguage { name color }
          }
        }
        contributionsCollection {
          contributionCalendar { totalContributions }
        }
        followers { totalCount }
      }
    }
    """ % USERNAME

    data = json.dumps({"query": query}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers)
    
    try:
        response = urllib.request.urlopen(req)
        result = json.loads(response.read().decode("utf-8"))
        if "errors" in result:
            raise Exception(f"GraphQL Error: {result['errors']}")
        return result["data"]["user"]
    except Exception as e:
        print(f"Error fetching data: {e}")
        raise e

def generate_svg(data):
    # Data extraction
    total_repos = data["repositories"]["totalCount"]
    total_followers = data["followers"]["totalCount"]
    total_contributions = data["contributionsCollection"]["contributionCalendar"]["totalContributions"]
    
    total_stars = sum(repo["stargazerCount"] for repo in data["repositories"]["nodes"])
    
    # Simple top languages calculation
    languages = {}
    for repo in data["repositories"]["nodes"]:
        lang = repo.get("primaryLanguage")
        if lang:
            name = lang["name"]
            languages[name] = languages.get(name, 0) + 1
            
    top_langs = sorted(languages.items(), key=lambda x: x[1], reverse=True)[:3]
    lang_str = ", ".join([f"{l[0]}" for l in top_langs]) if top_langs else "Python, Django, JavaScript"

    # SVG Template (Dark Mode, Visually Rich)
    svg_template = f"""<svg xmlns="http://www.w3.org/2000/svg" width="800" height="400" viewBox="0 0 800 400">
    <style>
        .bg {{ fill: #0d1117; }}
        .card-bg {{ fill: #161b22; stroke: #30363d; stroke-width: 2; rx: 10; ry: 10; }}
        .text-title {{ font-family: 'Segoe UI', Ubuntu, sans-serif; font-size: 24px; font-weight: bold; fill: #58a6ff; }}
        .text-subtitle {{ font-family: 'Segoe UI', Ubuntu, sans-serif; font-size: 16px; fill: #8b949e; }}
        .text-stat {{ font-family: 'Segoe UI', Ubuntu, sans-serif; font-size: 28px; font-weight: bold; fill: #c9d1d9; }}
        .text-label {{ font-family: 'Segoe UI', Ubuntu, sans-serif; font-size: 14px; fill: #8b949e; }}
        .line {{ stroke: #30363d; stroke-width: 2; }}
    </style>
    
    <!-- Background -->
    <rect width="800" height="400" class="bg" rx="15" ry="15" />
    <rect width="796" height="396" x="2" y="2" class="card-bg" fill="none"/>

    <!-- Header Section -->
    <text x="40" y="60" class="text-title">Hi, I'm Aditya Kumar 👋</text>
    <text x="40" y="90" class="text-subtitle">Aspiring Full-Stack Developer | BCA Student @ Shobhit University</text>
    <line x1="40" y1="110" x2="760" y2="110" class="line" />

    <!-- GitHub Stats Cards -->
    <!-- Card 1: Contributions -->
    <rect x="40" y="140" width="220" height="100" class="card-bg" />
    <text x="150" y="185" class="text-stat" text-anchor="middle">{total_contributions}</text>
    <text x="150" y="215" class="text-label" text-anchor="middle">Total Contributions</text>

    <!-- Card 2: Stars -->
    <rect x="290" y="140" width="220" height="100" class="card-bg" />
    <text x="400" y="185" class="text-stat" text-anchor="middle">{total_stars}</text>
    <text x="400" y="215" class="text-label" text-anchor="middle">Total Stars</text>

    <!-- Card 3: Repositories -->
    <rect x="540" y="140" width="220" height="100" class="card-bg" />
    <text x="650" y="185" class="text-stat" text-anchor="middle">{total_repos}</text>
    <text x="650" y="215" class="text-label" text-anchor="middle">Public Repositories</text>

    <!-- Bottom Section: Tech & Languages -->
    <rect x="40" y="270" width="720" height="90" class="card-bg" />
    <text x="60" y="305" class="text-title" style="font-size: 18px;">Top Languages &amp; Tech</text>
    <text x="60" y="335" class="text-subtitle" style="font-size: 14px;">{lang_str} | React | PostgreSQL | Bootstrap</text>
    
</svg>"""
    return svg_template

def main():
    print("Fetching data from GitHub API...")
    user_data = fetch_github_data()
    
    print("Generating SVG...")
    svg_content = generate_svg(user_data)
    
    # Ensure assets folder exists
    os.makedirs("assets", exist_ok=True)
    file_path = "assets/github-dashboard.svg"
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(svg_content)
        
    print(f"Successfully generated {file_path}!")

if __name__ == "__main__":
    main()
