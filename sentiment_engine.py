"""Directional sentiment; gamma regime is reported independently."""
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
    components['dealer'] = float(np.clip(100*dg/max(abs(g), abs(dg), 1), -100, 100)) if np.isfinite(dg) and np.isfinite(g) else np.nan
    bias = position.get('bias', np.nan)
    components['flow'] = float(100*bias) if np.isfinite(bias) else np.nan
    # These are not directionally interpretable without validated conventions.
    components['volatility'] = np.nan
    components['dex'] = np.nan
    effective = {k: WEIGHTS[k] * (t['coverage'] if k == 'technical' else 1.)
                 for k, v in components.items() if np.isfinite(v)}
    coverage = sum(effective.values())
    score = sum(effective[k]*components[k] for k in effective)/coverage if coverage else np.nan
    label = classify_sentiment(score) if coverage >= .45 and np.isfinite(score) else 'Insufficient data'
    warnings = list(t['notes']) + ['Volatility excluded from directional scoring',
                                   'DEX excluded pending provider sign-convention verification']
    # Guardrail only when BOTH independent bearish technical conditions are confirmed.
    if label in ('Bullish', 'Mild Bullish') and t['below_ema'] and t['falling_ema'] and t['below_donchian_mid']:
        label = 'Neutral'
        warnings.append('Bullish label capped at Neutral: below falling EMA200 and Donchian midpoint; inspect conflicting flow/positioning signals')
    if t['coverage'] < 1:
        warnings.append(f'Technical coverage {t["coverage"]:.0%}: missing subfactors excluded from weighted score')
    return {'label': label, 'score': score, 'confidence': round(100*coverage),
            'coverage': round(100*coverage), 'components': components, 'technical': t,
            'gamma': 'Positive' if np.isfinite(g) and g >= 0 else ('Negative' if np.isfinite(g) else 'Unknown'),
            'warnings': warnings}
