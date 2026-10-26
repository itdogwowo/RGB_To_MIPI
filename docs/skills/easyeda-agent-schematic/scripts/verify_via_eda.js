// verify_via_eda.js — run inside EasyEDA Pro through `lceda-pro invoke`.
//
// This is the authoritative check: the editor itself reports the components,
// the wires and the netlist, so there is no need to guess pin geometry from
// the .esch2 file.
//
// Usage:
//   lceda-pro invoke --session $S --ext-uuid eda --timeout 120000 \
//       --code "$(cat verify_via_eda.js)"
//
// The code is an async function body; it must `return` a JSON-serialisable value.

const out = {};

out.client = eda.sys_Environment.isClient();
out.version = eda.sys_Environment.getEditorCurrentVersion();

// --- components on the current schematic page
const comps = await eda.sch_PrimitiveComponent.getAll();
out.components = comps.map((c) => ({
  id: c.getState_PrimitiveId(),
  designator: c.getState_Designator(),
  type: c.getState_ComponentType(),
}));

// --- wires (a wire group is one net-forming polyline)
const wireIds = await eda.sch_PrimitiveWire.getAllPrimitiveId();
out.wireGroups = wireIds.length;

// --- pins of every component, with absolute coordinates as the editor sees them
out.pins = [];
for (const c of comps) {
  const d = c.getState_Designator();
  if (!d) continue;
  const pins = await eda.sch_PrimitiveComponent.getAllPinsByPrimitiveId(
    c.getState_PrimitiveId()
  );
  out.pins.push({
    designator: d,
    pins: pins.map((p) => ({ n: p.pinNumber, net: p.net, x: p.x, y: p.y })),
  });
}

// --- unconnected pins, straight from the editor's point of view
out.unconnected = [];
for (const item of out.pins) {
  for (const p of item.pins) {
    if (!p.net) out.unconnected.push(`${item.designator}.${p.n}`);
  }
}

// --- DRC (strict, no UI, verbose)
await eda.sch_Document.save();
await new Promise((r) => setTimeout(r, 8000));
const violations = await eda.sch_Drc.check(true, false, true);
out.drc = {
  count: violations.length,
  items: violations.map(
    (v) => `${v.rule}(${v.type}): ${v.primitives.map((p) => p.name).join('|')}`
  ),
};

// --- netlist (Protel2 is plain text and easy to diff)
try {
  const f = await eda.sch_ManufactureData.getNetlistFile('AGENT_VERIFY', 'Protel2');
  const txt = await f.text();
  out.netlistText = txt;
  out.netlistNets = (txt.match(/^\(/gm) || []).length;
} catch (e) {
  out.netlistError = String(e);
}

return out;
