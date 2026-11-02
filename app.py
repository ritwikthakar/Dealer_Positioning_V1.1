
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from data_engine import REQUIRED,load_files,normalize,check_quality,future_expirations,quote_age_warning
from positioning_engine import positioning
from volatility_engine import weekly_em_history,expected_move_table,regime
from strategy_engine import butterfly_scan

st.set_page_config(page_title="Dealer Positioning Command Center",page_icon="🎯",layout="wide")
st.title("🎯 Dealer Positioning Command Center")
st.caption("Positioning is a proxy for dealer exposure, not observed dealer inventory or a guaranteed price forecast.")

@st.cache_data(show_spinner=False)
def cached_normalize(data):return normalize(data)

with st.sidebar:
 st.header("Data")
 files=st.file_uploader("Upload CSV datasets",type="csv",accept_multiple_files=True)
 if not files:
  st.info("Upload history, GEX, DEX, expected move, flow, and unusual activity. Strike GEX and option chain are optional.")
  st.stop()
 raw,names,errors=load_files(files)
 for e in errors:st.warning(e)
 missing=REQUIRED-set(raw)
 if missing:st.error("Missing: "+", ".join(sorted(missing)));st.stop()
 data=cached_normalize(raw)
 history=data["history"].dropna(subset=["Date","Close Price"]).sort_values("Date")
 if history.empty:st.error("History has no valid price/date rows");st.stop()
 latest=history.Date.max().date()
 selected=st.date_input("Analysis date",value=latest,min_value=history.Date.min().date(),max_value=latest)
 asof=pd.Timestamp(selected)
 historical=history[history.Date<=asof]
 if historical.empty:st.stop()
 snapshot_date=history.Date.max().date()
 st.caption("Expiration filters include 0DTE. No minimum exposure-share cutoff.")
 expiration_options=sorted(data["gex"].loc[data["gex"].expiration>=asof,"expiration"].dropna().unique())
 expiration=st.selectbox("GEX expiry focus",["Aggregate"]+[pd.Timestamp(x).date() for x in expiration_options])
 show_raw=st.toggle("Show diagnostics",False)

if selected!=latest:
 st.error("Historical mode: positioning snapshots cannot be reconstructed for this date. Current snapshot analysis is disabled to avoid look-ahead bias.")
 st.dataframe(historical.tail(20),use_container_width=True)
 st.stop()

issues=check_quality(data,asof)
for issue in issues:st.warning(issue)
g=future_expirations(data["gex"],asof)
x=future_expirations(data["dex"],asof)
if g.empty or x.empty:st.error("No current GEX/DEX expirations");st.stop()
em=expected_move_table(data["em"],asof)
if em.empty:st.warning("Expected move file has no future observations")
strikes=data.get("gex_strike")
p=positioning(historical,g,x,strikes,data["flow"])
weekly=weekly_em_history(historical)
r=regime(p,historical,weekly)
ticker=str(data["flow"].Symbol.dropna().iloc[0]) if data["flow"].Symbol.notna().any() else "Underlying"

def fmt(v,precision=2):
 return "—" if not np.isfinite(v) else f"{v:,.{precision}f}"
def money(v):
 if not np.isfinite(v):return "—"
 return f"{v/1e9:,.2f}B" if abs(v)>=1e9 else (f"{v/1e6:,.2f}M" if abs(v)>=1e6 else f"{v:,.0f}")

st.subheader(f"{ticker} · {latest} · ${fmt(p['spot'])}")
a,b,c,d,e=st.columns(5)
a.metric("Gamma regime",p["gamma_regime"])
b.metric("Net GEX (history)",money(p["gex"]),delta=money(p["gex_change"]))
c.metric("Net DEX (history)",money(p["dex"]),delta=money(p["dex_change"]))
d.metric("IV 30d",f"{fmt(p['iv30'])}%")
e.metric("IV rank",f"{fmt(p['iv_rank'])}%")
t1,t2,t3,t4,t5=st.tabs(["🎯 Overview","🧭 Regime","🧲 Positioning","🌊 Flow","🦋 Butterfly Lab"])

with t1:
 st.markdown("#### Key positioning levels")
 c1,c2,c3,c4=st.columns(4)
 c1.metric("Largest +GEX",fmt(p["largest_positive"]))
 c2.metric("Largest −GEX",fmt(p["largest_negative"]))
 c3.metric("Proximity-weighted +GEX",fmt(p["nearest_positive"]))
 c4.metric("Profile zero crossing",fmt(p["flip"]))
 st.caption(p["flip_source"]+". These levels are not guaranteed magnets, support or resistance.")
 if not em.empty:
  fig=go.Figure()
  fig.add_trace(go.Scatter(x=em.date,y=em.upper_price,name="EM upper",mode="lines"))
  fig.add_trace(go.Scatter(x=em.date,y=em.lower_price,name="EM lower",mode="lines",fill="tonexty"))
  fig.add_hline(y=p["spot"],line_dash="dash",annotation_text="History close")
  for name,k in [("Largest +GEX","largest_positive"),("Largest −GEX","largest_negative"),("Profile cross","flip")]:
   if np.isfinite(p[k]):fig.add_hline(y=p[k],line_dash="dot",annotation_text=name)
  fig.update_layout(height=440,title="Expected-move envelope and reference levels",yaxis_title="Price")
  st.plotly_chart(fig,use_container_width=True)
  st.dataframe(em[["date","DTE","lower_price","upper_price","expected_move_amt"]].head(15),hide_index=True,use_container_width=True)

