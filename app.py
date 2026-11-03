import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from data_engine import REQUIRED, load_files, normalize, check_quality, future_expirations
from positioning_engine import positioning
from volatility_engine import weekly_em_history, expected_move_table, regime
from sentiment_engine import sentiment
from ranking_engine import scan_top5, MATRIX

st.set_page_config(page_title='Dealer Positioning Command Center', page_icon='🎯', layout='wide')
st.title('🎯 Dealer Positioning Command Center')
st.caption('Dealer exposure is a proxy, not verified inventory. Strategy scores are heuristics, not win probabilities.')

with st.sidebar:
    st.header('Data')
    files=st.file_uploader('Upload CSV datasets',type='csv',accept_multiple_files=True)
    if not files:st.info('Upload the eight CSV datasets.');st.stop()
    raw,names,errors=load_files(files)
    for error in errors:st.warning(error)
    missing=REQUIRED-set(raw)
    if missing:st.error('Missing: '+', '.join(sorted(missing)));st.stop()
    data=normalize(raw)
    history=data['history'].dropna(subset=['Date','Close Price']).sort_values('Date')
    if history.empty:st.error('No valid history');st.stop()
    latest=history.Date.max().date()
    selected=st.date_input('Analysis date',latest,min_value=history.Date.min().date(),max_value=latest)
    asof=pd.Timestamp(selected)
    expiration_options=sorted(data['gex'].loc[data['gex'].expiration>=asof,'expiration'].dropna().unique())
    expiration=st.selectbox('GEX expiry focus',['Aggregate']+[pd.Timestamp(x).date() for x in expiration_options])
    max_risk=st.number_input('Maximum debit / risk ($)',min_value=25.,value=1500.,step=25.)
    min_oi=st.number_input('Minimum open interest',min_value=0,value=10)
    max_spread=st.slider('Maximum relative bid/ask spread',.05,1.,.35,.05)
    diagnostics=st.toggle('Show diagnostics',False)

if selected!=latest:
    st.error('Historical positioning snapshots are unavailable for this date. Live strategy recommendations disabled to prevent look-ahead bias.')
    st.dataframe(history[history.Date<=asof].tail(20),use_container_width=True)
    st.stop()
issues=check_quality(data,asof)
for issue in issues:st.warning(issue)
g=future_expirations(data['gex'],asof);x=future_expirations(data['dex'],asof)
if g.empty or x.empty:st.error('No current GEX/DEX expirations');st.stop()
p=positioning(history,g,x,data.get('gex_strike'),data['flow'])
weekly=weekly_em_history(history)
r=regime(p,history,weekly)
s=sentiment(p,history,r)
em=expected_move_table(data['em'],asof)
ticker=str(data['flow'].Symbol.dropna().iloc[0]) if data['flow'].Symbol.notna().any() else 'Underlying'

st.subheader(f'{ticker} · {latest} · ${p["spot"]:,.2f}')
# Two responsive rows avoid Streamlit truncating labels and large numbers.
def compact_exposure(value):
    if not np.isfinite(value):
        return '—'
    if abs(value) >= 1e9:
        return f'{value / 1e9:,.2f}B'
    if abs(value) >= 1e6:
        return f'{value / 1e6:,.2f}M'
    if abs(value) >= 1e3:
        return f'{value / 1e3:,.1f}K'
    return f'{value:,.0f}'

with st.container(border=True):
    a,b,c=st.columns(3)
    a.metric('Market sentiment',s['label'])
    b.metric('Gamma regime',s['gamma'])
    c.metric('Confidence / coverage',f'{s["confidence"]}%')
    st.divider()
    d,e=st.columns(2)
    d.metric('Net GEX',compact_exposure(p['gex']),help=f'Raw GEX: {p["gex"]:,.0f}')
    e.metric('30-day implied volatility',f'{p["iv30"]:.2f}%' if np.isfinite(p['iv30']) else '—')

t1,t2,t3,t4,t5=st.tabs(['🎯 Overview','🧭 Regime','🧲 Positioning','🌊 Flow','🏆 Top 5 Strategies'])
with t1:
    st.markdown('#### Key positioning levels')
    cols=st.columns(4)
    for col,(label,key) in zip(cols,[('Largest +GEX','largest_positive'),('Largest −GEX','largest_negative'),('Proximity-weighted +GEX','nearest_positive'),('Profile crossing proxy','flip')]):
        v=p[key];col.metric(label,f'{v:,.2f}' if np.isfinite(v) else '—')
    st.caption(p['flip_source']+'; neither crossings nor walls guarantee price behavior.')
    if not em.empty:
        fig=go.Figure()
        fig.add_trace(go.Scatter(x=em.date,y=em.upper_price,name='EM upper'))
        fig.add_trace(go.Scatter(x=em.date,y=em.lower_price,name='EM lower',fill='tonexty'))
        fig.add_hline(y=p['spot'],line_dash='dash')
        fig.update_layout(height=420,title='Expected move envelope')
        st.plotly_chart(fig,use_container_width=True)
        st.dataframe(em.head(15),use_container_width=True,hide_index=True)
