#!/usr/bin/env python3
"""
Polymarket NBA Markets Scraper
Fetches and lists all active Polymarket prediction markets related to NBA.
"""

import requests
import json
from datetime import datetime


GAMMA_API_BASE = "https://gamma-api.polymarket.com"


def fetch_nba_markets():
    """Fetch NBA-related markets from Polymarket's Gamma API."""
    markets = []
    offset = 0
    limit = 100

    print("Fetching NBA markets from Polymarket...\n")

    while True:
        params = {
            "limit": limit,
            "offset": offset,
            "active": "true",
            "closed": "false",
            "tag_slug": "nba",
        }

        response = requests.get(
            f"{GAMMA_API_BASE}/markets",
            params=params,
            timeout=15,
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()
        data = response.json()

        if not data:
            break

        markets.extend(data)

        if len(data) < limit:
            break

        offset += limit

    return markets


def fetch_nba_markets_keyword():
    """Fallback: search markets by NBA keyword in question text."""
    markets = []
    offset = 0
    limit = 100

    while True:
        params = {
            "limit": limit,
            "offset": offset,
            "_c": "question",
            "question_slug": "nba",
        }

        response = requests.get(
            f"{GAMMA_API_BASE}/markets",
            params=params,
            timeout=15,
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()
        data = response.json()

        if not data:
            break

        # Filter by NBA in question text
        nba_markets = [
            m for m in data
            if "nba" in m.get("question", "").lower()
            or "nba" in m.get("description", "").lower()
        ]
        markets.extend(nba_markets)

        if len(data) < limit:
            break

        offset += limit

    return markets


def fetch_all_nba_markets():
    """Fetch NBA markets using multiple strategies."""
    all_markets = {}

    # Strategy 1: tag-based search
    try:
        tag_markets = fetch_nba_markets()
        for m in tag_markets:
            all_markets[m["id"]] = m
        print(f"Found {len(tag_markets)} markets via NBA tag")
    except Exception as e:
        print(f"Tag search failed: {e}")

    # Strategy 2: keyword search as fallback/supplement
    try:
        params = {
            "limit": 200,
            "active": "true",
            "closed": "false",
        }
        response = requests.get(
            f"{GAMMA_API_BASE}/markets",
            params=params,
            timeout=15,
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()
        data = response.json()

        keyword_markets = [
            m for m in data
            if "nba" in m.get("question", "").lower()
            or "nba" in m.get("groupItemTitle", "").lower()
        ]
        for m in keyword_markets:
            all_markets[m["id"]] = m
        print(f"Found {len(keyword_markets)} additional markets via keyword search")
    except Exception as e:
        print(f"Keyword search failed: {e}")

    return list(all_markets.values())


def format_market(market, index):
    """Format a single market for display."""
    question = market.get("question", "N/A")
    end_date = market.get("endDate", "N/A")
    volume = market.get("volume", 0)
    liquidity = market.get("liquidity", 0)
    active = market.get("active", False)
    closed = market.get("closed", False)
    url = market.get("url", "")
    market_id = market.get("id", "N/A")

    # Format end date
    if end_date and end_date != "N/A":
        try:
            dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
            end_date = dt.strftime("%Y-%m-%d %H:%M UTC")
        except Exception:
            pass

    # Format volume/liquidity
    try:
        volume_str = f"${float(volume):,.0f}"
    except (ValueError, TypeError):
        volume_str = "N/A"

    try:
        liquidity_str = f"${float(liquidity):,.0f}"
    except (ValueError, TypeError):
        liquidity_str = "N/A"

    status = "Active" if active and not closed else ("Closed" if closed else "Inactive")

    # Get outcomes/options
    outcomes = market.get("outcomes", "[]")
    if isinstance(outcomes, str):
        try:
            outcomes = json.loads(outcomes)
        except Exception:
            outcomes = []

    lines = [
        f"\n{'='*70}",
        f"#{index}  {question}",
        f"{'='*70}",
        f"  Status:    {status}",
        f"  Ends:      {end_date}",
        f"  Volume:    {volume_str}",
        f"  Liquidity: {liquidity_str}",
    ]

    if outcomes:
        lines.append(f"  Options:   {', '.join(str(o) for o in outcomes[:6])}"
                     + (" ..." if len(outcomes) > 6 else ""))

    if url:
        lines.append(f"  URL:       https://polymarket.com{url}" if not url.startswith("http") else f"  URL:       {url}")

    return "\n".join(lines)


def main():
    try:
        markets = fetch_all_nba_markets()
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to Polymarket API. Check your internet connection.")
        return
    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error: {e}")
        return

    if not markets:
        print("\nNo NBA-related markets found.")
        return

    # Sort by volume descending
    markets.sort(key=lambda m: float(m.get("volume", 0) or 0), reverse=True)

    print(f"\nFound {len(markets)} NBA-related market(s) on Polymarket:\n")

    for i, market in enumerate(markets, 1):
        print(format_market(market, i))

    print(f"\n{'='*70}")
    print(f"Total: {len(markets)} NBA markets found")
    print(f"Data fetched at: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")


if __name__ == "__main__":
    main()
