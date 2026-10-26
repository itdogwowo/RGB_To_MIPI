#!/bin/bash
# Rebuild the shield schematic v3 using the REAL client symbols
# (SSD2828QN4 + DFR display/touch connectors) taken from the user's edited file.
set -e
SKILL="/Users/tungkinlee/Documents/Git/Sourcetree/RGB_To_MIPI/.git/scratch/easyeda-eprj3-skill"
ROOT="/Users/tungkinlee/Documents/Git/Sourcetree/RGB_To_MIPI"
DIR="$ROOT/RGB_To_MIPI-pcb/ESP32P4_SSD2828_TouchBar"
SRC="$ROOT/.git/scratch/backup/user-edit.esch2"
cd "$SKILL"

rm -rf "$DIR/sch" "$DIR/pcb" "$DIR"/*.eprj3 "$DIR/.tmp"
node scripts/init.js --dir "$DIR" --name ESP32P4_SSD2828_TouchBar \
     --schematic SCH --sheet P1 --pcb PCB1 --board-w 2700 --board-h 1500 >/dev/null

python3 - "$DIR" <<'PY'
import subprocess, sys
DIR = sys.argv[1]
def gen(name, designator, pins):
    r = subprocess.run(["node","scripts/generate-symbol.js","from-pins","--dir",DIR,
                        "--name",name,"--designator",designator,"--pins",pins],
                       capture_output=True, text=True)
    if r.returncode: print(r.stdout, r.stderr); raise SystemExit(1)
J6_NAMES = ["IO15","IO14","IO13","IO12","IO11","IO10","IO9","IO6","IO5","IO4","IO3","IO2",
            "IO54","IO53","IO52","IO50","IO49","IO48","IO47","IO46","IO45","IO44","IO43",
            "IO40","IO41","IO42","GND"]
J7_NAMES = ["IO16","IO17","IO18","IO19","IO20","IO21","IO22","IO23","GND","IO39","IO38","IO37",
            "IO36","GND","IO34","IO33","IO32","IO26","IO27","IO28","IO29","IO30","IO31",
            "LDO_VO4","3V3","GND","5V"]
gen("HDR27_J6","J",";".join(f"{i+1}:{nm}:20:{130-10*i}:180" for i,nm in enumerate(J6_NAMES)))
gen("HDR27_J7","J",";".join(f"{i+1}:{nm}:20:{130-10*i}:180" for i,nm in enumerate(J7_NAMES)))
gen("LDO5","U","1:IN:-20:20:0;3:EN:-20:0:0;2:GND:-20:-20:0;4:BYP:20:-20:180;5:OUT:20:20:180")
gen("XTAL","Y","1:XI:-20:0:0;2:XO:20:0:180")
LS_LEFT = {20:90, 11:70, 19:50, 18:40, 17:30, 16:20, 15:10, 14:0, 13:-10, 12:-20, 10:-50}
LS_RIGHT = {1:90, 2:50, 3:40, 4:30, 5:20, 6:10, 7:0, 8:-10, 9:-20}
names = {20:"VCCB",11:"OE",19:"B1",18:"B2",17:"B3",16:"B4",15:"B5",14:"B6",13:"B7",12:"B8",
         10:"GND",1:"VCCA",2:"A1",3:"A2",4:"A3",5:"A4",6:"A5",7:"A6",8:"A7",9:"A8"}
spec = [f"{n}:{names[n]}:-20:{y}:0" for n,y in LS_LEFT.items()] + \
       [f"{n}:{names[n]}:20:{y}:180" for n,y in LS_RIGHT.items()]
gen("LS8","U",";".join(spec))
print("symbols ready")
PY

python3 "$ROOT/tools/mk_lib_entries.py" "$SRC" "$DIR"
cd "$ROOT" && python3 tools/gen2.py "$DIR"
cd "$SKILL" && node scripts/validate.js --dir "$DIR" | tail -2
