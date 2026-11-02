
import unittest
import numpy as np
import pandas as pd
from data_engine import classify,future_expirations
from positioning_engine import profile_crossings
from strategy_engine import expiry_payoff

class TestEngines(unittest.TestCase):
 def test_zero_crossing(self):
  d=pd.DataFrame({"strike":[90,100],"gex_profile":[-5,5]})
  self.assertEqual(profile_crossings(d),[95.])
 def test_zero_dte_retained(self):
  d=pd.DataFrame({"expiration":pd.to_datetime(["2026-11-02","2026-11-03"])})
  self.assertEqual(len(future_expirations(d,"2026-11-02")),2)
 def test_butterfly_tail_risk_exceeds_debit(self):
  # 90/100/120 call BWB, debit $1: tail risk is $1,100
  payoff=expiry_payoff([0,90,100,120,200],"CALL",90,100,120,1)
  self.assertAlmostEqual(-payoff.min(),1100.)
 def test_schema(self):
  self.assertEqual(classify(pd.DataFrame(columns=["strike","call_gex","put_gex","net_gex"])),"gex_strike")

if __name__=="__main__":unittest.main()
