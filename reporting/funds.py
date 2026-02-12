"""Two very different fund profiles to demonstrate adaptive report generation."""

import numpy as np
import pandas as pd


def _make_dates(start: str, periods: int, freq: str = "ME") -> pd.DatetimeIndex:
    return pd.date_range(start, periods=periods, freq=freq)


# ─────────────────────────────────────────────────────────────────────
# Fund A: Aggressive equity hedge fund — high vol, concentrated, fat tails
# ─────────────────────────────────────────────────────────────────────

def fund_a_returns() -> pd.DataFrame:
    np.random.seed(101)
    dates = _make_dates("2020-01-01", 60)
    # Mix of normal + occasional large moves (fat tails)
    base = np.random.normal(0.012, 0.055, 60)
    shocks = np.random.choice([0, 0, 0, 0, -0.12, 0.10], 60)
    returns = base + shocks * (np.random.rand(60) > 0.85)
    return pd.DataFrame({"date": dates, "return": returns})


def fund_a_performance() -> pd.DataFrame:
    np.random.seed(101)
    dates = _make_dates("2020-01-01", 60)
    port = np.cumprod(1 + np.random.normal(0.012, 0.055, 60)) * 100
    bench = np.cumprod(1 + np.random.normal(0.006, 0.04, 60)) * 100
    return pd.DataFrame({"date": dates, "Portfolio": port, "Benchmark": bench})


def fund_a_holdings() -> pd.DataFrame:
    return pd.DataFrame({
        "Holding": [
            "Nvidia Corp", "Meta Platforms", "Amazon.com",
            "Tesla Inc", "Palantir Technologies", "ARM Holdings",
            "Coinbase Global", "MicroStrategy",
        ],
        "Sector": [
            "Technology", "Technology", "Consumer Discretionary",
            "Consumer Discretionary", "Technology", "Technology",
            "Financials", "Technology",
        ],
        "Weight (%)": [22.5, 15.8, 12.3, 10.1, 9.7, 8.5, 6.2, 4.9],
        "1Y Return (%)": [125.3, 42.1, 35.8, -18.5, 68.2, 52.4, 88.1, 145.2],
        "Volatility (%)": [42.5, 32.1, 28.5, 55.2, 48.3, 38.7, 62.1, 78.3],
    })


def fund_a_risk_scores() -> dict:
    return {
        "categories": [
            "Market Risk", "Credit Risk", "Liquidity Risk",
            "Operational Risk", "Concentration Risk", "ESG Risk",
        ],
        "Fund": [9.2, 3.0, 6.5, 4.5, 9.5, 7.8],
    }


def fund_a_allocation() -> pd.DataFrame:
    np.random.seed(101)
    dates = _make_dates("2020-01-01", 12, freq="QE")
    eq = np.clip(85 + np.cumsum(np.random.normal(0, 2, 12)), 75, 95)
    cash = 100 - eq
    return pd.DataFrame({
        "date": dates,
        "Equities": eq,
        "Cash": cash,
    })


def fund_a_sector_exposure() -> pd.DataFrame:
    return pd.DataFrame({
        "Sector": [
            "Technology", "Consumer Discretionary", "Financials",
            "Healthcare", "Industrials",
        ],
        "Weight (%)": [61.4, 22.4, 6.2, 5.5, 4.5],
    })


def fund_a_monthly_pnl() -> pd.DataFrame:
    """Monthly P&L attribution for top/bottom contributor analysis."""
    np.random.seed(101)
    dates = _make_dates("2024-01-01", 12)
    holdings = ["Nvidia", "Meta", "Amazon", "Tesla", "Palantir", "ARM", "Coinbase", "MicroStrategy"]
    data = {}
    for h in holdings:
        data[h] = np.random.normal(0.5, 2.5, 12)
    df = pd.DataFrame(data, index=dates)
    return df


# ─────────────────────────────────────────────────────────────────────
# Fund B: Conservative stable-income fund — low vol, diversified, yield-focused
# ─────────────────────────────────────────────────────────────────────

def fund_b_returns() -> pd.DataFrame:
    np.random.seed(202)
    dates = _make_dates("2020-01-01", 60)
    returns = np.random.normal(0.003, 0.008, 60)
    return pd.DataFrame({"date": dates, "return": returns})


def fund_b_performance() -> pd.DataFrame:
    np.random.seed(202)
    dates = _make_dates("2020-01-01", 60)
    port = np.cumprod(1 + np.random.normal(0.003, 0.008, 60)) * 100
    bench = np.cumprod(1 + np.random.normal(0.0025, 0.007, 60)) * 100
    return pd.DataFrame({"date": dates, "Portfolio": port, "Benchmark": bench})


