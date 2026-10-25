# 7 Pin Description

<!-- pdf:20 -->

SSD2828 Pin Function Description

Key: I = Input O =Output I/O = Bi-directional (input/output) P = Power pin GND = System VSS

**Table 7-1: Power Supply Pins**

| Name | Type | Connect to | Function | Description | When not in use |
|---|---|---|---|---|---|
| GND | P | GND | Ground of Power Supply | Ground for IC | - |
| MVDD | P | Power | Power for<br>Analog/Digital<br>Circuits and PLL Circuit | Power supply for the internal analog/digital circuit and PLL circuit. (1.2V +/-10%) | - |
| VDDIO | P | Power | Power for IO and Digital Interface Circuits | Power supply for IO and digital interface circuit. (1.8~3.3V +/-10%) | - |

**Table 7-1: MIPI Pins**

| Name | Type | Connect to | Function | Description | When not in use |
|---|---|---|---|---|---|
| CLKP0 | O | MIPI Rx | MIPI<br>Signals | Positive differential clock signal for DSI_0 | Open |
| CLKN0 | O | MIPI Rx | MIPI<br>Signals | Negative differential clock signal for DSI_0 | Open |
| DATAP0 | I/O | MIPI Rx | MIPI<br>Signals | Positive differential data signal 0 for DSI_0 | Open |
| DATAN0 | I/O | MIPI Rx | MIPI<br>Signals | Negative differential data signal 0 for DSI_0 | Open |
| DATAP1 | O | MIPI Rx | MIPI<br>Signals | Positive differential data signal 1 for DSI_0 | Open |
| DATAN1 | O | MIPI Rx | MIPI<br>Signals | Negative differential data signal 1 for DSI_0 | Open |
| DATAP2 | O | MIPI Rx | MIPI<br>Signals | Positive differential data signal 2 for DSI_0 | Open |
| DATAN2 | O | MIPI Rx | MIPI<br>Signals | Negative differential data signal 2 for DSI_0 | Open |
| DATAP3 | O | MIPI Rx | MIPI<br>Signals | Positive differential data signal 3 for DSI_0 | Open |
| DATAN3 | O | MIPI Rx | MIPI<br>Signals | Negative differential data signal 3 for DSI_0 | Open |

<!-- pdf:21 -->

**Table 7-2: Interface Logic Pins**

| Name | Type | Connect to | Function | Description | When not in use |
|---|---|---|---|---|---|
| DATA[23:0] | I/O | AP | RGB<br>Interface | RGB data for RGB interface | Open |
| VSYNC | I | AP | RGB<br>Interface | VSYNC for RGB interface | VDDIO or GND |
| PCLK | I | AP | RGB<br>Interface | PCLK for RGB interface | VDDIO or GND |
| DEN | I | AP | RGB<br>Interface | DEN for RGB interface | VDDIO or GND |
| HSYNC | I | AP | RGB<br>Interface | HSYNC for RGB interface | VDDIO or GND |
| SDC | I | AP | SPI<br>Interface | Data or command for SPI interface (for 8 bit 4 wire) | VDDIO or GND |
| CSX0 | I | AP | SPI<br>Interface | Chip select of DSI_0 for SPI interface | VDDIO |
| SCK | I | AP | SPI<br>Interface | Serial clock for SPI interface (for 8 bit 3 wire, 8 bit 4 wire, 24 bit 3 wire) | VDDIO or GND |
| SDI | I | AP | SPI<br>Interface | Serial data input for SPI interface (for 8 bit 3 wire, 8 bit 4 wire, 24 bit 3 wire) | VDDIO or GND |
| SDO | O | - | SPI<br>Interface | Serial data output for SPI interface (for 8 bit 3 wire, 8 bit 4 wire, 24 bit 3 wire) | Open |

<!-- pdf:22 -->

**Table 7-3: Miscellaneous Pins**

| Name | Type | Connect to | Function | Description | When not in use |
|---|---|---|---|---|---|
| SHUT | I | VDDIO or GND | Control<br>Signal | Shutdown signal of RGB interface (to put the driver into sleep mode). - 1: The panel is shut down (Sending 22h packet when SHUT changes from “0” → “1” in video mode) - 0: The panel is operating (Sending 32h packet at the beginning of video mode automatically) | VDDIO |
| PS[1:0] | I | VDDIO or GND | Control<br>Signal | Interface selection signal PS[1:0] is for SPI interface - 00: 3 wire 24 bit SPI interface - 01: 3 wire 8 bit SPI interface - 10: 4 wire 8 bit SPI interface - 11: SSL internal test mode | GND |
| TX_CLK_XIN | I | External<br>CLK | Control<br>Signal | Input system clock. 8 ~ 30MHz ----------------------------------------------------------------------- Input crystal range for the crystal oscillator input. 8Mhz to 30Mhz | - |
| TX_CLK_XIO | I/O | - | Control<br>Signal | Input system clock. Open. ----------------------------------------------------------------------- Input crystal range for the crystal oscillator input. 8Mhz to 30Mhz | Open |
| SYS_CLK_OUT | O | - | Control<br>Signal | Output system clock for MIPI slave | Open |
| RESET | I | VDDIO or GND | Control<br>Signal | Active low reset signal to the chip | VDDIO |
