"""Sample quantitative and qualitative data for report generation."""

import numpy as np
import pandas as pd


def get_portfolio_returns() -> pd.DataFrame:
    """Monthly portfolio returns for histogram."""
    np.random.seed(42)
    months = pd.date_range("2023-01-01", periods=60, freq="ME")
    returns = np.random.normal(loc=0.008, scale=0.035, size=60)
    return pd.DataFrame({"date": months, "return": returns})


def get_performance_timeseries() -> pd.DataFrame:
    """Cumulative performance for line chart."""
    np.random.seed(42)
    dates = pd.date_range("2020-01-01", periods=48, freq="ME")
    portfolio = np.cumprod(1 + np.random.normal(0.007, 0.03, 48)) * 100
    benchmark = np.cumprod(1 + np.random.normal(0.005, 0.025, 48)) * 100
    return pd.DataFrame({
        "date": dates,
        "Portfolio": portfolio,
        "Benchmark": benchmark,
    })


def get_risk_scores() -> dict:
    """Risk factor scores for spider web chart."""
    return {
        "categories": [
            "Market Risk", "Credit Risk", "Liquidity Risk",
            "Operational Risk", "Concentration Risk", "ESG Risk",
        ],
        "Fund A": [7.5, 6.0, 8.2, 5.5, 4.0, 7.0],
        "Fund B": [5.0, 8.5, 4.5, 7.0, 6.5, 5.5],
    }


def get_asset_allocation_timeseries() -> pd.DataFrame:
    """Asset allocation over time for stacked area chart."""
    np.random.seed(42)
    dates = pd.date_range("2020-01-01", periods=12, freq="QE")
    equities = np.clip(40 + np.cumsum(np.random.normal(0, 2, 12)), 30, 55)
    fixed_income = np.clip(30 + np.cumsum(np.random.normal(0, 1.5, 12)), 20, 40)
    alternatives = np.clip(15 + np.cumsum(np.random.normal(0, 1, 12)), 8, 25)
    # Normalize to 100%
    total = equities + fixed_income + alternatives
    cash = 100 - (equities / total * 100 + fixed_income / total * 100 + alternatives / total * 100)
    return pd.DataFrame({
        "date": dates,
        "Equities": equities / total * 100,
        "Fixed Income": fixed_income / total * 100,
        "Alternatives": alternatives / total * 100,
        "Cash": np.maximum(cash, 2),
    })


def get_holdings_table() -> pd.DataFrame:
    """Top holdings for table display."""
    return pd.DataFrame({
        "Holding": [
            "US Large Cap Equity ETF", "Global Aggregate Bond Fund",
            "Emerging Markets Fund", "Real Estate Investment Trust",
            "Private Equity Co-Invest", "Infrastructure Debt Fund",
            "Hedge Fund Multi-Strategy", "Short-Term Treasury Fund",
        ],
        "Asset Class": [
            "Equities", "Fixed Income", "Equities", "Real Assets",
            "Alternatives", "Fixed Income", "Alternatives", "Cash",
        ],
        "Weight (%)": [25.3, 20.1, 10.5, 8.7, 12.0, 9.4, 7.5, 6.5],
        "1Y Return (%)": [18.2, 3.1, 12.8, 7.5, 15.3, 5.2, 9.1, 4.8],
        "Volatility (%)": [14.5, 4.2, 18.3, 12.1, 16.8, 3.8, 8.5, 0.5],
    })


def get_qualitative_commentary() -> dict:
    """Qualitative commentary sections for the report."""
    return {
        "executive_summary": (
            "The portfolio delivered strong risk-adjusted returns over the trailing "
            "twelve months, outperforming the composite benchmark by 180 basis points. "
            "Strategic overweights in US equities and private equity drove the majority "
            "of excess return, while the fixed income allocation provided a stabilizing "
            "counterbalance during periods of elevated volatility. Looking ahead, we "
            "maintain a moderately constructive outlook with a focus on quality assets "
            "and selective exposure to growth opportunities."
        ),
        "market_outlook": (
            "Global equity markets have shown resilience despite persistent macro "
            "uncertainty. Central banks across developed economies have signaled a "
            "pause in rate hikes, providing a supportive backdrop for risk assets. "
            "Emerging markets present selective opportunities, particularly in Asia, "
            "where structural reforms and favorable demographics offer long-term "
            "tailwinds. We remain cautious on highly leveraged sectors and continue "
            "to monitor geopolitical developments closely."
        ),
        "risk_assessment": (
            "Portfolio risk metrics remain within established tolerance bands. "
            "Value-at-Risk (95%, 1-month) stands at 3.2%, below the 4.0% limit. "
            "Concentration risk has been reduced through recent rebalancing, with "
            "the top-10 holdings now representing 65% of total AUM, down from 72%. "
            "Liquidity coverage remains robust with 85% of the portfolio redeemable "
            "within 30 days."
        ),
    }
