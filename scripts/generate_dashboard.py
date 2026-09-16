const fs = require("fs");

const username = process.env.GITHUB_USERNAME;
const token = process.env.GITHUB_TOKEN;

async function github(query, variables = {}) {
  const response = await fetch("https://api.github.com/graphql", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
      "User-Agent": "github-dashboard"
    },
    body: JSON.stringify({
      query,
      variables
    })
  });

  const data = await response.json();

  if (data.errors) {
    throw new Error(JSON.stringify(data.errors));
  }

  return data.data;
}

async function main() {

  const query = `
    query($login: String!) {
      user(login: $login) {

        name
        login

        repositories(ownerAffiliations: OWNER, first: 1) {
          totalCount
        }

        followers {
          totalCount
        }

        following {
          totalCount
        }

        contributionsCollection {
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                contributionCount
                date
              }
            }
          }
        }
      }
    }
  `;

  const data = await github(query, {
    login: username
  });

  const user = data.user;

  const totalContributions =
    user.contributionsCollection.contributionCalendar.totalContributions;

  const weeks =
    user.contributionsCollection.contributionCalendar.weeks;


  // ------------------------------------------
  // CREATE CONTRIBUTION GRID
  // ------------------------------------------

  let contributionRects = "";

  let x = 95;

  weeks.forEach((week) => {

    let y = 400;

    week.contributionDays.forEach((day) => {

      const count = day.contributionCount;

      let color = "#161b22";

      if (count >= 1 && count <= 2)
        color = "#0e4429";

      if (count >= 3 && count <= 5)
        color = "#006d32";

      if (count >= 6 && count <= 9)
        color = "#26a641";

      if (count >= 10)
        color = "#39d353";

      contributionRects += `
        <rect
          x="${x}"
          y="${y}"
          width="14"
          height="14"
          rx="3"
          fill="${color}">
          <title>${day.date}: ${count} contributions</title>
        </rect>
      `;

      y += 19;
    });

    x += 19;
  });


  // ------------------------------------------
  // SVG
  // ------------------------------------------

  const svg = `
<svg xmlns="http://www.w3.org/2000/svg"
     width="1200"
     height="1850"
     viewBox="0 0 1200 1850">

  <rect width="1200"
        height="1850"
        fill="#0d1117"/>

  <rect x="20"
        y="20"
        width="1160"
        height="1810"
        rx="8"
        fill="none"
        stroke="#30363d"/>


  <!-- HEADER -->

  <text x="55"
        y="65"
        fill="#58a6ff"
        font-family="Arial"
        font-size="13"
        font-weight="bold">
    GITHUB / DEVELOPER DASHBOARD
  </text>

  <text x="55"
        y="115"
        fill="#f0f6fc"
        font-family="Arial"
        font-size="32"
        font-weight="bold">
    Hi, I'm ${user.name || user.login}
  </text>

  <text x="55"
        y="145"
        fill="#8b949e"
        font-family="Arial"
        font-size="15">
    BCA Student • Full-Stack Developer • Python &amp; Django
  </text>


  <!-- STATS -->

  <rect x="55"
        y="175"
        width="1090"
        height="105"
        rx="15"
        fill="#161b22"
        stroke="#30363d"/>


  <!-- REPOSITORIES -->

  <rect x="75"
        y="195"
        width="240"
        height="65"
        rx="10"
        fill="#0d1117"
        stroke="#30363d"/>

  <text x="95"
        y="220"
        fill="#8b949e"
        font-family="Arial"
        font-size="11">
    PUBLIC REPOSITORIES
  </text>

  <text x="95"
        y="248"
        fill="#f0f6fc"
        font-family="Arial"
        font-size="25"
        font-weight="bold">
    ${user.repositories.totalCount}
  </text>


  <!-- CONTRIBUTIONS -->

  <rect x="330"
        y="195"
        width="240"
        height="65"
        rx="10"
        fill="#0d1117"
        stroke="#30363d"/>

  <text x="350"
        y="220"
        fill="#8b949e"
        font-family="Arial"
        font-size="11">
    CONTRIBUTIONS
  </text>

  <text x="350"
        y="248"
        fill="#3fb950"
        font-family="Arial"
        font-size="25"
        font-weight="bold">
    ${totalContributions}
  </text>


  <!-- FOLLOWERS -->

  <rect x="585"
        y="195"
        width="240"
        height="65"
        rx="10"
        fill="#0d1117"
        stroke="#30363d"/>

  <text x="605"
        y="220"
        fill="#8b949e"
        font-family="Arial"
        font-size="11">
    FOLLOWERS
  </text>

  <text x="605"
        y="248"
        fill="#58a6ff"
        font-family="Arial"
        font-size="25"
        font-weight="bold">
    ${user.followers.totalCount}
  </text>


  <!-- FOLLOWING -->

  <rect x="840"
        y="195"
        width="240"
        height="65"
        rx="10"
        fill="#0d1117"
        stroke="#30363d"/>

  <text x="860"
        y="220"
        fill="#8b949e"
        font-family="Arial"
        font-size="11">
    FOLLOWING
  </text>

  <text x="860"
        y="248"
        fill="#d2a8ff"
        font-family="Arial"
        font-size="25"
        font-weight="bold">
    ${user.following.totalCount}
  </text>


  <!-- CONTRIBUTIONS -->

  <rect x="55"
        y="310"
        width="1090"
        height="300"
        rx="17"
        fill="#161b22"
        stroke="#30363d"/>

  <text x="80"
        y="350"
        fill="#f0f6fc"
        font-family="Arial"
        font-size="20"
        font-weight="bold">
    Contributions
  </text>

  <text x="80"
        y="373"
        fill="#8b949e"
        font-family="Arial"
        font-size="12">
    ${totalContributions} contributions in the last year
  </text>


  <!-- CONTRIBUTION GRID -->

  <rect x="75"
        y="390"
        width="1050"
        height="190"
        rx="13"
        fill="#0d1117"
        stroke="#30363d"/>

  ${contributionRects}


  <!-- LEGEND -->

  <text x="80"
        y="565"
        fill="#8b949e"
        font-family="Arial"
        font-size="10">
    Less
  </text>

  <rect x="115" y="555"
        width="12"
        height="12"
        rx="2"
        fill="#161b22"/>

  <rect x="133" y="555"
        width="12"
        height="12"
        rx="2"
        fill="#0e4429"/>

  <rect x="151" y="555"
        width="12"
        height="12"
        rx="2"
        fill="#006d32"/>

  <rect x="169" y="555"
        width="12"
        height="12"
        rx="2"
        fill="#26a641"/>

  <rect x="187" y="555"
        width="12"
        height="12"
        rx="2"
        fill="#39d353"/>

  <text x="207"
        y="565"
        fill="#8b949e"
        font-family="Arial"
        font-size="10">
    More
  </text>


  <!-- CODING ACTIVITY -->

  <rect x="55"
        y="640"
        width="540"
        height="230"
        rx="16"
        fill="#161b22"
        stroke="#30363d"/>

  <text x="80"
        y="680"
        fill="#f0f6fc"
        font-family="Arial"
        font-size="18"
        font-weight="bold">
    Coding Activity
  </text>

  <text x="80"
        y="702"
        fill="#8b949e"
        font-family="Arial"
        font-size="11">
    Live GitHub contribution activity
  </text>


  <!-- DYNAMIC ACTIVITY BARS -->

  ${weeks.slice(-8).map((week, i) => {

    const count = week.contributionDays.reduce(
      (sum, day) => sum + day.contributionCount,
      0
    );

    const height = Math.min(120, Math.max(20, count * 4));

    return `
      <rect
        x="${90 + i * 55}"
        y="${830 - height}"
        width="35"
        height="${height}"
        rx="4"
        fill="#238636">

        <title>
          ${count} contributions
        </title>

      </rect>
    `;

  }).join("")}


  <!-- DEVELOPER PROFILE -->

  <rect x="55"
        y="900"
        width="1090"
        height="150"
        rx="16"
        fill="#161b22"
        stroke="#30363d"/>

  <text x="80"
        y="940"
        fill="#f0f6fc"
        font-family="Arial"
        font-size="18"
        font-weight="bold">
    Developer Profile
  </text>

  <text x="80"
        y="970"
        fill="#8b949e"
        font-family="Arial"
        font-size="13">
    GitHub: @${user.login}
  </text>

  <text x="80"
        y="1000"
        fill="#3fb950"
        font-family="Arial"
        font-size="14">
    ${totalContributions} contributions
  </text>


  <!-- FOOTER -->

  <text x="600"
        y="1815"
        text-anchor="middle"
        fill="#8b949e"
        font-family="Arial"
        font-size="12">
    Code • Learn • Build • Repeat
  </text>

</svg>
`;

  fs.writeFileSync(
    "github-dashboard.svg",
    svg
  );

  console.log("Dashboard generated successfully!");
}

main().catch(console.error);
