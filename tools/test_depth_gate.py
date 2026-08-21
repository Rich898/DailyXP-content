#!/usr/bin/env python3
"""The calibration gate (UNDERSTANDING.md §7): no DEEPENED story renders unless
DAILYXP_DEPTH_REPORTS_LIVE=1. Exit 0 = all pass."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.pop("DAILYXP_DEPTH_REPORTS_LIVE", None)
import report_stories as rs

ok = []
s = rs.detect_deepened("t", "Sci", "knows", "connects", {"why": "x"})
ok.append(("gated: a genuine climb produces NO story", s is None))
os.environ["DAILYXP_DEPTH_REPORTS_LIVE"] = "1"
s = rs.detect_deepened("t", "Sci", "knows", "connects", {"why": "x"})
ok.append(("lifted: the same climb produces the DEEPENED story", bool(s) and s["status"] == "DEEPENED"))
os.environ.pop("DAILYXP_DEPTH_REPORTS_LIVE", None)
for name, cond in ok: print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
sys.exit(0 if all(c for _, c in ok) else 1)
