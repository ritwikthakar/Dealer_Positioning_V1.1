
import numpy as np
import pandas as pd

def weighted_median(values,weights):
 a=pd.DataFrame({"v":values,"w":weights}).dropna()
 a=a[a.w>0].sort_values("v")
 if a.empty:return np.nan
 return float(a.iloc[np.searchsorted(a.w.cumsum().to_numpy(),a.w.sum()/2)]["v"])

def profile_crossings(strikes):
 if strikes is None or "gex_profile" not in strikes:return []
 z=strikes[["strike","gex_profile"]].dropna().groupby("strike",as_index=False)["gex_profile"].sum().sort_values("strike")
 s=z.strike.to_numpy(float);v=z.gex_profile.to_numpy(float);out=[]
 for i in range(len(s)-1):
  if v[i]==0:out.append(float(s[i]))
  elif v[i]*v[i+1]<0:out.append(float(s[i]+(s[i+1]-s[i])*(-v[i])/(v[i+1]-v[i])))
 return out

def strike_metrics(strikes,spot,expiry=None):
 empty={"largest_positive":np.nan,"largest_negative":np.nan,"nearest_positive":np.nan,"call_wall":np.nan,"put_wall":np.nan,"profile_cross":np.nan,"cross_count":0}
 if strikes is None or strikes.empty or not np.isfinite(spot):return empty
 z=strikes.dropna(subset=["strike","net_gex"]).copy().groupby("strike",as_index=False)[["net_gex","call_gex","put_gex"]].sum()
 pos=z[z.net_gex>0];neg=z[z.net_gex<0]
 if not pos.empty:
  empty["largest_positive"]=float(pos.loc[pos.net_gex.idxmax(),"strike"])
  near=pos.assign(score=pos.net_gex*np.exp(-abs(pos.strike-spot)/max(spot*.015,.01)))
  empty["nearest_positive"]=float(near.loc[near.score.idxmax(),"strike"])
 if not neg.empty:empty["largest_negative"]=float(neg.loc[neg.net_gex.idxmin(),"strike"])
 above=z[z.strike>spot];below=z[z.strike<spot]
 if not above.empty and above.call_gex.max()>0:empty["call_wall"]=float(above.loc[above.call_gex.idxmax(),"strike"])
 if not below.empty and below.put_gex.min()<0:empty["put_wall"]=float(below.loc[below.put_gex.idxmin(),"strike"])
 crosses=profile_crossings(strikes)
 empty["cross_count"]=len(crosses)
 if crosses:empty["profile_cross"]=min(crosses,key=lambda x:abs(x-spot))
 return empty

def flow_metrics(flow):
 if flow is None or flow.empty:return {"bias":np.nan,"bull_premium":0.,"bear_premium":0.,"unknown_premium":0.}
 f=flow.copy();side=f.Side.astype(str).str.lower();typ=f.Type.astype(str).str.lower()
 prem=f.Premium.fillna(0).clip(lower=0)*np.where(f.Code.astype(str).str.upper().str.startswith("ML"),.45,1)
 bullish=((typ=="call")&(side=="ask"))|((typ=="put")&(side=="bid"))
 bearish=((typ=="put")&(side=="ask"))|((typ=="call")&(side=="bid"))
 bull=float(prem[bullish].sum());bear=float(prem[bearish].sum())
 unknown=float(prem[~(bullish|bearish)].sum())
 return {"bias":(bull-bear)/(bull+bear) if bull+bear else np.nan,"bull_premium":bull,"bear_premium":bear,"unknown_premium":unknown}

def positioning(history,gex,dex,strikes,flow):
 h=history.sort_values("Date")
 last=h.iloc[-1];prev=h.iloc[-2] if len(h)>1 else last
 spot=float(last["Close Price"]);g=float(last["GEX Net OI"]);dx=float(last["DEX Net OI"])
 sm=strike_metrics(strikes,spot)
 flip=sm["profile_cross"];source="Strike-profile zero crossing (not a modeled gamma flip)"
 if not np.isfinite(flip):
  weights=gex.call_gex.abs()+gex.put_gex.abs()
  flip=weighted_median(gex.gamma_flip,weights)
  source="Weighted median of expiration-reported flips (proxy)"
 if not np.isfinite(flip):source="Unavailable"
 return {"spot":spot,"gex":g,"dex":dx,"gex_change":g-float(prev["GEX Net OI"]),
 "dex_change":dx-float(prev["DEX Net OI"]),"iv30":float(last.get("IV 30d",np.nan)),
 "iv_rank":float(last.get("IV Rank",np.nan)),"gamma_regime":"Positive GEX proxy" if g>=0 else "Negative GEX proxy",
 "flip":flip,"flip_source":source,**sm,**flow_metrics(flow)}
