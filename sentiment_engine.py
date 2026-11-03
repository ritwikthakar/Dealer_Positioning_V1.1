import numpy as np
from technical_engine import technicals

WEIGHTS = {'technical': .25, 'dealer': .30, 'flow': .20, 'volatility': .15, 'dex': .10}


def classify_sentiment(score):
    if score >= 60: return 'Bullish'
    if score >= 20: return 'Mild Bullish'
    if score > -20: return 'Neutral'
    if score > -60: return 'Mild Bearish'
    return 'Bearish'


def sentiment(position, history, volatility_regime):
    t = technicals(history)
    components = {'technical': t['score']}
    g = position.get('gex', np.nan)
    dg = position.get('gex_change', np.nan)
    components['dealer'] = np.clip(100 * dg / max(abs(g), abs(dg), 1), -100, 100) if np.isfinite(dg) and np.isfinite(g) else np.nan
    bias = position.get('bias', np.nan)
    components['flow'] = 100 * bias if np.isfinite(bias) else np.nan
    # Volatility is not directional by itself. Exclude rather than assigning a fake sign.
    components['volatility'] = np.nan
    dex = position.get('dex_change', np.nan)
    dx = position.get('dex', np.nan)
    # DEX sign is convention-dependent: require verified provider convention to score direction.
    components['dex'] = np.nan
    available = {k: v for k, v in components.items() if np.isfinite(v)}
    coverage = sum(WEIGHTS[k] for k in available)
    score = sum(WEIGHTS[k] * v for k, v in available.items()) / coverage if coverage else np.nan
    # Never issue a directional verdict with insufficient evidence.
    label = classify_sentiment(score) if coverage >= .45 and np.isfinite(score) else 'Insufficient data'
    return {'label': label, 'score': score, 'confidence': round(100 * coverage),
            'components': components, 'technical': t,
            'gamma': 'Positive' if g >= 0 else 'Negative',
            'warnings': t['notes'] + ['Volatility excluded from directional scoring', 'DEX excluded pending sign-convention verification']}
