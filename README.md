# QQQ OHLC integration patch

Replace these five files in the repository root: `app.py`, `data_engine.py`, `technical_engine.py`, `sentiment_engine.py` (the latter is included for compatibility with the previous sentiment fix). The fifth file `test_ohlc.py` is an optional local regression test; it references files in `/mnt/data` and is not needed for deployment.

Upload the existing eight options CSV files plus `qqq_price-history-11-03-2026.csv` in the Streamlit sidebar. The new price-history schema is recognized by `Time`, `Open`, `High`, `Low`, `Latest`. The price-history data is merged into the options history on exact dates; only OHLC rows through the latest options-history date are considered. The OHLC close is used consistently for EMA and Donchian technicals. Dealer positioning continues to use the options-history close, and mismatches above 0.25% generate a warning. No future OHLC bar is used for the snapshot.

Donchian 20 and 55 levels exclude the current day's bar. The technical score uses the EMA200 and Donchian20 midpoint; Donchian55 is displayed as context, not an extra weighted factor. The existing 25/30/20/15/10 sentiment weights remain experimental. Signal coverage is not a confidence probability. Strategy ranking remains unchanged.

The patch was syntax-checked and the OHLC merge and technical indicator logic were tested with the user's QQQ options history and Barchart price-history files. Streamlit rendering and strategy pricing have not been end-to-end tested.
