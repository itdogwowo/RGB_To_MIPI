const names = ['sch_Net','sch_Netlist','sch_PrimitiveWire','sch_Document'];
const out = {};
for (const n of names) {
  const obj = eda[n];
  if (!obj) { out[n] = 'missing'; continue; }
  const proto = Object.getPrototypeOf(obj);
  const fns = new Set();
  for (const o of [obj, proto]) {
    for (const k of Object.getOwnPropertyNames(o || {})) {
      try { if (typeof obj[k] === 'function') fns.add(k); } catch (e) {}
    }
  }
  out[n] = [...fns].filter(k => !k.startsWith('_')).sort();
}
return out;
