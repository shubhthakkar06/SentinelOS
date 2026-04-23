const fs = await import("node:fs/promises");
const path = await import("node:path");
const { Presentation, PresentationFile } = await import("@oai/artifact-tool");

const W = 1280;
const H = 720;
const ROOT = path.resolve("/Users/shubhthakkar/Projects/SentinelOS");
const OUT_DIR = path.join(ROOT, "outputs", "sentinel_end_eval");
const SCRATCH_DIR = path.join(ROOT, "tmp", "slides", "sentinel_end_eval");
const PREVIEW_DIR = path.join(SCRATCH_DIR, "preview");
const VERIFY_DIR = path.join(SCRATCH_DIR, "verification");
const INSPECT_PATH = path.join(SCRATCH_DIR, "inspect.ndjson");
const REF_DIR = path.join(SCRATCH_DIR, "ref");

const PLATES = {
  hero: path.join(REF_DIR, "plate-hero.png"),
  mission: path.join(REF_DIR, "plate-mission.png"),
  architecture: path.join(REF_DIR, "plate-architecture.png"),
  evaluation: path.join(REF_DIR, "plate-evaluation.png"),
};

const FONT = {
  title: "Poppins",
  body: "Lato",
  mono: "Aptos Mono",
};

const C = {
  ink: "#F4FBFF",
  muted: "#B8D2DB",
  dim: "#7FA5AE",
  bg: "#031118",
  panel: "#061B24E8",
  panel2: "#0A2A33D9",
  panelSoft: "#092832B8",
  line: "#48D9EE66",
  cyan: "#48D9EE",
  teal: "#16B6B0",
  mint: "#54E38E",
  amber: "#FFC857",
  coral: "#FF6B5B",
  navy: "#051923",
  white: "#FFFFFF",
  clear: "#00000000",
};

const inspect = [];

