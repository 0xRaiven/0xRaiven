"""GitHub GraphQL/Search API client and developer metrics/rank calculator."""

import datetime
import json
import urllib.request


def exp_cdf(x, median):
    return 1 - (2 ** (-(max(0, x) / max(1, median))))


def calculate_rank(commits, prs, issues, repos):
    """
    Compute global developer rank (S, A+, A, A-, B+, etc.) using CDF distributions,
    excluding total stars earned and weighted for systems/tooling engineers.
    """
    c_score = exp_cdf(commits, 200)
    p_score = exp_cdf(prs, 10)
    i_score = exp_cdf(issues, 8)
    r_score = exp_cdf(repos, 3)

    score = (5.0 * c_score + 2.0 * r_score + 2.0 * p_score + 1.0 * i_score) / 10.0
    percentile = (1.0 - score) * 100

    if percentile <= 5.0:
        rank = "S"
    elif percentile <= 15.0:
        rank = "A+"
    elif percentile <= 28.0:
        rank = "A"
    elif percentile <= 42.0:
        rank = "A-"
    elif percentile <= 58.0:
        rank = "B+"
    elif percentile <= 72.0:
        rank = "B"
    elif percentile <= 85.0:
        rank = "B-"
    else:
        rank = "C"

    return rank, score, percentile


def fetch_github_data(token, username):
    """Fetch contribution calendar, commits, PRs, issues, and contributed repos from GitHub."""
    headers = {
        "Authorization": f"bearer {token}",
        "User-Agent": "0xraiven-Contribution-Builder",
        "Content-Type": "application/json",
        "Accept": "application/vnd.github+json",
    }

    query = f"""
    query {{
      user(login: "{username}") {{
        contributionsCollection {{
          totalCommitContributions
          restrictedContributionsCount
          totalPullRequestContributions
          totalIssueContributions
          totalRepositoryContributions
          totalPullRequestReviewContributions
          contributionCalendar {{
            totalContributions
            weeks {{
              contributionDays {{
                date
                contributionCount
                weekday
              }}
            }}
          }}
        }}
        repositoriesContributedTo(contributionTypes: [COMMIT, ISSUE, PULL_REQUEST, REPOSITORY]) {{
          totalCount
        }}
        repositories(ownerAffiliations: OWNER) {{
          totalCount
        }}
      }}
      prs: search(query: "type:pr author:{username}", type: ISSUE) {{
        issueCount
      }}
      issues: search(query: "type:issue author:{username}", type: ISSUE) {{
        issueCount
      }}
    }}
    """
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query}).encode("utf-8"),
        headers=headers,
    )

    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    u = data.get("data", {}).get("user", {})
    cc = u.get("contributionsCollection", {})
    cal = cc.get("contributionCalendar", {})

    cal_total = cal.get("totalContributions", 0)
    commit_contributions = cc.get("totalCommitContributions", 0) + cc.get("restrictedContributionsCount", 0)

    all_time_commits = 0
    try:
        search_commit_url = f"https://api.github.com/search/commits?q=author:{username}"
        req_commits = urllib.request.Request(
            search_commit_url,
            headers={**headers, "Accept": "application/vnd.github.cloak-preview+json"},
        )
        with urllib.request.urlopen(req_commits, timeout=10) as c_resp:
            c_data = json.loads(c_resp.read().decode("utf-8"))
            all_time_commits = c_data.get("total_count", 0)
    except Exception as e:
        print(f"Commit search fallback: {e}")

    commits = max(all_time_commits, commit_contributions, cal_total)
    prs = max(data.get("data", {}).get("prs", {}).get("issueCount", 0), cc.get("totalPullRequestContributions", 0))
    issues = max(data.get("data", {}).get("issues", {}).get("issueCount", 0), cc.get("totalIssueContributions", 0))

    repos = max(
        u.get("repositoriesContributedTo", {}).get("totalCount", 0),
        u.get("repositories", {}).get("totalCount", 0),
        cc.get("totalRepositoryContributions", 0),
    )

    return {
        "calendar": cal,
        "commits": commits,
        "prs": prs,
        "issues": issues,
        "repos": repos,
        "reviews": cc.get("totalPullRequestReviewContributions", 0),
    }


