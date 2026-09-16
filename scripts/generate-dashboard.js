const fs = require("fs");

const USERNAME = process.env.GITHUB_USERNAME || "adityakumar-ara";
const TOKEN = process.env.GITHUB_TOKEN;

if (!TOKEN) {
    throw new Error("GITHUB_TOKEN is missing.");
}


// ======================================================
// HELPERS
// ======================================================

function escapeXML(value = "") {
    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&apos;");
}


function shortText(text = "", max = 42) {
    text = String(text || "");

    if (text.length <= max) {
        return text;
    }

    return text.substring(0, max - 3) + "...";
}


function formatNumber(number) {
    return Number(number || 0).toLocaleString("en-US");
}


function getColorForContribution(count) {

    if (count === 0) return "#161b22";
    if (count <= 2) return "#0e4429";
    if (count <= 5) return "#006d32";
    if (count <= 9) return "#26a641";

    return "#39d353";
}


function getLanguageColor(color) {
    return color || "#8b949e";
}


// ======================================================
// GITHUB GRAPHQL
// ======================================================

async function github(query, variables = {}) {

    const response = await fetch(
        "https://api.github.com/graphql",
        {
            method: "POST",

            headers: {
                Authorization: `Bearer ${TOKEN}`,
                "Content-Type": "application/json",
                "User-Agent": "github-dashboard"
            },

            body: JSON.stringify({
                query,
                variables
            })
        }
    );


    if (!response.ok) {
        throw new Error(
            `GitHub API HTTP error: ${response.status}`
        );
    }


    const result = await response.json();


    if (result.errors) {
        throw new Error(
            JSON.stringify(result.errors, null, 2)
        );
    }


    return result.data;
}


// ======================================================
// FETCH USER DATA
// ======================================================

async function getUser() {

    const query = `

        query($login: String!) {

            user(login: $login) {

                login
                name
                bio
                location
                company
                websiteUrl
                avatarUrl
                url

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
                        url
                        description

                        stargazerCount
                        forkCount

                        primaryLanguage {
                            name
                            color
                        }

                        languages(
                            first: 10
                            orderBy: {
                                field: SIZE
                                direction: DESC
                            }
                        ) {

                            edges {

                                size

                                node {
                                    name
                                    color
                                }
                            }
                        }
                    }
                }


                contributionsCollection {

                    totalContributions

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
    `;


    const data = await github(
        query,
        {
            login: USERNAME
        }
    );


    return data.user;
}


// ======================================================
// LANGUAGE CALCULATION
// ======================================================

function calculateLanguages(repositories) {

    const languageMap = {};


    for (const repo of repositories) {

        if (!repo.languages) {
            continue;
        }


        for (const edge of repo.languages.edges) {

            const name = edge.node.name;
            const size = Number(edge.size || 0);


            if (!languageMap[name]) {

                languageMap[name] = {
                    name,
                    size,
                    color: edge.node.color
                };

            } else {

                languageMap[name].size += size;
            }
        }
    }


    const languages = Object.values(languageMap);


    languages.sort(
        (a, b) => b.size - a.size
    );


    const total = languages.reduce(
        (sum, language) => sum + language.size,
        0
    );


    return languages
        .slice(0, 6)
        .map(language => ({

            ...language,

            percentage: total
                ? ((language.size / total) * 100)
                    .toFixed(1)
                : "0.0"
        }));
}


// ======================================================
// CONTRIBUTION DATA
// ======================================================

function getContributionDays(user) {

    const weeks =
        user.contributionsCollection
            .contributionCalendar
            .weeks;


    const days = [];


    for (const week of weeks) {

        for (const day of week.contributionDays) {

            days.push({
                date: day.date,
                count: day.contributionCount,
                weekday: day.weekday
            });
        }
    }


    return days;
}


// ======================================================
// STREAK CALCULATION
// ======================================================

