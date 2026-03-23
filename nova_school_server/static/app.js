const state = {
  bootstrap: null,
  project: null,
  filePath: "",
  admin: null,
  adminUserAudit: [],
  room: "lounge:school",
  chatTimer: null,
  fileDirty: false,
  mentorThread: [],
  reviews: null,
  artifacts: [],
  curriculum: null,
  curriculumCourseId: "",
  curriculumModuleId: "",
  curriculumLastResult: null,
  curriculumAttempts: null,
  curriculumManageCourseId: "",
  curriculumAttemptUsername: "",
  curriculumDraft: null,
  playground: null,
  realtime: {
    projectSocket: null,
    socketProjectId: "",
    reconnectTimer: null,
    resizeTimer: null,
    liveRunSessionId: "",
    liveRunActive: false,
    fileRunActive: false,
    fileSessionId: "",
    cellSessionById: {},
    sessionTargets: {},
    cellOutputById: {},
    cellStatusById: {},
    fileTerminal: null,
    cellTerminals: {},
  },
  collab: {
    revision: 0,
    syncTimer: null,
    pollTimer: null,
    presenceTimer: null,
  },
};

const $ = (id) => document.getElementById(id);
const ui = {
  loginView: $("login-view"),
  appView: $("app-view"),
  loginForm: $("login-form"),
  status: $("status-banner"),
  rightPanel: $("right-panel"),
  schoolName: $("school-name"),
  sessionTitle: $("session-title"),
  projectList: $("project-list"),
  fileTree: $("file-tree"),
  filePath: $("file-path"),
  fileEditor: $("file-editor"),
  runStdin: $("run-stdin"),
  runOutput: $("run-output"),
  liveRunStatus: $("live-run-status"),
  notebookCells: $("notebook-cells"),
  collabStatus: $("collab-status"),
  collabPresence: $("collab-presence"),
  playgroundPanel: $("playground-panel"),
  playgroundStatus: $("playground-status"),
  playgroundServices: $("playground-services"),
  chatRoom: $("chat-room"),
  chatMessages: $("chat-messages"),
  chatInput: $("chat-input"),
  docSelect: $("doc-select"),
  docContent: $("doc-content"),
  curriculumPanel: $("curriculum-panel"),
  curriculumCourse: $("curriculum-course"),
  curriculumCourseMeta: $("curriculum-course-meta"),
  curriculumResultBanner: $("curriculum-result-banner"),
  curriculumModuleList: $("curriculum-module-list"),
  curriculumModuleDetail: $("curriculum-module-detail"),
  curriculumManagePanel: $("curriculum-manage-panel"),
  curriculumManageCourse: $("curriculum-manage-course"),
  curriculumReleaseScopeType: $("curriculum-release-scope-type"),
  curriculumReleaseScopeKey: $("curriculum-release-scope-key"),
  curriculumReleaseEnabled: $("curriculum-release-enabled"),
  curriculumReleaseNote: $("curriculum-release-note"),
  curriculumReleaseList: $("curriculum-release-list"),
  curriculumLearnerList: $("curriculum-learner-list"),
  curriculumAttemptUser: $("curriculum-attempt-user"),
  curriculumAttemptList: $("curriculum-attempt-list"),
  curriculumAuthorSource: $("curriculum-author-source"),
  curriculumAuthorStatus: $("curriculum-author-status"),
  curriculumAuthorEditor: $("curriculum-author-editor"),
  assistantStatus: $("assistant-status"),
  assistantForm: $("assistant-form"),
  assistantMode: $("assistant-mode"),
  assistantPrompt: $("assistant-prompt"),
  assistantOutput: $("assistant-output"),
  mentorThread: $("mentor-thread"),
  reviewPanel: $("review-panel"),
  reviewSubmissions: $("review-submissions"),
  reviewAssignments: $("review-assignments"),
  reviewAnalytics: $("review-analytics"),
  deploymentPanel: $("deployment-panel"),
  deploymentArtifacts: $("deployment-artifacts"),
  serverSettingsPanel: $("server-settings-panel"),
  adminPanel: $("admin-panel"),
  adminSummary: $("admin-summary"),
  manageUserMeta: $("manage-user-meta"),
  manageUserAudit: $("manage-user-audit"),
};

const permissionKeys = () => state.bootstrap?.permissions_catalog?.map((item) => item.key) || [];
const escapeHtml = (value) => String(value)
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll("\"", "&quot;")
  .replaceAll("'", "&#39;");
const notify = (text) => { ui.status.textContent = text || ""; };
const hasPermission = (key) => Boolean(state.bootstrap?.session?.permissions?.[key]);
const canManageServerSettings = (session = state.bootstrap?.session) => Boolean(session && (session.role === "admin" || session.role === "teacher" || session.permissions?.["admin.manage"]));
const projectSupportsPlayground = (project = state.project) => Boolean(project && project.template === "distributed-system");
const inferLanguage = (path) => ({
  py: "python",
  js: "javascript",
  cjs: "javascript",
  mjs: "javascript",
  cpp: "cpp",
  cc: "cpp",
  cxx: "cpp",
  java: "java",
  rs: "rust",
  html: "html",
  htm: "html",
})[(path.split(".").pop() || "").toLowerCase()] || "python";
const encodePath = (path) => path.split("/").map(encodeURIComponent).join("/");
const buildWsUrl = (path) => `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}${path}`;
const sameJson = (left, right) => JSON.stringify(left) === JSON.stringify(right);
const formatWhen = (value) => value ? new Date(value * 1000).toLocaleString() : "unbekannt";
const nonEmptyText = (value, fallback = "Keine Daten.") => {
  const text = String(value || "").trim();
  return text || fallback;
};
const MANAGED_SETTING_KEYS = new Set([
  "school_name",
  "server_public_host",
  "certificate_logo_path",
  "certificate_signatory_name",
  "certificate_signatory_title",
  "web_proxy_url",
  "web_proxy_no_proxy",
  "web_proxy_required",
  "lmstudio_base_url",
  "lmstudio_model",
  "runner_backend",
  "unsafe_process_backend_enabled",
  "playground_dispatch_mode",
  "container_runtime",
  "container_oci_runtime",
  "container_memory_limit",
  "container_cpu_limit",
  "container_pids_limit",
  "container_file_size_limit_kb",
  "container_nofile_limit",
  "container_tmpfs_limit",
  "container_seccomp_enabled",
  "container_seccomp_profile",
  "container_image_python",
  "container_image_node",
  "container_image_cpp",
  "container_image_java",
  "container_image_rust",
  "scheduler_max_concurrent_global",
  "scheduler_max_concurrent_student",
  "scheduler_max_concurrent_teacher",
  "scheduler_max_concurrent_admin",
]);
const renderReadoutItems = (items) => items.map((item) => `
  <dl class="readout-item">
    <dt>${escapeHtml(item.label)}</dt>
    <dd>${escapeHtml(item.value ?? "-")}</dd>
  </dl>
`).join("");

function populateServerSettingsPanel(settings = {}, runtime = {}) {
  const runtimeConfig = runtime?.config || {};
  const activeConfig = runtimeConfig.active || {};
  const storedConfig = runtimeConfig.stored || {};
  const runtimePaths = runtimeConfig.paths || {};
  const runtimeUrls = runtimeConfig.urls || {};
  $("settings-restart-flag").textContent = runtimeConfig.restart_required
    ? "Gespeicherte Grundkonfiguration weicht von der aktiven Laufzeit ab. Neustart erforderlich."
    : "Aktive Laufzeit und gespeicherte Grundkonfiguration sind synchron.";
  $("settings-runtime-summary").innerHTML = renderReadoutItems([
    { label: "Aktiver Bind-Host", value: activeConfig.host || "0.0.0.0" },
    { label: "Aktiver Port", value: activeConfig.port || 8877 },
    { label: "Lokale URL", value: runtimeUrls.local_url || "-" },
    { label: "LAN-URL", value: runtimeUrls.lan_url || "nicht erkannt" },
    { label: "Session-TTL", value: `${activeConfig.session_ttl_seconds || 43200} s` },
    { label: "Direktlauf-Timeout", value: `${activeConfig.run_timeout_seconds || 20} s` },
    { label: "Live-Timeout", value: `${activeConfig.live_run_timeout_seconds || 300} s` },
    { label: "Tenant-ID", value: activeConfig.tenant_id || "nova-school" },
  ]);
  $("settings-runtime-paths").innerHTML = renderReadoutItems([
    { label: "Config-Datei", value: runtimePaths.config_path || "-" },
    { label: "Datenbank", value: runtimePaths.database_path || "-" },
    { label: "Data-Pfad", value: runtimePaths.data_path || "-" },
    { label: "Dokumentationspfad", value: runtimePaths.docs_path || "-" },
    { label: "User-Workspaces", value: runtimePaths.users_workspace_path || "-" },
    { label: "Gruppen-Workspaces", value: runtimePaths.groups_workspace_path || "-" },
    { label: "NovaShell-Pfad", value: runtimePaths.nova_shell_path || "-" },
  ]);
  $("setting-school-name").value = settings.school_name || "";
  $("setting-host").value = storedConfig.host || activeConfig.host || "0.0.0.0";
  $("setting-port").value = storedConfig.port || activeConfig.port || 8877;
  $("setting-session-ttl").value = storedConfig.session_ttl_seconds || activeConfig.session_ttl_seconds || 43200;
  $("setting-run-timeout").value = storedConfig.run_timeout_seconds || activeConfig.run_timeout_seconds || 20;
  $("setting-live-run-timeout").value = storedConfig.live_run_timeout_seconds || activeConfig.live_run_timeout_seconds || 300;
  $("setting-tenant-id").value = storedConfig.tenant_id || activeConfig.tenant_id || "nova-school";
  $("setting-nova-shell-path").value = storedConfig.nova_shell_path || activeConfig.nova_shell_path || "";
  $("setting-server-public-host").value = settings.server_public_host || "";
  $("setting-certificate-logo-path").value = settings.certificate_logo_path || "";
  $("setting-certificate-signatory-name").value = settings.certificate_signatory_name || "";
  $("setting-certificate-signatory-title").value = settings.certificate_signatory_title || "";
  $("setting-web-proxy-url").value = settings.web_proxy_url || "";
  $("setting-web-proxy-no-proxy").value = settings.web_proxy_no_proxy || "";
  $("setting-web-proxy-required").checked = Boolean(settings.web_proxy_required);
  $("setting-lmstudio-base").value = settings.lmstudio_base_url || "";
  $("setting-lmstudio-model").value = settings.lmstudio_model || "";
  $("setting-playground-dispatch-mode").value = settings.playground_dispatch_mode || "worker";
  $("setting-runner-backend").value = settings.runner_backend || "container";
  $("setting-unsafe-process").checked = Boolean(settings.unsafe_process_backend_enabled);
  $("setting-container-runtime").value = settings.container_runtime || "docker";
  $("setting-container-oci-runtime").value = settings.container_oci_runtime || "";
  $("setting-container-memory").value = settings.container_memory_limit || "512m";
  $("setting-container-cpu").value = settings.container_cpu_limit || "1.5";
  $("setting-container-pids").value = settings.container_pids_limit || "128";
  $("setting-container-fsize").value = settings.container_file_size_limit_kb || 65536;
  $("setting-container-nofile").value = settings.container_nofile_limit || 256;
  $("setting-container-tmpfs").value = settings.container_tmpfs_limit || "64m";
  $("setting-container-seccomp-enabled").checked = Boolean(settings.container_seccomp_enabled ?? true);
  $("setting-container-seccomp-profile").value = settings.container_seccomp_profile || "";
  $("setting-container-image-python").value = settings.container_image_python || "python:3.12-slim";
  $("setting-container-image-node").value = settings.container_image_node || "node:20-bookworm-slim";
  $("setting-container-image-cpp").value = settings.container_image_cpp || "gcc:14";
  $("setting-container-image-java").value = settings.container_image_java || "eclipse-temurin:21";
  $("setting-container-image-rust").value = settings.container_image_rust || "rust:1.81";
  $("setting-scheduler-global").value = settings.scheduler_max_concurrent_global || 4;
  $("setting-scheduler-student").value = settings.scheduler_max_concurrent_student || 1;
  $("setting-scheduler-teacher").value = settings.scheduler_max_concurrent_teacher || 2;
  $("setting-scheduler-admin").value = settings.scheduler_max_concurrent_admin || 3;
  const extraSettings = Object.entries(settings || {}).filter(([key]) => !MANAGED_SETTING_KEYS.has(key));
  $("settings-extra-wrapper").classList.toggle("hidden", extraSettings.length === 0);
  $("settings-extra-fields").innerHTML = renderReadoutItems(extraSettings.map(([key, value]) => ({
    label: key,
    value: typeof value === "object" ? JSON.stringify(value) : String(value),
  })));
}

async function loadServerSettingsOverview() {
  if (!canManageServerSettings()) return;
  const payload = await api("/api/server/settings");
  populateServerSettingsPanel(payload.settings || {}, payload.runtime || {});
}

function restoreSelectValue(id, preferredValue) {
  const select = $(id);
  if (!select) return;
  const values = [...select.options].map((option) => option.value);
  if (preferredValue && values.includes(preferredValue)) {
    select.value = preferredValue;
  } else if (values.length) {
    select.value = values[0];
  }
}

function arrangeRightPanel(session) {
  if (!ui.rightPanel) return;
  const orderedSections = [];
  if (canManageServerSettings(session)) orderedSections.push(ui.serverSettingsPanel);
  if (session?.permissions?.["admin.manage"]) orderedSections.push(ui.adminPanel);
  if (session?.permissions?.["curriculum.manage"]) orderedSections.push(ui.curriculumManagePanel);
  if (session?.permissions?.["review.use"]) orderedSections.push(ui.reviewPanel);
  if (session?.permissions?.["deploy.use"]) orderedSections.push(ui.deploymentPanel);
  if (session?.permissions?.["curriculum.use"]) orderedSections.push(ui.curriculumPanel);
  const anchor = ui.rightPanel.firstElementChild;
  [...orderedSections].reverse().forEach((section) => {
    if (section?.parentElement === ui.rightPanel) {
      ui.rightPanel.insertBefore(section, anchor);
    }
  });
}
const formatRunOutput = (payload) => {
  const parts = [];
  const text = `${payload.stdout || ""}${payload.stderr ? `\n${payload.stderr}` : ""}`.trim();
  if (text) parts.push(text);
  if (payload.notes?.length) parts.push(`Hinweise:\n- ${payload.notes.join("\n- ")}`);
  return parts.join("\n\n").trim() || "Keine Ausgabe.";
};

