# 17 Example for system sleep in and out

<!-- pdf:161 -->

Note: Following example is only for reference, application must be related to the particular information of AP and driver IC, e.g.Wait time and TX_CLK (_XIN, _XIO) csontrol of AP

|  |  |
|---|---|
|  | Driver IC Sleep In |
|  | Driver IC Sleep In |
|  | Driver IC Sleep In |
|  | Driver IC Sleep In |
|  | Driver IC Sleep In |
|  | Driver IC Sleep In |
|  | Driver IC Sleep In |
|  | Driver IC Sleep In |
|  | Driver IC Sleep In |
|  |  |
|  |  |
|  |  |
|  |  |
|  |  |
|  |  |
|  |  |
|  |  |
| SSD2828 Sleep In |  |

> **Note (derived):** this table is an example sequence with concrete register writes (0xB9 0x0001 = PLL on, 0xB7 0x0300 = leave ULPS, 0xB7 0x0309 = video mode on). The document itself says it is only a reference; adapt wait times to your AP/panel.
