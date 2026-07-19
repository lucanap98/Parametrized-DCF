"""
dcf_model.py -- Parametrized discounted cash flow valuation.

Given a set of financial projections (Revenue, EBITDA, D&A, Capex, Change in
NWC, Tax Rate) across an explicit forecast period, computes unlevered free
cash flow, discounts it at a user-supplied WACC, estimates a terminal value
(Gordon growth or exit multiple), and produces an enterprise value / equity
value bridge plus a two-way sensitivity table.

Usage:
    python dcf_model.py sample_company.xlsx --wacc 0.13 --terminal-growth 0.04 --net-debt 1500
    python dcf_model.py sample_company.xlsx --wacc 0.13 --terminal-method exit_multiple --exit-multiple 7.5 --net-debt 1500
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from typing import Optional

import pandas as pd

STANDARD_LINES = ["Revenue", "EBITDA", "D&A", "Capex", "Change in NWC", "Tax Rate"]


def load_model(path: str, aliases: Optional[dict] = None) -> pd.DataFrame:
    """Load a projection model where rows are line items and columns are periods.

    If your model uses different labels (e.g. Portuguese), map them via
    `aliases`, e.g. {"Receita Liquida": "Revenue", "Impostos": "Tax Rate"}.
    """
    lower = path.lower()
    if lower.endswith((".xlsx", ".xls")):
        df = pd.read_excel(path, index_col=0)
    elif lower.endswith(".csv"):
        df = pd.read_csv(path, index_col=0)
    else:
        raise ValueError(f"Unsupported file type: {path}. Use .xlsx, .xls or .csv.")

    if aliases:
        df = df.rename(index=aliases)

    missing = [line for line in STANDARD_LINES if line not in df.index]
    if missing:
        raise ValueError(
            "Missing required line item(s): " + ", ".join(missing) + ". "
            "Found: " + ", ".join(str(i) for i in df.index) + ". "
            "Map non-English labels via the `aliases` argument to load_model()."
        )

    df = df.loc[STANDARD_LINES].apply(pd.to_numeric)

    # Tax Rate is sometimes entered as a percentage (34) instead of a decimal
    # (0.34). Normalize so downstream math always sees a decimal.
    tax_row = df.loc["Tax Rate"]
    if (tax_row.abs() > 1).any():
        df.loc["Tax Rate"] = tax_row / 100.0

    return df


@dataclass
class PeriodResult:
    period: str
    t: int
    revenue: float
    ebitda: float
    da: float
    ebit: float
    tax_rate: float
    tax: float
    nopat: float
    capex: float
    change_nwc: float
    fcf: float
    discount_factor: float
    pv_fcf: float


def compute_periods(df: pd.DataFrame, wacc: float) -> list:
    """Build unlevered FCF for each explicit forecast period.

    FCF = NOPAT + D&A - Capex - Change in NWC
    NOPAT = EBIT * (1 - tax rate), where EBIT = EBITDA - D&A.
    No tax benefit is assumed on a negative EBIT (conservative default).
    Change in NWC follows the convention: positive = cash use (NWC grew).
    """
    results = []
    for t, period in enumerate(df.columns, start=1):
        revenue = float(df.loc["Revenue", period])
        ebitda = float(df.loc["EBITDA", period])
        da = float(df.loc["D&A", period])
        capex = float(df.loc["Capex", period])
        change_nwc = float(df.loc["Change in NWC", period])
        tax_rate = float(df.loc["Tax Rate", period])

        ebit = ebitda - da
        tax = max(ebit, 0.0) * tax_rate
        nopat = ebit - tax
        fcf = nopat + da - capex - change_nwc
        discount_factor = 1.0 / ((1.0 + wacc) ** t)
        pv_fcf = fcf * discount_factor

        results.append(PeriodResult(
            period=period, t=t, revenue=revenue, ebitda=ebitda, da=da, ebit=ebit,
            tax_rate=tax_rate, tax=tax, nopat=nopat, capex=capex,
            change_nwc=change_nwc, fcf=fcf, discount_factor=discount_factor, pv_fcf=pv_fcf,
        ))
    return results


def terminal_value_gordon(last_fcf: float, wacc: float, g: float) -> float:
    if wacc <= g:
        raise ValueError(
            f"WACC ({wacc:.1%}) must exceed terminal growth ({g:.1%}) for the "
            "Gordon growth model -- otherwise the denominator is zero or negative."
        )
    return last_fcf * (1 + g) / (wacc - g)


def terminal_value_exit_multiple(last_ebitda: float, multiple: float) -> float:
    return last_ebitda * multiple


def _pv_explicit(periods: list, wacc: float) -> float:
    return sum(p.fcf / ((1.0 + wacc) ** p.t) for p in periods)


def build_sensitivity(
    periods: list,
    wacc: float,
    terminal_method: str,
    terminal_growth: Optional[float],
    exit_multiple: Optional[float],
    wacc_step: float,
    secondary_step: float,
    n_steps: int,
) -> pd.DataFrame:
    """Two-way sensitivity of enterprise value to WACC and the terminal
    assumption (terminal growth for Gordon, exit multiple otherwise)."""
    wacc_values = [wacc + i * wacc_step for i in range(-n_steps, n_steps + 1)]
    last_period = periods[-1]

    if terminal_method == "gordon":
        secondary_values = [terminal_growth + i * secondary_step for i in range(-n_steps, n_steps + 1)]
    else:
        secondary_values = [exit_multiple + i * secondary_step for i in range(-n_steps, n_steps + 1)]

    table = {}
    for sec in secondary_values:
        col = []
        for w in wacc_values:
            pv_fcf_w = _pv_explicit(periods, w)
            if terminal_method == "gordon":
                if w <= sec:
                    col.append(float("nan"))
                    continue
                tv = terminal_value_gordon(last_period.fcf, w, sec)
            else:
                tv = terminal_value_exit_multiple(last_period.ebitda, sec)
            pv_tv = tv / ((1.0 + w) ** last_period.t)
            col.append(pv_fcf_w + pv_tv)
        label = f"{sec:.1%}" if terminal_method == "gordon" else f"{sec:.1f}x"
        table[label] = col

    df_sens = pd.DataFrame(table, index=[f"{w:.1%}" for w in wacc_values])
    df_sens.index.name = "WACC"
    return df_sens


@dataclass
class DCFResult:
    periods: list
    wacc: float
    terminal_method: str
    terminal_growth: Optional[float]
    exit_multiple: Optional[float]
    terminal_value: float
    pv_terminal_value: float
    sum_pv_fcf: float
    enterprise_value: float
    net_debt: float
    equity_value: float
    implied_ev_ebitda: float
    sensitivity: pd.DataFrame

    def print_summary(self, detail: bool = False) -> None:
        print("=" * 92)
        print("DISCOUNTED CASH FLOW VALUATION")
        print("=" * 92)

        if detail:
            print(f"{'Period':<10}{'Revenue':>12}{'EBITDA':>12}{'EBIT':>12}{'NOPAT':>12}{'FCF':>12}{'PV(FCF)':>12}")
            for p in self.periods:
                print(f"{p.period:<10}{p.revenue:>12,.0f}{p.ebitda:>12,.0f}{p.ebit:>12,.0f}"
                      f"{p.nopat:>12,.0f}{p.fcf:>12,.0f}{p.pv_fcf:>12,.0f}")
            print("-" * 92)

        tv_label = "Gordon growth" if self.terminal_method == "gordon" else "Exit multiple"
        print(f"{'Sum of PV(FCF), explicit period:':<45}{self.sum_pv_fcf:>15,.0f}")
        print(f"{'Terminal value (' + tv_label + '):':<45}{self.terminal_value:>15,.0f}")
        print(f"{'PV of terminal value:':<45}{self.pv_terminal_value:>15,.0f}")
        print("-" * 92)
        print(f"{'Enterprise value:':<45}{self.enterprise_value:>15,.0f}")
        print(f"{'(-) Net debt:':<45}{self.net_debt:>15,.0f}")
        print(f"{'Equity value:':<45}{self.equity_value:>15,.0f}")
        print("-" * 92)
        print(f"Implied EV/EBITDA (last explicit year): {self.implied_ev_ebitda:.1f}x")
        pct_terminal = self.pv_terminal_value / self.enterprise_value if self.enterprise_value else float("nan")
        print(f"Terminal value as % of enterprise value: {pct_terminal:.0%}")
        print("=" * 92)

        axis = "WACC x terminal growth" if self.terminal_method == "gordon" else "WACC x exit multiple"
        print(f"\nSensitivity -- enterprise value ({axis}):\n")
        print(self.sensitivity.to_string(float_format=lambda x: f"{x:,.0f}"))


def run_dcf(
    df: pd.DataFrame,
    wacc: float,
    terminal_method: str = "gordon",
    terminal_growth: Optional[float] = None,
    exit_multiple: Optional[float] = None,
    net_debt: float = 0.0,
    wacc_step: float = 0.01,
    secondary_step: Optional[float] = None,
    n_steps: int = 2,
) -> DCFResult:
    if terminal_method not in ("gordon", "exit_multiple"):
        raise ValueError("terminal_method must be 'gordon' or 'exit_multiple'.")
    if terminal_method == "gordon" and terminal_growth is None:
        raise ValueError("--terminal-growth is required when terminal_method='gordon'.")
    if terminal_method == "exit_multiple" and exit_multiple is None:
        raise ValueError("--exit-multiple is required when terminal_method='exit_multiple'.")

    periods = compute_periods(df, wacc)
    last_period = periods[-1]
    sum_pv_fcf = sum(p.pv_fcf for p in periods)

    if terminal_method == "gordon":
        tv = terminal_value_gordon(last_period.fcf, wacc, terminal_growth)
    else:
        tv = terminal_value_exit_multiple(last_period.ebitda, exit_multiple)
    pv_tv = tv / ((1.0 + wacc) ** last_period.t)

    enterprise_value = sum_pv_fcf + pv_tv
    equity_value = enterprise_value - net_debt
    implied_ev_ebitda = enterprise_value / last_period.ebitda if last_period.ebitda else float("nan")

    if secondary_step is None:
        secondary_step = 0.005 if terminal_method == "gordon" else 0.5

    sensitivity = build_sensitivity(
        periods, wacc, terminal_method, terminal_growth, exit_multiple,
        wacc_step, secondary_step, n_steps,
    )

    return DCFResult(
        periods=periods, wacc=wacc, terminal_method=terminal_method,
        terminal_growth=terminal_growth, exit_multiple=exit_multiple,
        terminal_value=tv, pv_terminal_value=pv_tv, sum_pv_fcf=sum_pv_fcf,
        enterprise_value=enterprise_value, net_debt=net_debt, equity_value=equity_value,
        implied_ev_ebitda=implied_ev_ebitda, sensitivity=sensitivity,
    )


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="Parametrized DCF valuation from an Excel/CSV projection model.")
    parser.add_argument("model_file", help="Excel or CSV file: line items as rows, periods as columns.")
    parser.add_argument("--wacc", type=float, required=True, help="Discount rate, e.g. 0.13 for 13%%.")
    parser.add_argument("--terminal-method", choices=["gordon", "exit_multiple"], default="gordon")
    parser.add_argument("--terminal-growth", type=float, default=None,
                         help="Perpetuity growth rate, e.g. 0.04 for 4%% (required for --terminal-method gordon).")
    parser.add_argument("--exit-multiple", type=float, default=None,
                         help="EV/EBITDA exit multiple (required for --terminal-method exit_multiple).")
    parser.add_argument("--net-debt", type=float, default=0.0, help="Net debt, to bridge enterprise to equity value.")
    parser.add_argument("--wacc-step", type=float, default=0.01, help="Sensitivity step size for WACC.")
    parser.add_argument("--secondary-step", type=float, default=None,
                         help="Sensitivity step size for terminal growth or exit multiple.")
    parser.add_argument("--sensitivity-steps", type=int, default=2, help="Steps on each side of the base case.")
    parser.add_argument("--detail", action="store_true", help="Show the full per-period FCF build.")
    args = parser.parse_args(argv)

    try:
        df = load_model(args.model_file)
        result = run_dcf(
            df, wacc=args.wacc, terminal_method=args.terminal_method,
            terminal_growth=args.terminal_growth, exit_multiple=args.exit_multiple,
            net_debt=args.net_debt, wacc_step=args.wacc_step,
            secondary_step=args.secondary_step, n_steps=args.sensitivity_steps,
        )
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    result.print_summary(detail=args.detail)


if __name__ == "__main__":
    main()
