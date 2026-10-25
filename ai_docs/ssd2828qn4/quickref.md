# SSD2828QN4 — quick reference

Everything below is extracted from the datasheet (Rev 1.3, Mar 2013). Section numbers in
`backticks` point to files in `sections/`; register bits live in `registers.csv`.

## 1. Identity

- MIPI **master bridge**: input = parallel RGB (DPI-2.0, 16/18/24-bit) **or** serial SPI
  (DBI-2.0, up to 16-bit); output = MIPI **DSI** transmitter, 1–4 data lanes + 1 clock lane,
  up to **1 Gbps per lane (4 Gbps total)**. `01_general_description`, `05_functional_description`
- Standards: DSI v1.01.00, DCS v1.02.00, D-PHY v1.00.00.
- Video mode: up to **1920 px/line @ 60 Hz**, up to **2560 px/line @ 30 Hz**.
- Supply: **MVDD 1.2 V ±10 %** (core + PLL), **VDDIO 1.8–3.3 V ±10 %** (IO).
  External clock `TX_CLK_XIN` 8–30 MHz (crystal 8–30 MHz on XIN/XIO).
- Package: **68-pin QFN-EP**, tray. Order code `SSD2828QN4`.
- Command mode also supported (16/18/24 bpp, Raw or Pixel mode) plus CABC.

## 2. Mode / interface selection

| Signal | Where | Encoding |
|---|---|---|
| `PS[1:0]` | pins 17, 18 (input, strap) | 00 = 3-wire 24-bit SPI · 01 = 3-wire 8-bit SPI · 10 = 4-wire 8-bit SPI · 11 = SSL internal test mode |
| `LS[1:0]` | `LCFR` 0xDE bits 1:0 | 00 = 1 lane · 01 = 2 lanes · 10 = 3 lanes · 11 = 4 lanes |

RGB and SPI can be used together (RGB for pixels, SPI for register/command traffic).
`PS` pins must be tied to GND when unused; `CSX0` must stay high when SPI is unused.

## 3. Clock and PLL  (`09_configuration` §9.3.5, register `PLCR` 0xBA)

```
f_PRE = f_IN / MS
f_OUT = f_PRE * NS
5 MHz  <= f_IN  <= 100 MHz
5 MHz  <= f_REF <= 100 MHz
62.5 MHz <= f_OUT <= 1000 MHz
```

- Reference select `CFGR.CSS` (0xB7 bit 5): **0 = tx_clk, 1 = pclk** (default 0 → tx_clk must be present after power-up before registers can be written).
- `PLCR` 0xBA: `FR` bits 15:14 (frequency range), `MS` bits 12:8 (divider), `NS` bits 7:0 (multiplier). Reset 0x8120.
- PLL on/off `PCR.PEN` (0xB9 bit 0). **FR/MS/NS may only be changed while the PLL is off.**
- Multiplication factor per bpp and lane count: Tables 9-10 (pclk reference), 9-11 (tx_clk reference), 9-12 (burst mode) — these three tables are embedded as images in `09_configuration` because the PDF has no column rules in them.
- PLL lock status: `PLLR` 0xD5 (`PLS`); interrupt enable `ICR` 0xC5 bit 7.

## 4. Power-up sequence (`15_power_up_sequence`, example in `17_...`)

1. VDDIO / VDDIOC / MAVDDV
2. MVDD / VCC12A / MAVDD
3. release `RESB`
4. apply `TX_CLK`
5. configure through SPI, PLL on → e.g. `0xB9 = 0x0001`
6. leave ULPS → e.g. `0xB7 = 0x0300`
7. `SLP = 0`, `VEN & HS = 1` → video mode, e.g. `0xB7 = 0x0309`
8. drive RGB signals

## 5. Signal-path registers (RGB → DSI)