async function api(path, options = {}) {
  const response = await fetch(path, {
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
  return payload;
}

function appendRunOutput(text) {
  if (!text) return;
  appendTerminalChunk(fileTerminal(), ui.runOutput, text, state.realtime.fileRunActive);
}

function setRunOutput(text, active = false) {
  state.realtime.fileRunActive = active;
  resetTerminalOutput(fileTerminal(), ui.runOutput, text, active);
}

function resetLiveRunState() {
  if (state.realtime.resizeTimer) {
    clearTimeout(state.realtime.resizeTimer);
    state.realtime.resizeTimer = null;
  }
  state.realtime.liveRunSessionId = "";
  state.realtime.liveRunActive = false;
  state.realtime.fileRunActive = false;
  state.realtime.fileSessionId = "";
  state.realtime.cellSessionById = {};
  state.realtime.sessionTargets = {};
  state.realtime.cellOutputById = {};
  state.realtime.cellStatusById = {};
  state.realtime.fileTerminal = null;
  state.realtime.cellTerminals = {};
  ui.liveRunStatus.textContent = "Keine Live-Session aktiv.";
}

function defaultAnsiStyle() {
  return {
    fg: null,
    bg: null,
    bold: false,
    italic: false,
    underline: false,
    inverse: false,
  };
}

function cloneAnsiStyle(style) {
  return { ...style };
}

function blankTerminalCell() {
  return { ch: " ", style: cloneAnsiStyle(defaultAnsiStyle()) };
}

function blankTerminalLine(cols = 0) {
  return Array.from({ length: Math.max(0, cols) }, () => blankTerminalCell());
}

function cloneTerminalLines(lines) {
  return lines.map((line) => line.map((cell) => ({ ch: cell.ch, style: cloneAnsiStyle(cell.style) })));
}

function normalizeTerminalSize(cols, rows) {
  return {
    cols: Math.max(40, Math.min(320, Number(cols) || 120)),
    rows: Math.max(10, Math.min(120, Number(rows) || 30)),
  };
}

function createTerminalState() {
  const size = normalizeTerminalSize();
  return {
    lines: [[]],
    row: 0,
    col: 0,
    savedRow: 0,
    savedCol: 0,
    style: defaultAnsiStyle(),
    promptHint: false,
    active: false,
    cursorVisible: true,
    cols: size.cols,
    rows: size.rows,
    scrollTop: 0,
    scrollBottom: null,
    altScreen: false,
    mainSnapshot: null,
  };
}

function fileTerminal() {
  if (!state.realtime.fileTerminal) {
    state.realtime.fileTerminal = createTerminalState();
  }
  return state.realtime.fileTerminal;
}

function cellTerminal(cellId) {
  if (!state.realtime.cellTerminals[cellId]) {
    state.realtime.cellTerminals[cellId] = createTerminalState();
  }
  return state.realtime.cellTerminals[cellId];
}

function sgrColor(index, isBackground = false) {
  const basic = [
    "#1b1f23",
    "#c0392b",
    "#1e8449",
    "#b9770e",
    "#2e86c1",
    "#8e44ad",
    "#148f77",
    "#d5dbdb",
  ];
  const bright = [
    "#566573",
    "#e74c3c",
    "#2ecc71",
    "#f1c40f",
    "#3498db",
    "#bb8fce",
    "#48c9b0",
    "#fdfefe",
  ];
  const palette = index < 8 ? basic : bright;
  const color = palette[index % 8];
  return isBackground ? color : color;
}

function sgrExtendedColor(index) {
  const value = Number(index || 0);
  if (value < 16) return sgrColor(value);
  if (value >= 232) {
    const shade = 8 + ((value - 232) * 10);
    return `rgb(${shade}, ${shade}, ${shade})`;
  }
  const offset = value - 16;
  const r = Math.floor(offset / 36) % 6;
  const g = Math.floor(offset / 6) % 6;
  const b = offset % 6;
  const map = [0, 95, 135, 175, 215, 255];
  return `rgb(${map[r]}, ${map[g]}, ${map[b]})`;
}

function ansiStyleCss(style) {
  let fg = style.fg;
  let bg = style.bg;
  if (style.inverse) {
    const tmp = fg;
    fg = bg || "#182126";
    bg = tmp || "rgba(24, 33, 38, 0.18)";
  }
  return [
    fg ? `color:${fg}` : "",
    bg ? `background:${bg}` : "",
    style.bold ? "font-weight:700" : "",
    style.italic ? "font-style:italic" : "",
    style.underline ? "text-decoration:underline" : "",
  ].filter(Boolean).join(";");
}

function setTerminalSize(term, cols, rows) {
  const size = normalizeTerminalSize(cols, rows);
  term.cols = size.cols;
  term.rows = size.rows;
  term.scrollTop = 0;
  term.scrollBottom = term.altScreen ? size.rows - 1 : null;
  if (term.altScreen) {
    term.lines = term.lines.slice(0, size.rows);
    while (term.lines.length < size.rows) term.lines.push(blankTerminalLine(size.cols));
    term.lines = term.lines.map((line) => {
      const next = line.slice(0, size.cols);
      while (next.length < size.cols) next.push(blankTerminalCell());
      return next;
    });
    term.row = Math.max(0, Math.min(term.row, size.rows - 1));
    term.col = Math.max(0, Math.min(term.col, size.cols - 1));
  }
  return size;
}

function ensureTerminalLine(term, row) {
  while (term.lines.length <= row) term.lines.push(blankTerminalLine(term.altScreen ? term.cols : 0));
}

function ensureTerminalColumn(term, row, col) {
  ensureTerminalLine(term, row);
  const line = term.lines[row];
  while (line.length <= col) {
    line.push(blankTerminalCell());
  }
}

function terminalRegion(term) {
  const top = Math.max(0, term.scrollTop || 0);
  const fallbackBottom = term.altScreen ? Math.max(0, term.rows - 1) : Math.max(0, term.lines.length - 1);
  const bottom = Math.max(top, term.scrollBottom ?? fallbackBottom);
  ensureTerminalLine(term, bottom);
  return { top, bottom };
}

function shiftTerminalRegion(term, top, bottom, delta) {
  const count = Math.max(1, Math.abs(delta));
  ensureTerminalLine(term, bottom);
  for (let index = 0; index < count; index += 1) {
    if (delta > 0) {
      term.lines.splice(top, 1);
      term.lines.splice(bottom, 0, blankTerminalLine(term.altScreen ? term.cols : 0));
    } else {
      term.lines.splice(bottom, 1);
      term.lines.splice(top, 0, blankTerminalLine(term.altScreen ? term.cols : 0));
    }
  }
}

function terminalNewLine(term) {
  if (term.altScreen || term.scrollBottom !== null) {
    const region = terminalRegion(term);
    if (term.row >= region.top && term.row === region.bottom) {
      shiftTerminalRegion(term, region.top, region.bottom, 1);
      term.col = 0;
      return;
    }
  }
  term.row += 1;
  term.col = 0;
  ensureTerminalLine(term, term.row);
}

function terminalPutChar(term, ch) {
  if (ch === "\n") {
    terminalNewLine(term);
    return;
  }
  if (ch === "\r") {
    term.col = 0;
    return;
  }
  if (ch === "\b") {
    term.col = Math.max(0, term.col - 1);
    return;
  }
  if (ch === "\t") {
    const spaces = 4 - (term.col % 4 || 0);
    for (let index = 0; index < spaces; index += 1) terminalPutChar(term, " ");
    return;
  }
  if (term.altScreen && term.cols && term.col >= term.cols) {
    terminalNewLine(term);
  }
  ensureTerminalColumn(term, term.row, term.col);
  term.lines[term.row][term.col] = { ch, style: cloneAnsiStyle(term.style) };
  term.col += 1;
}

function clearTerminalRange(line, from, to) {
  for (let index = from; index < to; index += 1) {
    line[index] = blankTerminalCell();
  }
}

function applySgr(term, params) {
  const values = params.length ? params : [0];
  for (let index = 0; index < values.length; index += 1) {
    const code = Number(values[index] || 0);
    if (code === 0) term.style = defaultAnsiStyle();
    else if (code === 1) term.style.bold = true;
    else if (code === 3) term.style.italic = true;
    else if (code === 4) term.style.underline = true;
    else if (code === 7) term.style.inverse = true;
    else if (code === 22) term.style.bold = false;
    else if (code === 23) term.style.italic = false;
    else if (code === 24) term.style.underline = false;
    else if (code === 27) term.style.inverse = false;
    else if (code >= 30 && code <= 37) term.style.fg = sgrColor(code - 30);
    else if (code === 39) term.style.fg = null;
    else if (code >= 40 && code <= 47) term.style.bg = sgrColor(code - 40, true);
    else if (code === 49) term.style.bg = null;
    else if (code >= 90 && code <= 97) term.style.fg = sgrColor(code - 90 + 8);
    else if (code >= 100 && code <= 107) term.style.bg = sgrColor(code - 100 + 8, true);
    else if ((code === 38 || code === 48) && values[index + 1] === 5 && values[index + 2] !== undefined) {
      const color = sgrExtendedColor(values[index + 2]);
      if (code === 38) term.style.fg = color;
      else term.style.bg = color;
      index += 2;
    } else if ((code === 38 || code === 48) && values[index + 1] === 2 && values[index + 4] !== undefined) {
      const color = `rgb(${values[index + 2]}, ${values[index + 3]}, ${values[index + 4]})`;
      if (code === 38) term.style.fg = color;
      else term.style.bg = color;
      index += 4;
    }
  }
}

function terminalEnterAltScreen(term) {
  if (!term.altScreen) {
    term.mainSnapshot = {
      lines: cloneTerminalLines(term.lines),
      row: term.row,
      col: term.col,
      savedRow: term.savedRow,
      savedCol: term.savedCol,
      style: cloneAnsiStyle(term.style),
      cursorVisible: term.cursorVisible,
      scrollTop: term.scrollTop,
      scrollBottom: term.scrollBottom,
    };
  }
  term.altScreen = true;
  term.lines = Array.from({ length: term.rows }, () => blankTerminalLine(term.cols));
  term.row = 0;
  term.col = 0;
  term.savedRow = 0;
  term.savedCol = 0;
  term.style = defaultAnsiStyle();
  term.cursorVisible = true;
  term.scrollTop = 0;
  term.scrollBottom = term.rows - 1;
  term.promptHint = false;
}

function terminalLeaveAltScreen(term) {
  term.altScreen = false;
  const snapshot = term.mainSnapshot;
  term.mainSnapshot = null;
  if (!snapshot) {
    term.lines = [[]];
    term.row = 0;
    term.col = 0;
    term.savedRow = 0;
    term.savedCol = 0;
    term.style = defaultAnsiStyle();
    term.cursorVisible = true;
    term.scrollTop = 0;
    term.scrollBottom = null;
    return;
  }
  term.lines = cloneTerminalLines(snapshot.lines);
  term.row = snapshot.row;
  term.col = snapshot.col;
  term.savedRow = snapshot.savedRow;
  term.savedCol = snapshot.savedCol;
  term.style = cloneAnsiStyle(snapshot.style);
  term.cursorVisible = snapshot.cursorVisible;
  term.scrollTop = snapshot.scrollTop;
  term.scrollBottom = snapshot.scrollBottom;
}

function applyPrivateMode(term, rawParams, command) {
  const enable = command === "h";
  const params = rawParams.split(";").filter((item) => item !== "").map((item) => Number(item));
  params.forEach((mode) => {
    if (mode === 25) {
      term.cursorVisible = enable;
    } else if ([47, 1047, 1049].includes(mode)) {
      if (enable) terminalEnterAltScreen(term);
      else terminalLeaveAltScreen(term);
    }
  });
}

function applyCsi(term, rawParams, command) {
  let paramsText = rawParams;
  if (paramsText.startsWith("?")) {
    applyPrivateMode(term, paramsText.slice(1), command);
    return;
  }
  const params = paramsText.split(";").filter((item) => item !== "").map((item) => Number(item));
  if (command === "m") {
    applySgr(term, params);
    return;
  }
  if (command === "s") {
    term.savedRow = term.row;
    term.savedCol = term.col;
    return;
  }
  if (command === "u") {
    term.row = term.savedRow;
    term.col = term.savedCol;
    ensureTerminalLine(term, term.row);
    return;
  }
  if (command === "A") {
    term.row = Math.max(0, term.row - (params[0] || 1));
    ensureTerminalLine(term, term.row);
    return;
  }
  if (command === "B") {
    term.row += params[0] || 1;
    ensureTerminalLine(term, term.row);
    return;
  }
  if (command === "C") {
    term.col += params[0] || 1;
    return;
  }
  if (command === "D") {
    term.col = Math.max(0, term.col - (params[0] || 1));
    return;
  }
  if (command === "E") {
    term.row += params[0] || 1;
    term.col = 0;
    ensureTerminalLine(term, term.row);
    return;
  }
  if (command === "F") {
    term.row = Math.max(0, term.row - (params[0] || 1));
    term.col = 0;
    ensureTerminalLine(term, term.row);
    return;
  }
  if (command === "G") {
    term.col = Math.max(0, (params[0] || 1) - 1);
    return;
  }
  if (command === "d") {
    term.row = Math.max(0, (params[0] || 1) - 1);
    ensureTerminalLine(term, term.row);
    return;
  }
  if (command === "H" || command === "f") {
    term.row = Math.max(0, (params[0] || 1) - 1);
    term.col = Math.max(0, (params[1] || 1) - 1);
    ensureTerminalLine(term, term.row);
    return;
  }
  if (command === "J") {
    const mode = params[0] || 0;
    if (mode === 2) {
      term.lines = [[]];
      term.row = 0;
      term.col = 0;
    }
    return;
  }
  if (command === "r") {
    const top = Math.max(0, (params[0] || 1) - 1);
    const bottom = Math.max(top, (params[1] || term.rows || 1) - 1);
    term.scrollTop = top;
    term.scrollBottom = bottom;
    term.row = top;
    term.col = 0;
    ensureTerminalLine(term, bottom);
    return;
  }
  if (command === "K") {
    ensureTerminalLine(term, term.row);
    const line = term.lines[term.row];
    const mode = params[0] || 0;
    if (mode === 0) {
      clearTerminalRange(line, term.col, Math.max(line.length, term.col + 1));
    } else if (mode === 1) {
      clearTerminalRange(line, 0, term.col + 1);
    } else if (mode === 2) {
      clearTerminalRange(line, 0, Math.max(line.length, 1));
      term.col = 0;
    }
    return;
  }
  if (command === "L") {
    const { top, bottom } = terminalRegion(term);
    if (term.row >= top && term.row <= bottom) {
      const count = params[0] || 1;
      term.lines.splice(term.row, 0, ...Array.from({ length: count }, () => blankTerminalLine(term.altScreen ? term.cols : 0)));
      term.lines.splice(bottom + 1, count);
    }
    return;
  }
  if (command === "M") {
    const { top, bottom } = terminalRegion(term);
    if (term.row >= top && term.row <= bottom) {
      const count = params[0] || 1;
      term.lines.splice(term.row, count);
      term.lines.splice(bottom - count + 1, 0, ...Array.from({ length: count }, () => blankTerminalLine(term.altScreen ? term.cols : 0)));
    }
    return;
  }
  if (command === "P") {
    ensureTerminalLine(term, term.row);
    const line = term.lines[term.row];
    const count = params[0] || 1;
    line.splice(term.col, count);
    while (line.length < term.cols) line.push(blankTerminalCell());
    return;
  }
  if (command === "@") {
    ensureTerminalLine(term, term.row);
    const line = term.lines[term.row];
    const count = params[0] || 1;
    line.splice(term.col, 0, ...Array.from({ length: count }, () => blankTerminalCell()));
    if (term.altScreen && term.cols) line.length = term.cols;
    return;
  }
  if (command === "X") {
    ensureTerminalLine(term, term.row);
    const line = term.lines[term.row];
    clearTerminalRange(line, term.col, term.col + (params[0] || 1));
    return;
  }
  if (command === "S") {
    const { top, bottom } = terminalRegion(term);
    shiftTerminalRegion(term, top, bottom, params[0] || 1);
    return;
  }
  if (command === "T") {
    const { top, bottom } = terminalRegion(term);
    shiftTerminalRegion(term, top, bottom, -1 * (params[0] || 1));
  }
}

function terminalWrite(term, text) {
  let index = 0;
  while (index < text.length) {
    if (text[index] === "\u001b") {
      const next = text[index + 1];
      if (next === "[") {
        let end = index + 2;
        while (end < text.length && !/[@-~]/.test(text[end])) end += 1;
        if (end < text.length) {
          applyCsi(term, text.slice(index + 2, end), text[end]);
          index = end + 1;
          continue;
        }
      } else if (next === "]") {
        let end = index + 2;
        while (end < text.length && text[end] !== "\u0007") {
          if (text[end] === "\u001b" && text[end + 1] === "\\") {
            end += 2;
            break;
          }
          end += 1;
        }
        index = Math.min(text.length, end + 1);
        continue;
      } else if (next === "7") {
        term.savedRow = term.row;
        term.savedCol = term.col;
        index += 2;
        continue;
      } else if (next === "8") {
        term.row = term.savedRow;
        term.col = term.savedCol;
        ensureTerminalLine(term, term.row);
        index += 2;
        continue;
      } else if (next === "c") {
        resetTerminalOutput(term, null, "", term.active);
        index += 2;
        continue;
      }
    }
    terminalPutChar(term, text[index]);
    index += 1;
  }
  while (term.lines.length > 500) {
    term.lines.shift();
    term.row = Math.max(0, term.row - 1);
  }
}

function terminalPlainText(term) {
  return term.lines.map((line) => line.map((cell) => cell.ch).join("").replace(/\s+$/g, "")).join("\n");
}

function detectPrompt(term) {
  if (term.altScreen) return false;
  const lines = terminalPlainText(term).split("\n");
  const last = (lines.at(-1) || "").trimEnd();
  if (!last) return false;
  return /(:\s?$|>\s?$|\?\s?$|\$\s?$|#\s?$|eingabe\s*:?\s*$|name\s*:?\s*$|passwort\s*:?\s*$|choice\s*:?\s*$|prompt\s*:?\s*$)/i.test(last);
}

function renderTerminal(term, node) {
  if (!node) return;
  const htmlLines = term.lines.map((line, rowIndex) => {
    const segments = [];
    let currentText = "";
    let currentStyle = "";
    const lineLength = Math.max(line.length, rowIndex === term.row && term.active && term.cursorVisible ? term.col + 1 : 0);
    for (let index = 0; index < lineLength; index += 1) {
      const isCursor = term.active && term.cursorVisible && rowIndex === term.row && index === term.col;
      const cell = line[index] || { ch: " ", style: cloneAnsiStyle(defaultAnsiStyle()) };
      const style = ansiStyleCss(cell.style);
      if (isCursor) {
        if (currentText) {
          segments.push(`<span style="${currentStyle}">${escapeHtml(currentText)}</span>`);
          currentText = "";
        }
        segments.push(`<span class="term-cursor">${cell.ch === " " ? "&nbsp;" : escapeHtml(cell.ch)}</span>`);
        currentStyle = "";
        continue;
      }
      if (style !== currentStyle && currentText) {
        segments.push(`<span style="${currentStyle}">${escapeHtml(currentText)}</span>`);
        currentText = "";
      }
      currentStyle = style;
      currentText += cell.ch;
    }
    if (currentText) {
      segments.push(`<span style="${currentStyle}">${escapeHtml(currentText)}</span>`);
    }
    return segments.join("") || "&nbsp;";
  });
  node.innerHTML = htmlLines.join("\n");
}

function resetTerminalOutput(term, node, text, active = false) {
  term.lines = [[]];
  term.row = 0;
  term.col = 0;
  term.savedRow = 0;
  term.savedCol = 0;
  term.style = defaultAnsiStyle();
  term.active = active;
  term.cursorVisible = true;
  term.scrollTop = 0;
  term.scrollBottom = null;
  term.altScreen = false;
  term.mainSnapshot = null;
  if (text) terminalWrite(term, text);
  term.promptHint = detectPrompt(term);
  renderTerminal(term, node);
}

function appendTerminalChunk(term, node, text, active = true) {
  term.active = active;
  terminalWrite(term, text);
  term.promptHint = detectPrompt(term);
  renderTerminal(term, node);
}

function applyTerminalDescriptor(term, descriptor = {}) {
  if (!descriptor || typeof descriptor !== "object") return;
  setTerminalSize(term, descriptor.cols, descriptor.rows);
  if (descriptor.mode === "pty") {
    term.cursorVisible = true;
  }
}

function measureTerminalSurface(node) {
  const fallback = normalizeTerminalSize();
  if (!node) return fallback;
  const style = getComputedStyle(node);
  const probe = document.createElement("span");
  probe.textContent = "MMMMMMMMMM";
  probe.style.position = "absolute";
  probe.style.visibility = "hidden";
  probe.style.whiteSpace = "pre";
  probe.style.font = style.font;
  probe.style.letterSpacing = style.letterSpacing;
  document.body.appendChild(probe);
  const rect = probe.getBoundingClientRect();
  probe.remove();
  const charWidth = rect.width / 10 || 8;
  const charHeight = rect.height || parseFloat(style.lineHeight || "18") || 18;
  const paddingX = (parseFloat(style.paddingLeft || "0") || 0) + (parseFloat(style.paddingRight || "0") || 0);
  const paddingY = (parseFloat(style.paddingTop || "0") || 0) + (parseFloat(style.paddingBottom || "0") || 0);
  return normalizeTerminalSize(
    Math.floor((node.clientWidth - paddingX) / charWidth),
    Math.floor((node.clientHeight - paddingY) / charHeight),
  );
}

function terminalTargetFromNode(node) {
  if (!node) return null;
  if (node.dataset.terminalTarget === "file") return { kind: "file" };
  if (node.dataset.terminalCellId) return { kind: "cell", cellId: node.dataset.terminalCellId };
  return null;
}

function terminalSessionIdForNode(node) {
  const target = terminalTargetFromNode(node);
  if (!target) return "";
  if (target.kind === "file") return state.realtime.fileSessionId;
  return state.realtime.cellSessionById[target.cellId] || "";
}

function sendTerminalSessionInput(sessionId, text) {
  if (!sessionId || !text) return false;
  socketSend({ action: "run.stdin", session_id: sessionId, text });
  return true;
}

function controlSequenceForKey(key) {
  const upper = String(key || "").toUpperCase();
  if (/^[A-Z]$/.test(upper)) return String.fromCharCode(upper.charCodeAt(0) - 64);
  if (upper === "@") return "\u0000";
  if (upper === "[") return "\u001b";
  if (upper === "\\") return "\u001c";
  if (upper === "]") return "\u001d";
  if (upper === "^") return "\u001e";
  if (upper === "_") return "\u001f";
  return "";
}

function terminalKeySequence(event) {
  if (event.metaKey) return null;
  if (event.ctrlKey) {
    const ctrl = controlSequenceForKey(event.key);
    if (ctrl) return event.altKey ? `\u001b${ctrl}` : ctrl;
  }
  if (event.key === "Tab" && event.shiftKey) return "\u001b[Z";
  const mapped = {
    Enter: "\r",
    Backspace: "\u007f",
    Tab: "\t",
    Escape: "\u001b",
    ArrowUp: "\u001b[A",
    ArrowDown: "\u001b[B",
    ArrowRight: "\u001b[C",
    ArrowLeft: "\u001b[D",
    Home: "\u001b[H",
    End: "\u001b[F",
    Insert: "\u001b[2~",
    Delete: "\u001b[3~",
    PageUp: "\u001b[5~",
    PageDown: "\u001b[6~",
    F1: "\u001bOP",
    F2: "\u001bOQ",
    F3: "\u001bOR",
    F4: "\u001bOS",
    F5: "\u001b[15~",
    F6: "\u001b[17~",
    F7: "\u001b[18~",
    F8: "\u001b[19~",
    F9: "\u001b[20~",
    F10: "\u001b[21~",
    F11: "\u001b[23~",
    F12: "\u001b[24~",
  }[event.key];
  let sequence = mapped || "";
  if (!sequence && event.key.length === 1) sequence = event.key;
  if (!sequence) return null;
  return event.altKey && sequence !== "\u001b" ? `\u001b${sequence}` : sequence;
}

function handleTerminalKeydown(event) {
  const sessionId = terminalSessionIdForNode(event.currentTarget);
  if (!sessionId) return;
  const sequence = terminalKeySequence(event);
  if (sequence === null) return;
  event.preventDefault();
  sendTerminalSessionInput(sessionId, sequence);
}

function handleTerminalPaste(event) {
  const sessionId = terminalSessionIdForNode(event.currentTarget);
  if (!sessionId) return;
  const text = event.clipboardData?.getData("text") || "";
  if (!text) return;
  event.preventDefault();
  sendTerminalSessionInput(sessionId, text);
}

function attachTerminalSurface(node, target) {
  if (!node) return;
  node.classList.add("terminal-surface");
  node.tabIndex = 0;
  if (target.kind === "file") {
    node.dataset.terminalTarget = "file";
    delete node.dataset.terminalCellId;
  } else if (target.kind === "cell" && target.cellId) {
    node.dataset.terminalTarget = "cell";
    node.dataset.terminalCellId = target.cellId;
  }
  if (node.dataset.terminalBound === "1") return;
  node.dataset.terminalBound = "1";
  node.addEventListener("click", () => node.focus());
  node.addEventListener("keydown", handleTerminalKeydown);
  node.addEventListener("paste", handleTerminalPaste);
}

function sendTerminalResize(sessionId, node, term) {
  if (!sessionId || !node || !isProjectSocketOpen()) return;
  const size = measureTerminalSurface(node);
  setTerminalSize(term, size.cols, size.rows);
  renderTerminal(term, node);
  socketSend({ action: "run.resize", session_id: sessionId, terminal: size });
}

function broadcastActiveTerminalResize() {
  if (!isProjectSocketOpen()) return;
  if (state.realtime.fileSessionId) {
    sendTerminalResize(state.realtime.fileSessionId, ui.runOutput, fileTerminal());
  }
  Object.entries(state.realtime.cellSessionById).forEach(([cellId, sessionId]) => {
    const node = cellArticle(cellId)?.querySelector(".cell-output");
    if (node && sessionId) {
      sendTerminalResize(sessionId, node, cellTerminal(cellId));
    }
  });
}

function scheduleActiveTerminalResize() {
  if (state.realtime.resizeTimer) clearTimeout(state.realtime.resizeTimer);
  state.realtime.resizeTimer = setTimeout(() => {
    state.realtime.resizeTimer = null;
    try {
      broadcastActiveTerminalResize();
    } catch (error) {
      notify(error.message);
    }
  }, 80);
}

function setView(authenticated) {
  ui.loginView.classList.toggle("hidden", authenticated);
  ui.appView.classList.toggle("hidden", !authenticated);
}

function markdownToHtml(source) {
  let html = escapeHtml(source || "");
  html = html.replace(/```([\s\S]*?)```/g, (_, code) => `<pre><code>${code.trim()}</code></pre>`);
  html = html.replace(/^### (.*)$/gm, "<h3>$1</h3>").replace(/^## (.*)$/gm, "<h2>$1</h2>").replace(/^# (.*)$/gm, "<h1>$1</h1>");
  html = html.replace(/^- (.*)$/gm, "<li>$1</li>").replace(/(<li>.*<\/li>)/gs, "<ul>$1</ul>");
  return `<p>${html.replace(/\n\n/g, "</p><p>")}</p>`.replace(/<p><\/p>/g, "");
}

function renderProjects() {
  const projects = state.bootstrap?.projects || [];
  ui.projectList.innerHTML = projects.map((project) => `
    <button class="project-button ${state.project?.project_id === project.project_id ? "active" : ""}" data-project="${escapeHtml(project.project_id)}">
      <strong>${escapeHtml(project.name)}</strong><br />
      <small>${escapeHtml(project.owner_type)}: ${escapeHtml(project.owner_key)}</small>
    </button>
  `).join("");
  document.querySelectorAll("[data-project]").forEach((button) => button.addEventListener("click", () => {
    selectProject(button.dataset.project).catch((error) => notify(error.message));
  }));
}

function renderRooms() {
  const rooms = state.bootstrap?.rooms || [];
  ui.chatRoom.innerHTML = rooms.map((room) => `<option value="${escapeHtml(room.key)}">${escapeHtml(room.label)}</option>`).join("");
  if (!rooms.length) return;
  if (!rooms.some((room) => room.key === state.room)) {
    state.room = rooms[0].key;
  }
  ui.chatRoom.value = state.room;
  $("mute-room").innerHTML = ui.chatRoom.innerHTML;
}

function renderDocs() {
  const docs = state.bootstrap?.docs || [];
  ui.docSelect.innerHTML = docs.map((doc) => `<option value="${escapeHtml(doc.slug)}">${escapeHtml(doc.title)}</option>`).join("");
  if (!docs.length) return;
  if (!docs.some((doc) => doc.slug === ui.docSelect.value)) {
    ui.docSelect.value = docs[0].slug;
  }
}

function renderTemplates() {
  $("project-template").innerHTML = (state.bootstrap?.templates || []).map((item) => `<option value="${escapeHtml(item.key)}">${escapeHtml(item.label)}</option>`).join("");
  $("project-group").innerHTML = (state.bootstrap?.session?.groups || []).map((group) => `<option value="${escapeHtml(group.group_id)}">${escapeHtml(group.display_name)}</option>`).join("");
}

function openManual() {
  window.open("/manual", "_blank", "noopener");
}

function openReferenceLibrary() {
  window.open("/reference", "_blank", "noopener");
}

function renderBootstrap() {
  const session = state.bootstrap?.session;
  const settings = state.bootstrap?.settings || {};
  const lmstudio = state.bootstrap?.lmstudio || {};
  if (!session) return;

  ui.schoolName.textContent = settings.school_name || "Nova School Server";
  ui.sessionTitle.textContent = `${session.display_name} (${session.role})`;
  renderProjects();
  renderRooms();
  renderDocs();
  renderTemplates();
  $("open-reference-library").classList.toggle("hidden", !session.permissions["docs.read"]);
  ui.serverSettingsPanel.classList.toggle("hidden", !canManageServerSettings(session));
  ui.adminPanel.classList.toggle("hidden", !session.permissions["admin.manage"]);
  ui.reviewPanel.classList.toggle("hidden", !session.permissions["review.use"]);
  ui.deploymentPanel.classList.toggle("hidden", !session.permissions["deploy.use"]);
  ui.curriculumPanel.classList.toggle("hidden", !session.permissions["curriculum.use"]);
  ui.curriculumManagePanel.classList.toggle("hidden", !session.permissions["curriculum.manage"]);
  ui.playgroundPanel.classList.toggle("hidden", !session.permissions["playground.manage"] || !projectSupportsPlayground());
  $("open-server-settings").classList.toggle("hidden", !canManageServerSettings(session));
  arrangeRightPanel(session);

  const aiAllowed = Boolean(session.permissions["ai.use"]);
  const mentorAllowed = aiAllowed && Boolean(session.permissions["mentor.use"]);
  ui.assistantForm?.classList.toggle("hidden", !aiAllowed);
  ui.assistantMode?.querySelectorAll("option").forEach((option) => {
    if (option.value === "mentor") option.disabled = !mentorAllowed;
  });
  if (!mentorAllowed && ui.assistantMode?.value === "mentor") {
    ui.assistantMode.value = "direct";
  }
  ui.mentorThread?.classList.toggle("hidden", !mentorAllowed);
  ui.assistantStatus.textContent = aiAllowed
    ? (lmstudio.error ? `LM Studio Fehler: ${lmstudio.error}` : `LM Studio aktiv. Modell: ${lmstudio.model || "nicht gesetzt"}`)
    : "LM Studio ist fuer diese Sitzung nicht freigegeben.";
  if (!aiAllowed) {
    ui.assistantOutput.textContent = "Keine Codehilfe verfuegbar.";
    ui.mentorThread.innerHTML = "";
  }
}

function clearProjectView() {
  state.project = null;
  state.filePath = "";
  state.fileDirty = false;
  state.collab.revision = 0;
  state.mentorThread = [];
  state.playground = null;
  resetLiveRunState();
  renderProjects();
  renderTree([]);
  ui.filePath.value = "";
  ui.fileEditor.value = "";
  ui.runStdin.value = "";
  setRunOutput("Kein Projekt gewaehlt.");
  $("editor-project-name").textContent = "Editor";
  $("editor-project-meta").textContent = "";
  renderNotebook([]);
  renderCollabPresence([]);
  ui.collabStatus.textContent = "";
  renderMentorThread([]);
  renderPlayground();
}

async function afterBootstrapLoaded() {
  renderBootstrap();
  await loadDoc().catch(() => null);
  await loadCurriculumDashboard().catch(() => null);
  if (canManageServerSettings()) {
    await loadServerSettingsOverview().catch(() => null);
  }
  const selectedId = state.project?.project_id;
  const availableProjects = state.bootstrap?.projects || [];
  const targetProjectId = selectedId && availableProjects.some((project) => project.project_id === selectedId)
    ? selectedId
    : availableProjects[0]?.project_id;
  if (targetProjectId) {
    await selectProject(targetProjectId);
  } else {
    stopCollaborationLoops();
    closeProjectSocket();
    clearProjectView();
  }
  if (hasPermission("admin.manage")) {
    await loadAdminOverview();
  }
}

async function refreshBootstrap() {
  state.bootstrap = await api("/api/bootstrap");
  await afterBootstrapLoaded();
}

function isProjectSocketOpen() {
  return Boolean(state.realtime.projectSocket && state.realtime.projectSocket.readyState === WebSocket.OPEN);
}

function socketSend(payload) {
  if (!isProjectSocketOpen()) throw new Error("Echtzeitkanal ist nicht verbunden.");
  state.realtime.projectSocket.send(JSON.stringify(payload));
}

function closeProjectSocket() {
  if (state.realtime.reconnectTimer) {
    clearTimeout(state.realtime.reconnectTimer);
    state.realtime.reconnectTimer = null;
  }
  if (state.realtime.projectSocket) {
    state.realtime.projectSocket.onopen = null;
    state.realtime.projectSocket.onmessage = null;
    state.realtime.projectSocket.onerror = null;
    state.realtime.projectSocket.onclose = null;
    try {
      state.realtime.projectSocket.close();
    } catch (_error) {
      // ignore close race
    }
  }
  state.realtime.projectSocket = null;
  state.realtime.socketProjectId = "";
  resetLiveRunState();
}

function notebookRunPath(language) {
  return language === "python"
    ? "notebook.py"
    : language === "javascript"
      ? "notebook.js"
      : language === "cpp"
        ? "notebook.cpp"
        : language === "java"
          ? "Main.java"
          : language === "rust"
            ? "notebook.rs"
            : language === "html"
              ? "notebook.html"
              : "package.json";
}

function cellArticle(cellId) {
  return document.querySelector(`[data-cell-id="${CSS.escape(cellId)}"]`);
}

function cellStatusNode(cellId) {
  return cellArticle(cellId)?.querySelector(".cell-live-status") || null;
}

function setCellStatus(cellId, text) {
  state.realtime.cellStatusById[cellId] = text || "";
  const node = cellStatusNode(cellId);
  if (node) node.textContent = text || "";
}

function appendCellOutput(cellId, text) {
  if (!text) return;
  const node = cellArticle(cellId)?.querySelector(".cell-output");
  const terminal = cellTerminal(cellId);
  appendTerminalChunk(terminal, node, text, Boolean(state.realtime.cellSessionById[cellId]));
  state.realtime.cellOutputById[cellId] = terminalPlainText(terminal);
}

function setCellOutput(cellId, text) {
  const node = cellArticle(cellId)?.querySelector(".cell-output");
  const terminal = cellTerminal(cellId);
  resetTerminalOutput(terminal, node, text, Boolean(state.realtime.cellSessionById[cellId]));
  state.realtime.cellOutputById[cellId] = terminalPlainText(terminal);
}

function registerRunTarget(sessionId, target) {
  state.realtime.sessionTargets[sessionId] = target;
  if (target.kind === "file") {
    state.realtime.fileSessionId = sessionId;
    state.realtime.liveRunSessionId = sessionId;
    state.realtime.liveRunActive = true;
  }
  if (target.kind === "cell" && target.cellId) {
    state.realtime.cellSessionById[target.cellId] = sessionId;
  }
}

function clearRunTarget(sessionId) {
  const target = state.realtime.sessionTargets[sessionId];
  if (!target) return null;
  if (target.kind === "file" && state.realtime.fileSessionId === sessionId) {
    state.realtime.fileSessionId = "";
    state.realtime.liveRunSessionId = "";
    state.realtime.liveRunActive = false;
    state.realtime.fileRunActive = false;
    if (state.realtime.fileTerminal) state.realtime.fileTerminal.active = false;
  }
  if (target.kind === "cell" && target.cellId && state.realtime.cellSessionById[target.cellId] === sessionId) {
    delete state.realtime.cellSessionById[target.cellId];
    if (state.realtime.cellTerminals[target.cellId]) {
      state.realtime.cellTerminals[target.cellId].active = false;
    }
  }
  delete state.realtime.sessionTargets[sessionId];
  return target;
}

function scheduleProjectSocketReconnect(projectId) {
  if (state.realtime.reconnectTimer || !state.project || state.project.project_id !== projectId) return;
  state.realtime.reconnectTimer = setTimeout(() => {
    state.realtime.reconnectTimer = null;
    connectProjectSocket().catch(() => null);
  }, 1500);
}

function handleProjectSocketMessage(payload) {
  switch (payload.type) {
    case "hello":
      ui.liveRunStatus.textContent = "Live-Kanal verbunden.";
      break;
    case "pong":
      break;
    case "collab.presence":
      renderCollabPresence(payload.presence || []);
      break;
    case "collab.state":
      state.collab.revision = payload.revision || state.collab.revision;
      renderCollabPresence(payload.presence || []);
      {
        const incomingCells = payload.cells || [];
        const localCells = collectCells();
        if (payload.actor !== state.bootstrap?.session?.username || !sameJson(localCells, incomingCells)) {
          renderNotebook(incomingCells);
        }
      }
      ui.collabStatus.textContent = `Live-Sync ueber WebSocket aktiv (Revision ${state.collab.revision}).`;
      break;
    case "run.started":
      {
        const target = payload.client_meta?.target_kind === "cell"
          ? { kind: "cell", cellId: payload.client_meta?.cell_id || "" }
          : { kind: "file" };
        registerRunTarget(payload.session_id || "", target);
        if (target.kind === "cell" && target.cellId) {
          const terminal = cellTerminal(target.cellId);
          applyTerminalDescriptor(terminal, payload.terminal || {});
          setCellStatus(target.cellId, `Live-Session aktiv (${payload.language}).`);
          setCellOutput(target.cellId, "");
          if (payload.notes?.length) {
            appendCellOutput(target.cellId, `Hinweise:\n- ${payload.notes.join("\n- ")}\n\n`);
          }
          const node = cellArticle(target.cellId)?.querySelector(".cell-output");
          attachTerminalSurface(node, { kind: "cell", cellId: target.cellId });
          node?.focus();
          const article = cellArticle(target.cellId);
          if (article?.querySelector(".cell-stdin")?.value?.trim()) {
            sendCellLiveInput(article);
          }
        } else {
          applyTerminalDescriptor(fileTerminal(), payload.terminal || {});
          state.realtime.fileRunActive = true;
          ui.liveRunStatus.textContent = `Live-Session aktiv (${payload.language}).`;
          setRunOutput("", true);
          if (payload.notes?.length) {
            appendRunOutput(`Hinweise:\n- ${payload.notes.join("\n- ")}\n\n`);
          }
          attachTerminalSurface(ui.runOutput, { kind: "file" });
          ui.runOutput.focus();
          if (ui.runStdin.value.trim()) {
            sendLiveInput();
          }
        }
        scheduleActiveTerminalResize();
      }
      break;
    case "run.output":
      {
        const target = state.realtime.sessionTargets[payload.session_id] || null;
        if (target?.kind === "cell" && target.cellId) {
          appendCellOutput(target.cellId, payload.chunk || "");
          const terminal = cellTerminal(target.cellId);
          if (terminal.promptHint) {
            setCellStatus(target.cellId, "Live-Session wartet auf Eingabe...");
          }
        } else if (payload.session_id && payload.session_id === state.realtime.fileSessionId) {
          appendRunOutput(payload.chunk || "");
          if (fileTerminal().promptHint) {
            ui.liveRunStatus.textContent = "Live-Session wartet auf Eingabe...";
          }
        } else if (!target && payload.client_meta?.target_kind === "cell" && payload.client_meta?.cell_id) {
          appendCellOutput(payload.client_meta.cell_id, payload.chunk || "");
          const terminal = cellTerminal(payload.client_meta.cell_id);
          if (terminal.promptHint) {
            setCellStatus(payload.client_meta.cell_id, "Live-Session wartet auf Eingabe...");
          }
        }
      }
      break;
    case "run.exit":
      if (payload.session_id) {
        const target = clearRunTarget(payload.session_id) || (payload.client_meta?.target_kind === "cell"
          ? { kind: "cell", cellId: payload.client_meta?.cell_id || "" }
          : { kind: "file" });
        if (payload.preview_path) {
          window.open(`/preview/${state.project.project_id}/${encodePath(payload.preview_path)}`, "_blank");
        }
        if (target.kind === "cell" && target.cellId) {
          if (payload.timed_out) appendCellOutput(target.cellId, "\nZeitlimit erreicht.\n");
          setCellStatus(target.cellId, `Live beendet (Code ${payload.returncode}, ${payload.duration_ms} ms).`);
          const node = cellArticle(target.cellId)?.querySelector(".cell-output");
          const terminal = cellTerminal(target.cellId);
          terminal.active = false;
          renderTerminal(terminal, node);
        } else {
          state.realtime.fileRunActive = false;
          fileTerminal().active = false;
          renderTerminal(fileTerminal(), ui.runOutput);
          if (payload.timed_out) appendRunOutput("\nZeitlimit erreicht.\n");
          ui.liveRunStatus.textContent = `Live-Session beendet (Code ${payload.returncode}, ${payload.duration_ms} ms).`;
        }
      }
      break;
    case "error":
      ui.liveRunStatus.textContent = payload.message || "Echtzeitfehler.";
      notify(payload.message || "Echtzeitfehler.");
      break;
    default:
      break;
  }
}

async function connectProjectSocket() {
  if (!state.project) return false;
  if (isProjectSocketOpen() && state.realtime.socketProjectId === state.project.project_id) return true;
  closeProjectSocket();
  return new Promise((resolve) => {
    let settled = false;
    const projectId = state.project.project_id;
    const socket = new WebSocket(buildWsUrl(`/ws/projects/${encodeURIComponent(projectId)}`));
    state.realtime.projectSocket = socket;
    state.realtime.socketProjectId = projectId;

    const finish = (value) => {
      if (settled) return;
      settled = true;
      resolve(value);
    };

    socket.onopen = () => {
      finish(true);
      ui.liveRunStatus.textContent = "Live-Kanal verbunden.";
      if (hasPermission("notebook.collaborate")) {
        socketSend({ action: "collab.presence", cursor: currentCursorPayload() });
      }
    };
    socket.onmessage = (event) => {
      try {
        handleProjectSocketMessage(JSON.parse(event.data));
      } catch (error) {
        notify(error.message);
      }
    };
    socket.onerror = () => finish(false);
    socket.onclose = () => {
      if (!settled) finish(false);
      if (state.project?.project_id === projectId) {
        ui.liveRunStatus.textContent = "Live-Kanal getrennt. Verbinde neu...";
        scheduleProjectSocketReconnect(projectId);
      }
    };
    setTimeout(() => finish(isProjectSocketOpen()), 1200);
  });
}

async function selectProject(projectId) {
  stopCollaborationLoops();
  closeProjectSocket();
  state.project = (state.bootstrap?.projects || []).find((item) => item.project_id === projectId) || null;
  renderProjects();
  $("editor-project-name").textContent = state.project?.name || "Editor";
  $("editor-project-meta").textContent = state.project ? `${state.project.runtime} | ${state.project.workspace_root}` : "";
  if (!state.project) return;

  const tree = await api(`/api/projects/${state.project.project_id}/tree`);
  renderTree(tree.entries || []);
  await loadFile(state.project.main_file);
  await connectProjectSocket().catch(() => false);
  await loadNotebookState();
  state.room = `project:${state.project.project_id}`;
  renderRooms();
  await refreshChat();
  await Promise.allSettled([
    loadMentorThread(),
    loadPlayground(),
    loadReviewDashboard(),
    loadArtifacts(),
  ]);
}

function renderTree(entries) {
  const files = entries.filter((entry) => entry.kind === "file");
  ui.fileTree.innerHTML = files.map((entry) => `
    <button class="tree-button ${state.filePath === entry.path ? "active" : ""}" data-file="${escapeHtml(entry.path)}">${escapeHtml(entry.path)}</button>
  `).join("");
  document.querySelectorAll("[data-file]").forEach((button) => button.addEventListener("click", () => {
    loadFile(button.dataset.file).catch((error) => notify(error.message));
  }));
}

async function loadFile(path) {
  if (!state.project) return;
  const payload = await api(`/api/projects/${state.project.project_id}/file?path=${encodeURIComponent(path)}`);
  state.filePath = payload.path;
  state.fileDirty = false;
  ui.filePath.value = payload.path;
  ui.fileEditor.value = payload.content;
  setRunOutput("Datei geladen. Noch nicht ausgefuehrt.");
  renderTree((await api(`/api/projects/${state.project.project_id}/tree`)).entries || []);
}

async function saveFile() {
  if (!state.project) throw new Error("Kein Projekt gewaehlt.");
  const path = ui.filePath.value.trim();
  await api(`/api/projects/${state.project.project_id}/file`, {
    method: "PUT",
    body: { path, content: ui.fileEditor.value },
  });
  state.filePath = path;
  state.fileDirty = false;
  notify(`Gespeichert: ${path}`);
  setRunOutput("Datei gespeichert. Noch nicht neu ausgefuehrt.");
  renderTree((await api(`/api/projects/${state.project.project_id}/tree`)).entries || []);
}

async function runFile() {
  if (!state.project) throw new Error("Kein Projekt gewaehlt.");
  const path = ui.filePath.value.trim();
  const stdin = ui.runStdin.value.trim() ? (ui.runStdin.value.endsWith("\n") ? ui.runStdin.value : `${ui.runStdin.value}\n`) : ui.runStdin.value;
  const payload = await api(`/api/projects/${state.project.project_id}/run`, {
    method: "POST",
    body: { path, code: ui.fileEditor.value, language: inferLanguage(path), stdin },
  });
  state.fileDirty = false;
  setRunOutput(formatRunOutput(payload));
  if (payload.preview_path) {
    window.open(`/preview/${state.project.project_id}/${encodePath(payload.preview_path)}`, "_blank");
  }
}

async function startLiveRun() {
  if (!state.project) throw new Error("Kein Projekt gewaehlt.");
  if (state.realtime.fileSessionId) throw new Error("Im Editor laeuft bereits eine Live-Session.");
  const path = ui.filePath.value.trim();
  const connected = await connectProjectSocket();
  if (!connected || !isProjectSocketOpen()) {
    throw new Error("Live-Kanal konnte nicht aufgebaut werden.");
  }
  setRunOutput("", true);
  ui.liveRunStatus.textContent = "Live-Session startet...";
  const terminal = measureTerminalSurface(ui.runOutput);
  setTerminalSize(fileTerminal(), terminal.cols, terminal.rows);
  attachTerminalSurface(ui.runOutput, { kind: "file" });
  socketSend({
    action: "run.start",
    payload: {
      path,
      code: ui.fileEditor.value,
      language: inferLanguage(path),
      client_meta: { target_kind: "file" },
      terminal: { ...terminal, pty: true },
    },
  });
}

function sendLiveInput() {
  if (!state.realtime.fileSessionId) {
    throw new Error("Keine aktive Live-Session.");
  }
  const text = ui.runStdin.value;
  if (!text.trim()) return;
  const payload = text.endsWith("\n") ? text : `${text}\n`;
  socketSend({ action: "run.stdin", session_id: state.realtime.fileSessionId, text: payload });
  ui.runStdin.value = "";
}

function stopLiveRun() {
  if (!state.realtime.fileSessionId) return;
  socketSend({ action: "run.stop", session_id: state.realtime.fileSessionId });
}

async function startCellLiveRun(article) {
  if (!state.project) throw new Error("Kein Projekt gewaehlt.");
  const cellId = article?.dataset.cellId || "";
  if (!cellId) throw new Error("Zell-ID fehlt.");
  if (state.realtime.cellSessionById[cellId]) throw new Error("Fuer diese Zelle laeuft bereits eine Live-Session.");
  const connected = await connectProjectSocket();
  if (!connected || !isProjectSocketOpen()) throw new Error("Live-Kanal konnte nicht aufgebaut werden.");
  const language = article.querySelector(".cell-language").value;
  const code = article.querySelector(".cell-code").value;
  setCellOutput(cellId, "");
  setCellStatus(cellId, `Live-Session startet (${language})...`);
  const node = article.querySelector(".cell-output");
  const terminal = measureTerminalSurface(node);
  setTerminalSize(cellTerminal(cellId), terminal.cols, terminal.rows);
  attachTerminalSurface(node, { kind: "cell", cellId });
  socketSend({
    action: "run.start",
    payload: {
      language,
      code,
      path: notebookRunPath(language),
      command: language === "npm" ? code : undefined,
      client_meta: { target_kind: "cell", cell_id: cellId },
      terminal: { ...terminal, pty: true },
    },
  });
}

function sendCellLiveInput(article) {
  const cellId = article?.dataset.cellId || "";
  const sessionId = state.realtime.cellSessionById[cellId];
  if (!sessionId) throw new Error("Fuer diese Zelle ist keine Live-Session aktiv.");
  const input = article.querySelector(".cell-stdin").value;
  if (!input.trim()) return;
  const payload = input.endsWith("\n") ? input : `${input}\n`;
  socketSend({ action: "run.stdin", session_id: sessionId, text: payload });
  article.querySelector(".cell-stdin").value = "";
}

function stopCellLiveRun(article) {
  const cellId = article?.dataset.cellId || "";
  const sessionId = state.realtime.cellSessionById[cellId];
  if (!sessionId) return;
  socketSend({ action: "run.stop", session_id: sessionId });
}

function previewFile() {
  if (!state.project || !ui.filePath.value.trim()) return;
  window.open(`/preview/${state.project.project_id}/${encodePath(ui.filePath.value.trim())}`, "_blank");
}

function renderCollabPresence(presence) {
  if (!presence.length) {
    ui.collabPresence.innerHTML = "";
    return;
  }
  ui.collabPresence.innerHTML = presence.map((item) => {
    const cursor = item.cursor?.active_cell_id ? ` · ${escapeHtml(item.cursor.active_cell_id)}` : "";
    return `<span class="presence-chip">${escapeHtml(item.display_name)} (${escapeHtml(item.role)})${cursor}</span>`;
  }).join("");
}

function currentCursorPayload() {
  const activeElement = document.activeElement;
  const article = activeElement?.closest?.("[data-cell-id]");
  return {
    active_cell_id: article?.dataset.cellId || "",
    active_field: activeElement?.className || "",
    selection_start: typeof activeElement?.selectionStart === "number" ? activeElement.selectionStart : null,
    file_path: ui.filePath.value || "",
    ts: Date.now(),
  };
}

function stopCollaborationLoops() {
  if (state.collab.syncTimer) {
    clearTimeout(state.collab.syncTimer);
    state.collab.syncTimer = null;
  }
  if (state.collab.pollTimer) {
    clearInterval(state.collab.pollTimer);
    state.collab.pollTimer = null;
  }
  if (state.collab.presenceTimer) {
    clearInterval(state.collab.presenceTimer);
    state.collab.presenceTimer = null;
  }
}

function startCollaborationLoops() {
  if (!state.project || !hasPermission("notebook.collaborate")) return;
  stopCollaborationLoops();
  heartbeatNotebook().catch(() => null);
  if (!isProjectSocketOpen()) {
    state.collab.pollTimer = setInterval(() => pollNotebookState().catch(() => null), 4000);
  }
  state.collab.presenceTimer = setInterval(() => heartbeatNotebook().catch(() => null), 9000);
}

async function heartbeatNotebook() {
  if (!state.project || !hasPermission("notebook.collaborate")) return;
  if (isProjectSocketOpen()) {
    socketSend({ action: "collab.presence", cursor: currentCursorPayload() });
    return;
  }
  const payload = await api(`/api/projects/${state.project.project_id}/collab/presence`, {
    method: "POST",
    body: { cursor: currentCursorPayload() },
  });
  renderCollabPresence(payload.presence || []);
}

async function pollNotebookState() {
  if (!state.project || !hasPermission("notebook.collaborate")) return;
  const payload = await api(`/api/projects/${state.project.project_id}/collab/notebook`);
  renderCollabPresence(payload.presence || []);
  if (typeof payload.revision === "number" && payload.revision > state.collab.revision) {
    const localCells = collectCells();
    state.collab.revision = payload.revision;
    if (!state.collab.syncTimer && !sameJson(localCells, payload.cells || [])) {
      renderNotebook(payload.cells || []);
      ui.collabStatus.textContent = `Live-Sync aktualisiert. Revision ${payload.revision}.`;
    }
  }
}

function scheduleNotebookSync() {
  if (!state.project || !hasPermission("notebook.collaborate")) return;
  if (state.collab.syncTimer) clearTimeout(state.collab.syncTimer);
  ui.collabStatus.textContent = isProjectSocketOpen() ? "WebSocket-Sync wartet auf lokale Aenderungen..." : "Live-Sync wartet auf lokale Aenderungen...";
  state.collab.syncTimer = setTimeout(() => {
    syncNotebookNow().catch((error) => notify(error.message));
  }, 650);
}

async function syncNotebookNow(showNotification = false) {
  if (!state.project || !hasPermission("notebook.collaborate")) return;
  if (state.collab.syncTimer) {
    clearTimeout(state.collab.syncTimer);
    state.collab.syncTimer = null;
  }
  const localCells = collectCells();
  if (isProjectSocketOpen()) {
    socketSend({
      action: "collab.sync",
      cells: localCells,
      base_revision: state.collab.revision,
      cursor: currentCursorPayload(),
    });
    ui.collabStatus.textContent = `WebSocket-Sync aktiv (Revision ${state.collab.revision}).`;
    if (showNotification) notify("Notebook synchronisiert.");
    return;
  }
  const payload = await api(`/api/projects/${state.project.project_id}/collab/notebook`, {
    method: "PUT",
    body: {
      cells: localCells,
      base_revision: state.collab.revision,
      cursor: currentCursorPayload(),
    },
  });
  const visibleCells = collectCells();
  state.collab.revision = payload.revision || state.collab.revision;
  renderCollabPresence(payload.presence || []);
  if (!sameJson(payload.cells || [], visibleCells)) {
    renderNotebook(payload.cells || []);
  }
  ui.collabStatus.textContent = `Live-Sync aktiv (Revision ${state.collab.revision}).`;
  if (showNotification) notify("Notebook synchronisiert.");
}

async function loadNotebookState() {
  if (!state.project) return;
  if (hasPermission("notebook.collaborate")) {
    const payload = await api(`/api/projects/${state.project.project_id}/collab/notebook`);
    state.collab.revision = payload.revision || 0;
    ui.collabStatus.textContent = isProjectSocketOpen()
      ? `Live-Sync ueber WebSocket aktiv (Revision ${state.collab.revision}).`
      : `Live-Sync aktiv (Revision ${state.collab.revision}).`;
    renderCollabPresence(payload.presence || []);
    renderNotebook(payload.cells || []);
    startCollaborationLoops();
    return;
  }
  const payload = await api(`/api/projects/${state.project.project_id}/notebook`);
  state.collab.revision = 0;
  ui.collabStatus.textContent = "";
  renderCollabPresence([]);
  renderNotebook(payload.cells || []);
}

function collectCells() {
  return [...document.querySelectorAll("[data-cell-index]")].map((article, index) => ({
    id: article.dataset.cellId || `cell-${index}`,
    title: article.querySelector(".cell-title").value,
    language: article.querySelector(".cell-language").value,
    code: article.querySelector(".cell-code").value,
    stdin: article.querySelector(".cell-stdin").value,
    output: state.realtime.cellOutputById[article.dataset.cellId || `cell-${index}`] ?? article.querySelector(".cell-output").textContent,
  }));
}

function attachNotebookListeners() {
  document.querySelectorAll(".run-cell").forEach((button) => button.addEventListener("click", async (event) => {
    const article = event.target.closest("[data-cell-index]");
    if (!article || !state.project) return;
    const language = article.querySelector(".cell-language").value;
    const code = article.querySelector(".cell-code").value;
    const stdin = article.querySelector(".cell-stdin").value;
    const payload = await api(`/api/projects/${state.project.project_id}/run`, {
      method: "POST",
      body: {
        language,
        code,
        stdin,
        path: notebookRunPath(language),
        command: language === "npm" ? code : undefined,
      },
    });
    setCellOutput(article.dataset.cellId || "", formatRunOutput(payload));
    if (payload.preview_path) {
      window.open(`/preview/${state.project.project_id}/${encodePath(payload.preview_path)}`, "_blank");
    }
    if (hasPermission("notebook.collaborate")) {
      scheduleNotebookSync();
    }
  }));

  document.querySelectorAll(".live-cell").forEach((button) => button.addEventListener("click", (event) => {
    const article = event.target.closest("[data-cell-index]");
    startCellLiveRun(article).catch((error) => notify(error.message));
  }));

  document.querySelectorAll(".send-cell-input").forEach((button) => button.addEventListener("click", (event) => {
    const article = event.target.closest("[data-cell-index]");
    try {
      sendCellLiveInput(article);
    } catch (error) {
      notify(error.message);
    }
  }));

  document.querySelectorAll(".stop-cell-live").forEach((button) => button.addEventListener("click", (event) => {
    const article = event.target.closest("[data-cell-index]");
    try {
      stopCellLiveRun(article);
    } catch (error) {
      notify(error.message);
    }
  }));

  document.querySelectorAll(".delete-cell").forEach((button) => button.addEventListener("click", async (event) => {
    const article = event.target.closest("[data-cell-index]");
    const index = Number(article?.dataset.cellIndex || "-1");
    if (index < 0) return;
    const cellId = article?.dataset.cellId || "";
    if (cellId && state.realtime.cellSessionById[cellId]) {
      stopCellLiveRun(article);
    }
    delete state.realtime.cellSessionById[cellId];
    delete state.realtime.cellOutputById[cellId];
    delete state.realtime.cellStatusById[cellId];
    const cellsCopy = collectCells();
    cellsCopy.splice(index, 1);
    renderNotebook(cellsCopy);
    await saveNotebook();
  }));

  document.querySelectorAll(".cell-title, .cell-language, .cell-code").forEach((field) => {
    const handler = (event) => {
      const article = event.target.closest("[data-cell-index]");
      if (!article) return;
      setCellOutput(article.dataset.cellId || "", "Zelle geaendert. Die angezeigte Ausgabe gehoert eventuell zu einem aelteren Stand.");
      if (hasPermission("notebook.collaborate")) {
        scheduleNotebookSync();
      }
    };
    field.addEventListener("input", handler);
    field.addEventListener("change", handler);
    field.addEventListener("focus", () => heartbeatNotebook().catch(() => null));
  });

  document.querySelectorAll(".cell-stdin").forEach((field) => {
    field.addEventListener("focus", () => heartbeatNotebook().catch(() => null));
  });
}

function renderNotebook(cells) {
  ui.notebookCells.innerHTML = cells.map((cell, index) => `
    <article class="notebook-cell" data-cell-index="${index}" data-cell-id="${escapeHtml(cell.id || `cell-${index}`)}">
      <div class="cell-toolbar">
        <input class="cell-title" type="text" value="${escapeHtml(cell.title || `Zelle ${index + 1}`)}" />
        <select class="cell-language">
          ${["python", "javascript", "cpp", "java", "rust", "html", "node", "npm"].map((language) => `<option value="${language}" ${cell.language === language ? "selected" : ""}>${language}</option>`).join("")}
        </select>
        <button type="button" class="run-cell">Ausfuehren</button>
        <button type="button" class="live-cell">Live</button>
        <button type="button" class="send-cell-input">Eingabe senden</button>
        <button type="button" class="stop-cell-live">Stoppen</button>
        <button type="button" class="delete-cell">Loeschen</button>
      </div>
      <p class="muted cell-live-status">${escapeHtml(state.realtime.cellStatusById[cell.id || `cell-${index}`] || (state.realtime.cellSessionById[cell.id || `cell-${index}`] ? "Live-Session aktiv." : ""))}</p>
      <textarea class="cell-code" spellcheck="false">${escapeHtml(cell.code || "")}</textarea>
      <label class="cell-stdin-wrap">
        <span>Eingabe</span>
        <textarea class="cell-stdin" rows="3" spellcheck="false" placeholder="Optional: eine Eingabe pro Zeile fuer input(), scanf, cin oder readline.">${escapeHtml(cell.stdin || "")}</textarea>
      </label>
      <pre class="output-box cell-output terminal-surface">${escapeHtml(state.realtime.cellOutputById[cell.id || `cell-${index}`] ?? (cell.output || "Noch keine Ausgabe."))}</pre>
    </article>
  `).join("");
  cells.forEach((cell, index) => {
    const cellId = cell.id || `cell-${index}`;
    const node = cellArticle(cellId)?.querySelector(".cell-output");
    const text = state.realtime.cellOutputById[cellId] ?? cell.output ?? "Noch keine Ausgabe.";
    const terminal = cellTerminal(cellId);
    attachTerminalSurface(node, { kind: "cell", cellId });
    terminal.active = Boolean(state.realtime.cellSessionById[cellId]);
    if (state.realtime.cellOutputById[cellId] !== undefined || terminal.lines.some((line) => line.length > 0)) {
      renderTerminal(terminal, node);
    } else {
      resetTerminalOutput(terminal, node, text, terminal.active);
    }
  });
  attachNotebookListeners();
  scheduleActiveTerminalResize();
}

async function saveNotebook() {
  if (!state.project) throw new Error("Kein Projekt gewaehlt.");
  if (hasPermission("notebook.collaborate")) {
    await syncNotebookNow(true);
    return;
  }
  await api(`/api/projects/${state.project.project_id}/notebook`, {
    method: "PUT",
    body: { cells: collectCells() },
  });
  notify("Notebook gespeichert.");
}

function addCell() {
  const cells = collectCells();
  cells.push({
    id: `cell-${Date.now()}`,
    title: `Zelle ${cells.length + 1}`,
    language: "python",
    code: "",
    stdin: "",
    output: "",
  });
  renderNotebook(cells);
  if (hasPermission("notebook.collaborate")) {
    scheduleNotebookSync();
  }
}

function markFileDirty() {
  state.fileDirty = true;
  setRunOutput("Datei geaendert. Die angezeigte Ausgabe gehoert eventuell zu einem aelteren Stand. Speichern oder Datei ausfuehren.");
}

async function refreshChat() {
  if (!ui.chatRoom.value) return;
  state.room = ui.chatRoom.value;
  const payload = await api(`/api/chat/messages?room_key=${encodeURIComponent(state.room)}`);
  ui.chatMessages.innerHTML = (payload.messages || []).map((message) => `
    <article class="chat-message">
      <div class="chat-author">${escapeHtml(message.author_display_name)}</div>
      <div>${escapeHtml(message.message)}</div>
      <small>${formatWhen(message.created_at)}</small>
    </article>
  `).join("");
  if (payload.mute) notify(`Chat-Mute aktiv: ${payload.mute.reason}`);
}

async function sendChat(event) {
  event.preventDefault();
  if (!ui.chatInput.value.trim()) return;
  await api("/api/chat/messages", {
    method: "POST",
    body: { room_key: ui.chatRoom.value, message: ui.chatInput.value },
  });
  ui.chatInput.value = "";
  await refreshChat();
}

async function loadDoc() {
  if (!ui.docSelect.value) {
    ui.docContent.innerHTML = "";
    return;
  }
  const payload = await api(`/api/docs/${ui.docSelect.value}`);
  ui.docContent.innerHTML = markdownToHtml(payload.content);
}

function selectedCurriculumCourse() {
  const courses = state.curriculum?.courses || [];
  return courses.find((course) => course.course_id === state.curriculumCourseId) || courses[0] || null;
}

function selectedCurriculumItem(course) {
  if (!course) return null;
  if (state.curriculumModuleId === "__final__") return course.final_assessment;
  return course.modules.find((module) => module.module_id === state.curriculumModuleId) || course.modules[0] || null;
}

function curriculumCertificateUrl(courseId) {
  return `/api/curriculum/certificate?course_id=${encodeURIComponent(courseId)}`;
}

function selectedCurriculumManagerCourseId() {
  return state.curriculumManageCourseId || ui.curriculumManageCourse?.value || state.curriculumCourseId || "";
}

function curriculumDefinitions() {
  return state.curriculum?.manager?.course_definitions || [];
}

function cloneJson(value) {
  return JSON.parse(JSON.stringify(value));
}

function defaultCurriculumQuestion(type = "single", index = 1) {
  if (type === "text") {
    return {
      id: `frage-${index}`,
      type: "text",
      prompt: "Neue Textfrage",
      accepted: ["beispiel"],
      points: 1,
      explanation: "",
      placeholder: "Antwort",
    };
  }
  return {
    id: `frage-${index}`,
    type,
    prompt: type === "multi" ? "Neue Multiple-Choice-Frage" : "Neue Single-Choice-Frage",
    options: [
      { id: "a", label: "Option A" },
      { id: "b", label: "Option B" },
    ],
    correct: ["a"],
    points: 1,
    explanation: "",
  };
}

function defaultCurriculumModule(index = 1) {
  return {
    module_id: `m${String(index).padStart(2, "0")}-neues-modul`,
    title: `Neues Mini-Modul ${index}`,
    estimated_minutes: 30,
    objectives: ["erstes Lernziel"],
    lesson_markdown: "## Neues Mini-Modul\n\nHier die Inhalte des Mini-Moduls beschreiben.",
    quiz_pass_ratio: 0.67,
    questions: [defaultCurriculumQuestion("single", 1)],
  };
}

function defaultCurriculumDraft() {
  const stamp = String(Date.now()).slice(-6);
  return {
    course_id: `eigener-kurs-${stamp}`,
    title: "Eigener Kurs",
    subtitle: "Neuer Modullehrplan",
    subject_area: "Eigener Fachbereich",
    summary: "Kurzbeschreibung des eigenen Kurses.",
    audience: "Schulunterricht",
    estimated_hours: 6,
    certificate_title: "Nova School Zertifikat Eigener Kurs",
    pass_ratio: 0.7,
    final_pass_ratio: 0.75,
    certificate_theme: {
      label: "Eigener Fachbereich",
      accent: "#126d67",
      accent_dark: "#0a4d49",
      warm: "#8f412f",
      paper: "#fbf3e5",
    },
    modules: [defaultCurriculumModule(1)],
    final_assessment: {
      assessment_id: `eigener-kurs-${stamp}-abschluss`,
      title: "Abschlusspruefung Eigener Kurs",
      instructions: "Hier die Hinweise zur Abschlusspruefung eintragen.",
      questions: [defaultCurriculumQuestion("single", 1)],
    },
    is_custom: true,
  };
}

function questionOptionsToLines(question) {
  return (question.options || []).map((option) => `${option.id} | ${option.label}`).join("\n");
}

function linesToQuestionOptions(text) {
  return String(text || "").split(/\r?\n/).map((line, index) => {
    const raw = line.trim();
    if (!raw) return null;
    const parts = raw.split("|");
    const optionId = (parts[0] || String.fromCharCode(97 + index)).trim();
    const label = (parts[1] || parts[0] || `Option ${index + 1}`).trim();
    return { id: optionId, label };
  }).filter(Boolean);
}

function loadCurriculumDraftFromSource(courseId) {
  const source = curriculumDefinitions().find((course) => course.course_id === courseId);
  if (!source) {
    state.curriculumDraft = defaultCurriculumDraft();
    return;
  }
  const draft = cloneJson(source);
  if (!source.is_custom) {
    draft.course_id = `${source.course_id}-eigener-kurs`;
    draft.title = `${source.title} Eigene Version`;
    draft.certificate_title = `Nova School Zertifikat ${draft.title}`;
    draft.is_custom = true;
  }
  state.curriculumDraft = draft;
}

function curriculumQuestionEditor(question, scope, moduleIndex, questionIndex) {
  const isText = question.type === "text";
  return `
    <article class="admin-card stack compact">
      <div class="section-head">
        <h3>Frage ${questionIndex + 1}</h3>
        <div class="inline-actions">
          <button type="button" data-curriculum-question-up="${scope}:${moduleIndex}:${questionIndex}">Hoch</button>
          <button type="button" data-curriculum-question-down="${scope}:${moduleIndex}:${questionIndex}">Runter</button>
          <button type="button" data-curriculum-question-delete="${scope}:${moduleIndex}:${questionIndex}">Loeschen</button>
        </div>
      </div>
      <label><span>Frage-ID</span><input type="text" value="${escapeHtml(question.id || "")}" data-question-field="id" data-question-scope="${escapeHtml(scope)}" data-module-index="${escapeHtml(moduleIndex)}" data-question-index="${escapeHtml(questionIndex)}" /></label>
      <label><span>Fragetyp</span><select data-question-field="type" data-question-scope="${escapeHtml(scope)}" data-module-index="${escapeHtml(moduleIndex)}" data-question-index="${escapeHtml(questionIndex)}">
        <option value="single" ${question.type === "single" ? "selected" : ""}>Single Choice</option>
        <option value="multi" ${question.type === "multi" ? "selected" : ""}>Multiple Choice</option>
        <option value="text" ${question.type === "text" ? "selected" : ""}>Textantwort</option>
      </select></label>
      <label><span>Prompt</span><textarea rows="2" data-question-field="prompt" data-question-scope="${escapeHtml(scope)}" data-module-index="${escapeHtml(moduleIndex)}" data-question-index="${escapeHtml(questionIndex)}">${escapeHtml(question.prompt || "")}</textarea></label>
      <label><span>Punkte</span><input type="number" min="1" step="0.5" value="${escapeHtml(question.points || 1)}" data-question-field="points" data-question-scope="${escapeHtml(scope)}" data-module-index="${escapeHtml(moduleIndex)}" data-question-index="${escapeHtml(questionIndex)}" /></label>
      <label><span>Erklaerung</span><textarea rows="2" data-question-field="explanation" data-question-scope="${escapeHtml(scope)}" data-module-index="${escapeHtml(moduleIndex)}" data-question-index="${escapeHtml(questionIndex)}">${escapeHtml(question.explanation || "")}</textarea></label>
      ${isText ? `
        <label><span>Akzeptierte Antworten, eine pro Zeile</span><textarea rows="3" data-question-field="accepted" data-question-scope="${escapeHtml(scope)}" data-module-index="${escapeHtml(moduleIndex)}" data-question-index="${escapeHtml(questionIndex)}">${escapeHtml((question.accepted || []).join("\n"))}</textarea></label>
        <label><span>Placeholder</span><input type="text" value="${escapeHtml(question.placeholder || "")}" data-question-field="placeholder" data-question-scope="${escapeHtml(scope)}" data-module-index="${escapeHtml(moduleIndex)}" data-question-index="${escapeHtml(questionIndex)}" /></label>
      ` : `
        <label><span>Optionen, eine pro Zeile im Format <code>id | Text</code></span><textarea rows="4" data-question-field="options" data-question-scope="${escapeHtml(scope)}" data-module-index="${escapeHtml(moduleIndex)}" data-question-index="${escapeHtml(questionIndex)}">${escapeHtml(questionOptionsToLines(question))}</textarea></label>
        <label><span>Korrekte IDs ${question.type === "multi" ? "(kommagetrennt)" : ""}</span><input type="text" value="${escapeHtml((question.correct || []).join(", "))}" data-question-field="correct" data-question-scope="${escapeHtml(scope)}" data-module-index="${escapeHtml(moduleIndex)}" data-question-index="${escapeHtml(questionIndex)}" /></label>
      `}
    </article>
  `;
}

function renderCurriculumAuthoring() {
  const canManage = hasPermission("curriculum.manage");
  if (!canManage || !ui.curriculumAuthorEditor) return;
  const definitions = curriculumDefinitions();
  ui.curriculumAuthorSource.innerHTML = definitions.map((course) => `
    <option value="${escapeHtml(course.course_id)}">${escapeHtml(course.title)}${course.is_custom ? " | eigener Kurs" : " | Vorlage"}</option>
  `).join("");
  if (!state.curriculumDraft) {
    if (definitions.length) {
      loadCurriculumDraftFromSource(definitions[0].course_id);
    } else {
      state.curriculumDraft = defaultCurriculumDraft();
    }
  }
  const draft = state.curriculumDraft || defaultCurriculumDraft();
  if (definitions.length && !definitions.some((course) => course.course_id === ui.curriculumAuthorSource.value)) {
    ui.curriculumAuthorSource.value = definitions[0].course_id;
  }
  ui.curriculumAuthorStatus.textContent = draft.is_custom
    ? "Eigene Lehrkraft-Kurse werden serverseitig gespeichert und koennen danach wie reguläre Modullehrplaene freigeschaltet werden."
    : "Vordefinierte Kurse dienen als Vorlage. Zum Speichern bitte eine eigene Kurs-ID nutzen.";
  ui.curriculumAuthorEditor.innerHTML = `
    <article class="review-card stack compact">
      <h3>Kursmetadaten</h3>
      <label><span>Kurs-ID</span><input type="text" value="${escapeHtml(draft.course_id || "")}" data-draft-field="course_id" /></label>
      <label><span>Titel</span><input type="text" value="${escapeHtml(draft.title || "")}" data-draft-field="title" /></label>
      <label><span>Untertitel</span><input type="text" value="${escapeHtml(draft.subtitle || "")}" data-draft-field="subtitle" /></label>
      <label><span>Fachbereich</span><input type="text" value="${escapeHtml(draft.subject_area || "")}" data-draft-field="subject_area" /></label>
      <label><span>Kurzbeschreibung</span><textarea rows="3" data-draft-field="summary">${escapeHtml(draft.summary || "")}</textarea></label>
      <label><span>Zielgruppe</span><input type="text" value="${escapeHtml(draft.audience || "")}" data-draft-field="audience" /></label>
      <label><span>Geschaetzte Stunden</span><input type="number" min="1" value="${escapeHtml(draft.estimated_hours || 1)}" data-draft-field="estimated_hours" /></label>
      <label><span>Zertifikatstitel</span><input type="text" value="${escapeHtml(draft.certificate_title || "")}" data-draft-field="certificate_title" /></label>
      <label><span>Bestehensgrenze Mini-Module</span><input type="number" min="0.1" max="1" step="0.01" value="${escapeHtml(draft.pass_ratio || 0.7)}" data-draft-field="pass_ratio" /></label>
      <label><span>Bestehensgrenze Abschluss</span><input type="number" min="0.1" max="1" step="0.01" value="${escapeHtml(draft.final_pass_ratio || 0.75)}" data-draft-field="final_pass_ratio" /></label>
    </article>
    <article class="review-card stack compact">
      <h3>Zertifikatsdesign</h3>
      <label><span>Label</span><input type="text" value="${escapeHtml(draft.certificate_theme?.label || "")}" data-theme-field="label" /></label>
      <label><span>Akzentfarbe</span><input type="text" value="${escapeHtml(draft.certificate_theme?.accent || "")}" placeholder="#126d67" data-theme-field="accent" /></label>
      <label><span>Dunkle Akzentfarbe</span><input type="text" value="${escapeHtml(draft.certificate_theme?.accent_dark || "")}" placeholder="#0a4d49" data-theme-field="accent_dark" /></label>
      <label><span>Warme Zweitfarbe</span><input type="text" value="${escapeHtml(draft.certificate_theme?.warm || "")}" placeholder="#8f412f" data-theme-field="warm" /></label>
      <label><span>Papierfarbe</span><input type="text" value="${escapeHtml(draft.certificate_theme?.paper || "")}" placeholder="#fbf3e5" data-theme-field="paper" /></label>
    </article>
    <article class="review-card stack compact">
      <div class="section-head">
        <h3>Mini-Module</h3>
        <button type="button" data-curriculum-module-add>Mini-Modul hinzufuegen</button>
      </div>
      ${(draft.modules || []).map((module, moduleIndex) => `
        <article class="admin-card stack compact">
          <div class="section-head">
            <h3>${escapeHtml(module.title || `Mini-Modul ${moduleIndex + 1}`)}</h3>
            <div class="inline-actions">
              <button type="button" data-curriculum-module-up="${escapeHtml(moduleIndex)}">Hoch</button>
              <button type="button" data-curriculum-module-down="${escapeHtml(moduleIndex)}">Runter</button>
              <button type="button" data-curriculum-module-delete="${escapeHtml(moduleIndex)}">Loeschen</button>
            </div>
          </div>
          <label><span>Modul-ID</span><input type="text" value="${escapeHtml(module.module_id || "")}" data-module-field="module_id" data-module-index="${escapeHtml(moduleIndex)}" /></label>
          <label><span>Titel</span><input type="text" value="${escapeHtml(module.title || "")}" data-module-field="title" data-module-index="${escapeHtml(moduleIndex)}" /></label>
          <label><span>Dauer in Minuten</span><input type="number" min="10" value="${escapeHtml(module.estimated_minutes || 30)}" data-module-field="estimated_minutes" data-module-index="${escapeHtml(moduleIndex)}" /></label>
          <label><span>Bestehensgrenze</span><input type="number" min="0.1" max="1" step="0.01" value="${escapeHtml(module.quiz_pass_ratio || 0.67)}" data-module-field="quiz_pass_ratio" data-module-index="${escapeHtml(moduleIndex)}" /></label>
          <label><span>Lernziele, eine Zeile pro Ziel</span><textarea rows="3" data-module-field="objectives" data-module-index="${escapeHtml(moduleIndex)}">${escapeHtml((module.objectives || []).join("\n"))}</textarea></label>
          <label><span>Lerninhalt in Markdown</span><textarea rows="8" data-module-field="lesson_markdown" data-module-index="${escapeHtml(moduleIndex)}">${escapeHtml(module.lesson_markdown || "")}</textarea></label>
          <div class="section-head">
            <h3>Mini-Pruefung</h3>
            <button type="button" data-curriculum-question-add="module:${escapeHtml(moduleIndex)}">Frage hinzufuegen</button>
          </div>
          ${(module.questions || []).map((question, questionIndex) => curriculumQuestionEditor(question, "module", moduleIndex, questionIndex)).join("")}
        </article>
      `).join("")}
    </article>
    <article class="review-card stack compact">
      <div class="section-head">
        <h3>Abschlusspruefung</h3>
        <button type="button" data-curriculum-question-add="final:-1">Frage hinzufuegen</button>
      </div>
      <label><span>Assessment-ID</span><input type="text" value="${escapeHtml(draft.final_assessment?.assessment_id || "")}" data-final-field="assessment_id" /></label>
      <label><span>Titel</span><input type="text" value="${escapeHtml(draft.final_assessment?.title || "")}" data-final-field="title" /></label>
      <label><span>Hinweise</span><textarea rows="4" data-final-field="instructions">${escapeHtml(draft.final_assessment?.instructions || "")}</textarea></label>
      ${(draft.final_assessment?.questions || []).map((question, questionIndex) => curriculumQuestionEditor(question, "final", -1, questionIndex)).join("")}
    </article>
  `;

  ui.curriculumAuthorEditor.querySelectorAll("[data-draft-field]").forEach((field) => field.addEventListener("input", () => {
    const key = field.dataset.draftField;
    state.curriculumDraft[key] = field.type === "number" ? Number(field.value || 0) : field.value;
  }));
  ui.curriculumAuthorEditor.querySelectorAll("[data-theme-field]").forEach((field) => field.addEventListener("input", () => {
    state.curriculumDraft.certificate_theme ||= {};
    state.curriculumDraft.certificate_theme[field.dataset.themeField] = field.value;
  }));
  ui.curriculumAuthorEditor.querySelectorAll("[data-module-field]").forEach((field) => field.addEventListener("input", () => {
    const module = state.curriculumDraft.modules[Number(field.dataset.moduleIndex)];
    const key = field.dataset.moduleField;
    if (key === "estimated_minutes" || key === "quiz_pass_ratio") {
      module[key] = Number(field.value || 0);
    } else if (key === "objectives") {
      module[key] = String(field.value || "").split(/\r?\n/).map((item) => item.trim()).filter(Boolean);
    } else {
      module[key] = field.value;
    }
  }));
  ui.curriculumAuthorEditor.querySelectorAll("[data-final-field]").forEach((field) => field.addEventListener("input", () => {
    const key = field.dataset.finalField;
    state.curriculumDraft.final_assessment[key] = field.value;
  }));
  ui.curriculumAuthorEditor.querySelectorAll("[data-question-field]").forEach((field) => field.addEventListener("input", () => {
    const scope = field.dataset.questionScope;
    const moduleIndex = Number(field.dataset.moduleIndex);
    const questionIndex = Number(field.dataset.questionIndex);
    const questions = scope === "final"
      ? state.curriculumDraft.final_assessment.questions
      : state.curriculumDraft.modules[moduleIndex].questions;
    const question = questions[questionIndex];
    const key = field.dataset.questionField;
    if (key === "points") {
      question[key] = Number(field.value || 1);
    } else if (key === "options") {
      question.options = linesToQuestionOptions(field.value);
    } else if (key === "correct") {
      question.correct = String(field.value || "").split(",").map((item) => item.trim()).filter(Boolean);
    } else if (key === "accepted") {
      question.accepted = String(field.value || "").split(/\r?\n/).map((item) => item.trim()).filter(Boolean);
    } else {
      question[key] = field.value;
      if (key === "type") {
        if (field.value === "text") {
          question.accepted = question.accepted?.length ? question.accepted : ["beispiel"];
          question.placeholder ||= "Antwort";
          delete question.options;
          delete question.correct;
        } else {
          question.options = question.options?.length ? question.options : [{ id: "a", label: "Option A" }, { id: "b", label: "Option B" }];
          question.correct = question.correct?.length ? question.correct : ["a"];
          delete question.accepted;
          delete question.placeholder;
        }
        renderCurriculumAuthoring();
      }
    }
  }));

  ui.curriculumAuthorEditor.querySelector("[data-curriculum-module-add]")?.addEventListener("click", () => {
    state.curriculumDraft.modules.push(defaultCurriculumModule((state.curriculumDraft.modules || []).length + 1));
    renderCurriculumAuthoring();
  });
  ui.curriculumAuthorEditor.querySelectorAll("[data-curriculum-module-up]").forEach((button) => button.addEventListener("click", () => {
    const index = Number(button.dataset.curriculumModuleUp);
    if (index <= 0) return;
    const [item] = state.curriculumDraft.modules.splice(index, 1);
    state.curriculumDraft.modules.splice(index - 1, 0, item);
    renderCurriculumAuthoring();
  }));
  ui.curriculumAuthorEditor.querySelectorAll("[data-curriculum-module-down]").forEach((button) => button.addEventListener("click", () => {
    const index = Number(button.dataset.curriculumModuleDown);
    if (index >= state.curriculumDraft.modules.length - 1) return;
    const [item] = state.curriculumDraft.modules.splice(index, 1);
    state.curriculumDraft.modules.splice(index + 1, 0, item);
    renderCurriculumAuthoring();
  }));
  ui.curriculumAuthorEditor.querySelectorAll("[data-curriculum-module-delete]").forEach((button) => button.addEventListener("click", () => {
    const index = Number(button.dataset.curriculumModuleDelete);
    state.curriculumDraft.modules.splice(index, 1);
    if (!state.curriculumDraft.modules.length) {
      state.curriculumDraft.modules.push(defaultCurriculumModule(1));
    }
    renderCurriculumAuthoring();
  }));
  ui.curriculumAuthorEditor.querySelectorAll("[data-curriculum-question-add]").forEach((button) => button.addEventListener("click", () => {
    const [scope, rawIndex] = String(button.dataset.curriculumQuestionAdd || "").split(":");
    if (scope === "final") {
      state.curriculumDraft.final_assessment.questions.push(defaultCurriculumQuestion("single", state.curriculumDraft.final_assessment.questions.length + 1));
    } else {
      const module = state.curriculumDraft.modules[Number(rawIndex)];
      module.questions.push(defaultCurriculumQuestion("single", module.questions.length + 1));
    }
    renderCurriculumAuthoring();
  }));
  ui.curriculumAuthorEditor.querySelectorAll("[data-curriculum-question-delete]").forEach((button) => button.addEventListener("click", () => {
    const [scope, rawModuleIndex, rawQuestionIndex] = String(button.dataset.curriculumQuestionDelete || "").split(":");
    const questionIndex = Number(rawQuestionIndex);
    if (scope === "final") {
      state.curriculumDraft.final_assessment.questions.splice(questionIndex, 1);
      if (!state.curriculumDraft.final_assessment.questions.length) {
        state.curriculumDraft.final_assessment.questions.push(defaultCurriculumQuestion("single", 1));
      }
    } else {
      const questions = state.curriculumDraft.modules[Number(rawModuleIndex)].questions;
      questions.splice(questionIndex, 1);
      if (!questions.length) questions.push(defaultCurriculumQuestion("single", 1));
    }
    renderCurriculumAuthoring();
  }));
  ui.curriculumAuthorEditor.querySelectorAll("[data-curriculum-question-up]").forEach((button) => button.addEventListener("click", () => {
    const [scope, rawModuleIndex, rawQuestionIndex] = String(button.dataset.curriculumQuestionUp || "").split(":");
    const questionIndex = Number(rawQuestionIndex);
    if (questionIndex <= 0) return;
    const questions = scope === "final"
      ? state.curriculumDraft.final_assessment.questions
      : state.curriculumDraft.modules[Number(rawModuleIndex)].questions;
    const [item] = questions.splice(questionIndex, 1);
    questions.splice(questionIndex - 1, 0, item);
    renderCurriculumAuthoring();
  }));
  ui.curriculumAuthorEditor.querySelectorAll("[data-curriculum-question-down]").forEach((button) => button.addEventListener("click", () => {
    const [scope, rawModuleIndex, rawQuestionIndex] = String(button.dataset.curriculumQuestionDown || "").split(":");
    const questionIndex = Number(rawQuestionIndex);
    const questions = scope === "final"
      ? state.curriculumDraft.final_assessment.questions
      : state.curriculumDraft.modules[Number(rawModuleIndex)].questions;
    if (questionIndex >= questions.length - 1) return;
    const [item] = questions.splice(questionIndex, 1);
    questions.splice(questionIndex + 1, 0, item);
    renderCurriculumAuthoring();
  }));
}

function bindCurriculumCertificateButtons(scope = document) {
  scope.querySelectorAll("[data-curriculum-certificate]").forEach((button) => button.addEventListener("click", () => {
    const courseId = button.dataset.curriculumCertificate;
    if (!courseId) return;
    window.open(curriculumCertificateUrl(courseId), "_blank", "noopener");
  }));
}

function curriculumStatusMarkup(status) {
  const labels = {
    passed: "Bestanden",
    available: "Freigeschaltet",
    locked: "Gesperrt",
  };
  return `<span class="presence-chip">${escapeHtml(labels[status] || status || "offen")}</span>`;
}

function renderCurriculumDashboard() {
  if (!hasPermission("curriculum.use")) {
    state.curriculum = null;
    state.curriculumLastResult = null;
    ui.curriculumPanel.classList.add("hidden");
    return;
  }
  ui.curriculumPanel.classList.remove("hidden");
  const courses = state.curriculum?.courses || [];
  ui.curriculumCourse.innerHTML = courses.map((course) => `<option value="${escapeHtml(course.course_id)}">${escapeHtml(course.title)}</option>`).join("");
  if (!courses.length) {
    ui.curriculumCourseMeta.textContent = "Noch kein Kurs verfuegbar.";
    ui.curriculumResultBanner.innerHTML = "";
    ui.curriculumModuleList.innerHTML = "";
    ui.curriculumModuleDetail.innerHTML = "<p class=\"muted\">Kein Kurs geladen.</p>";
    return;
  }
  if (!courses.some((course) => course.course_id === state.curriculumCourseId)) {
    state.curriculumCourseId = courses[0].course_id;
    state.curriculumModuleId = courses[0]?.modules?.[0]?.module_id || "__final__";
  }
  ui.curriculumCourse.value = state.curriculumCourseId;
  const course = selectedCurriculumCourse();
  if (!course) return;
  const allowedModuleIds = new Set([...(course.modules || []).map((module) => module.module_id), "__final__"]);
  if (!allowedModuleIds.has(state.curriculumModuleId)) {
    state.curriculumModuleId = course.modules[0]?.module_id || "__final__";
  }
  const releaseText = course.release?.enabled
    ? `Freigeschaltet (${course.release.source || "direkt"})`
    : "Noch nicht freigeschaltet";
  ui.curriculumCourseMeta.textContent = `${course.subject_area || "Modullehrplan"} | ${course.summary} | Fortschritt: ${course.progress.passed_modules}/${course.progress.total_modules} Mini-Module | ${releaseText}`;
  const moduleCards = (course.modules || []).map((module) => `
    <button type="button" class="project-button ${state.curriculumModuleId === module.module_id ? "active" : ""}" data-curriculum-module="${escapeHtml(module.module_id)}">
      <strong>${escapeHtml(module.title)}</strong><br />
      <small>${curriculumStatusMarkup(module.status)} | Versuche: ${escapeHtml(module.attempt_count || 0)}</small>
    </button>
  `).join("");
  const finalCard = `
    <button type="button" class="project-button ${state.curriculumModuleId === "__final__" ? "active" : ""}" data-curriculum-module="__final__">
      <strong>Abschlusspruefung</strong><br />
      <small>${curriculumStatusMarkup(course.final_assessment?.unlocked ? (course.final_assessment?.passed ? "passed" : "available") : "locked")} | Versuche: ${escapeHtml(course.final_assessment?.attempt_count || 0)}</small>
    </button>
  `;
  ui.curriculumModuleList.innerHTML = `${moduleCards}${finalCard}`;
  ui.curriculumModuleList.querySelectorAll("[data-curriculum-module]").forEach((button) => button.addEventListener("click", () => {
    state.curriculumModuleId = button.dataset.curriculumModule;
    renderCurriculumDashboard();
  }));
  if (!state.curriculumModuleId) {
    state.curriculumModuleId = course.modules[0]?.module_id || "__final__";
  }
  const item = selectedCurriculumItem(course);
  const currentModuleKey = state.curriculumModuleId || course.modules[0]?.module_id || "__final__";
  const lastResult = state.curriculumLastResult
    && state.curriculumLastResult.courseId === course.course_id
    && state.curriculumLastResult.moduleId === currentModuleKey
      ? state.curriculumLastResult
      : null;
  if (lastResult) {
    const correctCount = (lastResult.feedback || []).filter((entry) => entry.correct).length;
    const resultTitle = lastResult.moduleId === "__final__"
      ? (lastResult.passed ? "Abschlusspruefung bestanden" : "Abschlusspruefung eingereicht")
      : (lastResult.passed ? "Mini-Pruefung bestanden" : "Mini-Pruefung eingereicht");
    ui.curriculumResultBanner.innerHTML = `
      <article class="review-card curriculum-result ${lastResult.passed ? "success" : "warning"}">
        <h3>${resultTitle}</h3>
        <p><strong>Punkte:</strong> ${escapeHtml(lastResult.score)} / ${escapeHtml(lastResult.maxScore)} | <strong>Richtige Antworten:</strong> ${escapeHtml(correctCount)} / ${escapeHtml((lastResult.feedback || []).length)}</p>
        <p>${lastResult.passed ? (lastResult.moduleId === "__final__" ? "Der Kurs ist abgeschlossen. Das Zertifikat kann jetzt heruntergeladen werden." : "Das Modul ist abgeschlossen. Das naechste Modul ist jetzt verfuegbar.") : "Bitte lies die Rueckmeldung und wiederhole die zentralen Inhalte des Moduls."}</p>
        ${lastResult.certificate ? `<button type="button" class="primary" data-curriculum-certificate="${escapeHtml(course.course_id)}">PDF-Zertifikat herunterladen</button>` : ""}
      </article>
    `;
  } else if (course.certificate?.status === "issued") {
    ui.curriculumResultBanner.innerHTML = `
      <article class="review-card curriculum-result success">
        <h3>Zertifikat vorhanden</h3>
        <p>Fuer diesen Kurs wurde bereits ein Zertifikat ausgestellt.</p>
        <button type="button" class="primary" data-curriculum-certificate="${escapeHtml(course.course_id)}">PDF-Zertifikat herunterladen</button>
      </article>
    `;
  } else {
    ui.curriculumResultBanner.innerHTML = "";
  }
  if (!item) {
    ui.curriculumModuleDetail.innerHTML = "<p class=\"muted\">Kein Modul ausgewaehlt.</p>";
    return;
  }
  const isFinal = item.assessment_id === course.final_assessment?.assessment_id;
  const unlocked = isFinal ? Boolean(course.final_assessment?.unlocked) : item.status !== "locked";
  const questions = item.quiz?.questions || item.questions || [];
  const passRatio = isFinal ? course.final_assessment?.pass_ratio : item.quiz?.pass_ratio;
  const itemLastResult = state.curriculumLastResult
    && state.curriculumLastResult.courseId === course.course_id
    && state.curriculumLastResult.moduleId === (isFinal ? "__final__" : item.module_id)
      ? state.curriculumLastResult
      : null;
  ui.curriculumModuleDetail.innerHTML = `
    <article class="review-card">
      <h3>${escapeHtml(isFinal ? course.final_assessment.title : item.title)}</h3>
      <p><strong>Status:</strong> ${isFinal ? (course.final_assessment.passed ? "bestanden" : (course.final_assessment.unlocked ? "freigeschaltet" : "gesperrt")) : item.status}</p>
      <p><strong>Ziel:</strong> ${escapeHtml(course.title)}</p>
      ${isFinal ? `<p>${escapeHtml(course.final_assessment.instructions || "")}</p>` : `<div class="doc-content">${markdownToHtml(item.lesson_markdown || "")}</div>`}
      ${!isFinal ? `<p><strong>Lernziele:</strong> ${(item.objectives || []).map((goal) => escapeHtml(goal)).join(" | ")}</p>` : ""}
      <p><strong>Bestehensgrenze:</strong> ${Math.round((Number(passRatio || 0) * 100))}%</p>
      ${course.certificate?.status === "issued" ? `<p><strong>Zertifikat:</strong> ${escapeHtml(course.certificate.metadata?.course_title || course.title)} | Score: ${escapeHtml(course.certificate.score)} <button type="button" data-curriculum-certificate="${escapeHtml(course.course_id)}">PDF herunterladen</button></p>` : ""}
      ${itemLastResult ? `
        <section class="stack compact">
          <p><strong>Sofort-Rueckmeldung:</strong> ${itemLastResult.passed ? "bestanden" : "noch nicht bestanden"} | ${escapeHtml(itemLastResult.score)} / ${escapeHtml(itemLastResult.maxScore)} Punkte</p>
          ${itemLastResult.feedback.map((entry) => `
            <article class="admin-card">
              <strong>${escapeHtml(entry.prompt)}</strong>
              <p>${entry.correct ? "Richtig." : "Noch nicht richtig."} ${escapeHtml(entry.explanation || "")}</p>
            </article>
          `).join("")}
        </section>
      ` : ""}
      ${unlocked ? `
        <form class="stack compact curriculum-assessment-form" data-course-id="${escapeHtml(course.course_id)}" data-module-id="${escapeHtml(isFinal ? "__final__" : item.module_id)}" data-assessment-kind="${escapeHtml(isFinal ? "final" : "module")}">
          ${questions.map((question) => {
            if (question.type === "single") {
              return `
                <fieldset class="stack compact">
                  <legend>${escapeHtml(question.prompt)}</legend>
                  ${(question.options || []).map((option) => `
                    <label><input type="radio" name="q:${escapeHtml(question.id)}" value="${escapeHtml(option.id)}" /> <span>${escapeHtml(option.label)}</span></label>
                  `).join("")}
                </fieldset>
              `;
            }
            if (question.type === "multi") {
              return `
                <fieldset class="stack compact">
                  <legend>${escapeHtml(question.prompt)}</legend>
                  ${(question.options || []).map((option) => `
                    <label><input type="checkbox" name="q:${escapeHtml(question.id)}" value="${escapeHtml(option.id)}" /> <span>${escapeHtml(option.label)}</span></label>
                  `).join("")}
                </fieldset>
              `;
            }
            return `
              <label>
                <span>${escapeHtml(question.prompt)}</span>
                <input type="text" name="q:${escapeHtml(question.id)}" placeholder="${escapeHtml(question.placeholder || "Antwort")}" />
              </label>
            `;
          }).join("")}
          <button type="submit" class="primary">${isFinal ? "Abschlusspruefung einreichen" : "Mini-Pruefung einreichen"}</button>
        </form>
      ` : `<p class="muted">Dieses Modul ist noch nicht freigeschaltet. Bestehe zuerst die vorherigen Mini-Module oder lasse den Kurs durch die Lehrkraft freischalten.</p>`}
    </article>
  `;
  ui.curriculumModuleDetail.querySelectorAll(".curriculum-assessment-form").forEach((form) => form.addEventListener("submit", (event) => {
    event.preventDefault();
    submitCurriculumAssessment(form).catch((error) => notify(error.message));
  }));
  bindCurriculumCertificateButtons(ui.curriculumPanel);
}

function updateCurriculumReleaseTargets() {
  const manager = state.curriculum?.manager || {};
  const scopeType = ui.curriculumReleaseScopeType.value || "user";
  const entries = scopeType === "group" ? (manager.groups || []) : (manager.users || []);
  ui.curriculumReleaseScopeKey.innerHTML = entries.map((entry) => {
    const value = scopeType === "group" ? entry.group_id : entry.username;
    const label = scopeType === "group"
      ? entry.display_name
      : `${entry.display_name} (${entry.username})`;
    return `<option value="${escapeHtml(value)}">${escapeHtml(label)}</option>`;
  }).join("");
}

function renderCurriculumManager() {
  const canManage = hasPermission("curriculum.manage");
  ui.curriculumManagePanel.classList.toggle("hidden", !canManage);
  if (!canManage) return;
  const courses = state.curriculum?.courses || [];
  const manager = state.curriculum?.manager || {};
  const preferredCourseId = state.curriculumManageCourseId || ui.curriculumManageCourse?.value || state.curriculumCourseId || courses[0]?.course_id || "";
  ui.curriculumManageCourse.innerHTML = courses.map((course) => `<option value="${escapeHtml(course.course_id)}">${escapeHtml(course.title)}</option>`).join("");
  if (!courses.length) {
    state.curriculumManageCourseId = "";
    ui.curriculumReleaseList.innerHTML = "<p class=\"muted\">Noch kein Kurs geladen.</p>";
    ui.curriculumLearnerList.innerHTML = "";
    ui.curriculumAttemptUser.innerHTML = "";
    ui.curriculumAttemptList.innerHTML = "<p class=\"muted\">Noch kein Pruefungsprotokoll verfuegbar.</p>";
    renderCurriculumAuthoring();
    return;
  }
  restoreSelectValue("curriculum-manage-course", preferredCourseId);
  state.curriculumManageCourseId = ui.curriculumManageCourse.value || courses[0].course_id;
  updateCurriculumReleaseTargets();
  const activeCourseId = selectedCurriculumManagerCourseId();
  const releases = (manager.releases || []).filter((entry) => entry.course_id === activeCourseId);
  const learners = (manager.learners || []).filter((entry) => entry.course_id === activeCourseId);
  ui.curriculumReleaseList.innerHTML = releases.map((entry) => `
    <article class="review-card">
      <h3>${escapeHtml(entry.scope_type === "group" ? `Gruppe ${entry.scope_key}` : `Benutzer ${entry.scope_key}`)}</h3>
      <p><strong>Status:</strong> ${entry.enabled ? "freigeschaltet" : "gesperrt"}</p>
      <p><strong>Notiz:</strong> ${escapeHtml(entry.note || "-")}</p>
      <p><strong>Aktualisiert:</strong> ${formatWhen(entry.updated_at)}</p>
    </article>
  `).join("") || "<p class=\"muted\">Noch keine Freigaben fuer diesen Kurs.</p>";
  ui.curriculumLearnerList.innerHTML = learners.map((entry) => `
    <article class="review-card">
      <h3>${escapeHtml(entry.display_name)}</h3>
      <p><strong>Freigabe:</strong> ${entry.release_enabled ? "ja" : "nein"}</p>
      <p><strong>Mini-Module:</strong> ${escapeHtml(entry.passed_modules)} / ${escapeHtml(entry.total_modules)}</p>
      <p><strong>Abschluss:</strong> ${entry.final_passed ? "bestanden" : "offen"}</p>
      <p><strong>Zertifikat:</strong> ${entry.certified ? "erteilt" : "noch nicht"}</p>
      <button type="button" data-curriculum-manage-learner="${escapeHtml(entry.username)}">Pruefungsprotokoll anzeigen</button>
    </article>
  `).join("") || "<p class=\"muted\">Noch keine Lernenden fuer diesen Kurs.</p>";
  ui.curriculumLearnerList.querySelectorAll("[data-curriculum-manage-learner]").forEach((button) => button.addEventListener("click", () => {
    state.curriculumAttemptUsername = button.dataset.curriculumManageLearner || "";
    loadCurriculumAttemptHistory().catch((error) => notify(error.message));
  }));
  ui.curriculumAttemptUser.innerHTML = learners.map((entry) => `
    <option value="${escapeHtml(entry.username)}">${escapeHtml(entry.display_name)} (${escapeHtml(entry.username)})</option>
  `).join("");
  if (!learners.length) {
    state.curriculumAttemptUsername = "";
    ui.curriculumAttemptList.innerHTML = "<p class=\"muted\">Fuer diesen Kurs liegen noch keine Schuelerzuordnungen vor.</p>";
    renderCurriculumAuthoring();
    return;
  }
  if (!learners.some((entry) => entry.username === state.curriculumAttemptUsername)) {
    state.curriculumAttemptUsername = learners[0].username;
  }
  ui.curriculumAttemptUser.value = state.curriculumAttemptUsername;
  renderCurriculumAuthoring();
}

function renderCurriculumAttemptHistory() {
  const payload = state.curriculumAttempts;
  if (!hasPermission("curriculum.manage")) {
    ui.curriculumAttemptList.innerHTML = "";
    return;
  }
  if (!payload || !payload.attempts?.length) {
    const learnerLabel = ui.curriculumAttemptUser?.selectedOptions?.[0]?.textContent || "den ausgewaehlten Schueler";
    ui.curriculumAttemptList.innerHTML = `<p class="muted">Fuer ${escapeHtml(learnerLabel)} liegt in diesem Kurs noch keine eingereichte Pruefung vor.</p>`;
    return;
  }
  const attempts = payload.attempts || [];
  const learner = payload.learner || {};
  const progress = payload.progress || {};
  const summary = `
    <article class="review-card">
      <h3>Pruefungsuebersicht: ${escapeHtml(learner.display_name || learner.username || "")}</h3>
      <p><strong>Kurs:</strong> ${escapeHtml(payload.course?.title || "")}</p>
      <p><strong>Fortschritt:</strong> ${escapeHtml(progress.passed_modules || 0)} / ${escapeHtml(progress.total_modules || 0)} Mini-Module | Abschluss: ${progress.final_passed ? "bestanden" : "offen"} | Zertifikat: ${progress.certified ? "erteilt" : "noch nicht"}</p>
      <p><strong>Eingereichte Pruefungen:</strong> ${escapeHtml(attempts.length)}</p>
    </article>
  `;
  const cards = attempts.map((attempt) => `
    <article class="review-card">
      <h3>${escapeHtml(attempt.module_title)}</h3>
      <p><strong>Typ:</strong> ${attempt.assessment_kind === "final" ? "Abschlusspruefung" : "Mini-Pruefung"}</p>
      <p><strong>Status:</strong> ${attempt.passed ? "bestanden" : "nicht bestanden"}</p>
      <p><strong>Punkte:</strong> ${escapeHtml(attempt.score)} / ${escapeHtml(attempt.max_score)} | <strong>Eingereicht:</strong> ${formatWhen(attempt.submitted_at)}</p>
      ${(attempt.feedback || []).map((entry) => `
        <article class="admin-card">
          <strong>${escapeHtml(entry.prompt)}</strong>
          <p>${entry.correct ? "Richtig." : "Nicht richtig."} ${escapeHtml(entry.explanation || "")}</p>
          <p><small>Punkte: ${escapeHtml(entry.earned)} / ${escapeHtml(entry.points)}</small></p>
        </article>
      `).join("")}
    </article>
  `).join("");
  ui.curriculumAttemptList.innerHTML = `${summary}${cards}`;
}

async function loadCurriculumAttemptHistory() {
  if (!hasPermission("curriculum.manage")) {
    state.curriculumAttempts = null;
    renderCurriculumAttemptHistory();
    return;
  }
  const courseId = selectedCurriculumManagerCourseId();
  const username = state.curriculumAttemptUsername || ui.curriculumAttemptUser?.value || "";
  if (!courseId || !username) {
    state.curriculumAttempts = null;
    renderCurriculumAttemptHistory();
    return;
  }
  state.curriculumAttemptUsername = username;
  const payload = await api(`/api/curriculum/attempts?course_id=${encodeURIComponent(courseId)}&username=${encodeURIComponent(username)}`);
  state.curriculumAttempts = payload;
  renderCurriculumAttemptHistory();
}

async function loadCurriculumDashboard() {
  if (!hasPermission("curriculum.use")) {
    state.curriculum = null;
    state.curriculumLastResult = null;
    state.curriculumAttempts = null;
    state.curriculumManageCourseId = "";
    renderCurriculumDashboard();
    renderCurriculumManager();
    renderCurriculumAttemptHistory();
    return;
  }
  state.curriculum = await api("/api/curriculum/dashboard");
  const courses = state.curriculum?.courses || [];
  if (!courses.some((course) => course.course_id === state.curriculumCourseId)) {
    state.curriculumCourseId = courses[0]?.course_id || "";
    state.curriculumModuleId = courses[0]?.modules?.[0]?.module_id || "";
  }
  if (!courses.some((course) => course.course_id === state.curriculumManageCourseId)) {
    state.curriculumManageCourseId = courses[0]?.course_id || "";
  }
  renderCurriculumDashboard();
  renderCurriculumManager();
  if (hasPermission("curriculum.manage")) {
    await loadCurriculumAttemptHistory();
  }
}

async function submitCurriculumAssessment(form) {
  const answers = {};
  const formData = new FormData(form);
  for (const [name, value] of formData.entries()) {
    if (!String(name).startsWith("q:")) continue;
    const key = String(name).slice(2);
    const field = form.querySelectorAll(`[name="${CSS.escape(name)}"]`);
    const isMulti = [...field].some((item) => item.type === "checkbox");
    if (isMulti) {
      answers[key] = formData.getAll(name).map((item) => String(item));
    } else {
      answers[key] = String(value);
    }
  }
  const payload = await api("/api/curriculum/submit", {
    method: "POST",
    body: {
      course_id: form.dataset.courseId,
      module_id: form.dataset.moduleId === "__final__" ? "" : form.dataset.moduleId,
      assessment_kind: form.dataset.assessmentKind,
      answers,
    },
  });
  state.curriculumLastResult = {
    courseId: payload.course_id,
    moduleId: form.dataset.moduleId || "__final__",
    passed: Boolean(payload.passed),
    score: payload.score,
    maxScore: payload.max_score,
    feedback: payload.feedback || [],
    certificate: payload.certificate || null,
  };
  notify(payload.passed ? "Pruefung bestanden." : "Pruefung eingereicht. Bitte Feedback pruefen.");
  state.curriculumCourseId = payload.course?.course_id || state.curriculumCourseId;
  state.curriculumModuleId = form.dataset.moduleId || state.curriculumModuleId;
  await loadCurriculumDashboard();
}

async function saveCurriculumRelease(event) {
  event.preventDefault();
  await api("/api/curriculum/releases", {
    method: "POST",
    body: {
      course_id: ui.curriculumManageCourse.value,
      scope_type: ui.curriculumReleaseScopeType.value,
      scope_key: ui.curriculumReleaseScopeKey.value,
      enabled: ui.curriculumReleaseEnabled.checked,
      note: ui.curriculumReleaseNote.value,
    },
  });
  notify("Modullehrplan-Freigabe gespeichert.");
  await loadCurriculumDashboard();
}

async function saveCurriculumDraft() {
  if (!hasPermission("curriculum.manage")) {
    throw new Error("Der Modullehrplan-Editor ist fuer diese Sitzung nicht freigegeben.");
  }
  if (!state.curriculumDraft) {
    state.curriculumDraft = defaultCurriculumDraft();
  }
  const payload = await api("/api/curriculum/catalog/save", {
    method: "POST",
    body: { course: state.curriculumDraft },
  });
  state.curriculumDraft = cloneJson(payload.course);
  state.curriculumCourseId = payload.course?.course_id || state.curriculumCourseId;
  state.curriculumManageCourseId = payload.course?.course_id || state.curriculumManageCourseId;
  state.curriculumAttemptUsername = "";
  notify(`Eigener Modullehrplan gespeichert: ${payload.course?.title || "Kurs"}`);
  await loadCurriculumDashboard();
  if (ui.curriculumManageCourse) {
    restoreSelectValue("curriculum-manage-course", payload.course?.course_id || "");
    state.curriculumManageCourseId = ui.curriculumManageCourse.value || state.curriculumManageCourseId;
    renderCurriculumManager();
  }
  if (ui.curriculumCourse) {
    restoreSelectValue("curriculum-course", payload.course?.course_id || "");
    state.curriculumCourseId = ui.curriculumCourse.value || state.curriculumCourseId;
    renderCurriculumDashboard();
  }
  if (ui.curriculumAuthorSource && payload.course?.course_id) {
    restoreSelectValue("curriculum-author-source", payload.course.course_id);
    ui.curriculumAuthorSource.value = payload.course.course_id;
    renderCurriculumAuthoring();
  }
}

function renderMentorThread(thread) {
  state.mentorThread = thread || [];
  if (!state.mentorThread.length) {
    ui.mentorThread.innerHTML = "";
    return;
  }
  ui.mentorThread.innerHTML = state.mentorThread.map((item) => `
    <article class="chat-message">
      <div class="chat-author">${escapeHtml(item.author || item.role || "Nova Mentor")}</div>
      <div>${escapeHtml(item.text || "")}</div>
      <small>${formatWhen(item.created_at)}</small>
    </article>
  `).join("");
}

async function loadMentorThread() {
  if (!state.project || !hasPermission("ai.use") || !hasPermission("mentor.use")) {
    renderMentorThread([]);
    return;
  }
  const payload = await api(`/api/projects/${state.project.project_id}/mentor/thread`);
  renderMentorThread(payload.thread || []);
}

async function askAssistant(event) {
  event.preventDefault();
  const prompt = ui.assistantPrompt.value.trim();
  if (!prompt) {
    ui.assistantOutput.textContent = "Keine Anfrage gesendet. Bitte zuerst eine Frage eingeben.";
    return;
  }
  if (!hasPermission("ai.use")) {
    throw new Error("LM Studio ist fuer diese Sitzung nicht freigegeben.");
  }

  const mode = ui.assistantMode?.value || "direct";
  ui.assistantOutput.textContent = mode === "mentor"
    ? "Nova Mentor verarbeitet die Anfrage..."
    : "LM Studio verarbeitet die Anfrage...";

  try {
    if (mode === "mentor") {
      if (!state.project) throw new Error("Fuer den Mentor ist ein aktives Projekt erforderlich.");
      if (!hasPermission("mentor.use")) throw new Error("Mentor-Modus ist fuer diese Sitzung nicht freigegeben.");
      const payload = await api(`/api/projects/${state.project.project_id}/mentor/ask`, {
        method: "POST",
        body: {
          prompt,
          code: ui.fileEditor.value,
          path: ui.filePath.value,
          run_output: ui.runOutput.textContent,
        },
      });
      ui.assistantOutput.textContent = payload.reply || "Keine Antwort.";
      renderMentorThread(payload.thread || []);
      notify(`Mentor-Antwort von ${payload.model || "dem aktiven Modell"} erhalten.`);
      return;
    }

    const payload = await api("/api/assistant/chat", {
      method: "POST",
      body: { prompt, code: ui.fileEditor.value, path: ui.filePath.value },
    });
    ui.assistantOutput.textContent = payload.text || "Keine Antwort.";
    notify(`LM Studio Antwort von ${payload.model || "dem aktiven Modell"} erhalten.`);
  } catch (error) {
    ui.assistantOutput.textContent = `LM Studio Fehler:\n${error.message}`;
    notify(error.message);
  }
}

function renderPlayground() {
  ui.playgroundPanel.classList.toggle("hidden", !hasPermission("playground.manage") || !projectSupportsPlayground());
  if (!hasPermission("playground.manage") || !projectSupportsPlayground()) {
    ui.playgroundStatus.textContent = "";
    ui.playgroundServices.innerHTML = "";
    return;
  }
  if (!state.project) {
    ui.playgroundStatus.textContent = "Kein Projekt gewaehlt.";
    ui.playgroundServices.innerHTML = "";
    return;
  }
  if (state.playground?.error) {
    ui.playgroundStatus.textContent = state.playground.error;
    ui.playgroundServices.innerHTML = "";
    return;
  }
  if (!state.playground) {
    ui.playgroundStatus.textContent = "Noch kein Playground geladen.";
    ui.playgroundServices.innerHTML = "";
    return;
  }

  const caName = state.playground.certificate_authority?.name || "nicht initialisiert";
  const policyName = state.playground.trust_policy?.name || "nicht initialisiert";
  const dispatchMode = state.playground.dispatch_mode || "worker";
  const workerCount = (state.playground.workers || []).filter((item) => item.online).length;
  ui.playgroundStatus.textContent = `Modus: ${dispatchMode} | CA: ${caName} | Policy: ${policyName} | Aktive Worker: ${workerCount}`;
  ui.playgroundServices.innerHTML = (state.playground.services || []).map((service) => `
    <article class="service-card">
      <h3>${escapeHtml(service.name)}</h3>
      <p><strong>Runtime:</strong> ${escapeHtml(service.runtime)}</p>
      <p><strong>Status:</strong> ${escapeHtml(service.job_status || (service.running ? "laeuft" : "gestoppt"))}</p>
      <p><strong>Entrypoint:</strong> ${escapeHtml(service.entrypoint)}</p>
      <p><strong>Port:</strong> ${escapeHtml(service.port || "-")}</p>
      <p><strong>URL:</strong> ${service.url ? `<a href="${escapeHtml(service.url)}" target="_blank" rel="noreferrer">${escapeHtml(service.url)}</a>` : "-"}</p>
      <p><strong>Worker:</strong> ${escapeHtml(service.worker_id)}</p>
      <pre class="output-box">${escapeHtml(nonEmptyText(service.log_tail, "Noch keine Logs."))}</pre>
    </article>
  `).join("") || "<p class=\"muted\">Keine Playground-Services gefunden.</p>";
}

async function loadPlayground() {
  if (!state.project || !hasPermission("playground.manage") || !projectSupportsPlayground()) {
    state.playground = null;
    renderPlayground();
    return;
  }
  try {
    state.playground = await api(`/api/projects/${state.project.project_id}/playground`);
  } catch (error) {
    if (String(error.message || "").includes("topology.json")) {
      state.playground = null;
    } else {
      state.playground = { error: error.message };
    }
  }
  renderPlayground();
}

async function startPlayground() {
  if (!state.project) throw new Error("Kein Projekt gewaehlt.");
  if (!projectSupportsPlayground()) throw new Error("Der Distributed Playground ist nur fuer Projekte mit topology.json verfuegbar.");
  state.playground = await api(`/api/projects/${state.project.project_id}/playground/start`, {
    method: "POST",
    body: {},
  });
  renderPlayground();
  notify("Distributed Playground gestartet.");
}

async function stopPlayground() {
  if (!state.project) throw new Error("Kein Projekt gewaehlt.");
  if (!projectSupportsPlayground()) throw new Error("Der Distributed Playground ist nur fuer Projekte mit topology.json verfuegbar.");
  state.playground = await api(`/api/projects/${state.project.project_id}/playground/stop`, {
    method: "POST",
    body: {},
  });
  renderPlayground();
  notify("Distributed Playground gestoppt.");
}

function feedbackBlock(feedbackEntries) {
  if (!feedbackEntries?.length) {
    return "<p class=\"muted\">Noch kein Feedback.</p>";
  }
  return feedbackEntries.map((entry) => `
    <article class="review-card">
      <h3>${escapeHtml(entry.reviewer_alias || "Review")}</h3>
      <p><strong>Status:</strong> ${escapeHtml(entry.status || "-")}</p>
      <p><strong>Zusammenfassung:</strong> ${escapeHtml(nonEmptyText(entry.feedback?.summary, "Noch keine Zusammenfassung."))}</p>
      <p><strong>Staerken:</strong> ${escapeHtml(nonEmptyText(entry.feedback?.strengths, "Keine Angaben."))}</p>
      <p><strong>Risiken:</strong> ${escapeHtml(nonEmptyText(entry.feedback?.risks, "Keine Angaben."))}</p>
      <p><strong>Fragen:</strong> ${escapeHtml(nonEmptyText(entry.feedback?.questions, "Keine Fragen."))}</p>
      <p><strong>Score:</strong> ${escapeHtml(entry.feedback?.score || "-")}</p>
    </article>
  `).join("");
}

function reviewAssignmentForm(assignment) {
  const feedback = assignment.feedback || {};
  return `
    <form class="stack compact review-feedback-form" data-assignment-id="${escapeHtml(assignment.assignment_id)}">
      <textarea name="summary" rows="3" placeholder="Kurze Zusammenfassung">${escapeHtml(feedback.summary || "")}</textarea>
      <textarea name="strengths" rows="3" placeholder="Staerken">${escapeHtml(feedback.strengths || "")}</textarea>
      <textarea name="risks" rows="3" placeholder="Risiken oder Bugs">${escapeHtml(feedback.risks || "")}</textarea>
      <textarea name="questions" rows="3" placeholder="Rueckfragen">${escapeHtml(feedback.questions || "")}</textarea>
      <label>
        <span>Score</span>
        <select name="score">
          ${[1, 2, 3, 4, 5].map((score) => `<option value="${score}" ${Number(feedback.score || 3) === score ? "selected" : ""}>${score}</option>`).join("")}
        </select>
      </label>
      <button type="submit" class="primary">${assignment.status === "completed" ? "Feedback aktualisieren" : "Feedback speichern"}</button>
    </form>
  `;
}

function attachReviewListeners() {
  document.querySelectorAll(".review-feedback-form").forEach((form) => form.addEventListener("submit", (event) => {
    submitReviewFeedback(event).catch((error) => notify(error.message));
  }));
}

function renderReviewDashboard() {
  if (!hasPermission("review.use")) return;
  const reviews = state.reviews || { submissions: [], assignments: [], analytics: [] };

  ui.reviewSubmissions.innerHTML = (reviews.submissions || []).map((submission) => `
    <article class="review-card">
      <h3>${escapeHtml(submission.project_name)}</h3>
      <p><strong>Status:</strong> ${escapeHtml(submission.review_status)}</p>
      <p><strong>Eingereicht:</strong> ${formatWhen(submission.created_at)}</p>
      <p><strong>Dateien:</strong> ${escapeHtml((submission.files || []).join(", ") || "keine")}</p>
      <p><strong>Vorschau:</strong> ${escapeHtml(submission.preview?.path || "-")}</p>
      <p><strong>Runs:</strong> ${escapeHtml(submission.analytics?.run_count || 0)} | Fehler bis Erfolg: ${escapeHtml(submission.analytics?.failed_runs_before_success || 0)}</p>
      <pre class="output-box">${escapeHtml(nonEmptyText(submission.preview?.content, "Keine Vorschau."))}</pre>
      ${feedbackBlock(submission.feedback || [])}
    </article>
  `).join("") || "<p class=\"muted\">Noch keine eigenen Einreichungen.</p>";

  ui.reviewAssignments.innerHTML = (reviews.assignments || []).map((assignment) => `
    <article class="review-card">
      <h3>${escapeHtml(assignment.submission_alias)}</h3>
      <p><strong>Reviewer:</strong> ${escapeHtml(assignment.reviewer_alias)}</p>
      <p><strong>Status:</strong> ${escapeHtml(assignment.status)}</p>
      <p><strong>Projekt:</strong> ${escapeHtml(assignment.submission?.project_name || "-")}</p>
      <p><strong>Dateien:</strong> ${escapeHtml((assignment.submission?.files || []).join(", ") || "keine")}</p>
      <p><strong>Vorschau:</strong> ${escapeHtml(assignment.submission?.preview?.path || "-")}</p>
      <p><strong>Runs:</strong> ${escapeHtml(assignment.submission?.analytics?.run_count || 0)} | Fehler bis Erfolg: ${escapeHtml(assignment.submission?.analytics?.failed_runs_before_success || 0)}</p>
      <pre class="output-box">${escapeHtml(nonEmptyText(assignment.submission?.preview?.content, "Keine Vorschau."))}</pre>
      ${reviewAssignmentForm(assignment)}
    </article>
  `).join("") || "<p class=\"muted\">Keine Review-Zuweisungen vorhanden.</p>";

  ui.reviewAnalytics.innerHTML = (reviews.analytics || []).map((submission) => `
    <article class="review-card">
      <h3>${escapeHtml(submission.project_name)}</h3>
      <p><strong>Status:</strong> ${escapeHtml(submission.review_status)}</p>
      <p><strong>Runs:</strong> ${escapeHtml(submission.analytics?.run_count || 0)}</p>
      <p><strong>Fehler vor Erfolg:</strong> ${escapeHtml(submission.analytics?.failed_runs_before_success || 0)}</p>
      <p><strong>Erfolg:</strong> ${submission.analytics?.succeeded ? "ja" : "nein"}</p>
    </article>
  `).join("") || "<p class=\"muted\">Keine Audit-Daten vorhanden.</p>";

  attachReviewListeners();
}

async function loadReviewDashboard() {
  if (!hasPermission("review.use")) {
    state.reviews = null;
    renderReviewDashboard();
    return;
  }
  state.reviews = await api("/api/reviews/dashboard");
  renderReviewDashboard();
}

async function submitCurrentProjectForReview() {
  if (!state.project) throw new Error("Kein Projekt gewaehlt.");
  await api(`/api/projects/${state.project.project_id}/reviews/submit`, { method: "POST", body: {} });
  notify("Projekt fuer Peer Review eingereicht.");
  await loadReviewDashboard();
}

async function submitReviewFeedback(event) {
  event.preventDefault();
  const form = event.target;
  const feedback = {
    summary: form.elements.summary.value,
    strengths: form.elements.strengths.value,
    risks: form.elements.risks.value,
    questions: form.elements.questions.value,
    score: Number(form.elements.score.value),
  };
  await api("/api/reviews/feedback", {
    method: "POST",
    body: { assignment_id: form.dataset.assignmentId, feedback },
  });
  notify("Review-Feedback gespeichert.");
  await loadReviewDashboard();
}

function renderArtifacts() {
  if (!hasPermission("deploy.use")) return;
  ui.deploymentArtifacts.innerHTML = (state.artifacts || []).map((artifact) => {
    const notes = (artifact.metadata?.notes || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("");
    const binaries = (artifact.metadata?.artifacts || []).join(", ");
    const link = artifact.kind === "share"
      ? `<a href="${escapeHtml(artifact.url)}" target="_blank" rel="noreferrer">Freigabe oeffnen</a>`
      : `<a href="${escapeHtml(artifact.download_url)}" target="_blank" rel="noreferrer">ZIP herunterladen</a>`;
    return `
      <article class="artifact-card">
        <h3>${escapeHtml(artifact.label)}</h3>
        <p><strong>Projekt:</strong> ${escapeHtml(artifact.project_name)}</p>
        <p><strong>Typ:</strong> ${escapeHtml(artifact.kind)}</p>
        <p><strong>Status:</strong> ${escapeHtml(artifact.status)}</p>
        <p><strong>Erstellt:</strong> ${formatWhen(artifact.created_at)}</p>
        <p>${link}</p>
        <p><strong>Build erfolgreich:</strong> ${artifact.metadata?.build_success === false ? "nein" : "ja"}</p>
        <p><strong>Artefakte:</strong> ${escapeHtml(binaries || "keine")}</p>
        ${notes ? `<ul>${notes}</ul>` : ""}
      </article>
    `;
  }).join("") || "<p class=\"muted\">Noch keine Shares oder Exporte vorhanden.</p>";
}

async function loadArtifacts() {
  if (!hasPermission("deploy.use")) {
    state.artifacts = [];
    renderArtifacts();
    return;
  }
  const payload = await api("/api/deployments");
  state.artifacts = payload.artifacts || [];
  renderArtifacts();
}

async function shareCurrentProject() {
  if (!state.project) throw new Error("Kein Projekt gewaehlt.");
  const artifact = await api(`/api/projects/${state.project.project_id}/deploy/share`, {
    method: "POST",
    body: {},
  });
  notify(`Share erstellt: ${artifact.url}`);
  await loadArtifacts();
}

async function exportCurrentProject() {
  if (!state.project) throw new Error("Kein Projekt gewaehlt.");
  const artifact = await api(`/api/projects/${state.project.project_id}/deploy/export`, {
    method: "POST",
    body: {},
  });
  notify(`Export erstellt: ${artifact.download_url}`);
  await loadArtifacts();
}

function renderPermissionGrid(targetId, selected = {}) {
  $(targetId).innerHTML = permissionKeys().map((key) => `
    <label class="permission-item"><input type="checkbox" data-key="${escapeHtml(key)}" ${selected[key] ? "checked" : ""} /> <span>${escapeHtml(key)}</span></label>
  `).join("");
}

function collectPermissions(targetId) {
  const payload = {};
  $(`${targetId}`).querySelectorAll("input[type=checkbox]").forEach((input) => {
    payload[input.dataset.key] = input.checked;
  });
  return payload;
}

function selectedManagedUser() {
  const users = state.admin?.users || [];
  return users.find((item) => item.username === $("manage-user-target").value) || users[0] || null;
}

function renderManagedUserForm() {
  const user = selectedManagedUser();
  if (!user) {
    $("manage-user-display").value = "";
    $("manage-user-role").value = "student";
    $("manage-user-status").value = "active";
    $("manage-user-password").value = "";
    ui.manageUserMeta.textContent = "Keine Benutzer vorhanden.";
    return;
  }
  $("manage-user-target").value = user.username;
  $("manage-user-display").value = user.display_name || "";
  $("manage-user-role").value = user.role || "student";
  $("manage-user-status").value = user.status || "active";
  $("manage-user-password").value = "";
  ui.manageUserMeta.textContent = `Erstellt: ${formatWhen(user.created_at)} | Letzte Aenderung: ${formatWhen(user.updated_at)}`;
}

function auditChangeMarkup(changes) {
  const entries = Object.entries(changes || {});
  if (!entries.length) {
    return "<p class=\"muted\">Keine Feldaenderungen hinterlegt.</p>";
  }
  return `<ul>${entries.map(([key, value]) => {
    if (key === "password" && value?.reset) {
      return "<li><strong>password</strong>: Passwort wurde zurueckgesetzt.</li>";
    }
    return `<li><strong>${escapeHtml(key)}</strong>: ${escapeHtml(value?.before ?? "-")} -> ${escapeHtml(value?.after ?? "-")}</li>`;
  }).join("")}</ul>`;
}

function auditPayloadMarkup(entry) {
  const payload = entry.payload || {};
  if (entry.action === "admin.user.create") {
    return `
      <p><strong>Anzeigename:</strong> ${escapeHtml(payload.display_name || "-")}</p>
      <p><strong>Rolle:</strong> ${escapeHtml(payload.role || "-")}</p>
      <p><strong>Status:</strong> ${escapeHtml(payload.status || "-")}</p>
    `;
  }
  if (entry.action === "admin.user.update" || entry.action === "admin.user.permissions") {
    return auditChangeMarkup(payload.changes || {});
  }
  return `<pre class="output-box">${escapeHtml(JSON.stringify(payload, null, 2))}</pre>`;
}

function renderManagedUserAudit() {
  const entries = state.adminUserAudit || [];
  ui.manageUserAudit.innerHTML = entries.map((entry) => `
    <article class="review-card">
      <h3>${escapeHtml(entry.action)}</h3>
      <p><strong>Zeit:</strong> ${formatWhen(entry.created_at)}</p>
      <p><strong>Ausgefuehrt von:</strong> ${escapeHtml(entry.actor_username || "-")}</p>
      ${auditPayloadMarkup(entry)}
    </article>
  `).join("") || "<p class=\"muted\">Noch keine protokollierten Benutzer-Aenderungen.</p>";
}

async function loadManagedUserAudit() {
  if (!hasPermission("admin.manage")) return;
  const user = selectedManagedUser();
  if (!user) {
    state.adminUserAudit = [];
    renderManagedUserAudit();
    return;
  }
  const payload = await api(`/api/admin/users/${encodeURIComponent(user.username)}/audit`);
  state.adminUserAudit = payload.entries || [];
  renderManagedUserAudit();
}

async function loadAdminOverview() {
  const previousMembershipUser = $("membership-user").value;
  const previousMuteUser = $("mute-user").value;
  const previousUserPermissionTarget = $("user-permission-target").value;
  const previousManageUserTarget = $("manage-user-target").value;
  const previousMembershipGroup = $("membership-group").value;
  const previousGroupPermissionTarget = $("group-permission-target").value;
  state.admin = await api("/api/admin/overview");
  const { users, groups, memberships, settings, reviews, artifacts, workers, dispatch_jobs, runtime } = state.admin;
  ui.adminSummary.innerHTML = `
    <p><strong>User:</strong> ${users.length}</p>
    <p><strong>Gruppen:</strong> ${groups.length}</p>
    <p><strong>Mitgliedschaften:</strong> ${memberships.length}</p>
    <p><strong>Runner:</strong> ${escapeHtml(settings.runner_backend || "container")} / ${escapeHtml(settings.container_runtime || "docker")}</p>
    <p><strong>Playground:</strong> ${escapeHtml(settings.playground_dispatch_mode || "worker")}</p>
    <p><strong>Worker:</strong> ${(workers || []).filter((item) => item.online).length} aktiv / ${(workers || []).length} gesamt</p>
    <p><strong>Dispatch-Jobs:</strong> ${(dispatch_jobs || []).length}</p>
    <p><strong>Host-Fallback:</strong> ${settings.unsafe_process_backend_enabled ? "aktiv" : "deaktiviert"}</p>
    <p><strong>Review-Einreichungen:</strong> ${(reviews?.submissions || []).length}</p>
    <p><strong>Deployment-Artefakte:</strong> ${(artifacts || []).length}</p>
  `;
  const userOptions = users.map((user) => `<option value="${escapeHtml(user.username)}">${escapeHtml(user.display_name)} (${escapeHtml(user.role)}, ${escapeHtml(user.status)})</option>`).join("");
  const groupOptions = groups.map((group) => `<option value="${escapeHtml(group.group_id)}">${escapeHtml(group.display_name)}</option>`).join("");
  ["membership-user", "mute-user", "user-permission-target", "manage-user-target"].forEach((id) => { $(id).innerHTML = userOptions; });
  ["membership-group", "group-permission-target"].forEach((id) => { $(id).innerHTML = groupOptions; });
  restoreSelectValue("membership-user", previousMembershipUser);
  restoreSelectValue("mute-user", previousMuteUser);
  restoreSelectValue("user-permission-target", previousUserPermissionTarget);
  restoreSelectValue("manage-user-target", previousManageUserTarget);
  restoreSelectValue("membership-group", previousMembershipGroup);
  restoreSelectValue("group-permission-target", previousGroupPermissionTarget);
  populateServerSettingsPanel(settings || {}, runtime || {});
  const user = users.find((item) => item.username === $("user-permission-target").value) || users[0];
  const group = groups.find((item) => item.group_id === $("group-permission-target").value) || groups[0];
  renderPermissionGrid("user-permissions", user?.permissions || {});
  renderPermissionGrid("group-permissions", group?.permissions || {});
  renderManagedUserForm();
  await loadManagedUserAudit();
}

async function init() {
  attachTerminalSurface(ui.runOutput, { kind: "file" });
  const session = await api("/api/session");
  if (!session.authenticated) {
    setView(false);
    return;
  }
  setView(true);
  await refreshBootstrap();
  if (state.chatTimer) clearInterval(state.chatTimer);
  state.chatTimer = setInterval(() => refreshChat().catch(() => null), 3000);
}

ui.loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const payload = await api("/api/login", {
      method: "POST",
      body: { username: $("login-username").value, password: $("login-password").value },
    });
    state.bootstrap = payload.bootstrap;
    setView(true);
    await afterBootstrapLoaded();
    if (state.chatTimer) clearInterval(state.chatTimer);
    state.chatTimer = setInterval(() => refreshChat().catch(() => null), 3000);
    notify("Anmeldung erfolgreich.");
  } catch (error) {
    notify(error.message);
  }
});

$("logout-button").addEventListener("click", async () => {
  stopCollaborationLoops();
  closeProjectSocket();
  await api("/api/logout", { method: "POST" });
  location.reload();
});
$("open-server-settings")?.addEventListener("click", () => {
  ui.serverSettingsPanel?.scrollIntoView({ behavior: "smooth", block: "start" });
});
$("open-manual").addEventListener("click", openManual);
$("open-reference-library").addEventListener("click", openReferenceLibrary);
$("refresh-bootstrap").addEventListener("click", () => refreshBootstrap().catch((error) => notify(error.message)));
$("reload-projects").addEventListener("click", () => refreshBootstrap().catch((error) => notify(error.message)));
$("save-file").addEventListener("click", () => saveFile().catch((error) => notify(error.message)));
$("run-file").addEventListener("click", () => runFile().catch((error) => notify(error.message)));
$("run-file-live").addEventListener("click", () => startLiveRun().catch((error) => notify(error.message)));
$("send-live-input").addEventListener("click", () => {
  try {
    sendLiveInput();
  } catch (error) {
    notify(error.message);
  }
});
$("stop-live-run").addEventListener("click", () => {
  try {
    stopLiveRun();
  } catch (error) {
    notify(error.message);
  }
});
ui.fileEditor?.addEventListener("input", markFileDirty);
$("open-preview").addEventListener("click", previewFile);
$("add-cell").addEventListener("click", addCell);
$("save-notebook").addEventListener("click", () => saveNotebook().catch((error) => notify(error.message)));
$("refresh-playground").addEventListener("click", () => loadPlayground().catch((error) => notify(error.message)));
$("start-playground").addEventListener("click", () => startPlayground().catch((error) => notify(error.message)));
$("stop-playground").addEventListener("click", () => stopPlayground().catch((error) => notify(error.message)));
$("refresh-chat").addEventListener("click", () => refreshChat().catch((error) => notify(error.message)));
ui.chatRoom.addEventListener("change", () => refreshChat().catch((error) => notify(error.message)));
$("chat-form").addEventListener("submit", (event) => sendChat(event).catch((error) => notify(error.message)));
ui.docSelect.addEventListener("change", () => loadDoc().catch((error) => notify(error.message)));
ui.assistantMode?.addEventListener("change", () => {
  const mentorMode = ui.assistantMode.value === "mentor";
  ui.mentorThread.classList.toggle("hidden", !mentorMode || !hasPermission("mentor.use"));
});
ui.assistantForm?.addEventListener("submit", (event) => askAssistant(event).catch((error) => {
  ui.assistantOutput.textContent = `LM Studio Fehler:\n${error.message}`;
  notify(error.message);
}));
$("refresh-reviews").addEventListener("click", () => loadReviewDashboard().catch((error) => notify(error.message)));
$("submit-review-project").addEventListener("click", () => submitCurrentProjectForReview().catch((error) => notify(error.message)));
$("refresh-artifacts").addEventListener("click", () => loadArtifacts().catch((error) => notify(error.message)));
$("share-project").addEventListener("click", () => shareCurrentProject().catch((error) => notify(error.message)));
$("export-project").addEventListener("click", () => exportCurrentProject().catch((error) => notify(error.message)));
$("refresh-curriculum").addEventListener("click", () => loadCurriculumDashboard().catch((error) => notify(error.message)));
$("refresh-curriculum-manage").addEventListener("click", () => loadCurriculumDashboard().catch((error) => notify(error.message)));
ui.curriculumCourse?.addEventListener("change", () => {
  state.curriculumCourseId = ui.curriculumCourse.value;
  state.curriculumModuleId = "";
  state.curriculumLastResult = null;
  renderCurriculumDashboard();
});
ui.curriculumManageCourse?.addEventListener("change", () => {
  state.curriculumManageCourseId = ui.curriculumManageCourse.value;
  state.curriculumAttempts = null;
  state.curriculumAttemptUsername = "";
  renderCurriculumManager();
  loadCurriculumAttemptHistory().catch((error) => notify(error.message));
});
ui.curriculumReleaseScopeType?.addEventListener("change", updateCurriculumReleaseTargets);
ui.curriculumAttemptUser?.addEventListener("change", () => {
  state.curriculumAttemptUsername = ui.curriculumAttemptUser.value;
  loadCurriculumAttemptHistory().catch((error) => notify(error.message));
});
$("curriculum-release-form")?.addEventListener("submit", (event) => saveCurriculumRelease(event).catch((error) => notify(error.message)));
$("curriculum-author-load")?.addEventListener("click", () => {
  loadCurriculumDraftFromSource(ui.curriculumAuthorSource?.value || "");
  renderCurriculumAuthoring();
  notify("Kursvorlage in den Editor geladen.");
});
$("curriculum-author-new")?.addEventListener("click", () => {
  state.curriculumDraft = defaultCurriculumDraft();
  renderCurriculumAuthoring();
  notify("Neuer eigener Modullehrplan vorbereitet.");
});
$("curriculum-author-save")?.addEventListener("click", () => saveCurriculumDraft().catch((error) => notify(error.message)));
$("refresh-admin").addEventListener("click", () => loadAdminOverview().catch((error) => notify(error.message)));
$("refresh-server-settings").addEventListener("click", () => loadServerSettingsOverview().catch((error) => notify(error.message)));

$("project-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  await api("/api/projects", {
    method: "POST",
    body: {
      name: $("project-name").value,
      description: $("project-description").value,
      template: $("project-template").value,
      owner_type: $("project-owner-type").value,
      group_id: $("project-group").value,
    },
  });
  notify("Projekt erstellt.");
  await refreshBootstrap();
});

