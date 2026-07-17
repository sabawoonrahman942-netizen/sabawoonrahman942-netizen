#!/usr/bin/env python3
"""
Fetches real, live data from the GitHub API for a given user and
writes it to data.json, which generate_svg.py then turns into the
dashboard image.

Requires an environment variable GH_TOKEN with a token that has at
least these scopes: read:user, public_repo (repo if you want private
repos counted too).
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


def get_profile_and_calendar():
    query = """
    query($login: String!) {
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
            primaryLanguage { name }
            languages(first: 5, orderBy: {field: SIZE, direction: DESC}) {
              edges { size node { name } }
            }
          }
        }
        pullRequests { totalCount }
        contributionsCollection {
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
    return gql(query, {"login": USERNAME})["user"]


def compute_streaks(weeks):
    days = []
    for w in weeks:
        for d in w["contributionDays"]:
            days.append((d["date"], d["contributionCount"]))
    days.sort()

    longest = current = 0
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
        if count > 0:
            running += 1
        else:
            break
    current = running
    return current, longest


def monthly_totals(weeks):
    totals = [0] * 12
    for w in weeks:
        for d in w["contributionDays"]:
            month = int(d["date"][5:7]) - 1
            totals[month] += d["contributionCount"]
    return totals


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
    months = monthly_totals(weeks)

    data = {
        "username": user["login"],
        "name": user.get("name") or user["login"],
        "generated_at": datetime.datetime.utcnow().strftime("%b %d, %Y"),
        "stats": {
            "total_repos": user["repositories"]["totalCount"],
            "total_stars": total_stars,
            "total_commits": user["contributionsCollection"]["totalCommitContributions"],
            "total_prs": user["contributionsCollection"]["totalPullRequestContributions"],
            "followers": user["followers"]["totalCount"],
            "following": user["following"]["totalCount"],
        },
        "languages": languages,
        "streak": {
            "current": current_streak,
            "longest": longest_streak,
            "total_contributions": total_contribs,
            "active_year": datetime.date.today().year,
        },
        "weeks": weeks,
        "months": months,
    }

    with open(os.path.join(os.path.dirname(__file__), "..", "data.json"), "w") as f:
        json.dump(data, f, indent=2)

    print("Wrote data.json")


if __name__ == "__main__":
    main()
