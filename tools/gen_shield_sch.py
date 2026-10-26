#!/usr/bin/env python3
"""Generate the ESP32P4 -> SSD2828 -> Touch Bar shield schematic.

Drives the official easyeda-eprj3-skill CLI scripts. All coordinates are in the
sheet's native units (A4 ~ 1170 x 825, y negative downwards).

Sheet plan (P1):
  left   : J6 (P4 IO header, 27P) + J7 (P4 IO header, 27P)
  centre : U1 SSD2828QN4
  right  : J1 DFR display connector (26P)
  bottom : U2 1.8V LDO, U3 1.2V LDO, crystal Y1
"""
import os, subprocess, sys, json

SKILL = "/Users/tungkinlee/Documents/Git/Sourcetree/RGB_To_MIPI/.git/scratch/easyeda-eprj3-skill"
DIR = "/Users/tungkinlee/Documents/Git/Sourcetree/RGB_To_MIPI/RGB_To_MIPI-pcb/ESP32P4_SSD2828_TouchBar"
SCH, SHEET = "SCH", "P1"

def run(*args, quiet=True):
    cmd = ["node", *args]
    r = subprocess.run(cmd, cwd=SKILL, capture_output=True, text=True)
    if r.returncode != 0:
        print("FAIL:", " ".join(args))
        print(r.stdout[-1500:])
        print(r.stderr[-1500:])
        sys.exit(1)
    if not quiet:
        print(r.stdout.strip())
    return r.stdout

def sym(name):
    return run("scripts/add-symbol.js", "--dir", DIR, "--sch", SCH, "--sheet", SHEET, *name)

def wire(segs, net=None):
    a = ["scripts/add-wire.js", "--dir", DIR, "--sch", SCH, "--sheet", SHEET,
         "--segs", ";".join(f"{x1},{y1},{x2},{y2}" for x1, y1, x2, y2 in segs)]
    if net:
        a += ["--net", net]
    run(*a)

def label(net, x, y):
    # wires already carry their NET attr via add-wire --net; nothing to do.
    return

def text(s, x, y, size=8):
    run("scripts/add-text.js", "--dir", DIR, "--sch", SCH, "--sheet", SHEET,
        "--value", s, "--x", str(x), "--y", str(y), "--size", str(size))

def rect(x1, y1, x2, y2):
    run("scripts/add-shape.js", "rect", "--dir", DIR, "--sch", SCH, "--sheet", SHEET,
        "--x1", str(x1), "--y1", str(y1), "--x2", str(x2), "--y2", str(y2))

# ---------------------------------------------------------------- geometry
# pin tables (relative y) matching the generated symbols
SSD_LEFT = ["DATA%d" % i for i in range(24)] + ["VSYNC", "HSYNC", "DEN", "PCLK"]
SSD_RIGHT = (["DATAP0", "DATAN0", "DATAP1", "DATAN1", "DATAP2", "DATAN2", "DATAP3", "DATAN3",
              "CLKP", "CLKN", "SCK", "SDI", "SDO", "CSX0", "SDC",
              "RESET", "SHUT", "PS0", "PS1", "TX_CLK_XIN", "TX_CLK_XIO", "SYS_CLK_OUT",
              "MVDD1", "MVDD2", "MVDD3", "MVDD4",
              "VDDIO1", "VDDIO2", "VDDIO3", "VDDIO4",
              "GND1", "GND2", "GND3", "GND4", "GND5", "GND6", "GND7",
              "NC1", "NC2", "NC3"])

def ssd_pin(name):
    """absolute tip coordinate of an SSD2828 pin"""
    X, Y = U1
    if name in SSD_LEFT:
        i = SSD_LEFT.index(name)
        return (X - 30, Y + 135 - 10 * i)
    i = SSD_RIGHT.index(name)
    return (X + 30, Y + 195 - 10 * i)

def hdr_pin(origin, n):
    """J6/J7 style: 27 pins, pin n tip to the right"""
    X, Y = origin
    return (X + 30, Y + 130 - 10 * (n - 1))

def conn_pin(origin, n):
    """J1 style: 26 pins, pin n tip to the left"""
    X, Y = origin
    return (X - 30, Y + 125 - 10 * (n - 1))

def ldo_pin(origin, n):
    """U2/U3 5-pin LDO: 1 IN(-x,+20) 2 GND(-x,-20) 3 EN(-x,0) 4 BYP(+x,-20) 5 OUT(+x,+20)"""
    X, Y = origin
    table = {1: (-30, 20), 2: (-30, -20), 3: (-30, 0), 4: (30, -20), 5: (30, 20)}
    dx, dy = table[n]
    return (X + dx, Y + dy)