const SLIDES = [
  {
    kind: "cover",
    section: "END EVALUATION",
    title: "SentinelOS",
    subtitle: "AI-Advised Microkernel OS Simulator for Autonomous Underwater Vehicles",
    tags: ["AUV real-time scheduling", "Fault prediction", "Priority inheritance", "Benchmarking"],
    footer: "Group 24 | Shubh Thakkar (241IT076) | Rishabh Rajgor (241IT062)",
    plate: "hero",
  },
  {
    kind: "bullets",
    section: "BACKGROUND",
    title: "Why AUVs Need OS-Level Reliability",
    subtitle: "Autonomous underwater vehicles cannot depend on manual recovery once a mission is underway.",
    plate: "hero",
    bullets: [
      ["Hard deadlines", "Navigation, sonar, depth control, and hull checks must complete inside tight timing windows."],
      ["Finite energy", "Every scheduling decision affects battery draw, mission duration, and thermal load."],
      ["Fault isolation", "A logging or communication fault should not cascade into core vehicle control."],
      ["No quick reboot", "At depth, the OS must recover, degrade gracefully, or surface safely without operator access."],
    ],
    callout: "End-eval focus: prove the simulator handles timing, faults, resources, and evaluation metrics together.",
  },
  {
    kind: "bullets",
    section: "PROBLEM",
    title: "Problem Statement and Final Scope",
    subtitle: "Design and evaluate a simulated OS layer that protects mission-critical AUV processes.",
    plate: "architecture",
    bullets: [
      ["Predict fault risk", "Use task and system-state signals to estimate fault probability before damage spreads."],
      ["Adapt priority safely", "Let AI advise the scheduler, while deterministic kernel logic remains in control."],
      ["Model real constraints", "Include memory pressure, battery state, depth pressure, I/O waits, and survival mode."],
      ["Benchmark policies", "Compare Hybrid, EDF, Static Priority, and Round Robin on the same seeded workload."],
    ],
    callout: "Final scope is a Python OS simulator, not a certified RTOS or hardware deployment.",
  },
  {
    kind: "cards",
    section: "FROM MID TO FINAL",
    title: "What Changed Since Mid Evaluation",
    subtitle: "The mid deck proposed modules; the final implementation connects them into a measurable system.",
    plate: "mission",
    cards: [
      ["Mid-Eval Plan", "AI advisory, scheduling module, controlled fault injection, metrics, and simulation-based evaluation."],
      ["Final Build", "Microkernel-style simulator with task lifecycle, schedulers, resources, environment, BMS, CLI, and AI advisor."],
      ["Evaluation Layer", "Fresh benchmark run, JSON outputs, chart-ready KPIs, and deterministic tests across key modules."],
    ],
    metrics: [
      ["4", "Scheduler policies implemented"],
      ["15", "AUV task/service types modeled"],
      ["10+", "KPIs collected per simulation"],
    ],
  },
  {
    kind: "architecture",
    section: "SYSTEM DESIGN",
    title: "Final System Architecture",
    subtitle: "The simulator separates mission dynamics, kernel control, resource management, AI advice, and monitoring.",
    plate: "architecture",
    layers: [
      ["Simulation Layer", "SystemSimulator drives ticks, events, task lifecycle, environment, and survival phases."],
      ["Kernel Layer", "Kernel admits tasks, dispatches scheduler decisions, requeues states, and records context switches."],
      ["Resource Layer", "ResourceManager controls memory, BMS energy drain, admission control, and pressure states."],
      ["Adaptive Layer", "AIAdvisor estimates risk and returns a priority boost without taking over kernel authority."],
      ["Monitoring Layer", "Metrics, visualizer, logger, JSON exports, and CLI make evaluation reproducible."],
    ],
  },
  {
    kind: "state",
    section: "PROCESS MODEL",
    title: "Task and Process Model",
    subtitle: "AUV services and jobs move through a full process-state machine instead of a single ready queue.",
    plate: "architecture",
    bullets: [
      ["7 states", "NEW, READY, RUNNING, BLOCKED, WAITING, SUSPENDED, FAULT, and TERMINATED transitions."],
      ["Persistent services", "Navigation, DepthControl, HullIntegrity, BatteryMonitor, O2Scrubber, and thermal services respawn."],
      ["I/O wait realism", "Sonar, hydrophone, GPS, comms, and logging can enter WAITING for device response."],
      ["Fault recovery", "Tasks can fault, retry recovery, or terminate after repeated failures."],
    ],
  },
  {
    kind: "comparison",
    section: "SCHEDULING",
    title: "Scheduling Module",
    subtitle: "Four policies share the same task model but optimize different OS goals.",
    plate: "architecture",
    rows: [
      ["Hybrid", "Weighted score = criticality + priority + aging + deadline + AI boost - execution penalty."],
      ["EDF", "Runs the task with the earliest deadline; priority breaks deadline ties."],
      ["Static Priority", "Promotes critical services and sorts by effective priority plus energy tie-break."],
      ["Round Robin", "Fairness baseline; each ready task rotates with equal opportunity."],
    ],
    callout: "All schedulers use effective_priority, so AI boosts and PIP boosts are visible to dispatch logic.",
  },
  {
    kind: "pipeline",
    section: "AI ADVISORY",
    title: "AI Fault Advisor",
    subtitle: "The model is advisory: it predicts risk and recommends priority boosts, but the kernel still decides.",
    plate: "mission",
    steps: [
      ["Telemetry features", "Task type, base priority, criticality, remaining time, memory availability, and system state."],
      ["Random Forest", "Offline-trained model estimates fault probability with bounded, deterministic inference cost."],
      ["Risk factors", "Critical task, memory pressure, and deadline proximity become explainable advisory reasons."],
      ["Priority boost", "Fault probability is converted into a graduated boost added to effective priority."],
    ],
    metrics: [
      ["94.2%", "stored model accuracy"],
      ["79%", "stored model precision"],
      ["0-12+", "typical priority boost range"],
    ],
  },
  {
    kind: "formula",
    section: "FAULT MODEL",
    title: "Physics-Informed Fault Model",
    subtitle: "Faults depend on system state, so the AI learns meaningful correlations instead of random noise.",
    plate: "evaluation",
    formula: "fault risk = task base risk x memory pressure x deadline urgency x criticality x depth x temperature x mission mode",
    factors: [
      ["Memory pressure", "LOW to CRITICAL pressure raises allocation and runtime risk."],
      ["Deadline urgency", "Negative or low slack sharply increases fault likelihood."],
      ["Depth pressure", "Deep water raises hull, seal, ballast, and sensor risks."],
      ["Thermal state", "Hot battery cells can trigger thermal cascade faults."],
    ],
  },
  {
    kind: "resources",
    section: "RESOURCE MODEL",
    title: "Resource, Battery, and Environment Model",
    subtitle: "The OS reacts to vehicle state, not just abstract task queues.",
    plate: "mission",
    cards: [
      ["Memory Admission", "Transient jobs are capped and cannot consume memory reserved for core services."],
      ["Battery BMS", "8-cell pack tracks SOC, voltage sag, temperature, health, ETA, and thermal throttling."],
      ["Underwater Environment", "Depth, pressure, speed, heading, sonar mode, comms strength, and hull stress update every tick."],
      ["Survival Mode", "Low-power phases suspend non-critical tasks, reduce power draw, switch sonar mode, and trigger auto-surface."],
    ],
  },
  {
    kind: "pip",
    section: "REAL-TIME CORRECTNESS",
    title: "Priority Inheritance Protocol",
    subtitle: "The lock manager demonstrates and fixes priority inversion, a core real-time OS problem.",
    plate: "architecture",
    bullets: [
      ["Inversion case", "LOW holds a lock needed by HIGH, while MED can keep preempting LOW."],
      ["PIP fix", "LOW temporarily inherits HIGH priority until it releases the lock."],
      ["Implementation", "LockManager tracks holders, wait queues, inversion events, and inheritance boosts."],
      ["Scheduler integration", "Schedulers read effective_priority, so inherited priority changes dispatch order."],
    ],
    placeholder: "Insert screenshot: `venv/bin/python -m pytest tests/test_priority_inversion.py -q`",
  },
  {
    kind: "demo",
    section: "DEMO FLOW",
    title: "CLI and Demo Flow",
    subtitle: "The final system can be demonstrated through the SentinelOS terminal and benchmark scripts.",
    plate: "mission",
    bullets: [
      ["Boot sequence", "Shows kernel, scheduler, BMS, navigation, comms, and AI advisory initialization."],
      ["Operator commands", "`ps`, `top`, `run`, `step`, `sched`, `mission`, `dive`, `sonar`, `battery`, `fault`, and AI commands."],
      ["Live status prompt", "Displays power, depth, heading, memory pressure, scheduler, and mission mode."],
      ["Reproducible benchmark", "`venv/bin/python scripts/compare_schedulers.py --seed 42 --steps 200`."],
    ],
    placeholder: "Insert screenshot: interactive shell with `top` dashboard or `ps` process table.",
  },
  {
    kind: "results",
    section: "EVALUATION",
    title: "Experimental Evaluation",
    subtitle: "All schedulers ran on the same seeded 200-step workload with AI enabled.",
    plate: "evaluation",
    results: {
      categories: ["Hybrid", "EDF", "Priority", "RR"],
      completion: [96.1, 95.8, 100.0, 96.2],
      deadline: [44.9, 80.4, 23.1, 51.0],
      faults: [26, 46, 15, 30],
      context: [197, 67, 105, 200],
    },
    takeaways: [
      ["Best deadline behavior", "Static Priority: 23.1% miss rate; 100.0% completion."],
      ["Fewest faults", "Static Priority: 15 total faults."],
      ["Fewest switches", "EDF: 67 context switches."],
      ["Lowest energy", "Round Robin: 301.4 energy units."],
    ],
  },
  {
    kind: "validation",
    section: "VALIDATION",
    title: "Validation, Limitations, and Future Scope",
    subtitle: "End evaluation should show both what works and what remains to polish.",
    plate: "evaluation",
    columns: [
      ["Validation", ["53 deterministic pytest cases written", "48 pass in current run", "Scheduler, PIP, metrics, and resource modules covered", "Benchmark JSON exported per scheduler"]],
      ["Known Gaps", ["5 tests still use legacy metric/BMS assumptions", "Retrain or re-export ML model with current scikit-learn", "No real AUV hardware or certified RTOS timing", "CLI has a richer primary shell plus older demo script to clean"]],
      ["Future Scope", ["Update tests after BMS refactor", "Multi-run statistical confidence intervals", "Persistent database for experiment history", "Dashboard/API for live visualization"]],
    ],
  },
  {
    kind: "closing",
    section: "CONCLUSION",
    title: "Conclusion",
    subtitle: "SentinelOS demonstrates how AI advisory can support a deterministic microkernel simulator for autonomous AUV missions.",
    plate: "hero",
    bullets: [
      ["Final implementation", "Combines real-time scheduling, fault injection, BMS resources, environment physics, and AI risk advice."],
      ["Explainable evaluation", "Results compare policies using completion rate, deadline misses, faults, energy, and context switches."],
      ["OS concept value", "The project connects scheduling theory, priority inversion, process states, and resource control to an AUV domain."],
    ],
    footer: "Thank You",
  },
];

