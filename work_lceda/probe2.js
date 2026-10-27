const out = { steps: [] };
try {
  const nl = await eda.sch_Netlist.getNetlist();
  out.netlistType = Array.isArray(nl) ? 'array' : typeof nl;
  out.netlistLen = Array.isArray(nl) ? nl.length : (nl && Object.keys(nl).length);
  out.netlistSample = Array.isArray(nl) ? nl.slice(0, 3) : nl;
} catch (e) { out.netlistError = String(e); }
try {
  const drc = await eda.sch_Drc.check(true, false, true);
  out.drcCount = drc.length;
  out.drcSample = drc.slice(0, 5).map(v => ({ rule: v.rule, type: v.type, prims: (v.primitives||[]).map(p => p.name) }));
} catch (e) { out.drcError = String(e); }
try {
  const wires = await eda.sch_PrimitiveWire.getAll();
  out.wireCount = wires.length;
  out.wireSample = wires.slice(0, 3).map(w => ({ id: w.getState_PrimitiveId(), net: w.getState_Net && w.getState_Net() }));
} catch (e) { out.wireError = String(e); }
return out;