$("create-user-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  await api("/api/admin/users", {
    method: "POST",
    body: {
      username: $("admin-user-username").value,
      display_name: $("admin-user-display").value,
      password: $("admin-user-password").value,
      role: $("admin-user-role").value,
    },
  });
  notify("Benutzer angelegt.");
  await loadAdminOverview();
});

$("manage-user-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = await api("/api/admin/users/manage", {
    method: "POST",
    body: {
      username: $("manage-user-target").value,
      display_name: $("manage-user-display").value,
      role: $("manage-user-role").value,
      status: $("manage-user-status").value,
      password: $("manage-user-password").value,
    },
  });
  notify(Object.keys(payload.changes || {}).length ? "Benutzer aktualisiert und protokolliert." : "Keine Aenderung gespeichert.");
  await loadAdminOverview();
});

$("create-group-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  await api("/api/admin/groups", {
    method: "POST",
    body: { display_name: $("admin-group-name").value, description: $("admin-group-description").value },
  });
  notify("Gruppe angelegt.");
  await loadAdminOverview();
  await refreshBootstrap();
});

$("membership-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  await api("/api/admin/memberships", {
    method: "POST",
    body: {
      username: $("membership-user").value,
      group_id: $("membership-group").value,
      action: $("membership-action").value,
    },
  });
  notify("Mitgliedschaft aktualisiert.");
  await loadAdminOverview();
  await refreshBootstrap();
});

