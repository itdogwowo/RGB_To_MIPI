await eda.dmt_EditorControl.openDocument('7a3203061012a805');
await new Promise(r => setTimeout(r, 2000));
const comps = await eda.sch_PrimitiveComponent.getAll();
const out = [];
for (const c of comps) {
  const d = c.getState_Designator();
  if (!d) continue;
  const pins = await eda.sch_PrimitiveComponent.getAllPinsByPrimitiveId(c.getState_PrimitiveId());
  out.push({ ref: d, pins: pins.map(p => ({ n: p.pinNumber, x: p.x, y: p.y })) });
}
return out;
