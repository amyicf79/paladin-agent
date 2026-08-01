# -*- coding: utf-8 -*-
"""audit_web.py — Triniry 三环审计 Web 视图"""

import sys; sys.path.insert(0, "H:/GA/GenericAgent/paladin")

try:
    from fastapi import FastAPI, Request
    from fastapi.responses import HTMLResponse
except ImportError:
    FastAPI = None

app = FastAPI(title="Paladin Audit")

@app.get("/", response_class=HTMLResponse)
async def index():
    try:
        from trace import get_trace
        from paladin_adapter import PaladinAdapter
        from experience_store import ExperienceStore
        from market_scheduler import MarketScheduler

        tracer = get_trace()
        events = tracer.query(limit=50)
        n_traces = len(set(e.get("trace_id","?") for e in events))

        adapter = PaladinAdapter()
        acc = adapter.get_accuracy(50)

        store = ExperienceStore()
        exp_count = len(store.index)

        sched = MarketScheduler()
        stats = sched.get_meltdown_stats()
        explore_rate = stats.get("explore_rate", 0)
        eps = stats.get("epsilon", 0.1)

        html = f"""<html>
<head><title>Paladin Audit</title>
<style>body{{font-family:sans-serif;background:#111;color:#ddd;padding:20px}}
table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #333;padding:8px;text-align:left}}
th{{background:#222}}h2{{color:#4caf50}}.card{{background:#1a1a1a;padding:15px;margin:10px 0;border-radius:5px}}
.metric{{font-size:24px;font-weight:bold}}.green{{color:#4caf50}}.yellow{{color:#ff9800}}.red{{color:#f44336}}
</style></head><body>
<h1>Paladin Audit Dashboard</h1>
<div class=card><h2>Summary</h2>
<table><tr><th>Metric</th><th>Value</th></tr>
<tr><td>Traces</td><td class=metric>{n_traces}</td></tr>
<tr><td>Experiences</td><td class=metric>{exp_count}</td></tr>
<tr><td>Gate Accuracy</td><td class=metric>{f"{acc['accuracy']:.1%}" if acc.get("accuracy") else "N/A (cold start)"}</td></tr>
<tr><td>Epsilon</td><td class=metric>{eps}</td></tr>
<tr><td>Explore Rate</td><td class=metric>{explore_rate:.1%}</td></tr>
</table></div>
<div class=card><h2>Recent Trace Events ({len(events)})</h2>
<table><tr><th>Trace</th><th>Event</th><th>Agent</th><th>Zone</th><th>Outcome</th></tr>"""

        for e in events[-20:]:
            tid = str(e.get("trace_id",""))[:8]
            event = e.get("event","?")
            agent = e.get("agent","?")
            zone = e.get("zone","?")
            oc = e.get("outcome",{})
            status = oc.get("status","-")
            html += f"<tr><td>{tid}</td><td>{event}</td><td>{agent}</td><td>{zone}</td><td>{status}</td></tr>"

        html += "</table></div></body></html>"
        return HTMLResponse(html)
    except Exception as ex:
        return HTMLResponse(f"<html><body><h1>Error</h1><pre>{ex}</pre></body></html>")

if __name__ == "__main__" and FastAPI:
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8765)

elif FastAPI is None:
    print("⚠️ fastapi not installed. Run: pip install fastapi uvicorn")
else:
    print("✅ audit_web.py ready. Run: python audit_web.py")
