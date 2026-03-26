#!/usr/bin/env python3
"""
Polymarket NBA Markets Scraper
Fetches NBA-related prediction markets from Polymarket's Gamma API.
Strategy:
  1. Query the /events endpoint with tag=nba for precise results.
  2. Fall back to paginated /markets scan filtered by NBA keywords.
Results are printed to the terminal and saved as a CSV file.
"""

import requests
import json
import csv
from datetime import datetime

GAMMA_API_BASE = "https://gamma-api.polymarket.com"

# All 30 NBA franchises + common shorthands so we catch team-specific markets
NBA_KEYWORDS = [
    "nba",
    # League events
    "nba finals", "nba champion", "nba playoffs", "nba draft",
    "nba mvp", "nba all-star", "nba title",
    # All 30 teams
    "atlanta hawks", "boston celtics", "brooklyn nets", "charlotte hornets",
    "chicago bulls", "cleveland cavaliers", "dallas mavericks", "denver nuggets",
    "detroit pistons", "golden state warriors", "houston rockets",
    "indiana pacers", "los angeles clippers", "los angeles lakers",
    "memphis grizzlies", "miami heat", "milwaukee bucks", "minnesota timberwolves",
    "new orleans pelicans", "new york knicks", "oklahoma city thunder",
    "orlando magic", "philadelphia 76ers", "phoenix suns",
    "portland trail blazers", "sacramento kings", "san antonio spurs",
    "toronto raptors", "utah jazz", "washington wizards",
    # Short-form team names (unambiguous)
    "lakers", "celtics", "warriors", "knicks", "nuggets", "bucks",
    "heat", "suns", "nets", "76ers", "sixers", "clippers", "rockets",
    "mavericks", "mavs", "cavaliers", "cavs", "raptors", "grizzlies",
    "pelicans", "thunder", "pacers", "hawks", "bulls", "pistons",
    "timberwolves", "t-wolves", "trail blazers", "blazers", "kings",
    "spurs", "magic", "jazz", "wizards", "hornets",
]


# ─── API helpers ──────────────────────────────────────────────────────────────

def _get(path, params):
    """GET request with a browser-like User-Agent to avoid 403s."""
    headers = {
        "Accept": "application/json",
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0 Safari/537.36"
        ),
    }
    resp = requests.get(
        f"{GAMMA_API_BASE}{path}",
        params=params,
        headers=headers,
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json()


# ─── Fetch strategies ─────────────────────────────────────────────────────────

def fetch_nba_events():
    """
    Fast path: query the /events endpoint filtered by the 'nba' tag.
    Returns a flat list of market-like dicts extracted from each event.
    """
    print("Strategy 1: Querying /events?tag=nba ...")
    markets = []
    offset = 0
    batch_size = 100

    while True:
        data = _get("/events", {
            "tag": "nba",
            "closed": "false",
            "limit": batch_size,
            "offset": offset,
        })
        if not data:
            break

        for event in data:
            for m in event.get("markets", []):
                # Attach event-level metadata if the market itself is missing it
                if not m.get("question"):
                    m["question"] = event.get("title", "")
                if not m.get("url"):
                    slug = event.get("slug", "")
                    m["url"] = f"https://polymarket.com/event/{slug}" if slug else ""
                markets.append(m)

        print(f"  Events fetched: {offset + len(data)}  |  Markets so far: {len(markets)}")

        if len(data) < batch_size:
            break
        offset += batch_size

    return markets


def fetch_all_markets_paginated():
    """
    Slow path: download every active market and filter by NBA keywords.
    Used when the tag endpoint returns nothing.
    """
    print("Strategy 2: Full paginated scan of /markets ...")
    all_markets = []
    offset = 0
    batch_size = 200

    while True:
        batch = _get("/markets", {
            "limit": batch_size,
            "offset": offset,
            "active": "true",
            "closed": "false",
        })
        if not batch:
            break

        all_markets.extend(batch)
        print(f"  Downloaded {len(all_markets)} markets so far...")

        if len(batch) < batch_size:
            break
        offset += batch_size

    return [m for m in all_markets if _is_nba(m)]


def _is_nba(market):
    """Return True if any NBA keyword appears in the market's text fields."""
    text = " ".join([
        market.get("question", ""),
        market.get("description", ""),
        market.get("groupItemTitle", ""),
    ]).lower()
    return any(kw in text for kw in NBA_KEYWORDS)


# ─── Output helpers ───────────────────────────────────────────────────────────

def _fmt_money(value):
    try:
        return f"{float(value or 0):,.0f}"
    except (ValueError, TypeError):
        return "0"


def _fmt_date(iso_str):
    if not iso_str:
        return ""
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return iso_str[:10]


def _market_url(market):
    url = market.get("url", "")
    if url and not url.startswith("http"):
        return f"https://polymarket.com{url}"
    return url


def print_markets(markets):
    """Pretty-print markets to the terminal."""
    for i, m in enumerate(markets, 1):
        question = m.get("question", "N/A")
        volume   = _fmt_money(m.get("volume", 0))
        end_date = _fmt_date(m.get("endDate", ""))
        url      = _market_url(m)
        print(f"#{i:>3}  {question}")
        print(f"       Volume: ${volume}  |  Ends: {end_date}")
        if url:
            print(f"       {url}")
        print()


def save_csv(markets, filename):
    """Save markets to a CSV file."""
    if not markets:
        return

    fieldnames = ["#", "Question", "Status", "End Date",
                  "Volume ($)", "Liquidity ($)", "Options", "URL"]

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for i, m in enumerate(markets, 1):
            active = m.get("active", False)
            closed = m.get("closed", False)
            status = "Active" if active and not closed else "Closed"

            outcomes = m.get("outcomes", "[]")
            if isinstance(outcomes, str):
                try:
                    outcomes = json.loads(outcomes)
                except Exception:
                    outcomes = []
            options = ", ".join(str(o) for o in outcomes)

            writer.writerow({
                "#": i,
                "Question":     m.get("question", "N/A"),
                "Status":       status,
                "End Date":     _fmt_date(m.get("endDate", "")),
                "Volume ($)":   _fmt_money(m.get("volume", 0)),
                "Liquidity ($)": _fmt_money(m.get("liquidity", 0)),
                "Options":      options,
                "URL":          _market_url(m),
            })

    print(f"Saved to: {filename}")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    try:
        # Try the fast tag-based approach first
        nba_markets = fetch_nba_events()

        # If the tag endpoint returned nothing, do a full scan
        if not nba_markets:
            print("Tag endpoint returned no results; falling back to full scan.")
            nba_markets = fetch_all_markets_paginated()

    except requests.exceptions.ConnectionError:
        print("Error: No internet connection.")
        return
    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error: {e}")
        return

    if not nba_markets:
        print("\nNo NBA markets found.")
        return

    # Deduplicate by market id (events endpoint may yield duplicates)
    seen = set()
    unique = []
    for m in nba_markets:
        key = m.get("id") or m.get("question", "")
        if key not in seen:
            seen.add(key)
            unique.append(m)
    nba_markets = unique

    # Sort by volume descending
    nba_markets.sort(
        key=lambda m: float(m.get("volume", 0) or 0),
        reverse=True,
    )

    print(f"\nFound {len(nba_markets)} NBA markets.\n")
    print("=" * 65)
    print_markets(nba_markets)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    filename  = f"nba_markets_{timestamp}.csv"
    save_csv(nba_markets, filename)
    print(f"\nTotal: {len(nba_markets)} NBA markets  |  CSV: {filename}")


if __name__ == "__main__":
    main()
