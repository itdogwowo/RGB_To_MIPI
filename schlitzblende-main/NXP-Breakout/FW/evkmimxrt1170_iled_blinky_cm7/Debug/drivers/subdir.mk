################################################################################
# Automatically-generated file. Do not edit!
################################################################################

# Add inputs and outputs from these tool invocations to the build variables 
C_SRCS += \
../drivers/fsl_anatop_ai.c \
../drivers/fsl_cache.c \
../drivers/fsl_clock.c \
../drivers/fsl_common.c \
../drivers/fsl_common_arm.c \
../drivers/fsl_dcdc.c \
../drivers/fsl_elcdif.c \
../drivers/fsl_gpio.c \
../drivers/fsl_lcdifv2.c \
../drivers/fsl_lpuart.c \
../drivers/fsl_mipi_dsi.c \
../drivers/fsl_pmu.c \
../drivers/fsl_soc_src.c 

C_DEPS += \
./drivers/fsl_anatop_ai.d \
./drivers/fsl_cache.d \
./drivers/fsl_clock.d \
./drivers/fsl_common.d \
./drivers/fsl_common_arm.d \
./drivers/fsl_dcdc.d \
./drivers/fsl_elcdif.d \
./drivers/fsl_gpio.d \
./drivers/fsl_lcdifv2.d \
./drivers/fsl_lpuart.d \
./drivers/fsl_mipi_dsi.d \
./drivers/fsl_pmu.d \
./drivers/fsl_soc_src.d 

OBJS += \
./drivers/fsl_anatop_ai.o \
./drivers/fsl_cache.o \
./drivers/fsl_clock.o \
./drivers/fsl_common.o \
./drivers/fsl_common_arm.o \
./drivers/fsl_dcdc.o \
./drivers/fsl_elcdif.o \
./drivers/fsl_gpio.o \
./drivers/fsl_lcdifv2.o \
./drivers/fsl_lpuart.o \
./drivers/fsl_mipi_dsi.o \
./drivers/fsl_pmu.o \
./drivers/fsl_soc_src.o 


# Each subdirectory must supply rules for building sources it contributes
drivers/%.o: ../drivers/%.c drivers/subdir.mk
	@echo 'Building file: $<'
	@echo 'Invoking: MCU C Compiler'
	arm-none-eabi-gcc -std=gnu99 -D__REDLIB__ -DUSE_SDRAM=1 -DXIP_BOOT_HEADER_DCD_ENABLE=1 -DCPU_MIMXRT1176DVMAA -DCPU_MIMXRT1176DVMAA_cm7 -DSDK_DEBUGCONSOLE=1 -DXIP_EXTERNAL_FLASH=1 -DXIP_BOOT_HEADER_ENABLE=1 -DMCUXPRESSO_SDK -DSERIAL_PORT_TYPE_UART=1 -DCR_INTEGER_PRINTF -DPRINTF_FLOAT_ENABLE=0 -D__MCUXPRESSO -D__USE_CMSIS -DDEBUG -I"/Users/andylithia/github/schlitzblende/NXP-Breakout/FW/evkmimxrt1170_iled_blinky_cm7/source" -I"/Users/andylithia/github/schlitzblende/NXP-Breakout/FW/evkmimxrt1170_iled_blinky_cm7/drivers" -I"/Users/andylithia/github/schlitzblende/NXP-Breakout/FW/evkmimxrt1170_iled_blinky_cm7/device" -I"/Users/andylithia/github/schlitzblende/NXP-Breakout/FW/evkmimxrt1170_iled_blinky_cm7/utilities" -I"/Users/andylithia/github/schlitzblende/NXP-Breakout/FW/evkmimxrt1170_iled_blinky_cm7/component/uart" -I"/Users/andylithia/github/schlitzblende/NXP-Breakout/FW/evkmimxrt1170_iled_blinky_cm7/component/serial_manager" -I"/Users/andylithia/github/schlitzblende/NXP-Breakout/FW/evkmimxrt1170_iled_blinky_cm7/component/lists" -I"/Users/andylithia/github/schlitzblende/NXP-Breakout/FW/evkmimxrt1170_iled_blinky_cm7/startup" -I"/Users/andylithia/github/schlitzblende/NXP-Breakout/FW/evkmimxrt1170_iled_blinky_cm7/xip" -I"/Users/andylithia/github/schlitzblende/NXP-Breakout/FW/evkmimxrt1170_iled_blinky_cm7/CMSIS" -I"/Users/andylithia/github/schlitzblende/NXP-Breakout/FW/evkmimxrt1170_iled_blinky_cm7/board" -O0 -fno-common -g3 -c -ffunction-sections -fdata-sections -ffreestanding -fno-builtin -fmerge-constants -fmacro-prefix-map="$(<D)/"= -mcpu=cortex-m7 -mfpu=fpv5-d16 -mfloat-abi=hard -mthumb -D__REDLIB__ -fstack-usage -specs=redlib.specs -MMD -MP -MF"$(@:%.o=%.d)" -MT"$(@:%.o=%.o)" -MT"$(@:%.o=%.d)" -o "$@" "$<"
	@echo 'Finished building: $<'
	@echo ' '


clean: clean-drivers

clean-drivers:
	-$(RM) ./drivers/fsl_anatop_ai.d ./drivers/fsl_anatop_ai.o ./drivers/fsl_cache.d ./drivers/fsl_cache.o ./drivers/fsl_clock.d ./drivers/fsl_clock.o ./drivers/fsl_common.d ./drivers/fsl_common.o ./drivers/fsl_common_arm.d ./drivers/fsl_common_arm.o ./drivers/fsl_dcdc.d ./drivers/fsl_dcdc.o ./drivers/fsl_elcdif.d ./drivers/fsl_elcdif.o ./drivers/fsl_gpio.d ./drivers/fsl_gpio.o ./drivers/fsl_lcdifv2.d ./drivers/fsl_lcdifv2.o ./drivers/fsl_lpuart.d ./drivers/fsl_lpuart.o ./drivers/fsl_mipi_dsi.d ./drivers/fsl_mipi_dsi.o ./drivers/fsl_pmu.d ./drivers/fsl_pmu.o ./drivers/fsl_soc_src.d ./drivers/fsl_soc_src.o

.PHONY: clean-drivers