$("mute-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  await api("/api/admin/mutes", {
    method: "POST",
    body: {
      room_key: $("mute-room").value,
      target_username: $("mute-user").value,
      duration_minutes: Number($("mute-duration").value),
      reason: $("mute-reason").value,
    },
  });
  notify("Mute gesetzt.");
});

$("worker-bootstrap-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const runtime = $("worker-bootstrap-runtime").value;
  const capabilities = runtime === "*" ? ["runtime:*"] : [`runtime:${runtime}`];
  const labels = runtime === "*" ? { runtime: "*" } : { runtime };
  const payload = await api("/api/admin/workers/bootstrap", {
    method: "POST",
    body: {
      worker_id: $("worker-bootstrap-id").value.trim(),
      display_name: $("worker-bootstrap-name").value.trim(),
      capabilities,
      labels,
    },
  });
  $("worker-bootstrap-output").value = JSON.stringify(payload.bootstrap || {}, null, 2);
  notify("Worker-Bootstrap erzeugt.");
  await loadAdminOverview();
});

$("save-user-permissions").addEventListener("click", async () => {
  await api("/api/admin/users/permissions", {
    method: "POST",
    body: { username: $("user-permission-target").value, permissions: collectPermissions("user-permissions") },
  });
  notify("Benutzerrechte gespeichert.");
  await loadAdminOverview();
  await refreshBootstrap();
});