with t2:
 st.subheader(r["label"])
 st.write("**Playbook:** "+r["strategy"])
 c1,c2,c3=st.columns(3)
 c1.metric("Transition / expansion risk",f"{r['risk_score']}/100")
 c2.metric("Short vs mid IV",fmt(r["term_acceleration"]*100)+"%" if np.isfinite(r["term_acceleration"]) else "—")
 c3.metric("Completed-week containment",fmt(r["containment"]*100)+"%" if np.isfinite(r["containment"]) else "—")
 st.caption("Risk score is a heuristic, not a calibrated probability. Historical weekly EM uses prior-week closing price and 30-day IV / √52.")
 if not weekly.empty:st.dataframe(weekly.tail(15),hide_index=True,use_container_width=True)

with t3:
 st.markdown("#### Expiration GEX and DEX")
 focus=g if expiration=="Aggregate" else g[g.expiration==pd.Timestamp(expiration)]
 focusx=x if expiration=="Aggregate" else x[x.expiration==pd.Timestamp(expiration)]
 if focus.empty:st.info("No GEX for selected expiration")
 else:
  fig=go.Figure()
  fig.add_trace(go.Bar(x=focus.expiration,y=focus.call_gex,name="Call GEX"))
  fig.add_trace(go.Bar(x=focus.expiration,y=focus.put_gex,name="Put GEX"))
  fig.update_layout(barmode="relative",height=350)
  st.plotly_chart(fig,use_container_width=True)
  st.dataframe(focus,use_container_width=True,hide_index=True)
 st.markdown("#### DEX by expiration")
 st.dataframe(focusx,use_container_width=True,hide_index=True)
 if strikes is not None:
  st.markdown("#### Strike-level gamma concentration (aggregate snapshot)")
  z=strikes.dropna(subset=["strike","net_gex"]).copy()
  z=z[(z.strike>=p["spot"]*.85)&(z.strike<=p["spot"]*1.15)].sort_values("strike")
  fig=go.Figure(go.Bar(x=z.strike,y=z.net_gex,name="Net GEX"))
  fig.add_vline(x=p["spot"],line_dash="dash")
  fig.update_layout(height=430,xaxis_title="Strike",yaxis_title="GEX")
  st.plotly_chart(fig,use_container_width=True)
  st.caption("Aggregate strike file cannot be filtered by expiry. Use the option-chain proxy in Butterfly Lab for expiry-specific concentration.")

with t4:
 st.markdown("#### Flow interpretation")
 c1,c2,c3=st.columns(3)
 c1.metric("Ask-call / bid-put proxy",money(p["bull_premium"]))
 c2.metric("Ask-put / bid-call proxy",money(p["bear_premium"]))
 c3.metric("Unclassified premium",money(p["unknown_premium"]))
 st.caption("Trade-side flow is not verified opening interest, institutional intent or actual dealer delta. Multi-leg trades are downweighted, not fully resolved.")
 st.dataframe(data["flow"].sort_values("Premium",ascending=False).head(30),hide_index=True,use_container_width=True)
 st.markdown("#### Unusual activity")
 st.dataframe(data["unusual"].sort_values("Vol/OI",ascending=False).head(30),hide_index=True,use_container_width=True)

with t5:
 st.markdown("#### Defined-risk broken-wing butterfly lab")
 st.caption("Natural quotes (buy at ask, sell at bid). Expiry payoff only; no probability or pre-expiry mark estimate.")
 chain=data.get("option_chain")
 if chain is None:st.info("Upload an option chain to activate the scanner.")
 else:
  q=chain.copy()
  for col in ["bid","ask","strike","open_interest"]:
   if col not in q:q[col]=np.nan
  exps=sorted(q.loc[q.expiration_date>=asof,"expiration_date"].dropna().unique())
  if not exps:st.warning("No live chain expirations")
  else:
   aa,bb,cc,dd=st.columns(4)
   expiry=aa.selectbox("Expiry",[pd.Timestamp(v).date() for v in exps])
   typ=bb.selectbox("Option type",["PUT","CALL"])
   risk=cc.number_input("Maximum loss ($)",min_value=10.,value=250.,step=25.)
   oi=dd.number_input("Minimum OI per leg",min_value=0,value=10,step=10)
   spread=st.slider("Maximum relative bid-ask spread per leg",.05,1.,.35,.05)
   if st.button("Scan butterflies",type="primary"):
    with st.spinner("Scanning candidate strikes…"):
     results=butterfly_scan(q,pd.Timestamp(expiry),typ,p["spot"],max_loss=risk,min_oi=oi,max_spread=spread)
    if results.empty:st.info("No candidates satisfy the filters.")
    else:
     st.dataframe(results,hide_index=True,use_container_width=True)
     st.download_button("Export candidate CSV",results.to_csv(index=False),"butterfly_candidates.csv","text/csv")
   st.warning("For American-style options, early assignment and exercise mechanics can create operational risk. Check broker risk and liquidity before trading.")

if show_raw:
 with st.expander("Data provenance and quality",expanded=True):
  st.json({"files":names,"history_last":str(latest),"gex_expirations":len(g),"dex_expirations":len(x),
           "strike_gex_loaded":strikes is not None,"chain_loaded":"option_chain" in data,
           "issues":issues,"profile_crossings":p["cross_count"]})