def calculate_stats(calendar, raw_metrics):
    """Derive streaks, weekly totals, best day, daily average, and developer rank."""
    total = calendar.get("totalContributions", 0)
    weeks = calendar.get("weeks", [])
    all_days = [d for w in weeks for d in w["contributionDays"]]

    this_week_count = sum(d["contributionCount"] for d in weeks[-1]["contributionDays"])
    start_this_week = datetime.datetime.strptime(weeks[-1]["contributionDays"][0]["date"], "%Y-%m-%d").strftime("%b %d")
    end_this_week = datetime.datetime.strptime(weeks[-1]["contributionDays"][-1]["date"], "%Y-%m-%d").strftime("%b %d")

    start_dt = datetime.datetime.strptime(all_days[0]["date"], "%Y-%m-%d")
    end_dt = datetime.datetime.strptime(all_days[-1]["date"], "%Y-%m-%d")
    total_range = f"{start_dt.strftime('%b %Y')} \u2192 {end_dt.strftime('%b %Y')}"

    best_day_count = 0
    best_day_date = ""
    for d in all_days:
        if d["contributionCount"] > best_day_count:
            best_day_count = d["contributionCount"]
            best_day_date = datetime.datetime.strptime(d["date"], "%Y-%m-%d").strftime("%b %d")

    avg = total / max(1, len(all_days))

    longest_streak = 0
    longest_streak_start = None
    longest_streak_end = None
    streak = 0
    s_start = None

    for d in all_days:
        if d["contributionCount"] > 0:
            if streak == 0:
                s_start = d["date"]
            streak += 1
            if streak > longest_streak:
                longest_streak = streak
                longest_streak_start = s_start
                longest_streak_end = d["date"]
        else:
            streak = 0
            s_start = None

    rev_days = list(reversed(all_days))
    idx = 0
    while idx < len(rev_days) and rev_days[idx]["contributionCount"] == 0 and idx < 2:
        idx += 1

    current_streak = 0
    c_start = None
    c_end = None
    while idx < len(rev_days) and rev_days[idx]["contributionCount"] > 0:
        if c_end is None:
            c_end = rev_days[idx]["date"]
        c_start = rev_days[idx]["date"]
        current_streak += 1
        idx += 1

    if longest_streak_start and longest_streak_end:
        l_s = datetime.datetime.strptime(longest_streak_start, "%Y-%m-%d").strftime("%b %d")
        l_e = datetime.datetime.strptime(longest_streak_end, "%Y-%m-%d").strftime("%b %d")
        longest_range = f"{l_s} \u2192 {l_e}"
    else:
        longest_range = "--"

    if c_start and c_end:
        c_s = datetime.datetime.strptime(c_start, "%Y-%m-%d").strftime("%b %d")
        c_e = datetime.datetime.strptime(c_end, "%Y-%m-%d").strftime("%b %d")
        curr_range = f"{c_s} \u2192 {c_e}"
    else:
        curr_range = "--"

    commits = raw_metrics.get("commits") or total
    prs = raw_metrics.get("prs", 0)
    issues = raw_metrics.get("issues", 0)
    repos = raw_metrics.get("repos", 0)
    rank, score, pct = calculate_rank(commits, prs, issues, repos)

    return {
        "total": total,
        "total_range": total_range,
        "this_week": this_week_count,
        "this_week_range": f"{start_this_week} \u2192 {end_this_week}",
        "best_day": best_day_count,
        "best_day_date": best_day_date or "--",
        "average": avg,
        "longest_streak": longest_streak,
        "longest_range": longest_range,
        "current_streak": current_streak,
        "curr_range": curr_range,
        "commits": commits,
        "prs": prs,
        "issues": issues,
        "repos": repos,
        "rank": rank,
        "rank_score": score,
        "rank_pct": pct,
    }
