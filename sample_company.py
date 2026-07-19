"""
sample_company.py -- Generates a sample 5-year projection model for a
fictitious Brazilian PME, for use as demo input to dcf_model.py.

Usage:
    python sample_company.py
"""

import pandas as pd

PERIODS = ["2026E", "2027E", "2028E", "2029E", "2030E"]

REVENUE_GROWTH = 0.08
EBITDA_MARGIN = 0.18
DA_PCT_REVENUE = 0.03
CAPEX_PCT_REVENUE = 0.04
NWC_PCT_REVENUE_GROWTH = 0.15  # change in NWC as a share of the revenue increase
TAX_RATE = 0.34  # IRPJ + CSLL combined, Brazil
REVENUE_0 = 10000.0  # R$ thousands, last actual year before the forecast


def build_sample() -> pd.DataFrame:
    data = {"Revenue": {}, "EBITDA": {}, "D&A": {}, "Capex": {}, "Change in NWC": {}, "Tax Rate": {}}
    prev_revenue = REVENUE_0
    revenue = REVENUE_0
    for period in PERIODS:
        revenue = revenue * (1 + REVENUE_GROWTH)
        ebitda = revenue * EBITDA_MARGIN
        da = revenue * DA_PCT_REVENUE
        capex = revenue * CAPEX_PCT_REVENUE
        change_nwc = (revenue - prev_revenue) * NWC_PCT_REVENUE_GROWTH

        data["Revenue"][period] = round(revenue, 1)
        data["EBITDA"][period] = round(ebitda, 1)
        data["D&A"][period] = round(da, 1)
        data["Capex"][period] = round(capex, 1)
        data["Change in NWC"][period] = round(change_nwc, 1)
        data["Tax Rate"][period] = TAX_RATE

        prev_revenue = revenue

    df = pd.DataFrame(data).T
    df.index.name = "Line Item"
    return df


if __name__ == "__main__":
    df = build_sample()
    df.to_excel("sample_company.xlsx")
    print("Generated sample_company.xlsx\n")
    print(df.to_string(float_format=lambda x: f"{x:,.2f}"))
