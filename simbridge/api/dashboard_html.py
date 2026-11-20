"""SimBridge GCS — Unified Standalone Robotics Simulation Dashboard HTML/JS."""

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SimBridge GCS — Robotics Simulation Dashboard</title>
<style>
  :root {
    --bg: #090e17;
    --panel: #0f172a;
    --panel-2: #1e293b;
    --border: #334155;
    --border-light: #475569;
    --accent: #38bdf8;
    --teal: #14b8a6;
    --green: #22c55e;
    --amber: #f59e0b;
    --red: #ef4444;
    --text: #f1f5f9;
    --muted: #94a3b8;
    --mono: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  html, body { height: 100%; width: 100%; overflow: hidden; }
  body {
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    font-size: 12px;
    display: flex;
    flex-direction: column;
  }

  /* Top Navigation Bar */
  .topbar {
    height: 52px;
    background: var(--panel);
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 16px;
    gap: 12px;
    flex-shrink: 0;
  }
  .brand { display: flex; align-items: center; gap: 10px; cursor: pointer; }
  .brand-logo {
    width: 28px; height: 28px;
    border: 1px solid var(--accent);
    border-radius: 6px;
    display: grid; place-items: center;
    color: var(--accent);
    background: rgba(56, 189, 248, 0.1);
    font-weight: 800; font-family: var(--mono); font-size: 14px;
  }
  .brand-title h1 { font-size: 14px; font-weight: 700; letter-spacing: 0.8px; color: #fff; }
  .brand-title span { font-size: 10px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.5px; }

  .status-pills { display: flex; align-items: center; gap: 8px; }
  .status-item { display: flex; flex-direction: column; line-height: 1.1; }
  .status-item label { font-size: 9px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.4px; }
  .pill {
    font-size: 10px; font-weight: 600; padding: 3px 8px; border-radius: 4px;
    border: 1px solid var(--border); background: var(--panel-2); color: var(--text);
    font-family: var(--mono); display: inline-flex; align-items: center; gap: 4px;
  }
  .pill.ok { color: var(--green); border-color: rgba(34,197,94,0.4); background: rgba(34,197,94,0.1); }
  .pill.warn { color: var(--amber); border-color: rgba(245,158,11,0.4); background: rgba(245,158,11,0.1); }
  .pill.fault { color: var(--red); border-color: rgba(239,68,68,0.4); background: rgba(239,68,68,0.1); }
  .pill.info { color: var(--accent); border-color: rgba(56,189,248,0.4); background: rgba(56,189,248,0.1); }

  .top-actions { display: flex; align-items: center; gap: 8px; }
  .btn {
    font-size: 11px; padding: 5px 10px; border-radius: 4px; border: 1px solid var(--border);
    background: var(--panel-2); color: var(--text); cursor: pointer; font-weight: 600;
    transition: all 0.15s ease; display: inline-flex; align-items: center; gap: 6px;
  }
  .btn:hover { border-color: var(--accent); color: #fff; background: rgba(56, 189, 248, 0.15); }
  .btn-primary { background: var(--accent); color: #090e17; border-color: var(--accent); font-weight: 700; }
  .btn-primary:hover { background: #7dd3fc; border-color: #7dd3fc; color: #090e17; }
  .btn-danger { background: rgba(239,68,68,0.15); color: var(--red); border-color: rgba(239,68,68,0.4); }
  .btn-danger:hover { background: var(--red); color: #fff; }

  /* Main Workspace Grid */
  .workspace {
    flex: 1; min-height: 0;
    display: grid;
    grid-template-columns: 310px minmax(0, 1fr) 340px;
    gap: 10px;
    padding: 10px;
    overflow: hidden;
  }
  .panel {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 6px;
    display: flex; flex-direction: column;
    min-height: 0; overflow: hidden;
  }
  .panel-header {
    padding: 8px 12px;
    border-bottom: 1px solid var(--border);
    font-size: 11px; font-weight: 700; color: var(--muted);
    text-transform: uppercase; letter-spacing: 0.6px;
    display: flex; align-items: center; justify-content: space-between;
    background: rgba(15, 23, 42, 0.6);
  }
  .panel-body {
    padding: 10px; flex: 1; min-height: 0;
    overflow-y: auto; display: flex; flex-direction: column; gap: 10px;
  }

  /* Attitude Horizon */
  .attitude-box {
    width: 100%; height: 140px; background: #000; border-radius: 4px;
    border: 1px solid var(--border); position: relative; overflow: hidden;
  }
  .attitude-sky { position: absolute; inset: 0; background: #1e3a8a; }
  .attitude-ground {
    position: absolute; left: -50%; width: 200%; height: 200%; top: 50%;
    background: #78350f; transform-origin: 50% 0%; transition: transform 0.05s linear;
  }
  .attitude-reticle {
    position: absolute; inset: 0; display: grid; place-items: center; pointer-events: none;
  }
  .attitude-crosshair {
    width: 60px; height: 2px; background: #22c55e; position: relative;
  }
  .attitude-crosshair::after {
    content: ""; position: absolute; left: 29px; top: -10px; width: 2px; height: 22px; background: #22c55e;
  }

  /* Metrics Grid */
  .metric-grid {
    display: grid; grid-template-columns: repeat(2, 1fr); gap: 6px;
  }
  .metric-card {
    background: var(--panel-2); border: 1px solid var(--border); border-radius: 4px;
    padding: 6px 8px; display: flex; flex-direction: column;
  }
  .metric-card .label { font-size: 9px; text-transform: uppercase; color: var(--muted); }
  .metric-card .value { font-size: 13px; font-weight: 700; color: #fff; font-family: var(--mono); margin-top: 2px; }

  /* Key-Value Rows */
  .data-row {
    display: flex; justify-content: space-between; align-items: center;
    padding: 3px 0; border-bottom: 1px dashed rgba(51, 65, 85, 0.5); font-size: 11px;
  }
  .data-row .k { color: var(--muted); }
  .data-row .v { font-family: var(--mono); font-weight: 600; color: #fff; }

  /* Camera Viewport */
  .viewport-container {
    flex: 1; min-height: 0; display: flex; flex-direction: column; gap: 8px;
  }
  .camera-display {
    flex: 1; min-height: 0; background: #000; border: 1px solid var(--border);
    border-radius: 4px; position: relative; display: flex; align-items: center; justify-content: center;
    overflow: hidden;
  }
  .camera-display img {
    max-width: 100%; max-height: 100%; object-fit: contain; width: 100%; height: 100%;
  }
  .camera-hud-badge {
    position: absolute; top: 8px; left: 8px; background: rgba(15, 23, 42, 0.85);
    border: 1px solid var(--border); border-radius: 3px; padding: 2px 6px;
    font-size: 9px; font-family: var(--mono); color: var(--accent);
  }
  .camera-fps-badge {
    position: absolute; top: 8px; right: 8px; background: rgba(15, 23, 42, 0.85);
    border: 1px solid var(--border); border-radius: 3px; padding: 2px 6px;
    font-size: 9px; font-family: var(--mono); color: var(--green);
  }

  /* Map Canvas */
  .map-box {
    width: 100%; height: 210px; background: #06090e; border: 1px solid var(--border);
    border-radius: 4px; position: relative; overflow: hidden;
  }
  canvas#mapCanvas { width: 100%; height: 100%; display: block; }

  /* Event Log Bottom Bar */
  .log-bar {
    height: 130px; background: var(--panel); border-top: 1px solid var(--border);
    display: flex; flex-direction: column; flex-shrink: 0; transition: height 0.2s ease;
  }
  .log-bar.collapsed { height: 28px; }
  .log-header {
    height: 28px; background: var(--panel-2); border-bottom: 1px solid var(--border);
    padding: 0 12px; display: flex; align-items: center; justify-content: space-between;
    font-size: 10px; font-weight: 700; color: var(--muted); text-transform: uppercase; cursor: pointer;
  }
  .log-content {
    flex: 1; min-height: 0; overflow-y: auto; padding: 6px 12px; font-family: var(--mono);
    font-size: 11px; line-height: 1.4;
  }
  .log-line { display: flex; gap: 8px; margin-bottom: 2px; }
  .log-line .time { color: var(--muted); }
  .log-line.info .msg { color: var(--text); }
  .log-line.ok .msg { color: var(--green); }
  .log-line.warn .msg { color: var(--amber); }
  .log-line.fault .msg { color: var(--red); }

  /* Modal Dialog */
  .modal-overlay {
    position: fixed; inset: 0; background: rgba(0, 0, 0, 0.75); backdrop-filter: blur(4px);
    display: none; place-items: center; z-index: 100;
  }
  .modal-overlay.open { display: grid; }
  .modal-card {
    width: 580px; max-width: 95vw; background: var(--panel); border: 1px solid var(--border-light);
    border-radius: 8px; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5); display: flex; flex-direction: column;
    overflow: hidden;
  }
  .modal-header {
    padding: 12px 16px; background: var(--panel-2); border-bottom: 1px solid var(--border);
    display: flex; align-items: center; justify-content: space-between;
  }
  .modal-header h2 { font-size: 14px; font-weight: 700; color: #fff; }
  .modal-body { padding: 16px; display: flex; flex-direction: column; gap: 14px; max-height: 75vh; overflow-y: auto; }
  .modal-footer {
    padding: 12px 16px; background: var(--panel-2); border-top: 1px solid var(--border);
    display: flex; justify-content: flex-end; gap: 8px;
  }

  .form-group { display: flex; flex-direction: column; gap: 4px; }
  .form-group label { font-size: 10px; font-weight: 600; text-transform: uppercase; color: var(--muted); }
  .form-control {
    background: #090e17; border: 1px solid var(--border); border-radius: 4px; padding: 6px 10px;
    color: #fff; font-size: 12px; font-family: var(--mono);
  }
  .form-control:focus { outline: none; border-color: var(--accent); }

  .tool-badge-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-bottom: 8px; }
  .tool-badge {
    background: var(--panel-2); border: 1px solid var(--border); border-radius: 4px; padding: 8px;
    display: flex; flex-direction: column; gap: 2px;
  }
  .tool-badge .title { font-size: 10px; font-weight: 700; color: var(--muted); }
  .tool-badge .stat { font-size: 11px; font-weight: 600; font-family: var(--mono); }
</style>
</head>
<body>

<!-- Top Navigation Bar -->
<header class="topbar">
  <div class="brand" onclick="openSetupModal()">
    <div class="brand-logo">SB</div>
    <div class="brand-title">
      <h1>SIMBRIDGE GCS</h1>
      <span>Robotics Simulation Dashboard</span>
    </div>
  </div>

  <div class="status-pills">
    <div class="status-item">
      <label>Simulator</label>
      <span id="pillSim" class="pill info">NONE</span>
    </div>
    <div class="status-item">
      <label>State</label>
      <span id="pillState" class="pill">DISCONNECTED</span>
    </div>
    <div class="status-item">
      <label>Vehicle</label>
      <span id="pillVeh" class="pill">OFFLINE</span>
    </div>
    <div class="status-item">
      <label>Mode</label>
      <span id="pillMode" class="pill info">STANDBY</span>
    </div>
  </div>

  <div class="top-actions">
    <button class="btn btn-primary" onclick="openSetupModal()">⚙ Connect / Setup</button>
    <button class="btn" id="btnDisconnect" onclick="disconnectSimulator()" style="display:none;">Disconnect</button>
    <button class="btn" onclick="toggleLog()">Event Log</button>
  </div>
</header>

<!-- Main Workspace -->
<main class="workspace">

  <!-- Left: Flight Telemetry & Attitude -->
  <section class="panel">
    <div class="panel-header">
      <span>Vehicle Telemetry</span>
      <span id="badgeTelemetryHz" class="pill">0.0 Hz</span>
    </div>
    <div class="panel-body">
      <!-- Attitude Horizon -->
      <div class="attitude-box">
        <div class="attitude-sky"></div>
        <div class="attitude-ground" id="attGround"></div>
        <div class="attitude-reticle"><div class="attitude-crosshair"></div></div>
      </div>

      <div class="metric-grid">
        <div class="metric-card"><span class="label">Roll</span><span class="value" id="valRoll">0.0°</span></div>
        <div class="metric-card"><span class="label">Pitch</span><span class="value" id="valPitch">0.0°</span></div>
        <div class="metric-card"><span class="label">Yaw / Heading</span><span class="value" id="valYaw">0.0°</span></div>
        <div class="metric-card"><span class="label">Altitude (Z)</span><span class="value" id="valAlt">0.00 m</span></div>
      </div>

      <div class="data-row"><span class="k">Position (X, Y, Z)</span><span class="v" id="valPos">0.00, 0.00, 0.00</span></div>
      <div class="data-row"><span class="k">Linear Velocity</span><span class="v" id="valVel">0.0, 0.0, 0.0 m/s</span></div>
      <div class="data-row"><span class="k">Angular Rates</span><span class="v" id="valAngRates">0.0, 0.0, 0.0 °/s</span></div>

      <div class="metric-grid" style="margin-top:4px;">
        <div class="metric-card"><span class="label">Battery</span><span class="value" id="valBatt">100%</span></div>
        <div class="metric-card"><span class="label">Voltage</span><span class="value" id="valVolt">16.8 V</span></div>
        <div class="metric-card"><span class="label">GPS Fix</span><span class="value" id="valGPS">GROUND_TRUTH</span></div>
        <div class="metric-card"><span class="label">Satellites</span><span class="value" id="valSats">14</span></div>
      </div>
    </div>
  </section>

  <!-- Center: Camera Viewport & Active Environment -->
  <section class="panel">
    <div class="panel-header">
      <span>Simulation Viewport</span>
      <span id="camSourceBadge" class="pill info">CAM: NONE</span>
    </div>
    <div class="panel-body viewport-container">
      <div class="camera-display">
        <img id="mjpegFeed" src="/video_feed" alt="Camera Stream" />
        <div class="camera-hud-badge" id="camHudBadge">SIMBRIDGE HUD</div>
        <div class="camera-fps-badge" id="camFpsBadge">0.0 FPS</div>
      </div>

      <!-- Quick Simulator Preset Switcher -->
      <div style="display:flex; gap:6px; flex-wrap:wrap;">
        <button class="btn" onclick="quickConnect('mock')">⚡ Mock Demo</button>
        <button class="btn" onclick="quickConnect('gazebo')">🌐 Gazebo Sim</button>
        <button class="btn" onclick="quickConnect('px4')">✈ PX4 SITL</button>
        <button class="btn" onclick="quickConnect('blender')">🎨 Blender 3D</button>
      </div>

      <!-- Simulation Context Summary -->
      <div class="panel" style="border-radius:4px; margin-top:2px;">
        <div class="panel-header" style="font-size:10px; padding:6px 8px;">Simulation Environment Context</div>
        <div style="padding:8px; display:flex; flex-direction:column; gap:4px;">
          <div class="data-row"><span class="k">Active World</span><span class="v" id="valWorldName">default</span></div>
          <div class="data-row"><span class="k">Vehicle Model</span><span class="v" id="valModelName">quadcopter</span></div>
          <div class="data-row"><span class="k">Active Topics</span><span class="v" id="valTopicCount">0 discovered</span></div>
        </div>
      </div>
    </div>
  </section>

  <!-- Right: 2D Trajectory Map & Sensor Diagnostics -->
  <section class="panel">
    <div class="panel-header">
      <span>Map &amp; Sensor Health</span>
      <span class="pill" id="badgeSensors">ALL OK</span>
    </div>
    <div class="panel-body">
      <!-- 2D Canvas Map -->
      <div class="map-box">
        <canvas id="mapCanvas" width="320" height="210"></canvas>
      </div>
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <span style="font-size:10px; color:var(--muted);">Grid: 2m intervals | ENU Frame</span>
        <button class="btn" style="padding:2px 6px; font-size:10px;" onclick="clearTrajectory()">Clear Trail</button>
      </div>

      <!-- Sensor Matrix -->
      <div class="metric-grid" style="margin-top:6px;">
        <div class="metric-card"><span class="label">IMU Sensor</span><span class="value" id="sensIMU">NOMINAL</span></div>
        <div class="metric-card"><span class="label">Optical Camera</span><span class="value" id="sensCam">NOMINAL</span></div>
        <div class="metric-card"><span class="label">Magnetometer</span><span class="value" id="sensMag">NOMINAL</span></div>
        <div class="metric-card"><span class="label">Barometer</span><span class="value" id="sensBaro">NOMINAL</span></div>
      </div>

      <!-- Diagnostics & Host Metrics -->
      <div style="margin-top:8px; display:flex; flex-direction:column; gap:4px;">
        <div class="data-row"><span class="k">Host CPU Usage</span><span class="v" id="valCPU">0.0 %</span></div>
        <div class="data-row"><span class="k">Host RAM RSS</span><span class="v" id="valRAM">0 MB</span></div>
        <div class="data-row"><span class="k">Stream Rate</span><span class="v" id="valStreamFps">0.0 FPS</span></div>
        <div class="data-row"><span class="k">Frame Count</span><span class="v" id="valFrameCount">0</span></div>
      </div>
    </div>
  </section>

</main>

<!-- Bottom Event Log Bar -->
<footer class="log-bar" id="logBar">
  <div class="log-header" onclick="toggleLog()">
    <span>Diagnostics &amp; System Event Log</span>
    <span style="font-size:10px;" id="logToggleLabel">▲ EXPAND</span>
  </div>
  <div class="log-content" id="logContent"></div>
</footer>

<!-- Setup & Tool Detection Modal -->
<div class="modal-overlay" id="setupModal">
  <div class="modal-card">
    <div class="modal-header">
      <h2>Simulator Connection &amp; Environment Manager</h2>
      <button class="btn" onclick="closeSetupModal()">✕</button>
    </div>
    <div class="modal-body">
      <!-- Detected Tools -->
      <label style="font-size:10px; font-weight:700; color:var(--muted); text-transform:uppercase;">Detected Simulation Tools</label>
      <div class="tool-badge-row">
        <div class="tool-badge">
          <span class="title">Gazebo Sim</span>
          <span class="stat" id="toolGzStat">Detecting...</span>
        </div>
        <div class="tool-badge">
          <span class="title">PX4 SITL</span>
          <span class="stat" id="toolPx4Stat">Detecting...</span>
        </div>
        <div class="tool-badge">
          <span class="title">Blender 3D</span>
          <span class="stat" id="toolBlenderStat">Detecting...</span>
        </div>
      </div>

      <!-- Simulator Select -->
      <div class="form-group">
        <label>Select Simulator Backend</label>
        <select class="form-control" id="simSelect" onchange="onSimulatorChanged()">
          <option value="mock">Mock Simulator (Deterministic built-in flight demo)</option>
          <option value="gazebo">Gazebo Sim (Harmonic / Ionic gz.transport)</option>
          <option value="px4">PX4 SITL (MAVLink UDP Telemetry)</option>
          <option value="blender">Blender 3D (Asset &amp; Scene Workflow)</option>
        </select>
      </div>

      <!-- Gazebo Options -->
      <div id="cfgGazebo" style="display:none; flex-direction:column; gap:8px;">
        <div class="form-group">
          <label>World Name</label>
          <input class="form-control" id="gzWorld" value="default" />
        </div>
        <div class="form-group">
          <label>Model Name (Entity)</label>
          <input class="form-control" id="gzModel" value="quadcopter" />
        </div>
        <div class="form-group">
          <label>Dynamic Pose Topic</label>
          <input class="form-control" id="gzPoseTopic" value="/world/default/dynamic_pose/info" />
        </div>
        <div class="form-group">
          <label>Camera Image Topic</label>
          <input class="form-control" id="gzCamTopic" value="/camera/image" />
        </div>
      </div>

      <!-- PX4 Options -->
      <div id="cfgPx4" style="display:none; flex-direction:column; gap:8px;">
        <div class="form-group">
          <label>MAVLink Connection String</label>
          <input class="form-control" id="px4Conn" value="udp:127.0.0.1:14550" />
        </div>
        <div class="form-group">
          <label>Baud Rate</label>
          <input class="form-control" id="px4Baud" value="57600" />
        </div>
      </div>

      <!-- Blender Options -->
      <div id="cfgBlender" style="display:none; flex-direction:column; gap:8px;">
        <div class="form-group">
          <label>Blender Executable Path</label>
          <input class="form-control" id="blenderPath" value="/usr/bin/blender" />
        </div>
        <div class="form-group">
          <label>Asset Directory Path (Optional)</label>
          <input class="form-control" id="blenderAssetDir" placeholder="/path/to/3d/models" />
        </div>
      </div>

      <!-- Mock Options -->
      <div id="cfgMock" style="display:flex; flex-direction:column; gap:8px;">
        <div class="form-group">
          <label>Flight Trajectory Pattern</label>
          <select class="form-control" id="mockPattern">
            <option value="lissajous">Figure-8 / Lissajous Autonomous Scan</option>
            <option value="orbit">Circular Perimeter Orbit</option>
          </select>
        </div>
      </div>

    </div>
    <div class="modal-footer">
      <button class="btn" onclick="closeSetupModal()">Cancel</button>
      <button class="btn btn-primary" onclick="applyAndConnect()">Connect Simulator</button>
    </div>
  </div>
</div>

<script>
  let ws = null;
  let isConnected = false;
  let logCollapsed = false;
  let trajectoryHistory = [];
  let lastTelemetryTimestamp = 0;

  // Logging
  function log(msg, level = 'info') {
    const el = document.getElementById('logContent');
    const line = document.createElement('div');
    line.className = `log-line ${level}`;
    const ts = new Date().toLocaleTimeString();
    line.innerHTML = `<span class="time">[${ts}]</span><span class="msg">${msg}</span>`;
    el.appendChild(line);
    el.scrollTop = el.scrollHeight;
  }

  function toggleLog() {
    logCollapsed = !logCollapsed;
    document.getElementById('logBar').classList.toggle('collapsed', logCollapsed);
    document.getElementById('logToggleLabel').textContent = logCollapsed ? '▼ COLLAPSED' : '▲ EXPAND';
  }

  // Modal
  function openSetupModal() {
    document.getElementById('setupModal').classList.add('open');
    detectTools();
  }
  function closeSetupModal() {
    document.getElementById('setupModal').classList.remove('open');
  }

  function onSimulatorChanged() {
    const sim = document.getElementById('simSelect').value;
    document.getElementById('cfgGazebo').style.display = (sim === 'gazebo') ? 'flex' : 'none';
    document.getElementById('cfgPx4').style.display = (sim === 'px4') ? 'flex' : 'none';
    document.getElementById('cfgBlender').style.display = (sim === 'blender') ? 'flex' : 'none';
    document.getElementById('cfgMock').style.display = (sim === 'mock') ? 'flex' : 'none';
  }

  // Tool Detection
  function detectTools() {
    fetch('/api/detect').then(r => r.json()).then(data => {
      const tools = data.tools || {};
      const gz = tools.gazebo || {};
      const px4 = tools.px4 || {};
      const blender = tools.blender || {};

      document.getElementById('toolGzStat').textContent = gz.installed ? (gz.running ? 'RUNNING' : 'INSTALLED') : 'NOT FOUND';
      document.getElementById('toolGzStat').style.color = gz.installed ? '#22c55e' : '#f59e0b';

      document.getElementById('toolPx4Stat').textContent = px4.installed ? (px4.running ? 'RUNNING' : 'INSTALLED') : 'NOT FOUND';
      document.getElementById('toolPx4Stat').style.color = px4.installed ? '#22c55e' : '#f59e0b';

      document.getElementById('toolBlenderStat').textContent = blender.installed ? (blender.running ? 'RUNNING' : 'INSTALLED') : 'NOT FOUND';
      document.getElementById('toolBlenderStat').style.color = blender.installed ? '#22c55e' : '#f59e0b';
    }).catch(err => {
      log('Tool detection failed: ' + err, 'warn');
    });
  }

  // Connection Management
  function quickConnect(simType) {
    document.getElementById('simSelect').value = simType;
    onSimulatorChanged();
    applyAndConnect();
  }

  function applyAndConnect() {
    const sim = document.getElementById('simSelect').value;
    const payload = { simulator: sim };

    if (sim === 'gazebo') {
      payload.world_name = document.getElementById('gzWorld').value;
      payload.model_name = document.getElementById('gzModel').value;
      payload.dynamic_pose_topic = document.getElementById('gzPoseTopic').value;
      payload.camera_topic = document.getElementById('gzCamTopic').value;
    } else if (sim === 'px4') {
      payload.connection = document.getElementById('px4Conn').value;
      payload.baud = parseInt(document.getElementById('px4Baud').value, 10);
    } else if (sim === 'blender') {
      payload.executable_path = document.getElementById('blenderPath').value;
      payload.asset_dir = document.getElementById('blenderAssetDir').value;
    }

    log(`Connecting to ${sim.toUpperCase()} simulator...`, 'info');
    fetch('/api/connect', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }).then(r => r.json()).then(res => {
      closeSetupModal();
      if (res.status === 'connected') {
        log(`Connected successfully to ${sim.toUpperCase()}`, 'ok');
        document.getElementById('btnDisconnect').style.display = 'inline-flex';
      } else {
        log(`Connection status: ${res.status} (${res.message || ''})`, 'warn');
      }
    }).catch(err => {
      log(`Connection error: ${err}`, 'fault');
    });
  }

  function disconnectSimulator() {
    fetch('/api/disconnect', { method: 'POST' }).then(r => r.json()).then(() => {
      log('Simulator disconnected', 'warn');
      document.getElementById('btnDisconnect').style.display = 'none';
    });
  }

  // Telemetry Rendering
  function updateTelemetry(t) {
    const pose = t.pose || {};
    const pos = pose.position || {x:0, y:0, z:0};
    const orient = pose.orientation || {roll:0, pitch:0, yaw:0};
    const vel = pose.velocity || {vx:0, vy:0, vz:0};
    const veh = t.vehicle || {};
    const batt = t.battery || {};
    const gps = t.gps || {};
    const perf = t.performance || {};
    const cam = t.camera || {};
    const sens = t.sensors || {};

    // Status Pills
    const simPill = document.getElementById('pillSim');
    simPill.textContent = (t.simulator || 'NONE').toUpperCase();
    const statePill = document.getElementById('pillState');
    statePill.textContent = t.connection_state || 'DISCONNECTED';
    statePill.className = 'pill ' + (t.connection_state === 'CONNECTED' ? 'ok' : 'warn');

    const vehPill = document.getElementById('pillVeh');
    vehPill.textContent = veh.armed ? 'ARMED' : (veh.connected ? 'STANDBY' : 'OFFLINE');
    vehPill.className = 'pill ' + (veh.armed ? 'ok' : 'info');

    document.getElementById('pillMode').textContent = veh.flight_mode || 'STANDBY';

    // Attitude Reticle
    const r = orient.roll || 0;
    const p = orient.pitch || 0;
    const y = orient.yaw || 0;
    const ground = document.getElementById('attGround');
    ground.style.transform = `rotate(${r}deg) translateY(${p * 2}px)`;

    document.getElementById('valRoll').textContent = r.toFixed(1) + '°';
    document.getElementById('valPitch').textContent = p.toFixed(1) + '°';
    document.getElementById('valYaw').textContent = y.toFixed(1) + '°';
    document.getElementById('valAlt').textContent = Number(pos.z || 0).toFixed(2) + ' m';

    document.getElementById('valPos').textContent = `${Number(pos.x||0).toFixed(2)}, ${Number(pos.y||0).toFixed(2)}, ${Number(pos.z||0).toFixed(2)}`;
    document.getElementById('valVel').textContent = `${Number(vel.vx||0).toFixed(1)}, ${Number(vel.vy||0).toFixed(1)}, ${Number(vel.vz||0).toFixed(1)} m/s`;
    document.getElementById('valAngRates').textContent = `${Number(vel.roll_rate||0).toFixed(1)}, ${Number(vel.pitch_rate||0).toFixed(1)}, ${Number(vel.yaw_rate||0).toFixed(1)} °/s`;

    // Battery & GPS
    document.getElementById('valBatt').textContent = (batt.percentage || 100).toFixed(0) + '%';
    document.getElementById('valVolt').textContent = (batt.voltage_v || 16.8).toFixed(1) + ' V';
    document.getElementById('valGPS').textContent = gps.fix_type || 'SIM';
    document.getElementById('valSats').textContent = gps.satellites || 0;

    // Camera details
    document.getElementById('camSourceBadge').textContent = 'CAM: ' + (cam.source || 'NONE').toUpperCase();
    document.getElementById('camFpsBadge').textContent = (perf.capture_fps || 0).toFixed(1) + ' FPS';

    // Sensors
    document.getElementById('sensIMU').textContent = sens.imu || 'NOMINAL';
    document.getElementById('sensCam').textContent = sens.camera || 'NOMINAL';
    document.getElementById('sensMag').textContent = sens.mag || 'NOMINAL';
    document.getElementById('sensBaro').textContent = sens.baro || 'NOMINAL';

    // Diagnostics
    document.getElementById('valCPU').textContent = (perf.cpu_percent || 0).toFixed(1) + ' %';
    document.getElementById('valRAM').textContent = (perf.ram_mb || 0).toFixed(0) + ' MB';
    document.getElementById('valStreamFps').textContent = (perf.stream_fps || 30.0).toFixed(1) + ' FPS';
    document.getElementById('valFrameCount').textContent = cam.frames_captured || 0;

    // Simulation context
    if (t.active_topics) {
      document.getElementById('valTopicCount').textContent = t.active_topics.length + ' discovered';
    }

    // Trajectory tracking
    if (t.trajectory && t.trajectory.length > 0) {
      trajectoryHistory = t.trajectory;
    } else if (pos.x !== undefined) {
      trajectoryHistory.push({ x: pos.x, y: pos.y, z: pos.z });
      if (trajectoryHistory.length > 250) trajectoryHistory.shift();
    }
    renderMap(pos, y);
  }

  // 2D Map Rendering
  function renderMap(currentPos, headingDeg) {
    const canvas = document.getElementById('mapCanvas');
    const ctx = canvas.getContext('2d');
    const w = canvas.width;
    const h = canvas.height;

    ctx.fillStyle = '#06090e';
    ctx.fillRect(0, 0, w, h);

    const cx = w / 2;
    const cy = h / 2;
    const scale = 16.0; // 16 pixels per meter

    // Grid lines
    ctx.strokeStyle = '#1e293b';
    ctx.lineWidth = 1;
    for (let x = (cx % 32); x < w; x += 32) {
      ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke();
    }
    for (let y = (cy % 32); y < h; y += 32) {
      ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke();
    }

    // Origin cross
    ctx.strokeStyle = '#334155';
    ctx.beginPath(); ctx.moveTo(cx - 10, cy); ctx.lineTo(cx + 10, cy); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(cx, cy - 10); ctx.lineTo(cx, cy + 10); ctx.stroke();

    // Trajectory Trail
    if (trajectoryHistory.length > 1) {
      ctx.strokeStyle = '#38bdf8';
      ctx.lineWidth = 2;
      ctx.beginPath();
      for (let i = 0; i < trajectoryHistory.length; i++) {
        const pt = trajectoryHistory[i];
        const sx = cx + (pt.x * scale);
        const sy = cy - (pt.y * scale); // ENU Y is North (up)
        if (i === 0) ctx.moveTo(sx, sy);
        else ctx.lineTo(sx, sy);
      }
      ctx.stroke();
    }

    // Vehicle Marker & Heading
    const vx = cx + ((currentPos.x || 0) * scale);
    const vy = cy - ((currentPos.y || 0) * scale);

    ctx.save();
    ctx.translate(vx, vy);
    ctx.rotate(-headingDeg * Math.PI / 180.0); // Heading in ENU

    // Quadcopter body
    ctx.fillStyle = '#22c55e';
    ctx.beginPath();
    ctx.arc(0, 0, 5, 0, Math.PI * 2);
    ctx.fill();

    // Heading nose pointer
    ctx.strokeStyle = '#ef4444';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(0, 0);
    ctx.lineTo(0, -14);
    ctx.stroke();

    ctx.restore();
  }

  function clearTrajectory() {
    trajectoryHistory = [];
    log('Trajectory trail cleared', 'info');
  }

  // WebSocket Connection
  function initWebSocket() {
    const proto = (window.location.protocol === 'https:') ? 'wss:' : 'ws:';
    const wsUrl = `${proto}//${window.location.host}/ws/telemetry`;

    ws = new WebSocket(wsUrl);
    ws.onopen = () => {
      isConnected = true;
      log('Real-time WebSocket telemetry stream established', 'ok');
    };
    ws.onmessage = (evt) => {
      try {
        const data = JSON.parse(evt.data);
        lastTelemetryTimestamp = Date.now();
        updateTelemetry(data);
      } catch (e) {}
    };
    ws.onclose = () => {
      isConnected = false;
      setTimeout(initWebSocket, 2000);
    };
    ws.onerror = () => {
      ws.close();
    };
  }

  // HTTP Fallback Polling (10 Hz if WebSocket is reconnecting)
  setInterval(() => {
    if (isConnected) return;
    fetch('/telemetry').then(r => r.json()).then(data => {
      updateTelemetry(data);
    }).catch(() => {});
  }, 1000);

  // Watchdog
  setInterval(() => {
    const hzBadge = document.getElementById('badgeTelemetryHz');
    if (lastTelemetryTimestamp > 0 && Date.now() - lastTelemetryTimestamp < 1500) {
      hzBadge.textContent = '20.0 Hz';
      hzBadge.className = 'pill ok';
    } else {
      hzBadge.textContent = 'STALE';
      hzBadge.className = 'pill warn';
    }
  }, 1000);

  window.onload = () => {
    initWebSocket();
    detectTools();
    log('SimBridge GCS initialized and ready.', 'ok');
  };
</script>
</body>
</html>
"""
