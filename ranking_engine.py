import numpy as np
import pandas as pd

MATRIX = {
 ('Bullish','Positive'): ['Call calendar','Bull put credit spread'],
 ('Bullish','Negative'): ['Call diagonal','Bull call debit spread'],
 ('Mild Bullish','Positive'): ['Call calendar','Bull put credit spread'],
 ('Mild Bullish','Negative'): ['Call diagonal','Call calendar','Bull call debit spread'],
 ('Neutral','Positive'): ['Call calendar','Put calendar','Double calendar'],
 ('Neutral','Negative'): ['Call calendar','Put calendar'],
 ('Mild Bearish','Positive'): ['Put calendar','Put diagonal'],
 ('Mild Bearish','Negative'): ['Put diagonal','Put calendar','Bear put debit spread'],
 ('Bearish','Positive'): ['Put calendar','Bear put debit spread'],
 ('Bearish','Negative'): ['Bear put debit spread','Put diagonal'],
}


def _liquid(chain, asof, min_oi=10, max_spread=.35):
    q = chain.copy()
    q['type'] = q['type'].astype(str).str.upper()
    for col in ('strike','bid','ask','open_interest'):
        q[col] = pd.to_numeric(q[col], errors='coerce') if col in q else np.nan
    q = q.dropna(subset=['strike','bid','ask','expiration_date'])
    q = q[(q.bid >= 0) & (q.ask >= q.bid) & (q.ask > 0) & (q.expiration_date >= pd.Timestamp(asof))]
    q = q[q.open_interest.fillna(0) >= min_oi]
    q = q[(q.ask-q.bid)/((q.ask+q.bid)/2).clip(lower=.01) <= max_spread]
    return q.drop_duplicates(['type','expiration_date','strike'])


def scan_top5(chain, asof, spot, sentiment, max_risk=1500, min_oi=10, max_spread=.35):
    """Conservative executable-price calendar/vertical candidates; no synthetic option quotes."""
    columns = ['Strategy','Short expiry','Long expiry','Short strike','Long strike','Entry debit $','Max loss $','Score','Notes']
    if sentiment['label'] == 'Insufficient data' or chain is None or chain.empty:
        return pd.DataFrame(columns=columns)
    allowed = MATRIX.get((sentiment['label'],sentiment['gamma']), [])
    q = _liquid(chain, asof, min_oi, max_spread)
    if q.empty: return pd.DataFrame(columns=columns)
    q = q.assign(dte=(q.expiration_date-pd.Timestamp(asof)).dt.days)
    q = q[(q.dte >= 1) & (q.dte <= 45) & (abs(q.strike-spot)/spot <= .12)]
    rows=[]
    for typ in ('CALL','PUT'):
        z=q[q.type==typ]
        for strike, group in z.groupby('strike'):
            shortlegs=group[(group.dte>=5)&(group.dte<=30)].sort_values('dte')
            for _, short in shortlegs.iterrows():
                longs=group[(group.dte>short.dte)&(group.dte<=45)&(group.dte-short.dte<=14)]
                for _, long in longs.iterrows():
                    debit=(long.ask-short.bid)*100
                    if not (0 < debit <= max_risk):continue
                    name='Call calendar' if typ=='CALL' else 'Put calendar'
                    if name not in allowed:continue
                    # Calendars: debit is not always a hard upper bound on loss for American-style short options.
                    score=round(70-100*abs(strike-spot)/spot + min(10, sentiment['confidence']/10),1)
                    rows.append([name,short.expiration_date.date(),long.expiration_date.date(),strike,strike,round(debit,2),np.nan,score,'Debit only; assignment/early exercise risk; model exit P/L'])
        # Same-expiration verticals, fully bounded maximum loss.
        for exp, group in z.groupby('expiration_date'):
            if not (5 <= (exp-pd.Timestamp(asof)).days <= 30):continue
            g=group.sort_values('strike').reset_index(drop=True)
            for i in range(len(g)-1):
                a,b=g.iloc[i],g.iloc[i+1]
                if b.strike-a.strike > max(spot*.025, 10):continue
                if typ=='CALL' and 'Bull call debit spread' in allowed:
                    debit=(a.ask-b.bid)*100;name='Bull call debit spread';lo=a;hi=b
                elif typ=='PUT' and 'Bear put debit spread' in allowed:
                    debit=(b.ask-a.bid)*100;name='Bear put debit spread';lo=a;hi=b
                else:continue
                width=(b.strike-a.strike)*100
                if not (0 < debit < width and debit <= max_risk):continue
                score=round(75-100*abs((a.strike+b.strike)/2-spot)/spot,1)
                rows.append([name,exp.date(),exp.date(),lo.strike,hi.strike,round(debit,2),round(debit,2),score,'Defined-risk debit vertical; natural quotes'])
    if not rows:return pd.DataFrame(columns=columns)
    result=pd.DataFrame(rows,columns=columns).sort_values('Score',ascending=False)
    # One candidate per structure/strike/expiry, with up to five results.
    return result.drop_duplicates(['Strategy','Short expiry','Long expiry','Short strike','Long strike']).head(5).reset_index(drop=True)
