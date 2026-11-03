"""Price structure scoring with independent EMA and Donchian availability."""
import numpy as np
import pandas as pd


def technicals(history):
    h = history.sort_values('Date').copy()
    close = pd.to_numeric(h['Close Price'], errors='coerce')
    ema = close.ewm(span=200, adjust=False, min_periods=200).mean()
    spot = float(close.iloc[-1])
    e = float(ema.iloc[-1])
    prev_e = float(ema.iloc[-6]) if len(ema) >= 206 else np.nan
    result = {'ema200': e, 'ema200_slope': e-prev_e if np.isfinite(e) and np.isfinite(prev_e) else np.nan,
              'donchian_high': np.nan, 'donchian_low': np.nan, 'donchian_mid': np.nan,
              'score': np.nan, 'coverage': 0., 'complete': False, 'notes': [], 'below_ema': False,
              'falling_ema': False, 'below_donchian_mid': False}
    contributions = []
    if np.isfinite(e):
        result['below_ema'] = spot < e
        result['falling_ema'] = np.isfinite(prev_e) and e < prev_e
        # EMA subfactor: position 70%, slope 30% when available.
        ema_score = 100 * np.sign(spot-e)
        if np.isfinite(prev_e):
            ema_score = 70*np.sign(spot-e) + 30*np.sign(e-prev_e)
        contributions.append((.60, float(ema_score)))
    else:
        result['notes'].append('EMA200 unavailable: 200 valid closing observations required')
    if {'High', 'Low'} <= set(h.columns):
        high = pd.to_numeric(h['High'], errors='coerce')
        low = pd.to_numeric(h['Low'], errors='coerce')
        if len(h) >= 21 and high.iloc[-21:-1].notna().all() and low.iloc[-21:-1].notna().all():
            hi, lo = float(high.iloc[-21:-1].max()), float(low.iloc[-21:-1].min())
            result.update(donchian_high=hi, donchian_low=lo, donchian_mid=(hi+lo)/2)
            result['below_donchian_mid'] = spot < (hi+lo)/2
            contributions.append((.40, float(100*np.sign(spot-(hi+lo)/2))))
        else:
            result['notes'].append('Donchian unavailable: 20 prior complete daily high/low bars required')
    else:
        result['notes'].append('Donchian unavailable: history has no daily High/Low columns')
    result['coverage'] = sum(w for w, _ in contributions)
    if contributions:
        result['score'] = sum(w*s for w,s in contributions)/result['coverage']
    result['complete'] = result['coverage'] >= .999
    return result