| Register | Addr | Key fields |
|---|---|---|
| `VICR1` | 0xB1 | `VSA` 15:8, `HSA` 7:0 |
| `VICR2` | 0xB2 | `VBP` 15:8, `HBP` 7:0 |
| `VICR3` | 0xB3 | `VFP` 15:8, `HFP` 7:0 |
| `VICR4` | 0xB4 | `HACT` 15:0 (max 0x0A00) |
| `VICR5` | 0xB5 | `VACT` 15:0 |
| `VICR6` | 0xB6 | `VS_P`, `HS_P`, `PCLK_P`, `CBM`, `NVB`, `NVD`, `BLLP`, `VCS`, `VM`, `VPF` |
| `VICR7` | 0xDD | `VBN` 7:4, `VFN` 3:0 (non-video-data windows) |
| `CFGR` | 0xB7 | `TXD` 11, `LPE` 10, `EOT` 9, `ECD` 8, `REN` 7, `DCS` 6, `CSS` 5, `HCLK` 4, `VEN` 3, `SLP` 2, `CKE` 1, `HS` 0 |
| `PSCR1-3` | 0xBC–0xBE | packet size |
| `PDR` | 0xBF | generic packet drop |
| `OCR` | 0xC0 | `RST` 8 (soft reset), `COP` 0 (cancel operation) |
| `LCFR` | 0xDE | `LS` 1:0 lane count |

## 6. Status / handshake

`ISR` 0xC6, `ESR` 0xC7, `ARSR` 0xC3 (ACK response), `TSR` 0xD3 (TE), `PLLR` 0xD5 (lock),
`RDCR` 0xC2 (returned byte count), `MRSR` 0xC1 (max return size), `LRR` 0xD4 (SPI read command, default 0x00FA).

## 7. Timing (`14_ac_characteristics`, machine-readable in `timing.csv`)

`T` = period of the PLL output clock (before lock: period of the PLL reference clock).
`W` = number of pixels in one horizontal line. SPI timing is `T`-relative (`8T`, `16T`, …).

## 8. Register map (66 registers, 0xB0–0xFF)

| Offset | Mnemonic | Register | Reset |
|---|---|---|---|
| 0xB0 | DIR | Device Identification Register | 0x2828 |
| 0xB1 | VICR1 | RGB Interface Control Register 1 | 0x020A |
| 0xB2 | VICR2 | RGB Interface Control Register 2 | 0x0214 |
| 0xB3 | VICR3 | RGB Interface Control Register 3 | 0x0428 |
| 0xB4 | VICR4 | RGB Interface Control Register 4 | 0x0780 |
| 0xB5 | VICR5 | RGB Interface Control Register 5 | 0x0438 |
| 0xB6 | VICR6 | RGB Interface Control Register 6 | 0x0024 |
| 0xB7 | CFGR | Configuration Register | 0x0301 |
| 0xB8 | VCR | VC Control Register | 0x0045 |
| 0xB9 | PCR | PLL Control Register | 0x0000 |
| 0xBA | PLCR | PLL Configuration Register | 0x8120 |
| 0xBB | CCR | Clock Control Register | 0x0003 |
| 0xBC | PSCR1 | Packet Size Control Register 1 | 0x0000 |
| 0xBD | PSCR2 | Packet Size Control Register 2 | 0x0000 |
| 0xBE | PSCR2 | Packet Size Control Register 3 | 0x0100 |
| 0xBF | GPDR | Packet Drop Register | 0x0000 |
| 0xC0 | OCR | Operation Control Register | 0x0000 |
| 0xC1 | MRSR | Maximum Return Size Register | 0x0001 |
| 0xC2 | RDCR | Return Data Count Register | 0x0000 |
| 0xC3 | ARSR | ACK Response Register | 0x0000 |
| 0xC4 | LCR | Line Control Register | 0x0000 |
| 0xC5 | ICR | Interrupt Control Register | 0x0080 |
| 0xC6 | ISR | Interrupt Status Register | 0xCF06 |
| 0xC7 | ESR | Error Status Register | 0x0000 |
| 0xC9 | DAR1 | Delay Adjustment Register 1 | 0x1402 |
| 0xCA | DAR2 | Delay Adjustment Register 2 | 0x2803 |
| 0xCB | DAR3 | Delay Adjustment Register 3 | 0x0416 |
| 0xCC | DAR4 | Delay Adjustment Register 4 | 0x0A0A |
| 0xCD | DAR5 | Delay Adjustment Register 5 | 0x1000 |
| 0xCE | DAR6 | Delay Adjustment Register 6 | 0x0405 |
| 0xCF | HTTR1 | HS TX Timer Register 1 | 0x0000 |
| 0xD0 | HTTR2 | HS TX Timer Register 2 | 0x0010 |
| 0xD1 | LRTR1 | LP RX Timer Register 1 | 0x0000 |
| 0xD2 | LRTR2 | LP RX Timer Register 2 | 0x0010 |
| 0xD3 | TSR | TE Status Register | 0x0000 |
| 0xD4 | LRR | SPI Read Register | 0x00FA |
| 0xD5 | PLLR | PLL Lock Register | 0x1450 |
| 0xD6 | TR | Test Register | 0x0005 |
| 0xD7 | TECR | TE Count Register | 0x0001 |
| 0xD8 | ACR1 | Analog Control Register 1 | 0x2020 |
| 0xD9 | ACR2 | Analog Control Register 2 | 0x64A0 |
| 0xDA | ACR3 | Analog Control Register 3 | 0x99A4 |
| 0xDB | ACR4 | Analog Control Register 4 | 0x8098 |
| 0xDC | IOCR | Interrupt Output Control Register | 0x0000 |
| 0xDD | VICR7 | RGB Interface Control Register 7 | 0x0000 |
| 0xDE | LCFR | Lane Configuration Register | 0x0000 |
| 0xDF | DAR7 | Delay Adjustment Register 7 | 0x0010 |
| 0xE0 | PUCR1 | Pull Control Register 1 | 0x5556 |
| 0xE1 | PUCR2 | Pull Control Register 2 | 0x6656 |
| 0xE2 | PUCR3 | Pull Control Register 3 | 0x0159 |
| 0xE9 | CBCR1 | CABC Brightness Control Register 1 | 0x0000 |
| 0xEA | CBCR2 | CABC Brightness Control Register 2 | 0x6900 |
| 0xEB | CBSR | CABC Brightness Status Register | 0x0000 |
| 0xEC | ECR | Encoder Control Register | 0x7800 |
| 0xED | VSDR | Video Sync Delay Register | 0x0002 |
| 0xEE | TMR | Trimming Register | 0x0000 |
| 0xEF | GPIO1 | GPIO Register 1 | 0x0000 |
| 0xF0 | GPIO2 | GPIO Register 2 | 0x0000 |
| 0xF1 | DLYA01 | DLYA01 Register | 0x2020 |
| 0xF2 | DLYA23 | DLYA23 Register | 0x2020 |
| 0xF3 | DLYB01 | DLYB01 Register | 0x2020 |
| 0xF4 | DLYB23 | DLYB23 Register | 0x2020 |
| 0xF5 | DLYC01 | DLYC01 Register | 0x2020 |
| 0xF6 | DLYC23 | DLYC23 Register | 0x2020 |
| 0xF7 | ACR5 | Analog Control Register 5 | 0x0000 |
| 0xFF | RR | Read Register | 0x0000 |