with t2:
    st.subheader(r['label'])
    st.write('**Volatility playbook:** '+r['strategy'])
    st.metric('Transition / expansion risk',f'{r["risk_score"]}/100')
    st.write('**Sentiment factors**')
    st.json(s['components'])
    tech=s['technical']
    c1,c2,c3=st.columns(3)
    c1.metric('200 EMA',f'{tech["ema200"]:.2f}' if np.isfinite(tech['ema200']) else 'Unavailable')
    c2.metric('Donchian 20 high',f'{tech["donchian_high"]:.2f}' if np.isfinite(tech['donchian_high']) else 'Unavailable')
    c3.metric('Donchian 20 low',f'{tech["donchian_low"]:.2f}' if np.isfinite(tech['donchian_low']) else 'Unavailable')
    for note in s['warnings']:st.caption(note)
    if not weekly.empty:st.dataframe(weekly.tail(15),use_container_width=True,hide_index=True)
with t3:
    focus=g if expiration=='Aggregate' else g[g.expiration==pd.Timestamp(expiration)]
    focusx=x if expiration=='Aggregate' else x[x.expiration==pd.Timestamp(expiration)]
    if not focus.empty:
        fig=go.Figure()
        fig.add_trace(go.Bar(x=focus.expiration,y=focus.call_gex,name='Call GEX'))
        fig.add_trace(go.Bar(x=focus.expiration,y=focus.put_gex,name='Put GEX'))
        fig.update_layout(barmode='relative',height=350)
        st.plotly_chart(fig,use_container_width=True)
        st.dataframe(focus,use_container_width=True,hide_index=True)
    st.markdown('#### DEX by expiration')
    st.dataframe(focusx,use_container_width=True,hide_index=True)
    strikes=data.get('gex_strike')
    if strikes is not None:
        z=strikes.dropna(subset=['strike','net_gex']).copy()
        z=z[(z.strike>=p['spot']*.85)&(z.strike<=p['spot']*1.15)].sort_values('strike')
        fig=go.Figure(go.Bar(x=z.strike,y=z.net_gex,name='Aggregate strike GEX'))
        fig.add_vline(x=p['spot'],line_dash='dash')
        st.plotly_chart(fig,use_container_width=True)
        st.caption('Aggregate strike data is not expiry-specific.')
with t4:
    c1,c2,c3=st.columns(3)
    c1.metric('Bullish-side premium proxy',f'${p["bull_premium"]:,.0f}')
    c2.metric('Bearish-side premium proxy',f'${p["bear_premium"]:,.0f}')
    c3.metric('Unclassified premium',f'${p["unknown_premium"]:,.0f}')
    st.caption('Flow classification does not establish opening/closing trades or dealer intent.')
    st.dataframe(data['flow'].sort_values('Premium',ascending=False).head(30),use_container_width=True,hide_index=True)
    st.markdown('#### Unusual activity')
    st.dataframe(data['unusual'].sort_values('Vol/OI',ascending=False).head(30),use_container_width=True,hide_index=True)
with t5:
    st.subheader('Top 5 Options Strategies')
    st.caption('Candidate universe is determined by sentiment × gamma regime. Quotes use long ask / short bid; scores are not success probabilities.')
    if s['label']=='Insufficient data':
        st.warning('Insufficient independent directional evidence. Add daily OHLC data with at least 200 closes and 20 complete high/low bars to enable reliable technical classification.')
    else:
        st.write('**Preferred families:** '+', '.join(MATRIX.get((s['label'],s['gamma']),[])))
    chain=data.get('option_chain')
    if chain is None:st.warning('Option chain required for strike/expiration recommendations.')
    else:
        result=scan_top5(chain,asof,p['spot'],s,max_risk,min_oi,max_spread)
        if result.empty:st.info('No validated candidates. No trade is preferable to an unsupported recommendation.')
        else:
            st.dataframe(result,use_container_width=True,hide_index=True)
            st.download_button('Export top-five candidates',result.to_csv(index=False),'top5_options.csv','text/csv')
        st.info('Calendar maximum loss is not shown as defined: early exercise/assignment and exit timing can alter risk. Diagonals, credit spreads, double calendars and BWBs remain planned extensions, not fabricated recommendations.')
if diagnostics:
    with st.expander('Data provenance and quality',expanded=True):
        st.json({'files':names,'latest_history':str(latest),'issues':issues,'chain_loaded':'option_chain' in data,'sentiment_coverage':s['confidence']})
