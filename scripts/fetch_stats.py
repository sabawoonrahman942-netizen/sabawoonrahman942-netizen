#!/usr/bin/env python3
"""
Fetches real, live data from the GitHub API for a given user and
writes it to data.json, which generate_svg.py then turns into the
dashboard image.

Requires GH_TOKEN. GitHub Actions supplies its short-lived repository
token; local runs should use a token authorized to read the public profile.
"""

import os
import json
import datetime
import requests

USERNAME = os.environ.get("GH_USERNAME", "sabawoonrahman942-netizen")
TOKEN = os.environ["GH_TOKEN"]

HEADERS = {"Authorization": f"Bearer {TOKEN}"}
GRAPHQL_URL = "https://api.github.com/graphql"
REST_URL = "https://api.github.com"


def gql(query, variables=None):
    r = requests.post(
        GRAPHQL_URL,
        json={"query": query, "variables": variables or {}},
        headers=HEADERS,
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    if "errors" in data:
        raise RuntimeError(data["errors"])
    return data["data"]


def rest_get(path, params=None):
    r = requests.get(f"{REST_URL}{path}", headers=HEADERS, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def get_profile_and_calendar():
    query = """
    query($login: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $login) {
        login
        name
        followers { totalCount }
        following { totalCount }
        createdAt
        repositories(first: 100, ownerAffiliations: OWNER, isFork: false,
                     orderBy: {field: STARGAZERS, direction: DESC}) {
          totalCount
          nodes {
            name
            stargazerCount
            createdAt
            primaryLanguage { name }
            languages(first: 100, orderBy: {field: SIZE, direction: DESC}) {
              edges { size node { name } }
            }
          }
        }
        pullRequests { totalCount }
        contributionsCollection(from: $from, to: $to) {
          totalCommitContributions
          totalPullRequestContributions
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays { date contributionCount }
            }
          }
        }
      }
    }
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    to_date = now.isoformat(timespec="seconds").replace("+00:00", "Z")
    from_date = (now - datetime.timedelta(days=365)).isoformat(timespec="seconds").replace("+00:00", "Z")
    result = gql(query, {"login": USERNAME, "from": from_date, "to": to_date})
    user = result.get("user")
    if user is None:
        raise RuntimeError(f"GitHub user not found: {USERNAME}")
    return user


def compute_streaks(weeks):
    days = []
    for w in weeks:
        for d in w["contributionDays"]:
            days.append((d["date"], d["contributionCount"]))
    days.sort()

    longest = 0
    running = 0
    today = datetime.date.today()

    for date_str, count in days:
        if count > 0:
            running += 1
            longest = max(longest, running)
        else:
            running = 0

    # current streak: walk backwards from most recent day
    running = 0
    for date_str, count in reversed(days):
        d = datetime.date.fromisoformat(date_str)
        if d > today:
            continue
        if d == today and count == 0 and running == 0:
            continue
        if count > 0:
            running += 1
        else:
            break
    current = running
    return current, longest


def monthly_activity(weeks):
    """Return exact contribution counts grouped into the last 12 calendar months."""
    month_start = datetime.date.today().replace(day=1)
    month_keys = []
    for _ in range(12):
        month_keys.append((month_start.year, month_start.month))
        month_start = (month_start - datetime.timedelta(days=1)).replace(day=1)
    month_keys.reverse()

    totals = {f"{year}-{month:02d}": 0 for year, month in month_keys}
    for week in weeks:
        for day in week["contributionDays"]:
            key = day["date"][:7]
            if key in totals:
                totals[key] += day["contributionCount"]

    values = [totals[f"{year}-{month:02d}"] for year, month in month_keys]
    labels = [f"{MONTH_ABBR[month - 1]} {year % 100:02d}" for year, month in month_keys]
    return values, labels


def fetch_issues_closed():
    """REST search API: sadece kullanicinin actigi ve kapanmis issue sayisi."""
    try:
        data = rest_get("/search/issues", {"q": f"author:{USERNAME}+type:issue+state:closed"})
        return data.get("total_count", 0)
    except Exception:
        return 0


MONTH_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def main():
    user = get_profile_and_calendar()
    repos = user["repositories"]["nodes"]

    total_stars = sum(r["stargazerCount"] for r in repos)

    lang_bytes = {}
    for r in repos:
        for edge in r["languages"]["edges"]:
            name = edge["node"]["name"]
            lang_bytes[name] = lang_bytes.get(name, 0) + edge["size"]

    total_bytes = sum(lang_bytes.values()) or 1
    top_langs = sorted(lang_bytes.items(), key=lambda x: -x[1])[:6]
    other_bytes = total_bytes - sum(v for _, v in top_langs)
    languages = [
        {"name": name, "pct": round(size / total_bytes * 100, 1)}
        for name, size in top_langs
    ]
    if other_bytes > 0:
        languages.append({"name": "Other", "pct": round(other_bytes / total_bytes * 100, 1)})

    weeks = user["contributionsCollection"]["contributionCalendar"]["weeks"]
    current_streak, longest_streak = compute_streaks(weeks)
    total_contribs = user["contributionsCollection"]["contributionCalendar"]["totalContributions"]
    activity_monthly, activity_month_labels = monthly_activity(weeks)

    issues_closed = fetch_issues_closed()

    data = {
        "username": user["login"],
        "name": user.get("name") or user["login"],
        "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%b %d, %Y %H:%M UTC"),
        "stats": {
            "total_repos": user["repositories"]["totalCount"],
            "total_stars": total_stars,
            "total_commits": user["contributionsCollection"]["totalCommitContributions"],
            "total_prs": user["contributionsCollection"]["totalPullRequestContributions"],
            "followers": user["followers"]["totalCount"],
            "following": user["following"]["totalCount"],
            "issues_closed": issues_closed,
        },
        "languages": languages,
        "streak": {
            "current": current_streak,
            "longest": longest_streak,
            "total_contributions": total_contribs,
            "active_year": datetime.date.today().year,
        },
        "weeks": weeks,
        "activity_monthly": activity_monthly,
        "activity_month_labels": activity_month_labels,
    }

    out_path = os.path.join(os.path.dirname(__file__), "..", "data.json")
    with open(out_path, "w") as f:
        json.dump(data, f, indent=2)

    print("Wrote data.json")


if __name__ == "__main__":
    main()
