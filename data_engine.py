
import io
import numpy as np
import pandas as pd

SCHEMAS = {
 "history":{"Date","Close Price","GEX Net OI","DEX Net OI"},
 "gex":{"expiration","net_gex","call_gex","put_gex","gamma_flip"},
 "dex":{"expiration","net_dex","call_dex","put_dex"},
 "gex_strike":{"strike","call_gex","put_gex","net_gex"},
 "em":{"date","expected_move_amt","upper_price","lower_price"},
 "flow":{"Symbol","Premium","Side","Code","Trade","Size"},
 "unusual":{"Symbol","Vol/OI","Moneyness","Imp Vol","Open Int"},
 "option_chain":{"type","strike","expiration_date","bid","ask","implied_volatility"}
}
REQUIRED={"history","gex","dex","em","flow","unusual"}

def number(x):
 if pd.isna(x): return np.nan
 s=str(x).strip().replace(",","").replace("$","").replace("%","")
 mult=1
 if s[-1:].upper() in ("K","M","B"):
  mult={"K":1e3,"M":1e6,"B":1e9}[s[-1].upper()];s=s[:-1]
 try:return float(s)*mult
 except (ValueError,TypeError):return np.nan

def classify(df):
 cols=set(df.columns)
 for name,req in SCHEMAS.items():
  if req<=cols:return name
 return None

def load_files(files):
 result={};errors=[];names={}
 for f in files:
  try:
   df=pd.read_csv(io.BytesIO(f.getvalue()))
   kind=classify(df)
   if not kind:errors.append(f"{f.name}: unrecognized schema");continue
   if kind in result:errors.append(f"{f.name}: duplicate {kind}; first file retained");continue
   result[kind]=df;names[kind]=f.name
  except Exception as exc:errors.append(f"{f.name}: {exc}")
 return result,names,errors

def normalize(data):
 d={k:v.copy() for k,v in data.items()}
 datecols={"history":"Date","gex":"expiration","dex":"expiration","em":"date","flow":"Exp Date","unusual":"Exp Date","option_chain":"expiration_date"}
 for k,col in datecols.items():
  if k in d and col in d[k]:
   d[k][col]=pd.to_datetime(d[k][col].astype(str).str.split(":").str[0],errors="coerce").dt.tz_localize(None).dt.normalize()
 for k,df in d.items():
  for col in df.columns:
   if col in {"Date","expiration","date","Exp Date","expiration_date","Symbol","Code","Side","Type","type","Moneyness","Bid x Size","Ask x Size","symbol","contract_symbol","last_trade_date"}:continue
   if pd.api.types.is_numeric_dtype(df[col]):continue
   if col in {"strike","call_gex","put_gex","net_gex","gex_profile","net_dex","call_dex","put_dex","gamma_flip","call_wall","put_wall","expected_move_amt","expected_move_percentage","upper_price","lower_price","implied_volatility","Close Price","GEX Net OI","DEX Net OI","IV 30d","IV Rank","IV 1d","IV 3d","IV 7d","IV 14d","IV 21d","Premium","Strike","Trade","Size","Volume","Open Int","Vol/OI","bid","ask","open_interest","volume","gamma","delta","Price~"} or col.startswith(("IV ","Max Pain")):
    df[col]=df[col].map(number)
 return d

def check_quality(d,asof):
 issues=[]
 for k in REQUIRED-set(d):issues.append(f"Missing required dataset: {k}")
 if issues:return issues
 for k,col in [("history","Date"),("gex","expiration"),("dex","expiration"),("em","date")]:
  if d[k][col].notna().sum()==0:issues.append(f"{k}: no valid dates")
 for k in ("gex","dex"):
  if not d[k].empty and (d[k]["expiration"].dropna()<pd.Timestamp(asof)).all():
   issues.append(f"{k}: all expirations are stale")
 if "option_chain" in d:
  q=d["option_chain"]
  if (q["ask"]<q["bid"]).any():issues.append("Option chain contains crossed quotes")
 return issues

def future_expirations(df,asof,include_today=True):
 dates=df["expiration"]
 return df.loc[dates.ge(pd.Timestamp(asof)) if include_today else dates.gt(pd.Timestamp(asof))].copy().sort_values("expiration")

def quote_age_warning(history_date,analysis_date):
 return "History date differs from analysis date; do not treat snapshot positioning as historical." if pd.Timestamp(history_date).date()!=pd.Timestamp(analysis_date).date() else None
