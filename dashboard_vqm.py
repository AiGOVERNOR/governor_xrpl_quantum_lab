"""
Governor VQM Dashboard
----------------------
Small FastAPI app that renders a minimal HTML dashboard and exposes
a /snapshot endpoint for the front-end.

It calls run_vqm_cycle_v4() directly, so you can run it independently
of api_vqm.py.
"""

import json
from typing import Any, Dict

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

from ecosystem.pipeline_v4 import run_vqm_cycle_v4

app = FastAPI(
    title="Governor VQM Dashboard",
    description="Minimal web UI over the Governor VQM brain.",
    version="1.0.0",
)


def _safe_get(d: Dict[str, Any], *keys: str) -> Any:
    cur: Any = d
    for k in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(k)
    return cur


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    """
    Serves a single-page HTML dashboard that polls /snapshot.
    """
    html = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Governor VQM Dashboard</title>
  <style>
    body {
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background-color: #050816;
      color: #f9fafb;
      margin: 0;
      padding: 0;
    }
    header {
      padding: 12px 20px;
      background: linear-gradient(90deg, #0f172a, #111827);
      border-bottom: 1px solid #1f2937;
    }
    h1 {
      margin: 0;
      font-size: 1.25rem;
    }
    main {
      padding: 16px;
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
    }
    .card {
      background: #020617;
      border-radius: 12px;
      border: 1px solid #1f2937;
      padding: 12px;
      box-shadow: 0 10px 25px rgba(0,0,0,0.45);
    }
    .card h2 {
      margin-top: 0;
      font-size: 1rem;
      margin-bottom: 8px;
      color: #e5e7eb;
    }
    .kv {
      font-size: 0.9rem;
      line-height: 1.3rem;
    }
    .badge {
      display: inline-block;
      padding: 2px 8px;
      border-radius: 999px;
      font-size: 0.75rem;
      margin-left: 6px;
    }
    .badge-normal { background: #065f46; }
    .badge-elevated { background: #92400e; }
    .badge-extreme { background: #7f1d1d; }
    .badge-low { background: #1d4ed8; }
    pre {
      font-size: 0.75rem;
      background: #020617;
      border-radius: 8px;
      padding: 8px;
      overflow: auto;
      border: 1px solid #111827;
    }
    footer {
      padding: 8px 16px;
      font-size: 0.75rem;
      color: #9ca3af;
      border-top: 1px solid #1f2937;
      background: #020617;
    }
    .pill {
      display: inline-block;
      padding: 2px 10px;
      border-radius: 999px;
      background: #0f172a;
      border: 1px solid #1f2937;
      margin-right: 6px;
      font-size: 0.7rem;
    }
  </style>
</head>
<body>
  <header>
    <h1>Governor VQM Dashboard <span id="band-pill" class="pill">band: unknown</span><span id="mode-pill" class="pill">mode: unknown</span></h1>
  </header>
  <main>
    <section class="card">
      <h2>Network State</h2>
      <div class="kv" id="network-state">
        Loading...
      </div>
    </section>
    <section class="card">
      <h2>Guardian</h2>
      <div class="kv" id="guardian-state">
        Loading...
      </div>
    </section>
    <section class="card">
      <h2>Scheduler</h2>
      <div class="kv" id="scheduler-state">
        Loading...
      </div>
    </section>
    <section class="card">
      <h2>Raw Snapshot</h2>
      <pre id="raw-json">Loading...</pre>
    </section>
  </main>
  <footer>
    <span id="timestamp-pill" class="pill">ts: --</span>
    <span class="pill">read-only · no signing · no trading</span>
  </footer>
  <script>
    function bandClass(band) {
      band = (band || "").toLowerCase();
      if (band === "low") return "badge badge-low";
      if (band === "elevated") return "badge badge-elevated";
      if (band === "extreme") return "badge badge-extreme";
      return "badge badge-normal";
    }

    async function refresh() {
      try {
        const res = await fetch('/snapshot');
        const data = await res.json();

        // Raw JSON
        document.getElementById('raw-json').textContent = JSON.stringify(data, null, 2);

        const ns = data.network_state || {};
        const fh = data.fee_horizon || {};
        const guardian = data.guardian || {};
        const scheduler = data.scheduler || {};
        const mesh_intent = data.mesh_intent || {};

        const band = fh.projected_fee_band || (mesh_intent.mode || 'unknown');
        const median = ns.txn_median_fee || 'n/a';
        const load = ns.load_factor || 'n/a';

        document.getElementById('network-state').textContent =
          `ledger: ${ns.ledger_seq || 'n/a'}
median_fee: ${median} drops
load_factor: ${load}
projected_fee_band: ${band}`;

        const guardianMode = guardian.policy ? guardian.policy.mode : (mesh_intent.mode || 'unknown');
        document.getElementById('guardian-state').textContent =
          `mode: ${guardianMode}
status: ${(guardian.policy && guardian.policy.status) || 'n/a'}
explanation: ${(guardian.llm && guardian.llm.explanation) || 'n/a'}`;

        const schedBand = scheduler.band || band;
        const jobs = (scheduler.jobs || []).map(
          j => `${j.name}: base=${j.base_concurrency}, mode=${j.mode || 'n/a'}`
        );
        document.getElementById('scheduler-state').textContent =
          `band: ${schedBand}
jobs:
- ${jobs.join('\\n- ') || 'none'}`;

        const bandPill = document.getElementById('band-pill');
        bandPill.textContent = `band: ${band}`;
        bandPill.className = 'pill ' + bandClass(band);

        const modePill = document.getElementById('mode-pill');
        modePill.textContent = `mode: ${guardianMode}`;
        modePill.className = 'pill';

        const tsPill = document.getElementById('timestamp-pill');
        tsPill.textContent = `ts: ${data.timestamp || '--'}`;
      } catch (e) {
        document.getElementById('raw-json').textContent =
          'Error loading snapshot:\\n' + (e && e.toString());
      }
    }

    refresh();
    setInterval(refresh, 10000);
  </script>
</body>
</html>
"""
    return HTMLResponse(content=html)


@app.get("/snapshot", response_class=JSONResponse)
def snapshot() -> JSONResponse:
    """
    Returns a fresh VQM state snapshot for the dashboard.
    """
    state = run_vqm_cycle_v4()
    return JSONResponse(content=state)
