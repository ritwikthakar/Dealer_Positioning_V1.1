# Sentiment + Top 5 scanner patch

Replace `app.py` and add `technical_engine.py`, `sentiment_engine.py`, `ranking_engine.py` at the repository root. The other original repository files remain unchanged.

Run: `pip install -r requirements.txt && streamlit run app.py`.

The BWB Lab tab is replaced by Top 5 Strategies. This initial implementation produces quote-grounded call/put calendars and directional debit verticals. It does not yet produce executable diagonals, credit spreads, double calendars, or BWBs. Those are displayed only as preferred families, never as unpriced trade recommendations.

The eight source files alone may lack complete OHLC; Donchian requires High and Low and the 200 EMA requires 200 valid closes. Without adequate evidence the sentiment engine intentionally returns Insufficient data and does not force a recommendation.

No strategy is guaranteed profitable. Check quotes, multiplier, option exercise style, dividends, and contract settlement before trading.