## 9. Where to look

| Question | File |
|---|---|
| What does this chip do, block-level | `sections/01_*`, `sections/05_*` |
| Pin number → net | `pinout.csv`, `sections/06_*` |
| Pin function / type / unused handling | `pins.csv`, `sections/07_*` |
| Register, bit fields, enum values | `registers.csv`, `sections/08_*` |
| RGB timing params (HSA/HBP/HFP/HACT/VACT) | `sections/08_*` 8.1.2–8.1.5 |
| Lane setup, video/command/burst modes | `sections/09_*` |
| MIPI packet structure, data types, byte order | `sections/09_*` §9.2, `sections/18_*` |
| SPI read/write protocol (3-wire, 4-wire) | `sections/10_*` |
| Electrical limits, DC/AC characteristics | `sections/11_*`–`sections/14_*`, `timing.csv` |
| Power up/down, sleep in/out | `sections/15_*`–`sections/17_*` |
| Package, marking, tray | `sections/19_*` |
| Which page in the original PDF | `INDEX.md`, `<!-- pdf:N -->` markers |

## 10. Caveats

- Subscripts are written with a leading underscore: `t_CLKH`, `f_OUT`, `T_MAX`.
- The PDF uses "(cid:…)" glyphs for arrows and bullets; these are normalised to `→` / list markers.
- Original typos kept: "Register6"/"Register7" (missing space), Table 7-1 used three times,
  chapter 19 numbered 18 in the table of contents.
- Tables 9-5, 9-6, 9-10, 9-11, 9-12 have no vertical rules in the PDF and are provided as images.
- Stacked fractions were flattened to linear text (see §9.3.5: `f_PRE = f_IN / MS`).
