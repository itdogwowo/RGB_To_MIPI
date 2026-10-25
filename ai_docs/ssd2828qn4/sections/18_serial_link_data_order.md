# 18 Serial Link Data Order

<!-- pdf:162 -->

There are many possible ways of doing parallel to serial conversion. SSD2828 provides flexibility by programming two register bits END and CO. During video mode, they must be programmed to 0 and 1 respectively.

Below is the order to receive the display data over the serial link, when the END bit is 1 and CO bit is 0.

For 16 bit per pixel data, below is the byte order. Each byte of data is sent in the order of LSB first and MSB last.

| MSB Byte 1 LSB | MSB Byte2 LSB | MSB Byte3 LSB | MSB Byte4 LSB |
|---|---|---|---|
| R4 | G2 | R4 | G2 |

Time

For 18 bit per pixel data, below is the byte order. Each byte of data is sent in the order of LSB first and MSB last.

| MSB Byte 1 LSB | MSB Byte2 LSB | MSB Byte3 LSB | MSB Byte4 LSB |
|---|---|---|---|
| R5 | G3 | B1 | G5 |

Time

For 24 bit per pixel data, below is the byte order. Each byte of data is sent in the order of LSB first and MSB last.

| MSB Byte 1 LSB | MSB Byte2 LSB | MSB Byte3 LSB | MSB Byte4 LSB |
|---|---|---|---|
| R7 | G7 | B7 | R7 |

Time

Below is the order to send the display data over the serial link, when the END bit is 0 and CO bit is 0.

For 16 bit per pixel data, below is the byte order. Each byte of data is sent in the order of LSB first and MSB last.

| MSB Byte 1 LSB | MSB Byte2 LSB | MSB Byte3 LSB | MSB Byte4 LSB |
|---|---|---|---|
| G2 | R4 | G2 | R4 |

Time

For 18 bit per pixel data, below is the byte order. Each byte of data is sent in the order of LSB first and MSB last.

| MSB Byte 1 LSB | MSB Byte2 LSB | MSB Byte3 LSB | MSB Byte4 LSB |
|---|---|---|---|
| G1 | R3 | B5 | R1 |

Time

<!-- pdf:163 -->

For 24 bit per pixel data, below is the byte order. Each byte of data is sent in the order of LSB first and MSB last.

| MSB Byte 1 LSB | MSB Byte2 LSB | MSB Byte3 LSB | MSB Byte4 LSB |
|---|---|---|---|
| B7 | G7 | R7 | R7 |

Time

Below is the order to send the display data over the serial link, when the END bit is 1 and CO bit is 1.

For 16 bit per pixel data, below is the byte order. Each byte of data is sent in the order of LSB first and MSB last.

| MSB Byte 1 LSB | MSB Byte2 LSB | MSB Byte3 LSB | MSB Byte4 LSB |
|---|---|---|---|
| B4 | G2 | B4 | G2 |

Time

For 18 bit per pixel data, below is the byte order. Each byte of data is sent in the order of LSB first and MSB last.

| MSB Byte 1 LSB | MSB Byte2 LSB | MSB Byte3 LSB | MSB Byte4 LSB |
|---|---|---|---|
| B5 | G3 | R1 | G5 |

Time

For 24 bit per pixel data, below is the byte order. Each byte of data is sent in the order of LSB first and MSB last.

| MSB Byte 1 LSB | MSB Byte2 LSB | MSB Byte3 LSB | MSB Byte4 LSB |
|---|---|---|---|
| B7 | G7 | R7 | R7 |

Time

Below is the order to send the display data over the serial link, when the END bit is 0 and CO bit is 1.

For 16 bit per pixel data, below is the byte order. Each byte of data is sent in the order of LSB first and MSB last.

| MSB Byte 1 LSB | MSB Byte2 LSB | MSB Byte3 LSB | MSB Byte4 LSB |
|---|---|---|---|
| G2 | B4 | G2 | B4 |

Time

For 18 bit per pixel data, below is the byte order. Each byte of data is sent in the order of LSB first and MSB last.

| MSB Byte 1 LSB | MSB Byte2 LSB | MSB Byte3 LSB | MSB Byte4 LSB |
|---|---|---|---|

<!-- pdf:164 -->

| G1 | G0 | R5 | R4 | R3 | R2 | R1 | R0 | B3 | B2 | B1 | B0 | G5 | G4 | G3 | G2 | R5 | R4 | R3 | R2 | R1 | R0 | B5 | B4 | B1 | B0 | G5 | G4 | G3 | G2 | G1 | G0 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|

Time

For 24 bit per pixel data, below is the byte order. Each byte of data is sent in the order of LSB first and MSB last.

| MSB Byte 1 LSB | MSB Byte2 LSB | MSB Byte3 LSB | MSB Byte4 LSB |
|---|---|---|---|
| R7 | G7 | B7 | R7 |

Time