function calculateStreak(days) {

    const contributionDates = new Set();


    for (const day of days) {

        if (day.count > 0) {
            contributionDates.add(day.date);
        }
    }


    if (days.length === 0) {

        return {
            current: 0,
            longest: 0
        };
    }


    const sortedDates =
        [...contributionDates].sort();


    let longest = 0;
    let current = 0;


    // ----------------------------------------------
    // LONGEST STREAK
    // ----------------------------------------------

    let running = 0;


    for (let i = 0; i < sortedDates.length; i++) {

        if (i === 0) {

            running = 1;

        } else {

            const previous =
                new Date(sortedDates[i - 1]);

            const currentDate =
                new Date(sortedDates[i]);


            const difference =
                Math.round(
                    (currentDate - previous) /
                    (1000 * 60 * 60 * 24)
                );


            if (difference === 1) {

                running++;

            } else {

                running = 1;
            }
        }


        longest = Math.max(
            longest,
            running
        );
    }


    // ----------------------------------------------
    // CURRENT STREAK
    // ----------------------------------------------

    const today =
        new Date().toISOString().split("T")[0];


    let cursor =
        new Date(today);


    // If today has no contribution,
    // start from yesterday.

    if (!contributionDates.has(today)) {

        cursor.setDate(
            cursor.getDate() - 1
        );
    }


    while (true) {

        const date =
            cursor.toISOString().split("T")[0];


        if (!contributionDates.has(date)) {
            break;
        }


        current++;


        cursor.setDate(
            cursor.getDate() - 1
        );
    }


    return {
        current,
        longest
    };
}


// ======================================================
// WEEKLY ACTIVITY
// ======================================================

function getWeeklyActivity(user) {

    const weeks =
        user.contributionsCollection
            .contributionCalendar
            .weeks;


    return weeks
        .slice(-12)
        .map(week => {

            const total =
                week.contributionDays.reduce(
                    (sum, day) =>
                        sum + day.contributionCount,
                    0
                );


            return {
                total
            };
        });
}


// ======================================================
// SVG
// ======================================================

