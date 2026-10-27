// experiment: draw one wire whose ENDPOINTS sit exactly on two pins, then read the netlist
const a = { x: 850, y: -510 };            // U1 pin 35 (DATA0)
const b = { x: 980.0000000000001, y: -689.9999999999999 }; // J1 pin 1
const mid = { x: a.x, y: b.y };

const w = await eda.sch_PrimitiveWire.create([[a.x, a.y, mid.x, mid.y], [mid.x, mid.y, b.x, b.y]]);
const wid = w.getState_PrimitiveId();
await eda.sch_Document.save();
await new Promise(r => setTimeout(r, 9000));
const names = await eda.sch_Net.getAllNetsName();
const nets = await eda.sch_Net.getAllNets();
const hit = (names || []).filter(n => /D0|NET|U1|J1/i.test(String(n)));
return { wireId: wid, netCount: (names||[]).length, namesSample: (names||[]).slice(0,10), hit, raw: (nets||[]).slice(0,2) };
