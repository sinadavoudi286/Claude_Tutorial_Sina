"""
SIC Code Lookup Script
Connects to WRDS (Wharton Research Data Services) and retrieves
SIC (Standard Industrial Classification) codes with their industry descriptions.

Usage:
    pip install wrds
    python sic_code_lookup.py
"""

import wrds
import pandas as pd


def get_sic_codes(username='sinadavoudi'):
    """Connect to WRDS and retrieve SIC codes with industry descriptions."""
    db = wrds.Connection(wrds_username=username)

    # Get all unique SIC codes with industry descriptions from Compustat
    sic_industries = db.raw_sql("""
        SELECT DISTINCT a.sich AS sic_code, b.sicdesc AS industry_description
        FROM comp.funda AS a
        JOIN comp.r_siccd AS b
          ON a.sich = b.siccd
        WHERE a.sich IS NOT NULL
        ORDER BY a.sich
    """)

    print(f"Total unique SIC codes found: {len(sic_industries)}")
    print(sic_industries.head(30))

    # Save to CSV
    sic_industries.to_csv('sic_code_lookup.csv', index=False)
    print("\nSaved full lookup table to sic_code_lookup.csv")

    db.close()
    return sic_industries


if __name__ == '__main__':
    df = get_sic_codes()