async function ensureDirs() {
  await fs.mkdir(OUT_DIR, { recursive: true });
  await fs.mkdir(PREVIEW_DIR, { recursive: true });
  await fs.mkdir(VERIFY_DIR, { recursive: true });
}

async function readImageBlob(imagePath) {
  const bytes = await fs.readFile(imagePath);
  return bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);
}

function line(fill = C.clear, width = 0, style = "solid") {
  return { style, fill, width };
}

function record(kind, slideNo, role, text, x, y, w, h) {
  inspect.push({
    kind,
    slide: slideNo,
    role,
    text: text || "",
    textChars: text ? String(text).length : 0,
    textLines: text ? Math.max(1, String(text).split(/\n/).length) : 0,
    bbox: [x, y, w, h],
  });
}

function addShape(slide, slideNo, geometry, x, y, w, h, fill = C.clear, stroke = C.clear, width = 0, role = "shape", extra = {}) {
  const shape = slide.shapes.add({
    geometry,
    position: { left: x, top: y, width: w, height: h },
    fill,
    line: line(stroke, width, extra.lineStyle || "solid"),
    ...extra,
  });
  record("shape", slideNo, role, "", x, y, w, h);
  return shape;
}

function addText(slide, slideNo, text, x, y, w, h, options = {}) {
  const {
    size = 22,
    color = C.ink,
    bold = false,
    face = FONT.body,
    align = "left",
    valign = "top",
    fill = C.clear,
    stroke = C.clear,
    strokeWidth = 0,
    role = "text",
    autoFit = "shrinkText",
    inset = 0,
  } = options;
  const box = addShape(slide, slideNo, "rect", x, y, w, h, fill, stroke, strokeWidth, role);
  box.text = String(text ?? "");
  box.text.fontSize = size;
  box.text.color = color;
  box.text.bold = Boolean(bold);
  box.text.typeface = face;
  box.text.alignment = align;
  box.text.verticalAlignment = valign;
  box.text.insets = { left: inset, right: inset, top: inset, bottom: inset };
  if (autoFit) box.text.autoFit = autoFit;
  record("textbox", slideNo, role, String(text ?? ""), x, y, w, h);
  return box;
}

async function addPlate(slide, slideNo, key, overlay = "#03111899") {
  const imagePath = PLATES[key] || PLATES.hero;
  const image = slide.images.add({
    blob: await readImageBlob(imagePath),
    fit: "cover",
    alt: "Text-free SentinelOS visual background",
  });
  image.position = { left: 0, top: 0, width: W, height: H };
  record("image", slideNo, `background ${key}`, imagePath, 0, 0, W, H);
  addShape(slide, slideNo, "rect", 0, 0, W, H, overlay, C.clear, 0, "readability overlay");
  addShape(slide, slideNo, "rect", 0, 0, W, H, "#00000025", C.clear, 0, "vignette overlay");
}

