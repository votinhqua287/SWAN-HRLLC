// Fig. 1 (system model) as an editable PowerPoint slide.
// Build:  NODE_PATH=<dir with node_modules/pptxgenjs> node paper/figures/src/fig_system.js
// Export: soffice --headless --convert-to pdf paper/figures/fig_system.pptx  (slide = figure canvas)
// The slide is drawn at 2x the printed size (7.0 in wide -> \columnwidth); text 13-15 pt -> 6.5-7.5 pt printed.
const pptxgen = require("pptxgenjs");
const path = require("path");

const W = 7.0, H = 3.9;
const FONT = "Times New Roman";
const C = {
  wg: "1F4E9C", feedLine: "1F4E9C", pa: "E8702A", paLine: "9C4A12", user: "111111",
  sa: "C0392B", plane: "EEF2F7", planeLine: "8C98A6", axis: "8C98A6", cable: "7F7F7F",
  bs: "F2F2F2", bsLine: "404040", text: "111111", dim: "555555",
};

const pres = new pptxgen();
pres.defineLayout({ name: "FIG1", width: W, height: H });
pres.layout = "FIG1";
pres.title = "SWAN system model";
const s = pres.addSlide();
s.background = { color: "FFFFFF" };

// ---------- helpers ----------
function line(x1, y1, x2, y2, o = {}) {
  s.addShape(pres.shapes.LINE, {
    x: Math.min(x1, x2), y: Math.min(y1, y2), w: Math.max(Math.abs(x2 - x1), 0.0001), h: Math.max(Math.abs(y2 - y1), 0.0001),
    flipH: x2 < x1, flipV: y2 < y1,
    line: { color: o.color || "000000", width: o.width || 1, dashType: o.dash || "solid",
            beginArrowType: o.begin || "none", endArrowType: o.end || "none" },
  });
}
function text(runs, x, y, w, h, o = {}) {
  const arr = (typeof runs === "string") ? [{ text: runs }] : runs;
  s.addText(arr.map(r => ({ text: r.text, options: Object.assign({}, r.options || {}) })), {
    x, y, w, h, margin: 0, isTextBox: true, fontFace: FONT, fontSize: o.size || 14, color: o.color || C.text,
    align: o.align || "center", valign: o.valign || "middle", bold: !!o.bold, wrap: false,
    fill: o.fill ? { color: o.fill } : undefined,
  });
}
const it = t => ({ text: t, options: { italic: true } });
const rm = t => ({ text: t });
// subscript: baseline -25 % (pptxgenjs writes baseline = value x 50); PowerPoint/LibreOffice shrink it automatically
const sub = (t, italic = false) => ({ text: t, options: { baseline: -500, italic } });
function circle(cx, cy, d, fill, lineColor, lw = 1) {
  s.addShape(pres.shapes.OVAL, { x: cx - d / 2, y: cy - d / 2, w: d, h: d, fill: { color: fill }, line: { color: lineColor, width: lw } });
}

// ---------- geometry ----------
const X0 = 0.55, SEG = 1.5, GAP = 0.10, M = 4, YWG = 1.47;          // waveguide along x at "height" YWG
const segA = m => X0 + SEG * (m - 1);                               // feed (left end) of segment m
const PA = [1.17, 2.60, 4.50, 5.45];                                // activated PA positions x_m
const YAX = 2.80, PH = 1.2, SK = 0.45;                              // ground plane: centre line, height, skew
const P = (u, v) => [X0 + SEG * M * u + SK * v, YAX - PH * v];      // (u in [0,1] along x, v in [-1/2,1/2] along y)