LS_LEFT = {20: 90, 11: 70, 19: 50, 18: 40, 17: 30, 16: 20, 15: 10, 14: 0, 13: -10, 12: -20, 10: -50}
LS_RIGHT = {1: 90, 2: 50, 3: 40, 4: 30, 5: 20, 6: 10, 7: 0, 8: -10, 9: -20}

def ls_pin(origin, n):
    X, Y = origin
    if n in LS_LEFT:
        return (X - 30, Y + LS_LEFT[n])
    return (X + 30, Y + LS_RIGHT[n])


def xtal_pin(origin, n):
    X, Y = origin
    return (X - 30, Y) if n == 1 else (X + 30, Y)

# ---------------------------------------------------------------- placement
U1 = (560, -300)          # SSD2828
J6 = (180, -295)          # P4 header J6
J7 = (180, -560)          # P4 header J7
J1 = (900, -250)          # DFR display
J2 = (900, -560)          # touch flex (level shift TBD)
U2 = (330, -765)          # 1.8V LDO
U3 = (470, -765)          # 1.2V LDO
Y1 = (200, -780)          # 24 MHz crystal
U4 = (600, -575)          # level shift: panel control (3V3 <-> 1V8)
U5 = (600, -735)          # level shift: touch SPI / I2C (3V3 <-> 1V8)

