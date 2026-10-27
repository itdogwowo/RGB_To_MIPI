const comps = await eda.sch_PrimitiveComponent.getAll();
const out = [];
for (const c of comps.slice(0, 4)) {
  const d = c.getState_Designator();
  const id = c.getState_PrimitiveId();
  let pins = [];
  try { pins = await eda.sch_PrimitiveComponent.getAllPinsByPrimitiveId(id); } catch (e) { pins = String(e); }
  out.push({ ref: d, id, sample: Array.isArray(pins) ? pins.slice(0, 3) : pins, keys: Array.isArray(pins) && pins[0] ? Object.keys(pins[0]) : [] });
}
return out;