// ---------- ground plane (service area D_x x D_y), centre line = projection of the waveguide ----------
const pts = [P(0, 0.5), P(1, 0.5), P(1, -0.5), P(0, -0.5)];
const px0 = Math.min(...pts.map(p => p[0])), py0 = Math.min(...pts.map(p => p[1]));
const px1 = Math.max(...pts.map(p => p[0])), py1 = Math.max(...pts.map(p => p[1]));
s.addShape(pres.shapes.CUSTOM_GEOMETRY, {
  x: px0, y: py0, w: px1 - px0, h: py1 - py0,
  fill: { color: C.plane }, line: { color: C.planeLine, width: 0.75 },
  points: pts.map(p => ({ x: p[0] - px0, y: p[1] - py0 })).concat([{ close: true }]),
});
line(X0 - 0.05, YAX, X0 + SEG * M + 0.22, YAX, { color: C.axis, width: 0.75, dash: "dash" });
text([rm("service area "), it("D"), sub("x", true), rm(" × "), it("D"), sub("y", true)], 4.30, 3.43, 2.0, 0.22, { size: 13, color: "4A5563", align: "right" });

// ---------- waveguide segments, feeds, PAs ----------
for (let m = 1; m <= M; m++) {
  const a = segA(m), b = segA(m) + SEG - GAP;
  s.addShape(pres.shapes.RECTANGLE, { x: a, y: YWG - 0.045, w: b - a, h: 0.09, fill: { color: C.wg }, line: { color: C.wg, width: 0.5 } });
  circle(a, YWG, 0.15, "FFFFFF", C.feedLine, 1.25);
}
text("waveguide segment", 5.30, 1.12, 1.14, 0.22, { size: 13, color: C.wg, align: "right" });

// ---------- height d ----------
const XD = X0 + SEG * M + 0.12;
line(XD, YWG + 0.08, XD, YAX - 0.02, { color: C.dim, width: 0.75, begin: "triangle", end: "triangle" });
text([it("d")], XD + 0.05, (YWG + YAX) / 2 - 0.12, 0.2, 0.24, { size: 15, align: "left" });

// ---------- users (black dots) ----------
// user 1 is the bursting user served by all segments in SA mode
const U = [[0.40, -0.33], [0.08, 0.28], [0.18, -0.30], [0.62, 0.32], [0.62, -0.30], [0.74, 0.10], [0.86, -0.25], [0.94, 0.33]];
const UP = U.map(([u, v]) => P(u, v));
UP.forEach(([x, y], i) => {
  circle(x, y, 0.11, C.user, C.user, 0.5);
  if (i === 0) text("1", x + 0.08, y - 0.02, 0.16, 0.18, { size: 13, align: "left" });
  else text(String(i + 1), x + 0.07, y - 0.21, 0.16, 0.18, { size: 13, align: "left" });
});

// ---------- SA links: every activated PA to the bursting user 1 ----------
const [ux, uy] = UP[0];
PA.forEach((x) => {
  const dx = ux - x, dy = uy - YWG, L = Math.hypot(dx, dy);
  line(x + 0.09 * dx / L, YWG + 0.09 * dy / L, ux - 0.07 * dx / L, uy - 0.07 * dy / L, { color: C.sa, width: 1.25, end: "triangle" });
});
PA.forEach((x, i) => {
  circle(x, YWG, 0.19, C.pa, C.paLine, 0.75);
  // label on the side away from the SA link (links of PAs left of user 1 go down-right)
  if (x < ux) text([it("x"), sub(String(i + 1))], x - 0.37, YWG + 0.08, 0.3, 0.22, { size: 14, align: "right" });
  else text([it("x"), sub(String(i + 1))], x + 0.07, YWG + 0.08, 0.3, 0.22, { size: 14, align: "left" });
});

// ---------- BS, per-user queues, bursty arrivals, feed cables ----------
s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 2.15, y: 0.22, w: 2.75, h: 0.62, rectRadius: 0.08,
  fill: { color: C.bs }, line: { color: C.bsLine, width: 1 } });
