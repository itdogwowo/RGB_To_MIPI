const p = await eda.dmt_Project.getCurrentProjectInfo();
return {
  uuid: p.uuid,
  name: p.friendlyName || p.name,
  boards: (p.data || []).map(b => ({
    board: b.name,
    schematic: b.schematic && b.schematic.name,
    pages: b.schematic && (b.schematic.page || []).map(x => x.uuid),
    pcb: b.pcb && b.pcb.uuid
  }))
};
