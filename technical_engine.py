import numpy as np
import pandas as pd


def technicals(history):
    h = history.sort_values('Date').copy()
    close = pd.to_numeric(h['Close Price'], errors='coerce')
    ema = close.ewm(span=200, adjust=False, min_periods=200).mean()
    spot = float(close.iloc[-1])
    result = {'ema200': float(ema.iloc[-1]), 'donchian_high': np.nan,
              'donchian_low': np.nan, 'donchian_mid': np.nan,
              'score': np.nan, 'complete': False, 'notes': []}
    if not np.isfinite(result['ema200']):
        result['notes'].append('200 EMA unavailable: fewer than 200 valid closes')
    if not {'High', 'Low'} <= set(h.columns):
        result['notes'].append('Donchian unavailable: daily High/Low required')
    else:
        high = pd.to_numeric(h['High'], errors='coerce')
        low = pd.to_numeric(h['Low'], errors='coerce')
        if len(h) >= 21 and high.iloc[-21:-1].notna().all() and low.iloc[-21:-1].notna().all():
            result['donchian_high'] = float(high.iloc[-21:-1].max())
            result['donchian_low'] = float(low.iloc[-21:-1].min())
            result['donchian_mid'] = (result['donchian_high'] + result['donchian_low']) / 2
        else:
            result['notes'].append('Donchian unavailable: 20 prior complete high/low observations required')
    if np.isfinite(result['ema200']) and np.isfinite(result['donchian_mid']):
        trend = np.sign(spot - result['ema200'])
        channel = np.sign(spot - result['donchian_mid'])
        result['score'] = float(100 * (.6 * trend + .4 * channel))
        result['complete'] = True
    return result