function addHeader(slide, slideNo, section) {
  addText(slide, slideNo, section, 58, 34, 470, 24, {
    size: 13,
    color: C.cyan,
    bold: true,
    face: FONT.mono,
    role: "section label",
    autoFit: null,
  });
  addText(slide, slideNo, `${String(slideNo).padStart(2, "0")} / ${String(SLIDES.length).padStart(2, "0")}`, 1090, 34, 130, 24, {
    size: 13,
    color: C.dim,
    bold: true,
    face: FONT.mono,
    align: "right",
    role: "slide number",
    autoFit: null,
  });
  addShape(slide, slideNo, "rect", 58, 68, 1162, 1.5, C.line, C.clear, 0, "header rule");
  addShape(slide, slideNo, "ellipse", 44, 58, 21, 21, C.cyan, C.bg, 2, "header marker");
}

function addTitle(slide, slideNo, data, opts = {}) {
  const { x = 58, y = 92, w = 780, titleSize = 41 } = opts;
  addText(slide, slideNo, data.title, x, y, w, 104, {
    size: titleSize,
    color: C.ink,
    bold: true,
    face: FONT.title,
    role: "title",
  });
  if (data.subtitle) {
    addText(slide, slideNo, data.subtitle, x + 2, y + 112, Math.min(w, 780), 58, {
      size: 18,
      color: C.muted,
      face: FONT.body,
      role: "subtitle",
    });
  }
}

function addBulletList(slide, slideNo, bullets, x, y, w, gap = 94) {
  bullets.forEach(([label, body], i) => {
    const yy = y + i * gap;
    addShape(slide, slideNo, "roundRect", x, yy, w, 72, C.panel, C.line, 1.2, `bullet panel ${label}`);
    addShape(slide, slideNo, "rect", x, yy, 7, 72, [C.cyan, C.mint, C.amber, C.coral][i % 4], C.clear, 0, "bullet accent");
    addShape(slide, slideNo, "ellipse", x + 22, yy + 22, 28, 28, [C.cyan, C.mint, C.amber, C.coral][i % 4], C.clear, 0, "bullet dot");
    addText(slide, slideNo, label, x + 66, yy + 14, 250, 24, {
      size: 16,
      color: C.ink,
      bold: true,
      face: FONT.title,
      role: `bullet label ${label}`,
    });
    addText(slide, slideNo, body, x + 66, yy + 40, w - 86, 25, {
      size: 14.5,
      color: C.muted,
      face: FONT.body,
      role: `bullet body ${label}`,
    });
  });
}

function addMetricPill(slide, slideNo, x, y, value, label, accent = C.cyan, w = 215) {
  addShape(slide, slideNo, "roundRect", x, y, w, 95, C.panel, accent, 1.4, `metric ${label}`);
  addText(slide, slideNo, value, x + 20, y + 12, w - 40, 44, {
    size: 31,
    color: accent,
    bold: true,
    face: FONT.title,
    role: `metric value ${label}`,
    autoFit: "shrinkText",
  });
  addText(slide, slideNo, label, x + 22, y + 57, w - 44, 27, {
    size: 13,
    color: C.muted,
    face: FONT.body,
    role: `metric label ${label}`,
  });
}

function addCallout(slide, slideNo, text, x, y, w, h, accent = C.amber) {
  addShape(slide, slideNo, "roundRect", x, y, w, h, "#091B22E6", accent, 1.3, "callout");
  addShape(slide, slideNo, "rect", x, y, 8, h, accent, C.clear, 0, "callout accent");
  addText(slide, slideNo, text, x + 24, y + 17, w - 46, h - 30, {
    size: 17,
    color: C.ink,
    bold: true,
    face: FONT.title,
    role: "callout text",
  });
}

function addCards(slide, slideNo, cards, x, y, cols, cardW, cardH) {
  cards.forEach(([label, body], i) => {
    const row = Math.floor(i / cols);
    const col = i % cols;
    const xx = x + col * (cardW + 22);
    const yy = y + row * (cardH + 22);
    const accent = [C.cyan, C.mint, C.amber, C.coral][i % 4];
    addShape(slide, slideNo, "roundRect", xx, yy, cardW, cardH, C.panel, C.line, 1.2, `card ${label}`);
    addShape(slide, slideNo, "rect", xx, yy, cardW, 6, accent, C.clear, 0, "card top accent");
    addText(slide, slideNo, label, xx + 22, yy + 18, cardW - 44, 27, {
      size: 16,
      color: accent,
      bold: true,
      face: FONT.title,
      role: `card label ${label}`,
    });
    addText(slide, slideNo, body, xx + 22, yy + 52, cardW - 44, cardH - 68, {
      size: 14.5,
      color: C.muted,
      face: FONT.body,
      role: `card body ${label}`,
    });
  });
}

