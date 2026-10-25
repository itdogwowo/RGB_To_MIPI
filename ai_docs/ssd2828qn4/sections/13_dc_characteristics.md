# 13 DC Characteristics

<!-- pdf:151 -->

Conditions: Voltage referenced to GND MVDD = 1.2V VDDIO = 1.8V Frame frequency = 60Hz Number of lane = 4 Display pattern = 1080x1920, 8 colors vertical bar TA = 25°C

**Table 13-1: DC Characteristics**

| Symbol | arameter | est Condition | Min | Typ | Max | Unit |
|---|---|---|---|---|---|---|
| I_MVDD_HS | High Speed Mode Current | 1Gbps | - | 46.8 | 76.2 | mA |
| I_VDDIO_HS (1.8V) | High Speed Mode Current | 1Gbps | - | 0.36 | 0.75 | mA |
| I_VDDIO_HS (3.3V) | High Speed Mode Current | 1Gbps | - | 0.79 | 1.64 | mA |
| I_MVDD_LP | Low Power Mode Current | 10Mbps | - | 16.00 | 39.90 | mA |
| I_VDDIO_LP (1.8V) | Low Power Mode Current | 10Mbps | - | 0.17 | 0.43 | mA |
| I_VDDIO_LP (3.3V) | Low Power Mode Current | 10Mbps | - | 0.37 | 0.94 | mA |
| I_MVDD_ULPS | Ultra Low Power State Current | PLL off, no change in all input signals | - | 292.4 | 435 | μA |
| I_VDDIO_ULPS (1.8V) | Ultra Low Power State Current | PLL off, no change in all input signals | - | 75.6 | 150 | μA |
| I_VDDIO_ULPS (3.3V) | Ultra Low Power State Current | PLL off, no change in all input signals | - | 165.2 | 327.8 | μA |
| VOH (CMOS) | Output High<br>Voltage (CMOS) | IOH = -2 ~ -16 mA | V_DDIO x 0.8 | - | - | V |
| VOL (CMOS) | Output Low Voltage (CMOS) | IOL= 2 ~ 16 mA | - | - | V_DDIO x 0.15 | V |
| VIH (CMOS) | Input High Voltage (CMOS) |  | V_DDIO x 0.7 | - | - | V |
| VIL (CMOS) | Input Low Voltage (CMOS) |  | - | - | V_DDIO x 0.2 | V |
| IOZ | Tri-state Output<br>Leakage Current |  | - | +/-1 | - | μA |
| IIN | Input Leakage<br>Current | VIN = V_DDIO or GND | - | +/-1 | - | μA |
| CIN | Input Capacitance |  | - | 2.2 | - | pF |

<!-- pdf:152 -->

**Table 13-2: HS Transmitter DC Characteristics**

| Symbol | Parameter | Min | Typ | Max | Unit |
|---|---|---|---|---|---|
| V_CMTX | HS Transmit Static Common-mode Voltage | 150 | - | 250 | mV |
| \|V_OD\| | HS Transmit Differential Voltage | 140 | - | 270 | mV |
| \|ΔV_OD\| | HS Differential Mismatch | - | - | 10 | mV |
| V_OHHS | HS Output High Voltage | - | - | 360 | mV |

**Table 13-3: LP Transmitter DC Characteristics**

| Symbol | Parameter | Min | Typ | Max | Unit |
|---|---|---|---|---|---|
| V_OH | LP Thevenin Output High Level | 1.1 | 1.2 | 1.3 | V |
| V_OL | LP Thevenin Output Low Level | -50 | - | 50 | mV |
| Z_OLP | LP Transmitter Output Impedance | 110 | - | - | Ohm |

**Table 13-4: LP Receiver DC Characteristics**

| Symbol | Parameter | Min | Typ | Max | Unit |
|---|---|---|---|---|---|
| V_IH | LP Logic 1 Input Voltage | 880 | - | - | mV |
| V_IL | LP Logic 0 Input Voltage | - | - | 550 | mV |
