# Dealer Positioning Command Center — Refactored

Run `pip install -r requirements.txt` and `streamlit run app.py`.

## Modules
- `data_engine.py`: CSV detection, parsing, expiration filtering, diagnostics.
- `positioning_engine.py`: GEX/DEX, strike concentrations, profile crossing, flow proxies.
- `volatility_engine.py`: weekly expected-move history, IV term structure, regime heuristic.
- `strategy_engine.py`: defined-risk butterfly scanner.
- `app.py`: five-tab Streamlit presentation.

## Important methodology limitations
- Historical aggregate GEX/DEX and current snapshot positioning may use different units or timestamps. Do not compare their absolute values directly.
- A strike-profile zero crossing is **not** a recalculated gamma flip across simulated spot prices.
- The strike-GEX CSV is aggregate, not expiry-specific.
- Option flow bid/ask classification is a directional **proxy**, not verified opening/closing trades.
- Weekly expected-move history uses an approximation from 30-day IV, not option-expiry-specific historical IV.
- Butterfly natural quotes are conservative quote-based estimates, not guaranteed executable fills.
- Historical date selection disables snapshot analysis rather than presenting misleading historical positioning.
- Expiration selection applies to expiration GEX/DEX tables, not aggregate strike GEX.

## Next stage
Add provenance metadata (export time, symbol, spot, currency and units) to each dataset; create a true spot-repriced gamma exposure profile and validate scoring against out-of-sample data.

## Link
https://dealerpositioningv11-7t6lat73vhr6gry62xqv9c.streamlit.app/