# ---------------------------------------------------------------- build
def main():
    # blocks
    rect(110, -140, 520, -710); text("P4 IO HEADERS  J6/J7  (RGB888 + SPI + control)", 115, -130, 9)
    rect(525, -80, 790, -520);  text("SSD2828QN4  RGB -> 1-lane MIPI DSI", 530, -70, 9)
    rect(800, -120, 1120, -400); text("TOUCH BAR DFR DISPLAY  (J1 DF40-26)", 805, -110, 9)
    rect(800, -420, 1120, -730); text("TOUCH FLEX  (J2)", 805, -410, 9)
    rect(545, -450, 790, -800); text("LEVEL SHIFT  3.3V <-> 1.8V  (U4 panel / U5 touch)", 550, -442, 9)
    rect(120, -720, 500, -815); text("POWER  5V/3V3 -> +1V8 / +1V2  + 24 MHz XTAL", 125, -710, 9)

    # --- components
    sym(["--symbol", "SSD2828QN4", "--x", str(U1[0]), "--y", str(U1[1]), "--refdes", "U1",
         "--name", "SSD2828QN4"])
    sym(["--symbol", "HDR27", "--x", str(J6[0]), "--y", str(J6[1]), "--refdes", "J6",
         "--name", "P4_IO_J6"])
    sym(["--symbol", "HDR27", "--x", str(J7[0]), "--y", str(J7[1]), "--refdes", "J7",
         "--name", "P4_IO_J7"])
    sym(["--symbol", "CONN26", "--x", str(J1[0]), "--y", str(J1[1]), "--refdes", "J1",
         "--name", "DFR_DF40_26P"])
    sym(["--symbol", "LDO5", "--x", str(U2[0]), "--y", str(U2[1]), "--refdes", "U2",
         "--name", "LDO_1V8"])
    sym(["--symbol", "LDO5", "--x", str(U3[0]), "--y", str(U3[1]), "--refdes", "U3",
         "--name", "LDO_1V2"])
    sym(["--symbol", "XTAL", "--x", str(Y1[0]), "--y", str(Y1[1]), "--refdes", "Y1",
         "--name", "24MHz"])

    # --- RGB bus: J6 pins 1..21 -> DATA0..DATA20  (straight wires)
    for i in range(21):
        p = hdr_pin(J6, i + 1)
        q = ssd_pin("DATA%d" % i)
        wire([(p[0], p[1], q[0], q[1])], net="RGB_D%d" % i)

    # --- SSD2828 left: remaining pins -> stubs + labels
    for name in ["DATA21", "DATA22", "DATA23", "VSYNC", "HSYNC", "DEN", "PCLK"]:
        x, y = ssd_pin(name)
        net = {"DEN": "RGB_DE", "PCLK": "RGB_PCLK", "VSYNC": "RGB_VSYNC",
               "DATA21": "RGB_D21", "DATA22": "RGB_D22", "DATA23": "RGB_D23"}.get(name, "RGB_" + name)
        if name == "HSYNC":
            wire([(x, y, x - 40, y)], net="GND")
            label("GND", x - 40, y)
        else:
            wire([(x, y, x - 40, y)], net=net)
            label(net, x - 40, y)

    # --- SSD2828 right: stubs + labels
    right_nets = {
        "DATAP0": "DSI_D0P", "DATAN0": "DSI_D0N", "CLKP": "DSI_CLKP", "CLKN": "DSI_CLKN",
        "SCK": "SPI_SCK", "SDI": "SPI_MOSI", "SDO": "SPI_MISO", "CSX0": "SPI_CS", "SDC": "SPI_DC",
        "RESET": "SSD_RST", "SHUT": "GND", "PS0": "GND", "PS1": "3V3",
        "TX_CLK_XIN": "XTAL_IN", "TX_CLK_XIO": "XTAL_OUT", "SYS_CLK_OUT": "SYS_CLK",
        "MVDD1": "1V2", "MVDD2": "1V2", "MVDD3": "1V2", "MVDD4": "1V2",
        "VDDIO1": "3V3", "VDDIO2": "3V3", "VDDIO3": "3V3", "VDDIO4": "3V3",
        "GND1": "GND", "GND2": "GND", "GND3": "GND", "GND4": "GND", "GND5": "GND",
        "GND6": "GND", "GND7": "GND",
        "NC1": "NC", "NC2": "NC", "NC3": "NC",
    }
    # unused DSI lanes: tie off with NC
    for name in ["DATAP1", "DATAN1", "DATAP2", "DATAN2", "DATAP3", "DATAN3"]:
        right_nets[name] = "NC"
    for name, net in right_nets.items():
        x, y = ssd_pin(name)
        if net == "NC":
            continue
        wire([(x, y, x + 40, y)], net=net)
        label(net, x + 40, y)

    # --- J7 : P4 control + remaining data, all labels
    j7_nets = {1: "RGB_D21", 2: "RGB_D22", 3: "RGB_D23", 4: "RGB_PCLK", 5: "RGB_DE",
               6: "RGB_VSYNC", 7: "SPI_SCK", 8: "SPI_MOSI", 11: "SPI_MISO", 12: "SPI_CS",
               13: "SPI_DC", 15: "SSD_RST", 16: "TE", 17: "T_CS", 18: "T_INT", 19: "T_RST",
               20: "I2C_SDA", 21: "I2C_SCL", 22: "D_RST", 23: "D_PWM", 25: "3V3", 27: "5V",
               9: "GND", 14: "GND", 26: "GND"}
    for n in range(1, 28):
        net = j7_nets.get(n)
        x, y = hdr_pin(J7, n)
        if not net:
            continue                      # leave unused pins dangling (spare IO / LDO_VO4)
        wire([(x, y, x + 40, y)], net=net)
        label(net, x + 40, y)

    # --- J6 : first 21 used (wired), rest are spare
    for n in (27,):
        x, y = hdr_pin(J6, n)
        wire([(x, y, x + 40, y)], net="GND")
        label("GND", x + 40, y)
    # pins 22..26 are the TF-card IOs -> left unused on purpose

    # --- J1 DFR 26-pin
    j1_nets = {1: "GND", 2: "GND", 3: "DSI_CLKP", 4: "D_SYNC_18", 5: "DSI_CLKN",
               6: "D_TE_18", 7: "GND", 8: "GND", 9: "DSI_D0P", 10: "D_INT_18", 11: "DSI_D0N",
               12: "D_RST_18", 13: "GND", 14: "GND", 15: "1V8", 16: "GND", 17: "1V8",
               18: "3V3", 19: "GND", 20: "3V3", 21: "D_I2C_SCL", 22: "3V3", 23: "D_I2C_SDA",
               24: "GND", 25: "GND", 26: "GND"}
    for n in range(1, 27):
        net = j1_nets.get(n)
        x, y = conn_pin(J1, n)
        if not net:
            continue
        wire([(x, y, x - 40, y)], net=net)
        label(net, x - 40, y)

    # --- J2 touch flex (26 pin): power + stubs, level shifting comes in v2
    sym(["--symbol", "CONN26", "--x", str(J2[0]), "--y", str(J2[1]), "--refdes", "J2",
         "--name", "TOUCH_FLEX_26P"])
    j2_nets = {1: "TS_DETECT", 2: "TS_LID", 3: "TS_VSYNC", 4: "TS_GPIO2",
               7: "TS_SPI_MISO", 8: "TS_SPI_CS", 9: "TS_SPI_CLK", 10: "TS_SPI_MOSI",
               13: "TS_INT", 14: "TS_I2C_SCL", 15: "TS_CLK_RST", 16: "TS_I2C_SDA",
               18: "TS_RST", 19: "TS_ROM_WC", 20: "1V8", 21: "1V8", 22: "5V",
               5: "GND", 6: "GND", 11: "GND", 12: "GND", 17: "GND", 23: "GND", 24: "GND",
               25: "GND", 26: "GND"}
    for n in range(1, 27):
        net = j2_nets.get(n)
        x, y = conn_pin(J2, n)
        if not net:
            continue
        wire([(x, y, x - 40, y)], net=net)

    # --- level shifters U4 (panel control) + U5 (touch)
    for ref, origin in (("U4", U4), ("U5", U5)):
        sym(["--symbol", "LS8", "--x", str(origin[0]), "--y", str(origin[1]), "--refdes", ref,
             "--name", "TXS0108E"])
        # power pins
        for n, net in ((20, "3V3"), (11, "1V8"), (10, "GND"), (1, "1V8")):
            x, y = ls_pin(origin, n)
            dx = -40 if n in (20, 11, 10) else 40
            wire([(x, y, x + dx, y)], net=net)

    u4_map = {19: "D_RST", 18: "TE"}          # B1/B2 (3V3 side)
    u4_a = {2: "D_RST_18", 3: "D_TE_18"}      # A1/A2 (1V8 side)
    for n, net in list(u4_map.items()) + list(u4_a.items()):
        x, y = ls_pin(U4, n)
        dx = -40 if n in u4_map else 40
        wire([(x, y, x + dx, y)], net=net)

    u5_b = {19: "SPI_SCK", 18: "SPI_MOSI", 17: "SPI_MISO", 16: "T_CS",
            15: "T_INT", 14: "T_RST", 13: "I2C_SDA", 12: "I2C_SCL"}
    u5_a = {2: "TS_SPI_CLK", 3: "TS_SPI_MOSI", 4: "TS_SPI_MISO", 5: "TS_SPI_CS",
            6: "TS_INT", 7: "TS_RST", 8: "TS_I2C_SDA", 9: "TS_I2C_SCL"}
    for n, net in list(u5_b.items()) + list(u5_a.items()):
        x, y = ls_pin(U5, n)
        dx = -40 if n in u5_b else 40
        wire([(x, y, x + dx, y)], net=net)

    # --- LDOs
    for ref, origin, out_net in (("U2", U2, "1V8"), ("U3", U3, "1V2")):
        for n, net in ((1, "3V3"), (2, "GND"), (3, "3V3"), (5, out_net)):
            x, y = ldo_pin(origin, n)
            dx = -40 if n in (1, 2, 3) else 40
            wire([(x, y, x + dx, y)], net=net)
            label(net, x + dx, y)

    # --- decoupling caps (vertical, top -> rail, bottom -> GND)
    caps = [("C1", 660, -770, "3V3"), ("C2", 700, -770, "1V2"),
            ("C3", 740, -770, "1V8"), ("C4", 780, -770, "3V3")]
    for ref, cx, cy, rail in caps:
        sym(["--symbol", "CAP", "--footprint", "C0603", "--x", str(cx), "--y", str(cy),
             "--rotation", "90", "--refdes", ref])
        wire([(cx, cy + 30, cx, cy + 45)], net=rail)
        wire([(cx, cy - 30, cx, cy - 45)], net="GND")

    # --- crystal load caps (22 pF) + crystal
    for ref, cx, net in (("C5", 140, "XTAL_IN"), ("C6", 260, "XTAL_OUT")):
        sym(["--symbol", "CAP", "--footprint", "C0603", "--x", str(cx), "--y", "-730",
             "--rotation", "90", "--refdes", ref])
        wire([(cx, -700, cx, -685)], net=net)
        wire([(cx, -760, cx, -775)], net="GND")
    x1, y1 = xtal_pin(Y1, 1)
    x2, y2 = xtal_pin(Y1, 2)
    wire([(x1, y1, x1 - 40, y1)], net="XTAL_IN")
    label("XTAL_IN", x1 - 40, y1)
    wire([(x2, y2, x2 + 40, y2)], net="XTAL_OUT")
    label("XTAL_OUT", x2 + 40, y2)

    print("built")

if __name__ == "__main__":
    main()
