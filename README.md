# Parametrized DCF

Discounted cash flow valuation with parametrizable assumptions -- built to plug into the same due diligence pipeline as [`Financial-Model-Validator`](https://github.com/lucanap98/Financial-Model-Validator) and [`Financial-Analysis`](https://github.com/lucanap98/Financial-Analysis).

Takes a set of financial projections (Revenue, EBITDA, D&A, Capex, Change in NWC, Tax Rate), computes unlevered free cash flow, discounts it at a user-supplied WACC, and estimates a terminal value using either the Gordon growth model or an exit multiple. Outputs an enterprise value / equity value bridge and a two-way sensitivity table.

## Why parametrized

Every DCF lives or dies on its assumptions, not its arithmetic. Rather than hardcoding a WACC-building process (CAPM inputs, beta lookups) this tool takes WACC and terminal growth as direct parameters -- the analyst supplies the judgment, the tool handles the mechanics and, critically, the sensitivity around them. Building WACC from first principles (CAPM) is a natural v2 addition, tracked in the roadmap below.

## Quick demo

```bash
pip install pandas openpyxl
python sample_company.py                              # generates a 5-year sample model
python dcf_model.py sample_company.xlsx --wacc 0.13 --terminal-growth 0.04 --net-debt 1500 --detail
```

Output:

```
============================================================================================
DISCOUNTED CASH FLOW VALUATION
============================================================================================
Period         Revenue      EBITDA        EBIT       NOPAT         FCF     PV(FCF)
2026E           10,800       1,944       1,620       1,069         841         744
2027E           11,664       2,100       1,750       1,155         908         711
2028E           12,597       2,268       1,890       1,247         981         680
2029E           13,605       2,449       2,041       1,347       1,060         650
2030E           14,693       2,645       2,204       1,455       1,144         621
--------------------------------------------------------------------------------------------
Sum of PV(FCF), explicit period:                       3,407
Terminal value (Gordon growth):                       13,225
PV of terminal value:                                  7,178
--------------------------------------------------------------------------------------------
Enterprise value:                                     10,585
(-) Net debt:                                          1,500
Equity value:                                          9,085
--------------------------------------------------------------------------------------------
Implied EV/EBITDA (last explicit year): 4.0x
Terminal value as % of enterprise value: 68%
============================================================================================

Sensitivity -- enterprise value (WACC x terminal growth):

        3.0%   3.5%   4.0%   4.5%   5.0%
WACC
11.0% 12,334 12,962 13,680 14,509 15,475
12.0% 10,928 11,404 11,938 12,545 13,237
13.0%  9,805 10,174 10,585 11,043 11,560
14.0%  8,887  9,180  9,503  9,859 10,255
15.0%  8,122  8,359  8,618  8,901  9,213
```

Terminal value is 68% of enterprise value here -- typical for a 5-year explicit period, and worth flagging to a reader: most of the valuation rests on the perpetuity assumption, not the forecast.

## Exit multiple instead of Gordon growth

```bash
python dcf_model.py sample_company.xlsx --wacc 0.13 --terminal-method exit_multiple --exit-multiple 7.5 --net-debt 1500
```

Swaps the terminal value calculation to `last EBITDA x multiple`, and the sensitivity table to WACC x exit multiple instead of WACC x terminal growth. Useful when a comparable transaction multiple is more defensible than a perpetuity growth assumption -- which is exactly the kind of check the comps checker (next in this portfolio) will exist to support.

## Using it on your own model

Input format: Excel or CSV where the **first column contains line item names** and the remaining columns are periods (`2026E`, `2027E`, ...) -- same convention as `Financial-Model-Validator`, intentionally, so both tools can eventually share one input file inside the platform (Track 2 of the [portfolio roadmap](https://github.com/lucanap98)).

Required line items: `Revenue`, `EBITDA`, `D&A`, `Capex`, `Change in NWC`, `Tax Rate`. If your model uses different labels (e.g. Portuguese), map them via `aliases`:

```python
from dcf_model import load_model, run_dcf

df = load_model("modelo.xlsx", aliases={
    "Receita Liquida": "Revenue",
    "Impostos": "Tax Rate",
})
result = run_dcf(df, wacc=0.13, terminal_growth=0.04, net_debt=1500)
result.print_summary()
```

`Tax Rate` accepts either a decimal (`0.34`) or a percentage (`34`) -- normalized automatically.

## Design notes

- **Fails fast, not gracefully.** Unlike `Financial-Model-Validator`, which degrades gracefully around missing inputs (it is a QC tool -- partial checks are still useful), this is a valuation engine: a DCF built on incomplete inputs isn't a smaller DCF, it's a wrong one. Missing line items or an invalid WACC/growth combination (WACC <= terminal growth) raise a clear error and exit immediately.
- **Conservative on negative EBIT.** No tax benefit is assumed when EBIT is negative in a given period -- avoids overstating FCF in a loss-making explicit year.
- **Change in NWC sign convention is fixed, not agnostic.** Positive = cash use (working capital grew). This is a deliberate simplification versus the validator's sign-agnostic checks; documented here rather than auto-detected, since a DCF is not the place to guess.
- **Terminal value is always shown as a % of enterprise value.** A DCF where 90% of the value sits in the terminal value is not wrong, but it should never be silently reported as pure output -- the diagnostic ships in the same call as the valuation.

## Roadmap

- [ ] Build WACC from CAPM inputs (risk-free rate, beta, market risk premium, cost of debt, tax shield) instead of taking it as a direct parameter
- [ ] Mid-year discounting convention (currently end-of-year)
- [ ] Multi-scenario mode (bear / base / bull cases in one run)
- [ ] Excel export of the full period-by-period build and sensitivity table

## About

Built by [Luca Rivitti](https://www.linkedin.com/) -- Valuation & Transaction Advisory @ Grant Thornton Brasil. Third module in a series translating transaction advisory workflows into Python. Together with [`Financial-Model-Validator`](https://github.com/lucanap98/Financial-Model-Validator) and the upcoming EBITDA normalizer and red flags detector, this forms the core of a systematic due diligence pipeline for small and mid-sized Brazilian companies (PMEs).