text([rm("BS: "), it("M"), rm(" RF chains, per-user queues")], 2.15, 0.26, 2.75, 0.27, { size: 14 });
text("TAPP (per frame) + TAS (per slot)", 2.15, 0.53, 2.75, 0.26, { size: 13 });
// queue icon
const QX = 0.75, QY = 0.40, QW = 0.72, QH = 0.28;
line(QX, QY, QX + QW, QY, { color: C.bsLine, width: 1 });
line(QX, QY + QH, QX + QW, QY + QH, { color: C.bsLine, width: 1 });
line(QX + QW, QY, QX + QW, QY + QH, { color: C.bsLine, width: 1 });
for (let i = 0; i < 3; i++) {
  s.addShape(pres.shapes.RECTANGLE, { x: QX + QW - 0.05 - 0.17 * (i + 1), y: QY + 0.05, w: 0.14, h: QH - 0.10,
    fill: { color: i === 0 ? "7A8AA0" : "A9B4C4" }, line: { color: "5B6B80", width: 0.5 } });
}
line(0.12, QY + QH / 2, QX - 0.02, QY + QH / 2, { color: C.bsLine, width: 1, end: "triangle" });
line(QX + QW + 0.02, QY + QH / 2, 2.13, QY + QH / 2, { color: C.bsLine, width: 1, end: "triangle" });
text("bursty ON–OFF arrivals", 0.08, 0.10, 2.0, 0.24, { size: 13, align: "left" });
const CAB = [2.45, 3.10, 3.90, 4.55];
CAB.forEach((x, i) => line(x, 0.84, segA(i + 1), YWG - 0.075, { color: C.cable, width: 1 }));

// ---------- legend (top right) ----------
const LX = 5.30, LY = 0.06, LW = 1.55, RH = 0.225;
s.addShape(pres.shapes.RECTANGLE, { x: LX, y: LY, w: LW, h: 4 * RH + 0.1, fill: { color: "FFFFFF" }, line: { color: "A0A0A0", width: 0.75 } });
const row = i => LY + 0.05 + RH * i;
circle(LX + 0.16, row(0) + RH / 2, 0.13, "FFFFFF", C.feedLine, 1.25); text("feed point", LX + 0.32, row(0), LW - 0.36, RH, { size: 13, align: "left" });
circle(LX + 0.16, row(1) + RH / 2, 0.16, C.pa, C.paLine, 0.75);      text("activated PA", LX + 0.32, row(1), LW - 0.36, RH, { size: 13, align: "left" });
circle(LX + 0.16, row(2) + RH / 2, 0.10, C.user, C.user, 0.5);       text("user", LX + 0.32, row(2), LW - 0.36, RH, { size: 13, align: "left" });
line(LX + 0.05, row(3) + RH / 2, LX + 0.27, row(3) + RH / 2, { color: C.sa, width: 1.25, end: "triangle" });
text("SA links", LX + 0.32, row(3), LW - 0.36, RH, { size: 13, align: "left" });

// ---------- dimensions: L_s and D_x along the front edge, D_y along the left edge ----------
const [fx0, fy] = P(0, -0.5), [fx1] = P(1, -0.5), [sx1] = P(0.25, -0.5);
const YL = fy + 0.14, YD = fy + 0.36;
line(fx0, YL, sx1, YL, { color: C.dim, width: 0.75, begin: "triangle", end: "triangle" });
text([it("L"), sub("s", true)], (fx0 + sx1) / 2 - 0.15, YL - 0.005, 0.3, 0.2, { size: 14, fill: "FFFFFF" });
line(fx0, YD, fx1, YD, { color: C.dim, width: 0.75, begin: "triangle", end: "triangle" });
text([it("D"), sub("x", true), rm(" = "), it("M L"), sub("s", true)], (fx0 + fx1) / 2 - 0.5, YD - 0.10, 1.0, 0.2, { size: 14, fill: "FFFFFF" });
const [lx0, ly0] = P(0, -0.5), [lx1, ly1] = P(0, 0.5);
line(lx0 - 0.16, ly0, lx1 - 0.16, ly1, { color: C.dim, width: 0.75, begin: "triangle", end: "triangle" });
text([it("D"), sub("y", true)], (lx0 + lx1) / 2 - 0.47, (ly0 + ly1) / 2 - 0.11, 0.25, 0.22, { size: 14 });

const out = path.join(__dirname, "..", "fig_system.pptx");
pres.writeFile({ fileName: out }).then(f => console.log("wrote " + f));
