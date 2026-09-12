import json, os, urllib.request, html
from datetime import datetime, timedelta, timezone
from pathlib import Path

USER = os.environ.get("GITHUB_USERNAME", "adityakumar-ara")
TOKEN = os.environ["GITHUB_TOKEN"]
OUT = Path("assets/github-dashboard.svg")
OUT.parent.mkdir(parents=True, exist_ok=True)

def gql(query, variables):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json", "User-Agent": "github-dashboard"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        result = json.load(r)
    if result.get("errors"):
        raise RuntimeError(result["errors"])
    return result["data"]["user"]

Q = '''query($login:String!){user(login:$login){name login bio followers{totalCount} following{totalCount} repositories(first:100,ownerAffiliations:OWNER,privacy:PUBLIC){totalCount nodes{name stargazerCount forkCount primaryLanguage{name}}} contributionsCollection{totalCommitContributions totalIssueContributions totalPullRequestContributions totalPullRequestReviewContributions contributionCalendar{totalContributions weeks{contributionDays{date contributionCount}}}}}}'''
d = gql(Q, {"login": USER})

def esc(x): return html.escape(str(x))
name = d.get("name") or USER
bio = d.get("bio") or "Aspiring Full-Stack Developer"
followers = d["followers"]["totalCount"]
following = d["following"]["totalCount"]
repos = d["repositories"]["nodes"]
repo_count = d["repositories"]["totalCount"]
cc = d["contributionsCollection"]
commits, issues, prs, reviews = (cc[k] for k in ["totalCommitContributions","totalIssueContributions","totalPullRequestContributions","totalPullRequestReviewContributions"])
total = cc["contributionCalendar"]["totalContributions"]
days = [x for w in cc["contributionCalendar"]["weeks"] for x in w["contributionDays"]]
days.sort(key=lambda x:x["date"])
lang={}
for r in repos:
    if r.get("primaryLanguage"):
        n=r["primaryLanguage"]["name"]; lang[n]=lang.get(n,0)+1
top=sorted(lang.items(), key=lambda x:x[1], reverse=True)[:5]
stars=sum(r["stargazerCount"] for r in repos); forks=sum(r["forkCount"] for r in repos)

daymap={x["date"]:x["contributionCount"] for x in days}
today=datetime.now(timezone.utc).date(); cur=today if daymap.get(str(today),0) else today-timedelta(days=1)
streak=0
while daymap.get(str(cur),0)>0: streak+=1; cur-=timedelta(days=1)
best=run=0; prev=None
for x in days:
    if x["contributionCount"]:
        run = run+1 if prev and (datetime.fromisoformat(x["date"])-datetime.fromisoformat(prev)).days==1 else 1
        best=max(best,run); prev=x["date"]
    else: run=0

W,H=1000,1640
BG="#07111B"; PANEL="#091A27"; PANEL2="#0B2030"; BORDER="#12364B"; TEXT="#E8F3F8"; MUTED="#8FA8B5"; CYAN="#12D8FF"; GREEN="#18D98A"; ORANGE="#F3A34B"
s=[]
s.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}"><rect width="100%" height="100%" rx="24" fill="{BG}"/><style>text{{font-family:Inter,Segoe UI,Arial,sans-serif}}.title{{font-size:25px;font-weight:700;fill:{TEXT}}}.h{{font-size:18px;font-weight:700;fill:{TEXT}}}.label{{font-size:11px;fill:{MUTED}}}.value{{font-size:20px;font-weight:700;fill:{TEXT}}}.small{{font-size:12px;fill:{MUTED}}}</style>')
# header
s.append(f'<rect x="18" y="18" width="964" height="150" rx="18" fill="{PANEL}" stroke="{BORDER}"/><circle cx="85" cy="93" r="38" fill="#0D2B3D" stroke="{CYAN}" stroke-width="3"/><text x="85" y="101" text-anchor="middle" font-size="22" font-weight="700" fill="{CYAN}">AK</text><text x="140" y="62" class="title">Hi, I\'m {esc(name)}</text><text x="140" y="88" class="small">BCA Student • Aspiring Full-Stack Developer • Python &amp; Django</text><text x="140" y="111" class="small">{esc(bio)[:90]}</text><text x="140" y="138" class="small">github.com/{esc(USER)}</text><text x="925" y="62" text-anchor="end" class="small">Followers</text><text x="925" y="86" text-anchor="end" class="value">{followers}</text><text x="925" y="115" text-anchor="end" class="small">Following {following}</text>')
# stat cards
for i,(lab,val) in enumerate([("Repositories",repo_count),("Contributions",total),("Commits",commits),("Issues",issues),("Pull Requests",prs)]):
    x=18+i*193; s.append(f'<rect x="{x}" y="185" width="177" height="88" rx="13" fill="{PANEL}" stroke="{BORDER}"/><text x="{x+14}" y="211" class="label">{lab}</text><text x="{x+14}" y="246" class="value">{val}</text>')
# heatmap
s.append(f'<rect x="18" y="291" width="964" height="225" rx="15" fill="{PANEL}" stroke="{BORDER}"/><text x="36" y="322" class="h">Contribution Activity</text>')
for idx,d in enumerate(days[-371:]):
    col,row=idx//7,idx%7; x=38+col*14; y=344+row*14; n=d["contributionCount"]
    fill="#102A39" if n==0 else "#0A624B" if n<3 else "#0C8C68" if n<6 else "#12C986"
    s.append(f'<rect x="{x}" y="{y}" width="11" height="11" rx="2" fill="{fill}"/>')
