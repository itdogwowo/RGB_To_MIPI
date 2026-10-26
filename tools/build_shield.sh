#!/bin/bash
# Rebuild the ESP32P4 -> SSD2828 -> TouchBar shield project from scratch.
set -e
SKILL="/Users/tungkinlee/Documents/Git/Sourcetree/RGB_To_MIPI/.git/scratch/easyeda-eprj3-skill"
DIR="/Users/tungkinlee/Documents/Git/Sourcetree/RGB_To_MIPI/RGB_To_MIPI-pcb/ESP32P4_SSD2828_TouchBar"
cd "$SKILL"

rm -rf "$DIR"
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

gen("HDR27","J",";".join(f"{n}:P{n}:20:{130-10*(n-1)}:180" for n in range(1,28)))
gen("CONN26","J",";".join(f"{n}:P{n}:-20:{125-10*(n-1)}:0" for n in range(1,27)))
gen("LDO5","U","1:IN:-20:20:0;3:EN:-20:0:0;2:GND:-20:-20:0;4:BYP:20:-20:180;5:OUT:20:20:180")
gen("XTAL","Y","1:XI:-20:0:0;2:XO:20:0:180")
# TXS0108E 20-pin level translator: left = 3V3 side (B), right = 1V8 side (A)
LS_LEFT = {20:90, 11:70, 19:50, 18:40, 17:30, 16:20, 15:10, 14:0, 13:-10, 12:-20, 10:-50}
LS_RIGHT = {1:90, 2:50, 3:40, 4:30, 5:20, 6:10, 7:0, 8:-10, 9:-20}
names = {20:"VCCB",11:"OE",19:"B1",18:"B2",17:"B3",16:"B4",15:"B5",14:"B6",13:"B7",12:"B8",
         10:"GND",1:"VCCA",2:"A1",3:"A2",4:"A3",5:"A4",6:"A5",7:"A6",8:"A7",9:"A8"}
spec=[]
for n,y in LS_LEFT.items():  spec.append(f"{n}:{names[n]}:-20:{y}:0")
for n,y in LS_RIGHT.items(): spec.append(f"{n}:{names[n]}:20:{y}:180")
gen("LS8","U",";".join(spec))

left = [("35","DATA0")]+[(str(36+i),f"DATA{i+1}") for i in range(23)] + \
       [("34","VSYNC"),("29","HSYNC"),("28","DEN"),("30","PCLK")]
right = [("1","DATAP0"),("2","DATAN0"),("4","DATAP1"),("5","DATAN1"),("10","DATAP2"),
         ("11","DATAN2"),("13","DATAP3"),("14","DATAN3"),("7","CLKP"),("8","CLKN"),
         ("25","SCK"),("24","SDI"),("23","SDO"),("59","CSX0"),("26","SDC"),
         ("22","RESET"),("27","SHUT"),("17","PS0"),("18","PS1"),
         ("63","TX_CLK_XIN"),("62","TX_CLK_XIO"),("61","SYS_CLK_OUT"),
         ("15","MVDD"),("31","MVDD"),("60","MVDD"),("66","MVDD"),
         ("16","VDDIO"),("33","VDDIO"),("64","VDDIO"),("68","VDDIO"),
         ("3","GND"),("6","GND"),("9","GND"),("12","GND"),("32","GND"),("65","GND"),("67","GND"),
         ("19","NC"),("20","NC"),("21","NC")]
spec=[]; y=135
for num,name in left: spec.append(f"{num}:{name}:-20:{y}:0"); y-=10
y=195
for num,name in right: spec.append(f"{num}:{name}:20:{y}:180"); y-=10
gen("SSD2828QN4","U",";".join(spec))
print("symbols ready")
PY

cd "/Users/tungkinlee/Documents/Git/Sourcetree/RGB_To_MIPI"
python3 tools/gen_shield_sch.py
cd "$SKILL"
node scripts/validate.js --dir "$DIR" | tail -3