function addScreenshotPlaceholder(slide, slideNo, x, y, w, h, text) {
  addShape(slide, slideNo, "roundRect", x, y, w, h, "#061B24B8", C.cyan, 2, "screenshot placeholder", { lineStyle: "dashed" });
  addShape(slide, slideNo, "rect", x + 20, y + 20, w - 40, 30, "#48D9EE18", C.clear, 0, "placeholder toolbar");
  for (let i = 0; i < 3; i += 1) {
    addShape(slide, slideNo, "ellipse", x + 36 + i * 24, y + 28, 11, 11, [C.coral, C.amber, C.mint][i], C.clear, 0, "placeholder dot");
  }
  addText(slide, slideNo, text, x + 42, y + h / 2 - 34, w - 84, 72, {
    size: 18,
    color: C.ink,
    bold: true,
    face: FONT.title,
    align: "center",
    valign: "middle",
    role: "screenshot instruction",
  });
}

async function slideCover(presentation, data, slideNo) {
  const slide = presentation.slides.add();
  await addPlate(slide, slideNo, data.plate, "#020E15B0");
  addShape(slide, slideNo, "rect", 0, 0, 680, H, "#020E15CC", C.clear, 0, "cover dark panel");
  addShape(slide, slideNo, "rect", 70, 116, 7, 430, C.cyan, C.clear, 0, "cover accent");
  addText(slide, slideNo, data.section, 95, 118, 420, 26, {
    size: 13,
    color: C.cyan,
    bold: true,
    face: FONT.mono,
    role: "cover section",
  });
  addText(slide, slideNo, data.title, 92, 164, 640, 92, {
    size: 59,
    color: C.ink,
    bold: true,
    face: FONT.title,
    role: "cover title",
  });
  addText(slide, slideNo, data.subtitle, 96, 264, 560, 70, {
    size: 20,
    color: C.muted,
    face: FONT.body,
    role: "cover subtitle",
  });
  data.tags.forEach((tag, i) => {
    addShape(slide, slideNo, "roundRect", 96, 376 + i * 44, 382, 30, "#48D9EE1F", C.line, 1, `tag ${tag}`);
    addText(slide, slideNo, tag, 114, 382 + i * 44, 340, 18, {
      size: 12.5,
      color: C.ink,
      face: FONT.mono,
      role: `tag text ${tag}`,
      autoFit: null,
    });
  });
  addText(slide, slideNo, data.footer, 96, 622, 760, 28, {
    size: 14.5,
    color: C.dim,
    face: FONT.body,
    role: "cover footer",
    autoFit: "shrinkText",
  });
}

async function slideBullets(presentation, data, slideNo) {
  const slide = presentation.slides.add();
  await addPlate(slide, slideNo, data.plate, "#031118AA");
  addHeader(slide, slideNo, data.section);
  addTitle(slide, slideNo, data);
  addBulletList(slide, slideNo, data.bullets, 72, 300, 735);
  if (data.callout) addCallout(slide, slideNo, data.callout, 835, 448, 360, 102, C.amber);
}

async function slideCardsLayout(presentation, data, slideNo) {
  const slide = presentation.slides.add();
  await addPlate(slide, slideNo, data.plate, "#031118A8");
  addHeader(slide, slideNo, data.section);
  addTitle(slide, slideNo, data);
  addCards(slide, slideNo, data.cards, 66, 308, 3, 360, 180);
  data.metrics.forEach(([value, label], i) => {
    addMetricPill(slide, slideNo, 144 + i * 335, 548, value, label, [C.cyan, C.mint, C.amber][i], 260);
  });
}

async function slideArchitecture(presentation, data, slideNo) {
  const slide = presentation.slides.add();
  await addPlate(slide, slideNo, data.plate, "#031118B2");
  addHeader(slide, slideNo, data.section);
  addTitle(slide, slideNo, data, { w: 850 });
  const startY = 292;
  data.layers.forEach(([label, body], i) => {
    const x = 92 + i * 226;
    const h = 238 - i * 18;
    const y = startY + i * 18;
    const accent = [C.cyan, C.mint, C.amber, C.coral, C.teal][i];
    addShape(slide, slideNo, "roundRect", x, y, 194, h, "#061B24E8", accent, 1.3, `architecture layer ${label}`);
    addText(slide, slideNo, label, x + 16, y + 20, 160, 42, {
      size: 17,
      color: accent,
      bold: true,
      face: FONT.title,
      role: `layer label ${label}`,
    });
    addText(slide, slideNo, body, x + 16, y + 74, 160, h - 92, {
      size: 12.5,
      color: C.muted,
      face: FONT.body,
      role: `layer body ${label}`,
    });
    if (i < data.layers.length - 1) {
      addShape(slide, slideNo, "rightArrow", x + 188, y + h / 2 - 13, 42, 26, "#48D9EE88", C.clear, 0, "architecture flow");
    }
  });
}

async function slideState(presentation, data, slideNo) {
  const slide = presentation.slides.add();
  await addPlate(slide, slideNo, data.plate, "#031118B8");
  addHeader(slide, slideNo, data.section);
  addTitle(slide, slideNo, data, { w: 780 });
  const states = ["NEW", "READY", "RUNNING", "WAITING", "BLOCKED", "FAULT", "TERMINATED"];
  states.forEach((s, i) => {
    const x = 92 + (i % 4) * 190;
    const y = 318 + Math.floor(i / 4) * 92;
    const accent = [C.dim, C.cyan, C.mint, C.amber, C.coral, C.coral, C.dim][i];
    addShape(slide, slideNo, "roundRect", x, y, 150, 54, "#061B24E8", accent, 1.2, `state ${s}`);
    addText(slide, slideNo, s, x + 12, y + 15, 126, 20, {
      size: 15,
      color: accent,
      bold: true,
      face: FONT.mono,
      align: "center",
      role: `state label ${s}`,
      autoFit: null,
    });
    if (i < states.length - 1 && i !== 3) {
      addShape(slide, slideNo, "rightArrow", x + 152, y + 15, 38, 24, "#48D9EE88", C.clear, 0, "state flow");
    }
  });
  addBulletList(slide, slideNo, data.bullets, 846, 288, 356, 88);
}

