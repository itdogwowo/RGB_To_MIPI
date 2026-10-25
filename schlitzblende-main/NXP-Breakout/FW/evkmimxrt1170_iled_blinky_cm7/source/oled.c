//
// Project Fobu
// Copyright 2020 Wenting Zhang
//
// Permission is hereby granted, free of charge, to any person obtaining a copy
// of this software and associated documentation files (the "Software"), to deal
// in the Software without restriction, including without limitation the rights
// to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
// copies of the Software, and to permit persons to whom the Software is
// furnished to do so, subject to the following conditions:
//
// The above copyright notice and this permission notice shall be included in
// all copies or substantial portions of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
// OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
// SOFTWARE.
//
// File : nt35310.c
// Brief: Driver for NT35310 LCD controller
//
#include "fsl_iomuxc.h"
#include "fsl_gpio.h"
#include "fsl_mipi_dsi.h"
#include "vout.h"
#include "utils.h"
#include "fsl_debug_console.h"
// #include "assets_iphone100_meme.h"
#include "assets_sushi1.h"
#include "assets_sushi2.h"
#include "assets_sushi3.h"
#include <stdlib.h>

#define BOARD_LCD_RST_GPIO	GPIO9
#define BOARD_LCD_RST_PIN  	1


#define LCD_CMD(params...) \
	{ \
		const uint8_t d[] = {params}; \
		vout_dsi_write(d, sizeof(d) / sizeof(uint8_t)); \
	}

void oled_init(void) {
	srand(123);
    const gpio_pin_config_t pinConfig = {kGPIO_DigitalOutput, 0, kGPIO_NoIntmode};

    IOMUXC_SetPinMux(
        IOMUXC_GPIO_AD_02_GPIO9_IO01,           /* GPIO_AD_02 is configured as GPIO9_IO01 */
        0U);

    GPIO_PinInit(BOARD_LCD_RST_GPIO, BOARD_LCD_RST_PIN, &pinConfig);

    GPIO_PinWrite(BOARD_LCD_RST_GPIO, BOARD_LCD_RST_PIN, 0);
    util_sleep_ms(100);
    GPIO_PinWrite(BOARD_LCD_RST_GPIO, BOARD_LCD_RST_PIN, 1);

    // Sleep out
    LCD_CMD(0x11);
    util_sleep_ms(200);

    // Initialization sequence
    LCD_CMD(0x2A, 0x00, 0x00, 0x00, 0x3B);
    LCD_CMD(0x2B, 0x00, 0x00, 0x08, 0x79);
    LCD_CMD(0x2C, 0xFF);

    LCD_CMD(0x51, 0xFF);

    LCD_CMD(0xB0, 0xAC);
    util_sleep_ms(10);
    LCD_CMD(0xD4, 0x07, 0xC0, 0x80, 0x00, 0x80);
    LCD_CMD(0xB0, 0xCA);
    LCD_CMD(0x35);

    LCD_CMD(0x29); // Display On

    LCD_CMD(0x53, 0x20); // Apply brightness

    // Read ID
    uint8_t rdid[1] = {0x04};
    uint8_t rdid_result[4] = {0x00, 0x00, 0x00, 0x00};
    uint32_t rdid_rxsize = 3;
    vout_dsi_read(rdid, 1, rdid_result, &rdid_rxsize);
    PRINTF("ID bytes: %d\r\n", rdid_rxsize);
    PRINTF("ID: %02x %02x %02x\r\n", rdid_result[0], rdid_result[1], rdid_result[2]);

    static uint8_t buffer_r[181];
    static uint8_t buffer_g[181];
    static uint8_t buffer_b[181];

    for (int i = 0; i < 180/3; i++) {
    	buffer_r[i*3+0] = 0xff;
    	buffer_r[i*3+1] = 0x00;
    	buffer_r[i*3+2] = 0x00;
    	buffer_g[i*3+0] = 0x00;
    	buffer_g[i*3+1] = 0xff;
    	buffer_g[i*3+2] = 0x00;
    	buffer_b[i*3+0] = 0x00;
    	buffer_b[i*3+1] = 0x00;
    	buffer_b[i*3+2] = 0xff;
    }

    util_sleep_ms(10);

    // Re-enable clock
    vout_dsi_enable_hs_clk();

    util_sleep_ms(10);

    uint8_t txdata[5];
    static uint8_t buffer[181];
    static uint8_t buffer_bk[181];
    for (int i = 0; i < 181; i++)
    	buffer_bk[i] = 0x00;
    buffer_bk[0] = 0x3c;

    // uint8_t *buffer = buffer_g;
//    int counter = 0;
//    while(1){
//
//		for(int i=0;i<2170;i++) {
//			memcpy(&buffer[1], &sushi1.pixel_data[(i)*60*3+1], 60*3);
//			buffer[0] = 0x3C;
//			vout_dsi_hs_write(buffer, 181);
//
//		}
//    }
	#define SUSHI_HEIGHT 120
    #define SUSHI_N 18
	#define SUSHI_TYPE_N 3

    static int sushi_list[SUSHI_N+3];
    int sushi_index = 0; // 0 - 17
    int sushi_position = 0; // 0 - 119
    int r = rand() % SUSHI_TYPE_N;
    static const uint8_t* sushi_assets_p[SUSHI_TYPE_N] = {sushi1.pixel_data, sushi2.pixel_data, sushi3.pixel_data};

	// Populate the list with random pictures
	for (int i=0;i<SUSHI_N+3;i++){
		r = rand() % SUSHI_TYPE_N;
		sushi_list[i] = r;
	}
    while(1){
		int sushi_draw_index    = 0;
		int sushi_draw_position = sushi_position;
		for(int i=-120;i<2160;i++){
			if((i>=0)&&(i<2160)){
				memcpy(&buffer[1], &sushi_assets_p[sushi_list[sushi_draw_index]][(sushi_draw_position)*60*3+1], 60*3);
				buffer[0] = 0x3c;
				vout_dsi_hs_write(buffer, 181);
			}
			sushi_draw_position ++;
			if(sushi_draw_position>=120){
				sushi_draw_index++;
				sushi_draw_position = 0;
			}
			// Shouldn't happen
			if(sushi_draw_index>=SUSHI_N+2)
				sushi_draw_index = 0;
		}
		// Fill the blank
		for (int i=0;i<10;i++) vout_dsi_hs_write(buffer_bk, 181);
        // util_sleep_ms(1);
        sushi_position++;
        if(sushi_position>=120){
        	sushi_position = 0;
        	for(int j=0;j<SUSHI_N+2;j++){
        		sushi_list[j] = sushi_list[j+1];
        	}
        	sushi_list[SUSHI_N+2] = rand() % SUSHI_TYPE_N;
        }

    }
    /*
    while (1) {
        for (int i = 0; i < 2160; i++) {
            if ((i>=sushi_position)&&(i<=(sushi_position+120-1))){
                // Draw Sushi
            	memcpy(&buffer[1], &sushi1.pixel_data[(i-sushi_position)*60*3+1], 60*3);
                buffer[0] = 0x3c;
                vout_dsi_hs_write(buffer, 181);

            } else {
                vout_dsi_hs_write(buffer_bk, 181);
            }
        }
        for (int i=0;i<10;i++)
            vout_dsi_hs_write(buffer_bk, 181);

        sushi_position++;
        if(sushi_position>=(2170)) sushi_position=-120;
        util_sleep_ms(1);
    }
     */
}
