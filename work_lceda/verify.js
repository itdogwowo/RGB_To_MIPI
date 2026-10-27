const page = '7a3203061012a805';
await eda.dmt_EditorControl.openDocument(page);
await new Promise(r => setTimeout(r, 2500));

const comps = await eda.sch_PrimitiveComponent.getAll();
const out = { components: [], unconnected: [], wireGroups: 0 };

for (const c of comps) {
  const d = c.getState_Designator();
  const t = c.getState_ComponentType && c.getState_ComponentType();
  if (!d && t !== 'sheet') continue;
  const id = c.getState_PrimitiveId();
  let pins = [];
  try { pins = await eda.sch_PrimitiveComponent.getAllPinsByPrimitiveId(id); } catch (e) { pins = []; }
  const rows = pins.map(p => ({ n: p.pinNumber, net: p.net || null, x: p.x, y: p.y }));
  out.components.push({ ref: d, type: t, pinCount: rows.length, pins: rows });
  for (const r of rows) if (!r.net) out.unconnected.push(d + '.' + r.n);
}
const w = await eda.sch_PrimitiveWire.getAllPrimitiveId();
out.wireGroups = w.length;
out.summary = {
  components: out.components.length,
  pinsTotal: out.components.reduce((s, c) => s + c.pinCount, 0),
  pinsConnected: out.components.reduce((s, c) => s + c.pins.filter(p => p.net).length, 0),
  unconnected: out.unconnected.length
};
return out;
