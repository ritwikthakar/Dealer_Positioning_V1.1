"""Completed-session technical indicators; Donchian bands exclude the current bar."""
import numpy as np
import pandas as pd

def technicals(history):
 h=history.sort_values('Date').copy()
 close=pd.to_numeric(h['OHLC Close'] if 'OHLC Close' in h else h['Close Price'],errors='coerce')
 # Prefer OHLC vendor closes for EMA/Donchian consistency; do not backfill missing bars with another vendor.
 ema=close.ewm(span=200,adjust=False,min_periods=200).mean()
 spot=float(close.iloc[-1]);e=float(ema.iloc[-1])
 prev_e=float(ema.iloc[-6]) if len(ema)>=206 else np.nan
 result={'ema200':e,'ema200_slope':e-prev_e if np.isfinite(e) and np.isfinite(prev_e) else np.nan,
         'donchian_high':np.nan,'donchian_low':np.nan,'donchian_mid':np.nan,
         'donchian55_high':np.nan,'donchian55_low':np.nan,'donchian55_mid':np.nan,
         'score':np.nan,'coverage':0.,'complete':False,'notes':[],
         'below_ema':False,'falling_ema':False,'below_donchian_mid':False,'spot':spot}
 contributions=[]
 if np.isfinite(e) and np.isfinite(spot):
  result['below_ema']=spot<e
  result['falling_ema']=np.isfinite(prev_e) and e<prev_e
  ema_score=70*np.sign(spot-e)+30*np.sign(e-prev_e) if np.isfinite(prev_e) else 100*np.sign(spot-e)
  contributions.append((.60,float(ema_score)))
 else:result['notes'].append('EMA200 unavailable: 200 valid daily closes required')
 if {'High','Low'}<=set(h.columns):
  hi=pd.to_numeric(h.High,errors='coerce');lo=pd.to_numeric(h.Low,errors='coerce')
  for n in (20,55):
   if len(h)>=n+1 and hi.iloc[-n-1:-1].notna().all() and lo.iloc[-n-1:-1].notna().all():
    upper=float(hi.iloc[-n-1:-1].max());lower=float(lo.iloc[-n-1:-1].min());mid=(upper+lower)/2
    prefix='donchian' if n==20 else 'donchian55'
    result.update({prefix+'_high':upper,prefix+'_low':lower,prefix+'_mid':mid})
    if n==20 and np.isfinite(spot):
     result['below_donchian_mid']=spot<mid
     contributions.append((.40,float(100*np.sign(spot-mid))))
   else:result['notes'].append(f'Donchian {n} unavailable: {n} complete prior OHLC bars required')
 else:result['notes'].append('Donchian unavailable: upload Barchart price history with High/Low')
 result['coverage']=sum(w for w,_ in contributions)
 if contributions:result['score']=sum(w*s for w,s in contributions)/result['coverage']
 result['complete']=result['coverage']>=.999
 if 'OHLC Close' in h and np.isfinite(spot):
  option_close=pd.to_numeric(h['Close Price'],errors='coerce').iloc[-1]
  if np.isfinite(option_close) and abs(option_close-spot)/spot>.0025:
   result['notes'].append(f'Vendor close mismatch on {h.Date.iloc[-1].date()}: options history {option_close:.2f} vs OHLC {spot:.2f}; verify session/adjustment before trading')
 return result
