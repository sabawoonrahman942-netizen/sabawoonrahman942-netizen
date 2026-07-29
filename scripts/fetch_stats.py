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


def rest_get(path, params=None):
    r = requests.get(f"{REST_URL}{path}", headers=HEADERS, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


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
            createdAt
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


def fetch_issues_closed():
    """REST search API: sadece kullanicinin actigi ve kapanmis issue sayisi."""
    try:
        data = rest_get("/search/issues", {"q": f"author:{USERNAME}+type:issue+state:closed"})
        return data.get("total_count", 0)
    except Exception:
        return 0


def fetch_contributors_count(repos, limit=6):
    """En cok yildizli ilk N reponun benzersiz katkicilarini toplar (API maliyetini sinirlamak icin)."""
    top = sorted(repos, key=lambda r: r["stargazerCount"], reverse=True)[:limit]
    seen = set()
    for r in top:
        try:
            contributors = rest_get(f"/repos/{USERNAME}/{r['name']}/contributors", {"per_page": 100})
            for c in contributors:
                if isinstance(c, dict) and c.get("login"):
                    seen.add(c["login"])
        except Exception:
            continue
    return max(len(seen), 1)


MONTH_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def stars_last_12_months(repos):
    """Son 12 ay icin kumulatif yildiz tahmini (repo olusturulma tarihine gore agirlikli).
    GitHub'da gercek 'star history' endpoint'i olmadigi icin bu bir yaklasimdir;
    toplam yildiz sayisi gercek ve dogrudur, aylik dagilim yaklasiktir."""
    now = datetime.datetime.utcnow()
    months = []
    for i in range(11, -1, -1):
        idx = now.month - i
        y = now.year + (idx - 1) // 12
        m = (idx - 1) % 12 + 1
        months.append((y, m))
    buckets = {f"{y}-{m:02d}": 0 for y, m in months}
    for r in sorted(repos, key=lambda r: r["createdAt"]):
        created = r["createdAt"][:7]
        if created in buckets:
            buckets[created] += r["stargazerCount"]
    running, values = 0, []
    for y, m in months:
        running += buckets[f"{y}-{m:02d}"]
        values.append(running)
    real_total = sum(r["stargazerCount"] for r in repos)
    if values and values[-1] < real_total:
        values[-1] = real_total
    labels = [MONTH_ABBR[m - 1] for _, m in months]
    return values, labels


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

    issues_closed = fetch_issues_closed()
    contributors = fetch_contributors_count(repos)
    stars_monthly, stars_month_labels = stars_last_12_months(repos)

    data = {
        "username": user["login"],
        "name": user.get("name") or user["login"],
        "generated_at": datetime.datetime.utcnow().strftime("%b %d, %Y %H:%M UTC"),
        "stats": {
            "total_repos": user["repositories"]["totalCount"],
            "total_stars": total_stars,
            "total_commits": user["contributionsCollection"]["totalCommitContributions"],
            "total_prs": user["contributionsCollection"]["totalPullRequestContributions"],
            "followers": user["followers"]["totalCount"],
            "following": user["following"]["totalCount"],
            "issues_closed": issues_closed,
            "contributors": contributors,
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
        "stars_monthly": stars_monthly,
        "stars_month_labels": stars_month_labels,
    }

    out_path = os.path.join(os.path.dirname(__file__), "..", "data.json")
    with open(out_path, "w") as f:
        json.dump(data, f, indent=2)

    print("Wrote data.json")


if __name__ == "__main__":
    main()
