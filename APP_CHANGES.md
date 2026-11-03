# Update `app.py` (two small edits)

1. Replace:

```python
c.metric('Confidence / coverage',f'{s["confidence"]}%')
```

with:

```python
c.metric('Signal coverage (not probability)', f'{s["coverage"]}%')
```

2. In the Regime tab, after `tech=s['technical']`, add:

```python
st.caption(f"Technical subfactor coverage: {tech['coverage']:.0%} | Directional score: {s['score']:.1f} (heuristic)")
st.caption('The history close, EMA and Donchian must use the same completed session. TradingView data may be one day ahead.')
```

No changes are needed in `ranking_engine.py` or other engine files. If your history has no `High` and `Low`, Donchian will remain unavailable and cannot be inferred from closes.