$("save-group-permissions").addEventListener("click", async () => {
  await api("/api/admin/groups/permissions", {
    method: "POST",
    body: { group_id: $("group-permission-target").value, permissions: collectPermissions("group-permissions") },
  });
  notify("Gruppenrechte gespeichert.");
  await loadAdminOverview();
  await refreshBootstrap();
});

$("user-permission-target").addEventListener("change", () => {
  const user = state.admin?.users?.find((item) => item.username === $("user-permission-target").value);
  renderPermissionGrid("user-permissions", user?.permissions || {});
});
$("group-permission-target").addEventListener("change", () => {
  const group = state.admin?.groups?.find((item) => item.group_id === $("group-permission-target").value);
  renderPermissionGrid("group-permissions", group?.permissions || {});
});
$("manage-user-target").addEventListener("change", () => {
  try {
    renderManagedUserForm();
    loadManagedUserAudit().catch((error) => notify(error.message));
  } catch (error) {
    notify(error.message);
  }
});

$("settings-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = await api("/api/server/settings", {
    method: "POST",
    body: {
      school_name: $("setting-school-name").value,
      host: $("setting-host").value,
      port: Number($("setting-port").value || 8877),
      session_ttl_seconds: Number($("setting-session-ttl").value || 43200),
      run_timeout_seconds: Number($("setting-run-timeout").value || 20),
      live_run_timeout_seconds: Number($("setting-live-run-timeout").value || 300),
      tenant_id: $("setting-tenant-id").value,
      nova_shell_path: $("setting-nova-shell-path").value,
      server_public_host: $("setting-server-public-host").value,
      certificate_logo_path: $("setting-certificate-logo-path").value,
      certificate_signatory_name: $("setting-certificate-signatory-name").value,
      certificate_signatory_title: $("setting-certificate-signatory-title").value,
      web_proxy_url: $("setting-web-proxy-url").value,
      web_proxy_no_proxy: $("setting-web-proxy-no-proxy").value,
      web_proxy_required: $("setting-web-proxy-required").checked,
      lmstudio_base_url: $("setting-lmstudio-base").value,
      lmstudio_model: $("setting-lmstudio-model").value,
      playground_dispatch_mode: $("setting-playground-dispatch-mode").value,
      runner_backend: $("setting-runner-backend").value,
      unsafe_process_backend_enabled: $("setting-unsafe-process").checked,
      container_runtime: $("setting-container-runtime").value,
      container_oci_runtime: $("setting-container-oci-runtime").value,
      container_memory_limit: $("setting-container-memory").value,
      container_cpu_limit: $("setting-container-cpu").value,
      container_pids_limit: $("setting-container-pids").value,
      container_file_size_limit_kb: Number($("setting-container-fsize").value || 65536),
      container_nofile_limit: Number($("setting-container-nofile").value || 256),
      container_tmpfs_limit: $("setting-container-tmpfs").value,
      container_seccomp_enabled: $("setting-container-seccomp-enabled").checked,
      container_seccomp_profile: $("setting-container-seccomp-profile").value,
      container_image_python: $("setting-container-image-python").value,
      container_image_node: $("setting-container-image-node").value,
      container_image_cpp: $("setting-container-image-cpp").value,
      container_image_java: $("setting-container-image-java").value,
      container_image_rust: $("setting-container-image-rust").value,
      scheduler_max_concurrent_global: Number($("setting-scheduler-global").value || 4),
      scheduler_max_concurrent_student: Number($("setting-scheduler-student").value || 1),
      scheduler_max_concurrent_teacher: Number($("setting-scheduler-teacher").value || 2),
      scheduler_max_concurrent_admin: Number($("setting-scheduler-admin").value || 3),
    },
  });
  notify(payload?.runtime?.restart_required
    ? "Einstellungen gespeichert. Aenderungen an Serverbasis und Laufzeit werden nach einem Neustart wirksam."
    : "Einstellungen gespeichert.");
  await refreshBootstrap();
  if (hasPermission("admin.manage")) {
    await loadAdminOverview();
  }
});

window.addEventListener("beforeunload", stopCollaborationLoops);
window.addEventListener("beforeunload", closeProjectSocket);
window.addEventListener("resize", () => scheduleActiveTerminalResize());

init().catch((error) => notify(error.message));