async function slideComparison(presentation, data, slideNo) {
  const slide = presentation.slides.add();
  await addPlate(slide, slideNo, data.plate, "#031118B0");
  addHeader(slide, slideNo, data.section);
  addTitle(slide, slideNo, data, { w: 820 });
  data.rows.forEach(([name, body], i) => {
    const y = 302 + i * 76;
    const accent = [C.cyan, C.mint, C.amber, C.coral][i];
    addShape(slide, slideNo, "roundRect", 82, y, 250, 56, C.panel, accent, 1.1, `scheduler name ${name}`);
    addText(slide, slideNo, name, 104, y + 16, 205, 22, {
      size: 17,
      color: accent,
      bold: true,
      face: FONT.title,
      role: `scheduler ${name}`,
    });
    addShape(slide, slideNo, "roundRect", 350, y, 760, 56, "#061B24CC", C.line, 1, `scheduler body ${name}`);
    addText(slide, slideNo, body, 374, y + 13, 710, 29, {
      size: 15,
      color: C.muted,
      face: FONT.body,
      role: `scheduler explanation ${name}`,
    });
  });
  addCallout(slide, slideNo, data.callout, 180, 624, 870, 54, C.mint);
}

async function slidePipeline(presentation, data, slideNo) {
  const slide = presentation.slides.add();
  await addPlate(slide, slideNo, data.plate, "#031118B0");
  addHeader(slide, slideNo, data.section);
  addTitle(slide, slideNo, data, { w: 820 });
  data.steps.forEach(([label, body], i) => {
    const x = 78 + i * 285;
    const accent = [C.cyan, C.mint, C.amber, C.coral][i];
    addShape(slide, slideNo, "roundRect", x, 322, 235, 166, C.panel, accent, 1.2, `pipeline ${label}`);
    addText(slide, slideNo, `0${i + 1}`, x + 18, 342, 50, 32, {
      size: 24,
      color: accent,
      bold: true,
      face: FONT.mono,
      role: `pipeline number ${label}`,
    });
    addText(slide, slideNo, label, x + 18, 382, 200, 28, {
      size: 16,
      color: C.ink,
      bold: true,
      face: FONT.title,
      role: `pipeline label ${label}`,
    });
    addText(slide, slideNo, body, x + 18, 420, 198, 50, {
      size: 12.5,
      color: C.muted,
      face: FONT.body,
      role: `pipeline body ${label}`,
    });
    if (i < data.steps.length - 1) {
      addShape(slide, slideNo, "rightArrow", x + 236, 388, 48, 34, "#48D9EE88", C.clear, 0, "pipeline arrow");
    }
  });
  data.metrics.forEach(([value, label], i) => addMetricPill(slide, slideNo, 225 + i * 290, 548, value, label, [C.cyan, C.mint, C.amber][i], 230));
}

async function slideFormula(presentation, data, slideNo) {
  const slide = presentation.slides.add();
  await addPlate(slide, slideNo, data.plate, "#031118B8");
  addHeader(slide, slideNo, data.section);
  addTitle(slide, slideNo, data, { w: 850 });
  addShape(slide, slideNo, "roundRect", 80, 292, 1120, 82, "#061B24E8", C.cyan, 1.4, "fault formula panel");
  addText(slide, slideNo, data.formula, 112, 315, 1054, 34, {
    size: 20,
    color: C.ink,
    bold: true,
    face: FONT.title,
    align: "center",
    role: "fault formula",
  });
  addCards(slide, slideNo, data.factors, 92, 420, 4, 260, 154);
}

async function slideResources(presentation, data, slideNo) {
  const slide = presentation.slides.add();
  await addPlate(slide, slideNo, data.plate, "#031118AA");
  addHeader(slide, slideNo, data.section);
  addTitle(slide, slideNo, data, { w: 840 });
  addCards(slide, slideNo, data.cards, 76, 300, 2, 535, 142);
}