# activity and language cards
s.append(f'<rect x="18" y="536" width="470" height="270" rx="15" fill="{PANEL}" stroke="{BORDER}"/><text x="36" y="568" class="h">Coding Activity</text><text x="36" y="592" class="small">Commits {commits} • PRs {prs} • Issues {issues} • Reviews {reviews}</text>')
months={}
for x in days: months[x["date"][:7]]=months.get(x["date"][:7],0)+x["contributionCount"]
vals=list(months.items())[-12:]; mx=max([v for _,v in vals] or [1])
for i,(m,v) in enumerate(vals):
    bh=int(120*v/mx); x=40+i*34; y=748-bh; s.append(f'<rect x="{x}" y="{y}" width="20" height="{bh}" rx="3" fill="{CYAN}"/><text x="{x+10}" y="770" text-anchor="middle" font-size="8" fill="{MUTED}">{m[5:]}</text>')
s.append(f'<rect x="512" y="536" width="470" height="270" rx="15" fill="{PANEL}" stroke="{BORDER}"/><text x="530" y="568" class="h">Most Used Languages</text>')
cx,cy,r=625,676,72; total_lang=sum(v for _,v in top) or 1; circ=2*3.14159*r; off=0; cols=[CYAN,GREEN,ORANGE,"#B77CFF","#FF5F8F"]
for i,(ln,v) in enumerate(top):
    dash=v/total_lang*circ; c=cols[i%len(cols)]; s.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{c}" stroke-width="24" stroke-dasharray="{dash} {circ-dash}" stroke-dashoffset="{-off}" transform="rotate(-90 {cx} {cy})"/><circle cx="735" cy="{610+i*30}" r="5" fill="{c}"/><text x="750" y="{614+i*30}" class="small">{esc(ln)} — {v}</text>'); off+=dash
s.append(f'<text x="{cx}" y="{cy+6}" text-anchor="middle" font-size="17" font-weight="700" fill="{TEXT}">{len(top)}</text>')
# streak/profile
s.append(f'<rect x="18" y="826" width="470" height="150" rx="15" fill="{PANEL}" stroke="{BORDER}"/><text x="36" y="858" class="h">Coding Streak</text><text x="36" y="905" font-size="34" font-weight="700" fill="{GREEN}">{streak} days</text><text x="36" y="932" class="small">Current streak</text><text x="250" y="905" font-size="34" font-weight="700" fill="{CYAN}">{best} days</text><text x="250" y="932" class="small">Longest streak</text>')
s.append(f'<rect x="512" y="826" width="470" height="150" rx="15" fill="{PANEL}" stroke="{BORDER}"/><text x="530" y="858" class="h">Developer Profile</text><text x="530" y="892" class="small">Public repositories</text><text x="900" y="892" text-anchor="end" class="value">{repo_count}</text><text x="530" y="920" class="small">Stars received</text><text x="900" y="920" text-anchor="end" class="value">{stars}</text><text x="530" y="948" class="small">Forks received</text><text x="900" y="948" text-anchor="end" class="value">{forks}</text>')
# about and tech
s.append(f'<rect x="18" y="996" width="470" height="290" rx="15" fill="{PANEL}" stroke="{BORDER}"/><text x="36" y="1028" class="h">About Me</text>')
for i,line in enumerate(["BCA student","Aspiring Full-Stack Developer","Python & Django developer","Learning React & REST APIs","Practicing Data Structures & Algorithms","Exploring AI & Machine Learning"]): s.append(f'<text x="40" y="{1060+i*32}" font-size="13" fill="{TEXT}">• {esc(line)}</text>')
s.append(f'<rect x="512" y="996" width="470" height="290" rx="15" fill="{PANEL}" stroke="{BORDER}"/><text x="530" y="1028" class="h">Technologies &amp; Languages</text>')
tech=["Python","Java","C","HTML5","CSS3","JavaScript","Bootstrap","React","Django","PostgreSQL","MySQL","Git/GitHub"]
for i,t in enumerate(tech):
    col,row=i%3,i//3; x=532+col*142; y=1060+row*48; s.append(f'<rect x="{x}" y="{y}" width="125" height="32" rx="8" fill="{PANEL2}" stroke="{BORDER}"/><text x="{x+10}" y="{y+21}" font-size="11" fill="{TEXT}">{t}</text>')
# footer activity
s.append(f'<text x="500" y="1330" text-anchor="middle" font-size="12" fill="{MUTED}">Generated automatically from public GitHub activity • Updated daily</text><rect x="18" y="1352" width="964" height="1" fill="{BORDER}"/><text x="500" y="1392" text-anchor="middle" font-size="20" font-weight="700" fill="{TEXT}">GitHub Activity</text>')
weekly=[sum(x["contributionCount"] for x in days[i:i+7]) for i in range(0,len(days),7)][-12:]; mx=max(weekly or [1])
for i,v in enumerate(weekly):
    bh=int(135*v/mx); x=55+i*70; y=1540-bh; s.append(f'<rect x="{x}" y="{y}" width="42" height="{bh}" rx="5" fill="{CYAN}"/><text x="{x+21}" y="1562" text-anchor="middle" font-size="9" fill="{MUTED}">W{i+1}</text>')
s.append(f'<text x="500" y="1610" text-anchor="middle" font-size="11" fill="{MUTED}">github.com/{esc(USER)}</text></svg>')
OUT.write_text("\n".join(s), encoding="utf-8")
print("Generated", OUT)
