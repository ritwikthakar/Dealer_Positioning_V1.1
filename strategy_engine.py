
import numpy as np
import pandas as pd

def expiry_payoff(spot,typ,lo,mid,hi,debit):
 s=np.asarray(spot,float)
 if typ=="PUT":intr=np.maximum(hi-s,0)-2*np.maximum(mid-s,0)+np.maximum(lo-s,0)
 else:intr=np.maximum(s-lo,0)-2*np.maximum(s-mid,0)+np.maximum(s-hi,0)
 return (intr-debit)*100

def butterfly_scan(chain,expiry,typ,spot,max_loss=250,min_oi=10,max_spread=.35,limit=150):
 q=chain.copy()
 q["type"]=q["type"].astype(str).str.upper()
 q=q[(q.expiration_date==pd.Timestamp(expiry))&(q.type==typ)]
 q=q.dropna(subset=["strike","bid","ask"])
 q=q[(q.bid>=0)&(q.ask>=q.bid)&(q.ask>0)]
 q=q.sort_values("open_interest" if "open_interest" in q else "strike",ascending=False).drop_duplicates("strike")
 if "open_interest" in q:q=q[q.open_interest>=min_oi]
 q=q[(q.ask-q.bid)/((q.ask+q.bid)/2).clip(lower=.01)<=max_spread]
 if len(q)<3:return pd.DataFrame()
 q=q.set_index("strike");strikes=sorted(q.index)
 # Restrict search to strikes around spot to avoid cubic scans across thousands of strikes.
 strikes=[k for k in strikes if abs(k-spot)<=spot*.12]
 rows=[]
 for i in range(1,len(strikes)-1):
  body=strikes[i]
  for lo in strikes[max(0,i-10):i]:
   for hi in strikes[i+1:i+11]:
    lower=body-lo;upper=hi-body
    if typ=="PUT" and upper<=lower:continue
    if typ=="CALL" and lower<=upper:continue
    a,b,c=q.loc[lo],q.loc[body],q.loc[hi]
    debit=float(a.ask-2*b.bid+c.ask)
    test=np.array([0,lo,body,hi,max(spot,hi)*2])
    p=expiry_payoff(test,typ,lo,body,hi,debit)
    risk=max(0.,-float(p.min()));reward=float(p.max())
    if risk<=0 or risk>max_loss or reward<=0:continue
    rows.append({"Type":typ,"Expiry":pd.Timestamp(expiry).date(),"Long lower":lo,"Short body":body,"Long upper":hi,
                 "Natural debit $":round(debit*100,2),"Max loss $":round(risk,2),"Max profit $":round(reward,2),
                 "Reward / risk":round(reward/risk,2),"Body distance":round(abs(body-spot),2)})
 return pd.DataFrame(rows).sort_values(["Reward / risk","Max profit $"],ascending=False).head(limit) if rows else pd.DataFrame()