async function slidePip(presentation, data, slideNo) {
  const slide = presentation.slides.add();
  await addPlate(slide, slideNo, data.plate, "#031118B4");
  addHeader(slide, slideNo, data.section);
  addTitle(slide, slideNo, data, { w: 790 });
  const lanes = [
    ["LOW", "holds sensor_bus lock", C.amber],
    ["MED", "would preempt LOW", C.coral],
    ["HIGH", "waits on same lock", C.mint],
  ];
  lanes.forEach(([name, body, accent], i) => {
    const y = 292 + i * 82;
    addShape(slide, slideNo, "roundRect", 86, y, 240, 56, C.panel, accent, 1.2, `pip lane ${name}`);
    addText(slide, slideNo, name, 108, y + 15, 70, 20, {
      size: 17,
      color: accent,
      bold: true,
      face: FONT.mono,
      role: `pip label ${name}`,
      autoFit: null,
    });
    addText(slide, slideNo, body, 184, y + 14, 120, 24, {
      size: 12.5,
      color: C.muted,
      face: FONT.body,
      role: `pip body ${name}`,
    });
    addShape(slide, slideNo, "rect", 348, y + 24, 520, 8, "#48D9EE33", C.clear, 0, `pip timeline ${name}`);
  });
  addShape(slide, slideNo, "rightArrow", 682, 304, 86, 42, "#54E38EBB", C.clear, 0, "pip boost arrow");
  addText(slide, slideNo, "PIP BOOST: LOW temporarily inherits HIGH priority", 430, 396, 470, 28, {
    size: 15,
    color: C.mint,
    bold: true,
    face: FONT.title,
    role: "pip boost label",
  });
  addBulletList(slide, slideNo, data.bullets, 910, 284, 292, 78);
  addScreenshotPlaceholder(slide, slideNo, 86, 584, 720, 70, data.placeholder);
}

async function slideDemo(presentation, data, slideNo) {
  const slide = presentation.slides.add();
  await addPlate(slide, slideNo, data.plate, "#03111896");
  addHeader(slide, slideNo, data.section);
  addTitle(slide, slideNo, data, { w: 820 });
  addBulletList(slide, slideNo, data.bullets, 70, 286, 510, 86);
  addScreenshotPlaceholder(slide, slideNo, 622, 286, 568, 318, data.placeholder);
  addText(slide, slideNo, "Suggested commands to capture: `python -m sentinel_os -i`, `top`, `ps`, `battery`, `sched priority`, `mission survival`.", 632, 622, 548, 40, {
    size: 14,
    color: C.dim,
    face: FONT.body,
    role: "demo screenshot hint",
  });
}

function styleChart(chart) {
  chart.hasLegend = true;
  chart.legend.position = "bottom";
  chart.legend.textStyle.fontSize = 12;
  chart.legend.textStyle.typeface = FONT.body;
  chart.legend.textStyle.fill = C.ink;
  chart.xAxis.textStyle.fontSize = 11;
  chart.xAxis.textStyle.typeface = FONT.body;
  chart.xAxis.textStyle.fill = C.ink;
  chart.yAxis.textStyle.fontSize = 10;
  chart.yAxis.textStyle.typeface = FONT.body;
  chart.yAxis.textStyle.fill = C.ink;
  chart.plotAreaFill = "#061B2400";
}

async function slideResults(presentation, data, slideNo) {
  const slide = presentation.slides.add();
  await addPlate(slide, slideNo, data.plate, "#031118A8");
  addHeader(slide, slideNo, data.section);
  addTitle(slide, slideNo, data, { w: 840 });

  addShape(slide, slideNo, "roundRect", 66, 286, 725, 314, "#061B24D9", C.line, 1.2, "chart panel");
  const chart = slide.charts.add("bar");
  chart.position = { left: 92, top: 308, width: 680, height: 268 };
  chart.categories = data.results.categories;
  const deadlineSeries = chart.series.add("Deadline miss %");
  deadlineSeries.values = data.results.deadline;
  deadlineSeries.categories = chart.categories;
  deadlineSeries.fill = C.coral;
  deadlineSeries.stroke = { fill: C.coral, width: 1.5, style: "solid" };
  const completionSeries = chart.series.add("Completion %");
  completionSeries.values = data.results.completion;
  completionSeries.categories = chart.categories;
  completionSeries.fill = C.mint;
  completionSeries.stroke = { fill: C.mint, width: 1.5, style: "solid" };
  chart.barOptions.direction = "column";
  chart.barOptions.grouping = "clustered";
  chart.dataLabels.showValue = true;
  chart.dataLabels.position = "outEnd";
  chart.dataLabels.textStyle.fontSize = 10;
  chart.dataLabels.textStyle.typeface = FONT.body;
  chart.dataLabels.textStyle.fill = C.ink;
  styleChart(chart);
  inspect.push({ kind: "chart", slide: slideNo, role: "benchmark chart", text: "Deadline miss and completion percentage chart", textChars: 54, textLines: 1, bbox: [92, 308, 680, 268] });

  data.takeaways.forEach(([label, body], i) => {
    const y = 286 + i * 86;
    const accent = [C.mint, C.cyan, C.amber, C.coral][i];
    addShape(slide, slideNo, "roundRect", 830, y, 350, 78, "#061B24D9", accent, 1.2, `result takeaway ${label}`);
    addText(slide, slideNo, label, 850, y + 13, 310, 27, {
      size: 21,
      color: accent,
      bold: true,
      face: FONT.title,
      role: `takeaway label ${label}`,
    });
    addText(slide, slideNo, body, 852, y + 43, 305, 24, {
      size: 12.8,
      color: C.muted,
      face: FONT.body,
      role: `takeaway body ${label}`,
    });
  });
  addText(slide, slideNo, "Optional screenshot: terminal benchmark table or `results/scheduler_comparison.png`.", 92, 616, 720, 26, {
    size: 13,
    color: C.dim,
    face: FONT.body,
    role: "optional screenshot hint",
  });
}