function createSVG(user) {

    const contributions =
        user.contributionsCollection;


    const calendar =
        contributions.contributionCalendar;


    const days =
        getContributionDays(user);


    const streak =
        calculateStreak(days);


    const weeklyActivity =
        getWeeklyActivity(user);


    const languages =
        calculateLanguages(
            user.repositories.nodes
        );


    const repositories =
        [...user.repositories.nodes]
            .sort(
                (a, b) =>
                    b.stargazerCount -
                    a.stargazerCount
            );


    const topRepositories =
        repositories.slice(0, 6);


    const totalContributions =
        calendar.totalContributions;


    // ==================================================
    // CONTRIBUTION GRID
    // ==================================================

    let contributionGrid = "";


    const weeks =
        calendar.weeks;


    const cellSize = 15;

    const gap = 3;

    const startX = 70;

    const startY = 410;


    weeks.forEach(
        (week, weekIndex) => {

            week.contributionDays.forEach(
                day => {

                    const x =
                        startX +
                        weekIndex *
                        (cellSize + gap);


                    const y =
                        startY +
                        day.weekday *
                        (cellSize + gap);


                    const color =
                        getColorForContribution(
                            day.contributionCount
                        );


                    contributionGrid += `

                        <rect
                            x="${x}"
                            y="${y}"
                            width="${cellSize}"
                            height="${cellSize}"
                            rx="3"
                            fill="${color}"
                        >

                            <title>
                                ${escapeXML(day.date)}:
                                ${day.contributionCount}
                                contributions
                            </title>

                        </rect>
                    `;
                }
            );
        }
    );


    // ==================================================
    // ACTIVITY BARS
    // ==================================================

    const maxActivity =
        Math.max(
            ...weeklyActivity.map(
                item => item.total
            ),
            1
        );


    let activityBars = "";


    weeklyActivity.forEach(
        (item, index) => {

            const barHeight =
                Math.max(
                    15,
                    (item.total / maxActivity) *
                    145
                );


            const x =
                70 + index * 62;


            const y =
                760 - barHeight;


            activityBars += `

                <rect
                    x="${x}"
                    y="${y}"
                    width="38"
                    height="${barHeight}"
                    rx="6"
                    fill="#238636"
                >

                    <title>
                        ${item.total}
                        contributions
                    </title>

                </rect>
            `;
        }
    );


    // ==================================================
    // LANGUAGE BARS
    // ==================================================

    let languageRows = "";


    languages.forEach(
        (language, index) => {

            const y =
                1010 + index * 48;


            const width =
                Math.max(
                    5,
                    Number(language.percentage) * 4
                );


            languageRows += `

                <text
                    x="90"
                    y="${y}"
                    fill="#f0f6fc"
                    font-family="Arial"
                    font-size="13"
                >
                    ${escapeXML(language.name)}
                </text>


                <rect
                    x="260"
                    y="${y - 13}"
                    width="220"
                    height="10"
                    rx="5"
                    fill="#21262d"
                />


                <rect
                    x="260"
                    y="${y - 13}"
                    width="${width}"
                    height="10"
                    rx="5"
                    fill="${getLanguageColor(language.color)}"
                />


                <text
                    x="500"
                    y="${y}"
                    fill="#8b949e"
                    font-family="Arial"
                    font-size="12"
                >
                    ${language.percentage}%
                </text>
            `;
        }
    );


    // ==================================================
    // REPOSITORIES
    // ==================================================

    let repositoryCards = "";


    topRepositories.forEach(
        (repo, index) => {

            const column =
                index % 2;


            const row =
                Math.floor(index / 2);


            const x =
                column === 0
                    ? 70
                    : 700;


            const y =
                1300 + row * 155;


            const language =
                repo.primaryLanguage
                    ? repo.primaryLanguage.name
                    : "Other";


            repositoryCards += `

                <rect
                    x="${x}"
                    y="${y}"
                    width="580"
                    height="130"
                    rx="14"
                    fill="#161b22"
                    stroke="#30363d"
                />


                <text
                    x="${x + 25}"
                    y="${y + 35}"
                    fill="#58a6ff"
                    font-family="Arial"
                    font-size="17"
                    font-weight="bold"
                >
                    ${escapeXML(
                        shortText(repo.name, 28)
                    )}
                </text>


                <text
                    x="${x + 25}"
                    y="${y + 63}"
                    fill="#8b949e"
                    font-family="Arial"
                    font-size="12"
                >
                    ${escapeXML(
                        shortText(
                            repo.description ||
                            "No description",
                            60
                        )
                    )}
                </text>


                <circle
                    cx="${x + 30}"
                    cy="${y + 98}"
                    r="5"
                    fill="${
                        repo.primaryLanguage?.color ||
                        "#8b949e"
                    }"
                />


                <text
                    x="${x + 42}"
                    y="${y + 102}"
                    fill="#8b949e"
                    font-family="Arial"
                    font-size="11"
                >
                    ${escapeXML(language)}
                </text>


                <text
                    x="${x + 230}"
                    y="${y + 102}"
                    fill="#8b949e"
                    font-family="Arial"
                    font-size="11"
                >
                    ★ ${repo.stargazerCount}
                </text>


                <text
                    x="${x + 330}"
                    y="${y + 102}"
                    fill="#8b949e"
                    font-family="Arial"
                    font-size="11"
                >
                    Forks ${repo.forkCount}
                </text>
            `;
        }
    );


    // ==================================================
    // TECHNOLOGIES
    // ==================================================

    const technologies = [
        "Java",
        "JavaScript",
        "Python",
        "HTML",
        "CSS",
        "Django",
        "Git",
        "GitHub",
        "SQL",
        "React",
        "Node.js",
        "VS Code"
    ];


    let technologyPills = "";


    technologies.forEach(
        (tech, index) => {

            const column =
                index % 4;


            const row =
                Math.floor(index / 4);


            const x =
                70 + column * 310;


            const y =
                1780 + row * 58;


            technologyPills += `

                <rect
                    x="${x}"
                    y="${y}"
                    width="275"
                    height="40"
                    rx="9"
                    fill="#161b22"
                    stroke="#30363d"
                />


                <text
                    x="${x + 20}"
                    y="${y + 26}"
                    fill="#f0f6fc"
                    font-family="Arial"
                    font-size="13"
                >
                    ${tech}
                </text>
            `;
        }
    );


    // ==================================================
    // SVG DOCUMENT
    // ==================================================

    return `

<svg
    xmlns="http://www.w3.org/2000/svg"
    width="1400"
    height="2050"
    viewBox="0 0 1400 2050"
>


    <!-- BACKGROUND -->

    <rect
        width="1400"
        height="2050"
        fill="#0d1117"
    />


    <!-- OUTER BORDER -->

    <rect
        x="20"
        y="20"
        width="1360"
        height="2010"
        rx="18"
        fill="none"
        stroke="#30363d"
    />


    <!-- ============================================ -->
    <!-- HEADER -->
    <!-- ============================================ -->

    <text
        x="70"
        y="75"
        fill="#58a6ff"
        font-family="Arial"
        font-size="13"
        font-weight="bold"
    >
        GITHUB / DEVELOPER DASHBOARD
    </text>


    <text
        x="70"
        y="125"
        fill="#f0f6fc"
        font-family="Arial"
        font-size="32"
        font-weight="bold"
    >
        Hi, I'm ${escapeXML(
            user.name || user.login
        )} 👋
    </text>


    <text
        x="70"
        y="155"
        fill="#8b949e"
        font-family="Arial"
        font-size="14"
    >
        ${escapeXML(
            user.bio ||
            "Developer • Programmer • Open Source Enthusiast"
        )}
    </text>


    <text
        x="70"
        y="182"
        fill="#8b949e"
        font-family="Arial"
        font-size="12"
    >
        @${escapeXML(user.login)}
        ${user.location
            ? " • " + escapeXML(user.location)
            : ""}
    </text>


    <!-- ============================================ -->
    <!-- STAT CARDS -->
    <!-- ============================================ -->

    <rect
        x="50"
        y="220"
        width="1300"
        height="125"
        rx="18"
        fill="#161b22"
        stroke="#30363d"
    />


    <!-- REPOSITORIES -->

    <rect
        x="70"
        y="242"
        width="235"
        height="80"
        rx="11"
        fill="#0d1117"
        stroke="#30363d"
    />

    <text
        x="90"
        y="268"
        fill="#8b949e"
        font-family="Arial"
        font-size="11"
    >
        PUBLIC REPOSITORIES
    </text>

    <text
        x="90"
        y="300"
        fill="#f0f6fc"
        font-family="Arial"
        font-size="25"
        font-weight="bold"
    >
        ${formatNumber(
            user.repositories.totalCount
        )}
    </text>


    <!-- CONTRIBUTIONS -->

    <rect
        x="325"
        y="242"
        width="235"
        height="80"
        rx="11"
        fill="#0d1117"
        stroke="#30363d"
    />

    <text
        x="345"
        y="268"
        fill="#8b949e"
        font-family="Arial"
        font-size="11"
    >
        CONTRIBUTIONS
    </text>

    <text
        x="345"
        y="300"
        fill="#3fb950"
        font-family="Arial"
        font-size="25"
        font-weight="bold"
    >
        ${formatNumber(totalContributions)}
    </text>


    <!-- COMMITS -->

    <rect
        x="580"
        y="242"
        width="235"
        height="80"
        rx="11"
        fill="#0d1117"
        stroke="#30363d"
    />

    <text
        x="600"
        y="268"
        fill="#8b949e"
        font-family="Arial"
        font-size="11"
    >
        COMMITS
    </text>

    <text
        x="600"
        y="300"
        fill="#58a6ff"
        font-family="Arial"
        font-size="25"
        font-weight="bold"
    >
        ${formatNumber(
            contributions.totalCommitContributions
        )}
    </text>


    <!-- PR -->

    <rect
        x="835"
        y="242"
        width="235"
        height="80"
        rx="11"
        fill="#0d1117"
        stroke="#30363d"
    />

    <text
        x="855"
        y="268"
        fill="#8b949e"
        font-family="Arial"
        font-size="11"
    >
        PULL REQUESTS
    </text>

    <text
        x="855"
        y="300"
        fill="#d2a8ff"
        font-family="Arial"
        font-size="25"
        font-weight="bold"
    >
        ${formatNumber(
            contributions.totalPullRequestContributions
        )}
    </text>


    <!-- ISSUES -->

    <rect
        x="1090"
        y="242"
        width="235"
        height="80"
        rx="11"
        fill="#0d1117"
        stroke="#30363d"
    />

    <text
        x="1110"
        y="268"
        fill="#8b949e"
        font-family="Arial"
        font-size="11"
    >
        ISSUES
    </text>

    <text
        x="1110"
        y="300"
        fill="#f0883e"
        font-family="Arial"
        font-size="25"
        font-weight="bold"
    >
        ${formatNumber(
            contributions.totalIssueContributions
        )}
    </text>


    <!-- ============================================ -->
    <!-- CONTRIBUTION GRAPH -->
    <!-- ============================================ -->

    <rect
        x="50"
        y="370"
        width="1300"
        height="285"
        rx="18"
        fill="#161b22"
        stroke="#30363d"
    />


    <text
        x="70"
        y="405"
        fill="#f0f6fc"
        font-family="Arial"
        font-size="19"
        font-weight="bold"
    >
        Contributions
    </text>


    <text
        x="70"
        y="430"
        fill="#8b949e"
        font-family="Arial"
        font-size="11"
    >
        ${formatNumber(totalContributions)}
        contributions in the last year
    </text>


    <rect
        x="55"
        y="445"
        width="1290"
        height="180"
        rx="12"
        fill="#0d1117"
        stroke="#30363d"
    />


    ${contributionGrid}


    <!-- LEGEND -->

    <text
        x="70"
        y="640"
        fill="#8b949e"
        font-family="Arial"
        font-size="10"
    >
        Less
    </text>


    <rect x="110" y="630"
        width="13"
        height="13"
        rx="3"
        fill="#161b22"/>

    <rect x="130" y="630"
        width="13"
        height="13"
        rx="3"
        fill="#0e4429"/>

    <rect x="150" y="630"
        width="13"
        height="13"
        rx="3"
        fill="#006d32"/>

    <rect x="170" y="630"
        width="13"
        height="13"
        rx="3"
        fill="#26a641"/>

    <rect x="190" y="630"
        width="13"
        height="13"
        rx="3"
        fill="#39d353"/>


    <text
        x="215"
        y="640"
        fill="#8b949e"
        font-family="Arial"
        font-size="10"
    >
        More
    </text>


    <!-- ============================================ -->
    <!-- CODING ACTIVITY -->
    <!-- ============================================ -->

    <rect
        x="50"
        y="680"
        width="820"
        height="330"
        rx="18"
        fill="#161b22"
        stroke="#30363d"
    />


    <text
        x="75"
        y="720"
        fill="#f0f6fc"
        font-family="Arial"
        font-size="19"
        font-weight="bold"
    >
        Coding Activity
    </text>


    <text
        x="75"
        y="745"
        fill="#8b949e"
        font-family="Arial"
        font-size="11"
    >
        Weekly GitHub contribution activity
    </text>


    <line
        x1="70"
        y1="760"
        x2="830"
        y2="760"
        stroke="#30363d"
    />


    ${activityBars}


    <text
        x="75"
        y="790"
        fill="#8b949e"
        font-family="Arial"
        font-size="10"
    >
        Older
    </text>


    <text
        x="785"
        y="790"
        fill="#8b949e"
        font-family="Arial"
        font-size="10"
    >
        Recent
    </text>


    <!-- ============================================ -->
    <!-- STREAK -->
    <!-- ============================================ -->

    <rect
        x="890"
        y="680"
        width="460"
        height="330"
        rx="18"
        fill="#161b22"
        stroke="#30363d"
    />


    <text
        x="915"
        y="720"
        fill="#f0f6fc"
        font-family="Arial"
        font-size="19"
        font-weight="bold"
    >
        Coding Streak 🔥
    </text>


    <text
        x="915"
        y="770"
        fill="#8b949e"
        font-family="Arial"
        font-size="12"
    >
        CURRENT STREAK
    </text>


    <text
        x="915"
        y="810"
        fill="#3fb950"
        font-family="Arial"
        font-size="32"
        font-weight="bold"
    >
        ${streak.current} days
    </text>


    <line
        x1="915"
        y1="835"
        x2="1320"
        y2="835"
        stroke="#30363d"
    />


    <text
        x="915"
        y="875"
        fill="#8b949e"
        font-family="Arial"
        font-size="12"
    >
        LONGEST STREAK
    </text>


    <text
        x="915"
        y="915"
        fill="#58a6ff"
        font-family="Arial"
        font-size="32"
        font-weight="bold"
    >
        ${streak.longest} days
    </text>


    <!-- ============================================ -->
    <!-- LANGUAGES -->
    <!-- ============================================ -->

    <rect
        x="50"
        y="1040"
        width="650"
        height="410"
        rx="18"
        fill="#161b22"
        stroke="#30363d"
    />


    <text
        x="75"
        y="1080"
        fill="#f0f6fc"
        font-family="Arial"
        font-size="19"
        font-weight="bold"
    >
        Most Used Languages
    </text>


    <text
        x="75"
        y="1105"
        fill="#8b949e"
        font-family="Arial"
        font-size="11"
    >
        Based on your public repositories
    </text>


    ${languageRows}


    <!-- ============================================ -->
    <!-- PROFILE -->
    <!-- ============================================ -->

    <rect
        x="730"
        y="1040"
        width="620"
        height="410"
        rx="18"
        fill="#161b22"
        stroke="#30363d"
    />


    <text
        x="755"
        y="1080"
        fill="#f0f6fc"
        font-family="Arial"
        font-size="19"
        font-weight="bold"
    >
        Developer Profile
    </text>


    <text
        x="755"
        y="1120"
        fill="#58a6ff"
        font-family="Arial"
        font-size="14"
    >
        @${escapeXML(user.login)}
    </text>


    <text
        x="755"
        y="1160"
        fill="#8b949e"
        font-family="Arial"
        font-size="12"
    >
        Followers
    </text>


    <text
        x="755"
        y="1190"
        fill="#f0f6fc"
        font-family="Arial"
        font-size="24"
        font-weight="bold"
    >
        ${formatNumber(
            user.followers.totalCount
        )}
    </text>


    <text
        x="950"
        y="1160"
        fill="#8b949e"
        font-family="Arial"
        font-size="12"
    >
        Following
    </text>


    <text
        x="950"
        y="1190"
        fill="#f0f6fc"
        font-family="Arial"
        font-size="24"
        font-weight="bold"
    >
        ${formatNumber(
            user.following.totalCount
        )}
    </text>


    <text
        x="755"
        y="1240"
        fill="#8b949e"
        font-family="Arial"
        font-size="12"
    >
        Location
    </text>


    <text
        x="755"
        y="1270"
        fill="#f0f6fc"
        font-family="Arial"
        font-size="13"
    >
        ${escapeXML(
            user.location || "Not specified"
        )}
    </text>


    <text
        x="755"
        y="1320"
        fill="#8b949e"
        font-family="Arial"
        font-size="12"
    >
        About
    </text>


    <text
        x="755"
        y="1350"
        fill="#f0f6fc"
        font-family="Arial"
        font-size="13"
    >
        ${escapeXML(
            shortText(
                user.bio ||
                "Developer and open-source enthusiast",
                70
            )
        )}
    </text>


    <!-- ============================================ -->
    <!-- TOP REPOSITORIES -->
    <!-- ============================================ -->

    <text
        x="50"
        y="1500"
        fill="#f0f6fc"
        font-family="Arial"
        font-size="21"
        font-weight="bold"
    >
        Top Repositories ⭐
    </text>


    <text
        x="50"
        y="1525"
        fill="#8b949e"
        font-family="Arial"
        font-size="11"
    >
        Your most starred public repositories
    </text>


    ${repositoryCards}


    <!-- ============================================ -->
    <!-- TECHNOLOGIES -->
    <!-- ============================================ -->

    <text
        x="50"
        y="1740"
        fill="#f0f6fc"
        font-family="Arial"
        font-size="21"
        font-weight="bold"
    >
        Technologies &amp; Tools
    </text>


    ${technologyPills}


    <!-- ============================================ -->
    <!-- FOOTER -->
    <!-- ============================================ -->

    <line
        x1="50"
        y1="1980"
        x2="1350"
        y2="1980"
        stroke="#30363d"
    />


    <text
        x="700"
        y="2010"
        text-anchor="middle"
        fill="#8b949e"
        font-family="Arial"
        font-size="11"
    >
        Generated automatically from GitHub •
        Last updated ${new Date().toISOString().split("T")[0]}
    </text>


</svg>
`;
}


// ======================================================
// MAIN
// ======================================================

async function main() {

    console.log(
        `Generating dashboard for @${USERNAME}...`
    );


    const user =
        await getUser();


    console.log(
        `Found ${user.repositories.totalCount} repositories`
    );


    const svg =
        createSVG(user);


    const output =
        "assets/github-dashboard.svg";


    fs.writeFileSync(
        output,
        svg,
        "utf8"
    );


    console.log(
        `Dashboard generated: ${output}`
    );
}


main().catch(error => {

    console.error(
        "Dashboard generation failed:"
    );

    console.error(error);

    process.exit(1);
});
