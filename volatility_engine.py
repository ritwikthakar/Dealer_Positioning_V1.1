
import numpy as np
import pandas as pd

def weekly_em_history(history):
 h=history.dropna(subset=["Date","Close Price"]).sort_values("Date").copy()
 if "IV 30d" not in h:return pd.DataFrame()
 h["week"]=h.Date.dt.to_period("W-FRI")
 groups=list(h.groupby("week",sort=True));rows=[]
 for i in range(1,len(groups)):
  prevweek,p=groups[i-1];week,w=groups[i]
  if week.ordinal-prevweek.ordinal!=1:continue
  anchor=p.iloc[-1];spot=anchor["Close Price"];iv=anchor["IV 30d"]
  if pd.isna(iv) or iv<=0:continue
  em=spot*iv/100/np.sqrt(52)
  high=w.High.max() if "High" in w and w.High.notna().all() else np.nan
  low=w.Low.min() if "Low" in w and w.Low.notna().all() else np.nan
  closed=bool(w["Close Price"].iloc[-1]>spot+em or w["Close Price"].iloc[-1]<spot-em)
  observed=bool(high>spot+em or low<spot-em) if np.isfinite(high) and np.isfinite(low) else None
  rows.append({"Week":str(week),"Anchor":spot,"Estimated EM":em,"Upper":spot+em,"Lower":spot-em,
               "Intraday breach":observed,"Last close outside":closed,"Range basis":"Daily high/low" if observed is not None else "Closes only",
               "Completed":i<len(groups)-1})
 return pd.DataFrame(rows)

def term_structure(history):
 last=history.sort_values("Date").iloc[-1]
 short=[last.get(c,np.nan) for c in ("IV 1d","IV 3d")]
 mid=[last.get(c,np.nan) for c in ("IV 14d","IV 21d","IV 30d")]
 a=np.array(short,dtype=float);b=np.array(mid,dtype=float)
 a=a[np.isfinite(a)&(a>0)];b=b[np.isfinite(b)&(b>0)]
 return float(a.mean()/b.mean()-1) if len(a) and len(b) else np.nan

def expected_move_table(em,asof):
 z=em[em.date>=pd.Timestamp(asof)].sort_values("date").copy()
 z["DTE"]=(z.date-pd.Timestamp(asof)).dt.days
 return z

def regime(position,history,weekly):
 g=position["gex"];dg=position["gex_change"];ivacc=term_structure(history)
 completed=weekly[weekly.Completed] if not weekly.empty else weekly
 recent=completed.tail(8)
 contained=(recent["Last close outside"].eq(False).mean() if len(recent) else np.nan)
 latest=weekly.iloc[-1] if not weekly.empty else None
 breach=bool(latest["Intraday breach"]) if latest is not None and latest["Intraday breach"] is not None else False
 score=(25 if g<0 else 0)+(20 if dg<0 else 0)+(20 if np.isfinite(ivacc) and ivacc>.08 else 0)+(30 if breach else 0)
 if breach or score>=60:label="Expansion risk";strategy="Directional diagonal / OTM calendar (confirmation required)"
 elif g>=0 and np.isfinite(contained) and contained>=.75:label="Compression candidate";strategy="ATM calendar; double calendar only if both boundaries credible"
 elif score>=35:label="Transition watch";strategy="Reduce size / wait"
 else:label="Mixed / unresolved";strategy="Wait for price and IV confirmation"
 return {"label":label,"strategy":strategy,"risk_score":score,"term_acceleration":ivacc,"containment":contained}
