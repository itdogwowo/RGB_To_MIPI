const names = await eda.sch_Net.getAllNetsName();
const all = await eda.sch_Net.getAllNets();
const out = {
  netCount: (names || []).length,
  sampleNames: (names || []).slice(0, 15),
  rawType: Array.isArray(all) ? 'array' : typeof all,
  firstShape: null,
  first: null
};
if (Array.isArray(all) && all.length) {
  out.firstShape = Object.keys(all[0] || {});
  out.first = all[0];
} else if (all && typeof all === 'object') {
  const k = Object.keys(all)[0];
  out.firstShape = ['object with keys', k, Object.keys(all[k] || {})];
  out.first = { name: k, value: all[k] };
}
return out;
