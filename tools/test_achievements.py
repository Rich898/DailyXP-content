#!/usr/bin/env python3
"""Self-contained regression test for achievements.py — all 12 badge types + idempotency.
Synthetic log/runs/state, no private data or names. CI-runnable: exit 0 = pass."""
import json, os, sys, tempfile, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import achievements as ach

tmp = tempfile.mkdtemp(prefix="ach_regress_"); os.makedirs(f"{tmp}/work")

def L(subj, topic, badge, frm, to, frep, trep, rd):
    return {"applied": True, "student": "s1", "subject": subj, "topic": topic, "badge": badge,
            "from_state": frm, "to_state": to, "from_repair": frep, "to_repair": trep, "run_date": rd}
log = [
    L("Maths","Prism","✓_sure","developing","solid",False,False,"2026-08-04"),
    L("Maths","Triangle","✓_sure","REPAIR","developing",True,False,"2026-08-05"),
    L("History","Causation","✓_sure","developing","solid",False,False,"2026-08-03"),
    L("History","Causation","✓_sure","solid","solid",False,False,"2026-08-05"),
    L("History","Causation","✓_sure","solid","solid",False,False,"2026-08-07"),
    L("English","Chars","FW","developing","developing",False,False,"2026-08-04"),
    L("English","Chars","✓_sure","developing","developing",False,False,"2026-08-06"),
]
with open(f"{tmp}/work/state_writer_log.jsonl","w") as f:
    for e in log: f.write(json.dumps(e)+"\n")

def R(tag, day, sd, sp, st, score, lucky=False, cw=False):
    return {"student":"s1","name":"s1","tag":tag,"day":day,"set_date":sd,"run_date":sd,
            "ts":sd+"T08:00:00+00:00","ts_raw":sd+"T08:00:00Z","attempt":1,"canonical":True,
            "is_test":False,"score":score,"speed":{"right":sp[0],"of":sp[1]},
            "steady":{"right":st[0],"of":st[1]},"questions":[],
            "shell_flags":{"skips":[],"confidentWrong":(["T1"] if cw else []),"slowWrong":[],
                           "fastWrong":[],"luckyGuess":(["S1"] if lucky else [])}}
runs = [
    R("P0","WED","2026-07-29",(7,7),(4,4),1000),
    R("M","MON","2026-08-03",(7,7),(4,4),1200),
    R("T","TUE","2026-08-04",(6,7),(3,4),1100, cw=True),
    R("W·BLITZ","WED","2026-08-05",(9,10),(2,2),1500),
    R("Th","THU","2026-08-06",(7,7),(4,4),1250, lucky=True),
    R("F·BOSS","FRI","2026-08-07",(2,2),(4,4),1400),
]
json.dump({"runs":runs}, open(f"{tmp}/work/runs.json","w"), indent=2)

def T(subj, topic, state): return {"subject":subj,"topic":topic,"state":state,"repair":False}
state = {"students":{"s1":{"topics":[
    T("Geography","Push/pull","solid"), T("Geography","Urbanisation","solid"),
    T("Maths","Triangle","developing"), T("Maths","Prism","solid"),
]}}}
json.dump(state, open(f"{tmp}/work/state.json","w"), indent=2)

awarded, _ = ach.process(tmp, dry_run=False)
got = {a["badge"] for a in awarded}
expect = {"First Blood","Clean Run","Boss Slayer","Blitz Master","Perfect Week","Streak",
          "Locked It","Comeback","Sure Shot","Untouchable","Calm Hands","Full Clear"}
awarded2, _ = ach.process(tmp, dry_run=False)

ok = True
def chk(d,c):
    global ok; print(f"  [{'PASS' if c else 'FAIL'}] {d}"); ok = ok and c
print("achievements regression:")
chk("all 12 badge types fired", not (expect - got))
chk("no unexpected badge types", not (got - expect))
chk("streak bronze only (5 days)", [a["key"] for a in awarded if a["badge"]=="Streak"] == ["Streak|bronze"])
chk("Full Clear = Geography only", [a["key"] for a in awarded if a["badge"]=="Full Clear"] == ["Full Clear|Geography"])
chk("idempotent: re-run awards nothing", len(awarded2) == 0)
shutil.rmtree(tmp)
print("ALL PASS ✓" if ok else "FAILURES ✗")
sys.exit(0 if ok else 1)