async function slideValidation(presentation, data, slideNo) {
  const slide = presentation.slides.add();
  await addPlate(slide, slideNo, data.plate, "#031118A8");
  addHeader(slide, slideNo, data.section);
  addTitle(slide, slideNo, data, { w: 840 });
  data.columns.forEach(([label, items], i) => {
    const x = 74 + i * 382;
    const accent = [C.mint, C.amber, C.cyan][i];
    addShape(slide, slideNo, "roundRect", x, 290, 342, 306, C.panel, accent, 1.3, `validation column ${label}`);
    addText(slide, slideNo, label, x + 22, 312, 296, 30, {
      size: 20,
      color: accent,
      bold: true,
      face: FONT.title,
      role: `validation label ${label}`,
    });
    items.forEach((item, j) => {
      const y = 366 + j * 48;
      addShape(slide, slideNo, "ellipse", x + 24, y + 8, 12, 12, accent, C.clear, 0, "validation dot");
      addText(slide, slideNo, item, x + 46, y, 268, 34, {
        size: 13.5,
        color: C.muted,
        face: FONT.body,
        role: `validation item ${label}`,
      });
    });
  });
}

async function slideClosing(presentation, data, slideNo) {
  const slide = presentation.slides.add();
  await addPlate(slide, slideNo, data.plate, "#020E15B0");
  addShape(slide, slideNo, "rect", 0, 0, 705, H, "#020E15D0", C.clear, 0, "closing dark panel");
  addHeader(slide, slideNo, data.section);
  addTitle(slide, slideNo, data, { x: 70, y: 114, w: 650, titleSize: 50 });
  addBulletList(slide, slideNo, data.bullets, 82, 346, 570, 86);
  addText(slide, slideNo, data.footer, 78, 624, 420, 54, {
    size: 34,
    color: C.cyan,
    bold: true,
    face: FONT.title,
    role: "thank you",
  });
}

async function buildDeck() {
  await ensureDirs();
  const presentation = Presentation.create({ slideSize: { width: W, height: H } });
  presentation.theme.colorScheme = {
    name: "SentinelOS Ocean",
    themeColors: {
      bg1: C.bg,
      tx1: C.ink,
      bg2: C.navy,
      tx2: C.muted,
      accent1: C.cyan,
      accent2: C.mint,
      accent3: C.amber,
      accent4: C.coral,
      accent5: C.teal,
      accent6: C.dim,
    },
  };

  for (let i = 0; i < SLIDES.length; i += 1) {
    const data = SLIDES[i];
    const slideNo = i + 1;
    if (data.kind === "cover") await slideCover(presentation, data, slideNo);
    else if (data.kind === "bullets") await slideBullets(presentation, data, slideNo);
    else if (data.kind === "cards") await slideCardsLayout(presentation, data, slideNo);
    else if (data.kind === "architecture") await slideArchitecture(presentation, data, slideNo);
    else if (data.kind === "state") await slideState(presentation, data, slideNo);
    else if (data.kind === "comparison") await slideComparison(presentation, data, slideNo);
    else if (data.kind === "pipeline") await slidePipeline(presentation, data, slideNo);
    else if (data.kind === "formula") await slideFormula(presentation, data, slideNo);
    else if (data.kind === "resources") await slideResources(presentation, data, slideNo);
    else if (data.kind === "pip") await slidePip(presentation, data, slideNo);
    else if (data.kind === "demo") await slideDemo(presentation, data, slideNo);
    else if (data.kind === "results") await slideResults(presentation, data, slideNo);
    else if (data.kind === "validation") await slideValidation(presentation, data, slideNo);
    else if (data.kind === "closing") await slideClosing(presentation, data, slideNo);
    else throw new Error(`Unhandled slide type: ${data.kind}`);
    presentation.slides.items[presentation.slides.items.length - 1].speakerNotes.setText(
      `Presenter guide: ${data.title}. Explain each point briefly and connect it to the final SentinelOS implementation.`
    );
  }
  return presentation;
}

async function saveBlob(blob, filePath) {
  const bytes = new Uint8Array(await blob.arrayBuffer());
  await fs.writeFile(filePath, bytes);
}

async function verifyAndExport(presentation) {
  inspect.unshift({ kind: "deck", slide: 0, role: "deck", text: "SentinelOS End Evaluation", textChars: 25, textLines: 1, bbox: [0, 0, W, H] });
  await fs.writeFile(INSPECT_PATH, inspect.map((r) => JSON.stringify(r)).join("\n") + "\n", "utf8");
  const previews = [];
  for (let i = 0; i < presentation.slides.items.length; i += 1) {
    const slide = presentation.slides.items[i];
    const png = await presentation.export({ slide, format: "png", scale: 1 });
    const previewPath = path.join(PREVIEW_DIR, `slide-${String(i + 1).padStart(2, "0")}.png`);
    await saveBlob(png, previewPath);
    previews.push(previewPath);
  }
  const pptx = await PresentationFile.exportPptx(presentation);
  const pptxPath = path.join(OUT_DIR, "output.pptx");
  await pptx.save(pptxPath);
  await fs.writeFile(
    path.join(VERIFY_DIR, "render_verify_loops.ndjson"),
    JSON.stringify({ loop: 1, slideCount: presentation.slides.count, previewDir: PREVIEW_DIR, pptxPath, timestamp: new Date().toISOString() }) + "\n",
    "utf8",
  );
  return { pptxPath, previews };
}

const presentation = await buildDeck();
const result = await verifyAndExport(presentation);
console.log(result.pptxPath);