def fund_b_holdings() -> pd.DataFrame:
    return pd.DataFrame({
        "Holding": [
            "US Aggregate Bond ETF", "Investment Grade Corp Bond Fund",
            "TIPS Inflation Protected", "Municipal Bond Fund",
            "Short Duration Govt Fund", "Mortgage-Backed Securities",
            "Global Sovereign Bond ETF", "High-Yield Bond (Small Alloc)",
            "Dividend Equity ETF", "Real Estate Income REIT",
        ],
        "Asset Class": [
            "Govt Bonds", "Corp Bonds", "Inflation-Linked",
            "Muni Bonds", "Short-Term", "Securitized",
            "Intl Bonds", "High Yield", "Equity-Income", "Real Assets",
        ],
        "Weight (%)": [18.5, 15.2, 12.0, 10.5, 10.0, 9.8, 8.5, 5.0, 6.5, 4.0],
        "Yield (%)": [4.2, 5.1, 3.8, 3.5, 4.8, 4.5, 3.2, 7.1, 3.0, 4.8],
        "Duration (yr)": [6.2, 5.8, 7.5, 4.5, 1.8, 4.2, 7.0, 3.5, 0.0, 0.0],
        "1Y Return (%)": [2.8, 4.5, 3.2, 3.0, 4.1, 3.8, 1.5, 6.2, 8.5, 7.1],
        "Volatility (%)": [4.2, 5.1, 4.8, 3.5, 1.2, 3.8, 5.5, 8.2, 12.5, 14.1],
    })


def fund_b_risk_scores() -> dict:
    return {
        "categories": [
            "Market Risk", "Credit Risk", "Liquidity Risk",
            "Operational Risk", "Concentration Risk", "ESG Risk",
        ],
        "Fund": [3.5, 6.5, 2.0, 3.0, 3.5, 4.0],
    }


def fund_b_allocation() -> pd.DataFrame:
    np.random.seed(202)
    dates = _make_dates("2020-01-01", 12, freq="QE")
    govt = np.clip(30 + np.cumsum(np.random.normal(0, 1, 12)), 25, 38)
    corp = np.clip(20 + np.cumsum(np.random.normal(0, 0.8, 12)), 15, 28)
    securitized = np.clip(10 + np.cumsum(np.random.normal(0, 0.5, 12)), 7, 15)
    equity_inc = np.clip(10 + np.cumsum(np.random.normal(0, 0.5, 12)), 5, 15)
    total = govt + corp + securitized + equity_inc
    cash = 100 - (govt / total * 100 + corp / total * 100 + securitized / total * 100 + equity_inc / total * 100)
    return pd.DataFrame({
        "date": dates,
        "Government Bonds": govt / total * 100,
        "Corporate Bonds": corp / total * 100,
        "Securitized": securitized / total * 100,
        "Equity-Income": equity_inc / total * 100,
        "Cash": np.maximum(cash, 1.5),
    })


def fund_b_income_stream() -> pd.DataFrame:
    """Quarterly income/yield data."""
    np.random.seed(202)
    dates = _make_dates("2020-01-01", 20, freq="QE")
    income = 0.95 + np.cumsum(np.random.normal(0.02, 0.03, 20))
    return pd.DataFrame({"date": dates, "income_per_unit": income})


def fund_b_duration_profile() -> pd.DataFrame:
    return pd.DataFrame({
        "Bucket": ["0-1Y", "1-3Y", "3-5Y", "5-7Y", "7-10Y", "10Y+"],
        "Weight (%)": [12.0, 18.5, 22.0, 25.0, 15.5, 7.0],
    })


# ─────────────────────────────────────────────────────────────────────
# Registry: load a fund by name
# ─────────────────────────────────────────────────────────────────────

FUND_REGISTRY = {
    "alpha_aggressive": {
        "name": "Alpha Aggressive Growth Fund",
        "returns": fund_a_returns,
        "performance": fund_a_performance,
        "holdings": fund_a_holdings,
        "risk_scores": fund_a_risk_scores,
        "allocation": fund_a_allocation,
        "extra": {
            "sector_exposure": fund_a_sector_exposure,
            "monthly_pnl": fund_a_monthly_pnl,
        },
    },
    "horizon_income": {
        "name": "Horizon Stable Income Fund",
        "returns": fund_b_returns,
        "performance": fund_b_performance,
        "holdings": fund_b_holdings,
        "risk_scores": fund_b_risk_scores,
        "allocation": fund_b_allocation,
        "extra": {
            "income_stream": fund_b_income_stream,
            "duration_profile": fund_b_duration_profile,
        },
    },
}


def load_fund(fund_id: str) -> dict:
    """Load all data for a fund, calling each data function."""
    reg = FUND_REGISTRY[fund_id]
    data = {
        "fund_id": fund_id,
        "name": reg["name"],
        "returns": reg["returns"](),
        "performance": reg["performance"](),
        "holdings": reg["holdings"](),
        "risk_scores": reg["risk_scores"](),
        "allocation": reg["allocation"](),
    }
    for key, fn in reg["extra"].items():
        data[key] = fn()
    return data
