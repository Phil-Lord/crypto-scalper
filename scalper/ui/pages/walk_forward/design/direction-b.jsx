// Direction B v3
// One worker grid serves whichever phase is active (IS or OOS — never both).
// Single-row horizontal scroll when worker count exceeds the visible width.
// Inactive phase's CTA is disabled while the other is running.

function DirectionB({ runState = "is-running" }) {
  const study = STUDIES[0];

  // Pick which workers feed the single grid based on what's running
  const isRunning = runState === "is-running";
  const oosRunning = runState === "oos-running";
  const workers = isRunning ? WORKERS : OOS_WORKERS;

  // OOS window selector — when OOS is running, the third (in-progress) window is current.
  // When IS is running, the user is just viewing past results, default to most recent done.
  const selectedWindow = oosRunning ? OOS_WINDOWS[2] : OOS_WINDOWS[0];

  return (
    <div className="app">
      <TopBar />
      <div className="body" style={{ flexDirection: "row" }}>
        {/* Studies rail */}
        <div style={{ width: 320, borderRight: "1px solid var(--line-soft)", display: "flex", flexDirection: "column", flexShrink: 0 }}>
          <div style={{ padding: "16px 18px 12px" }}>
            <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: 10 }}>
              <h2 className="h2">Studies</h2>
              <span className="muted" style={{ fontSize: 11 }}>{STUDIES.length}</span>
            </div>
            <div className="field compact">
              <input className="control" placeholder="Filter studies…" />
            </div>
          </div>
          <div style={{ flex: 1, overflow: "hidden" }}>
            {STUDIES.map((s, i) => <StudyRailRow key={s.name} study={s} active={i === 0} />)}
          </div>
          <div style={{ padding: "12px 18px", borderTop: "1px solid var(--line-soft)" }}>
            <button className="btn ghost block sm">+ NEW STUDY</button>
          </div>
        </div>

        {/* Detail */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
          {/* Context strip */}
          <div style={{ padding: "14px 24px", borderBottom: "1px solid var(--line-soft)", display: "flex", alignItems: "center", gap: 22 }}>
            <div>
              <div className="muted" style={{ fontSize: 10, textTransform: "uppercase", letterSpacing: "0.08em" }}>Selected study</div>
              <div className="mono" style={{ fontSize: 13, marginTop: 3 }}>{study.name}</div>
            </div>
            <div className="vdivider" style={{ alignSelf: "stretch" }}></div>
            <Stat label="Strategy" value={study.strategy} />
            <Stat label="Pair" value={study.pair} />
            <Stat label="Trials" value={study.trialsCount.toLocaleString()} />
            <Stat label="Best IS" value={study.bestIs.toFixed(3)} highlight />
            <Stat label="OOS windows" value={OOS_WINDOWS.length} />
            <div style={{ marginLeft: "auto", display: "flex", gap: 10 }}>
              <button className="btn ghost sm">EXPORT</button>
            </div>
          </div>

          {/* Run-state banner */}
          <div style={{ padding: "0 24px" }}>
            <RunStateBanner runState={runState} />
          </div>

          {/* IS row */}
          <div style={{ padding: "14px 24px 14px", borderBottom: "1px solid var(--line-soft)", display: "grid", gridTemplateColumns: "260px 1fr", gap: 28 }}>
            <div>
              <div className="section-title" style={{ marginBottom: 12 }}>
                <span className="num">01</span>
                <span>IN-SAMPLE</span>
                <span className="rule"></span>
                {isRunning && <StatusPill status="running" />}
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                <div className="field compact"><div className="label">Window</div><div className="control mono">{study.isStart} → {study.isEnd}</div></div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                  <div className="field compact"><div className="label">+ Trials</div><div className="control mono">200</div></div>
                  <div className="field compact"><div className="label">Workers</div><div className="control mono">8</div></div>
                </div>
                {isRunning
                  ? <button className="btn danger sm" style={{ marginTop: 4 }}>■ STOP</button>
                  : <button className="btn sm" style={{ marginTop: 4 }} disabled={oosRunning}>▶ ADD TRIALS</button>}
              </div>
            </div>

            <div style={{ minWidth: 0 }}>
              <WorkerStrip
                workers={workers}
                phase={isRunning ? "IS" : oosRunning ? "OOS" : null}
                idle={!isRunning && !oosRunning}
              />
            </div>
          </div>

          {/* OOS row */}
          <div style={{ padding: "14px 24px 14px", display: "grid", gridTemplateColumns: "260px 1fr", gap: 28, flex: 1, minHeight: 0 }}>
            <div style={{ display: "flex", flexDirection: "column" }}>
              <div className="section-title" style={{ marginBottom: 12 }}>
                <span className="num">02</span>
                <span>OUT-OF-SAMPLE</span>
                <span className="rule"></span>
                {oosRunning && <StatusPill status="running" />}
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                <div className="field compact"><div className="label">Window start</div><div className="control mono">2026-10-15</div></div>
                <div className="field compact"><div className="label">Window end</div><div className="control mono">2027-01-15</div></div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                  <div className="field compact"><div className="label">Top N</div><div className="control mono">25</div></div>
                  <div className="field compact"><div className="label">Workers</div><div className="control mono">6</div></div>
                </div>
                {oosRunning
                  ? <button className="btn danger sm" style={{ marginTop: 4 }}>■ STOP</button>
                  : <button className="btn sm" style={{ marginTop: 4 }} disabled={isRunning}>▶ EVALUATE NEW WINDOW</button>}
                <div className="banner info" style={{ fontSize: 11, marginTop: 2, lineHeight: 1.4 }}>
                  Same trials, different window. PK = study + trial + window.
                </div>
              </div>
            </div>

            <div style={{ display: "flex", flexDirection: "column", minHeight: 0, minWidth: 0 }}>
              {/* OOS window selector */}
              <div className="section-title" style={{ marginBottom: 10 }}>
                <span>OOS WINDOWS</span>
                <span className="rule"></span>
                <span className="muted" style={{ fontSize: 11, textTransform: "none", letterSpacing: 0 }}>showing scores for the selected window</span>
              </div>
              <WindowTabs windows={OOS_WINDOWS} selectedId={selectedWindow.id} />

              {/* Trials table */}
              <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 14, marginBottom: 8 }}>
                <span className="section-title" style={{ flex: "0 0 auto" }}>
                  <span>TOP {TOP_TRIALS.length} TRIALS</span>
                </span>
                <span className="rule" style={{ height: 1, flex: 1, background: "var(--line-soft)" }}></span>
                {selectedWindow.bestOos !== null && (
                  <>
                    <span className="pill error" style={{ fontSize: 10 }}>{selectedWindow.overfitCount} OVERFIT</span>
                    <span className="pill done" style={{ fontSize: 10 }}>{selectedWindow.generalisedCount} GENERALISE</span>
                  </>
                )}
              </div>
              <div className="panel" style={{ background: "var(--panel)", flex: 1, overflow: "hidden", minHeight: 0 }}>
                <table className="t">
                  <thead>
                    <tr>
                      <th>Trial</th>
                      <th className="num">IS score</th>
                      <th className="num">OOS score</th>
                      <th className="num">Δ</th>
                      <th>Verdict</th>
                      <th style={{ width: 32 }}></th>
                    </tr>
                  </thead>
                  <tbody>
                    {TOP_TRIALS.slice(0, 10).map(t => {
                      const oos = OOS_BY_WINDOW[selectedWindow.id][t.n];
                      const has = oos !== null && oos !== undefined;
                      const delta = has ? oos - t.isVal : null;
                      const overfit = has && oos < 0.5;
                      return (
                        <tr key={t.n} className={overfit ? "overfit" : ""}>
                          <td className="trial-cell">#{t.n}</td>
                          <td className="num">{t.isVal.toFixed(3)}</td>
                          <td className="num">{has
                            ? <span className={oos > 0 ? "pos" : "neg"}>{oos.toFixed(3)}</span>
                            : <span className="dim">—</span>}</td>
                          <td className="num">{delta !== null
                            ? <span className="delta mono">{delta > 0 ? "+" : ""}{delta.toFixed(3)}</span>
                            : <span className="dim">—</span>}</td>
                          <td>{!has
                            ? <span className="pill pending" style={{ fontSize: 10 }}>PENDING</span>
                            : overfit
                              ? <span className="pill error" style={{ fontSize: 10 }}>OVERFIT</span>
                              : <span className="pill done" style={{ fontSize: 10 }}>GENERALISES</span>}</td>
                          <td>
                            <button className="copy-btn" title="Copy trial parameters as JSON">
                              <svg width="13" height="13" viewBox="0 0 16 16" fill="none">
                                <rect x="4" y="4" width="9" height="9" rx="1.5" stroke="currentColor" strokeWidth="1.3"/>
                                <path d="M3 11V4a1 1 0 0 1 1-1h7" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/>
                              </svg>
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function RunStateBanner({ runState }) {
  if (runState === "is-running") {
    return (
      <div className="banner warn" style={{ marginTop: 12, fontSize: 12 }}>
        <span className="icon">●</span>
        <span><b>In-sample optimisation running.</b> Out-of-sample evaluation is disabled until this finishes — only one phase can run at a time.</span>
      </div>
    );
  }
  if (runState === "oos-running") {
    return (
      <div className="banner warn" style={{ marginTop: 12, fontSize: 12 }}>
        <span className="icon">●</span>
        <span><b>Out-of-sample evaluation running</b> on Oct 2026 – Jan 2027. In-sample is disabled until this finishes.</span>
      </div>
    );
  }
  return null;
}

function Stat({ label, value, highlight }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
      <div className="muted" style={{ fontSize: 10, textTransform: "uppercase", letterSpacing: "0.1em" }}>{label}</div>
      <div className="mono" style={{ fontSize: 14, color: highlight ? "var(--green-2)" : "var(--text)" }}>{value}</div>
    </div>
  );
}

function StudyRailRow({ study, active }) {
  return (
    <div className={"study-rail-row" + (active ? " active" : "")}
      style={{
        padding: "12px 18px",
        borderBottom: "1px solid var(--line-soft)",
        background: active ? "var(--panel-2)" : "transparent",
        boxShadow: active ? "inset 2px 0 0 var(--green-2)" : "none",
        cursor: "pointer",
      }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8 }}>
        <div className="mono" style={{ fontSize: 12, color: "var(--text)", lineHeight: 1.3, wordBreak: "break-all" }}>
          {study.name}
        </div>
        {study.lastRun === "running" && <StatusPill status="running" label="LIVE" />}
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 8 }}>
        <div style={{ display: "flex", gap: 14, fontSize: 11, color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
          <span><span className="dim">trials</span> {study.trialsCount.toLocaleString()}</span>
          <span><span className="dim">IS</span> {study.bestIs.toFixed(2)}</span>
          {study.bestOos !== null
            ? <span><span className="dim">OOS</span> {study.bestOos.toFixed(2)}</span>
            : <span className="dim">no OOS</span>}
        </div>
        {study.lastRun !== "running" && (
          <span className="dim mono" style={{ fontSize: 10 }}>{study.lastRun}</span>
        )}
      </div>
    </div>
  );
}

// Single-row, horizontally scrolling worker strip.
// Tiles keep their original size; ≥7 workers triggers horizontal scroll.
function WorkerStrip({ workers, phase, idle }) {
  return (
    <div>
      <div className="section-title" style={{ marginBottom: 10 }}>
        <span>{idle ? "WORKERS" : `${phase} WORKERS`} · {idle ? "—" : workers.length}</span>
        <span className="rule"></span>
        {idle
          ? <span className="muted mono" style={{ fontSize: 11, textTransform: "none", letterSpacing: 0 }}>idle · last run 2h ago</span>
          : <StatusPill status="running" label="LIVE" />}
      </div>
      {idle ? (
        <div style={{
          height: 90, display: "flex", alignItems: "center", justifyContent: "center",
          border: "1px dashed var(--line-soft)", borderRadius: 3,
          color: "var(--text-dim)", fontSize: 12,
        }}>
          No worker activity — start an IS or OOS run.
        </div>
      ) : (
        <div className="worker-strip">
          {workers.map(w => <WorkerTile key={w.id} w={w} />)}
        </div>
      )}
    </div>
  );
}

function WorkerTile({ w }) {
  const isPending = w.status === "pending";
  return (
    <div className="worker-tile worker-tile-fixed">
      <div className="top">
        <span>worker {w.id}</span>
        <StatusPill status={w.status} />
      </div>
      <div className="stat">
        {isPending ? <span className="dim">—</span> : w.best.toFixed(3)}
      </div>
      <div className="meta">
        <span>{isPending ? "queued" : `trial ${w.trial}`}</span>
        <span>{Math.round(w.progress * 100)}%</span>
      </div>
      <div className={"progress" + (w.status === "running" ? " amber" : "")}>
        <span style={{ width: `${w.progress * 100}%` }}></span>
      </div>
    </div>
  );
}

function WindowTabs({ windows, selectedId }) {
  return (
    <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
      {windows.map(w => {
        const active = w.id === selectedId;
        const running = w.status === "running";
        return (
          <div key={w.id} className={"window-tab" + (active ? " active" : "")}>
            <div className="window-tab-head">
              <span className="mono" style={{ fontSize: 12, color: active ? "var(--text)" : "var(--text-2)" }}>
                {w.label}
              </span>
              {running && <StatusPill status="running" />}
            </div>
            <div className="window-tab-meta">
              <span className="mono">{w.start} → {w.end}</span>
            </div>
            <div className="window-tab-stats">
              {w.bestOos !== null
                ? <>
                    <span><span className="dim">best</span> <span className="mono pos">{w.bestOos.toFixed(3)}</span></span>
                    <span><span className="dim">gen</span> <span className="mono">{w.generalisedCount}</span></span>
                    <span><span className="dim">over</span> <span className="mono" style={{ color: "var(--red)" }}>{w.overfitCount}</span></span>
                  </>
                : <span className="dim mono" style={{ fontSize: 10 }}>evaluating · {w.runAt}</span>}
            </div>
          </div>
        );
      })}
      <div className="window-tab new">
        <div className="window-tab-head">
          <span className="muted" style={{ fontSize: 12, fontFamily: "var(--font-mono)" }}>+ new window</span>
        </div>
        <div className="window-tab-meta dim">
          configure on the left
        </div>
      </div>
    </div>
  );
}

window.DirectionB = DirectionB;
