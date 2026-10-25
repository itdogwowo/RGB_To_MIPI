################################################################################
# Automatically-generated file. Do not edit!
################################################################################

# Add inputs and outputs from these tool invocations to the build variables 
C_SRCS += \
../xip/evkmimxrt1170_flexspi_nor_config.c \
../xip/fsl_flexspi_nor_boot.c 

C_DEPS += \
./xip/evkmimxrt1170_flexspi_nor_config.d \
./xip/fsl_flexspi_nor_boot.d 

OBJS += \
./xip/evkmimxrt1170_flexspi_nor_config.o \
./xip/fsl_flexspi_nor_boot.o 


# Each subdirectory must supply rules for building sources it contributes
xip/%.o: ../xip/%.c xip/subdir.mk
	@echo 'Building file: $<'
	@echo 'Invoking: MCU C Compiler'
	arm-none-eabi-gcc -std=gnu99 -D__REDLIB__ -DUSE_SDRAM=1 -DXIP_BOOT_HEADER_DCD_ENABLE=1 -DCPU_MIMXRT1176DVMAA -DCPU_MIMXRT1176DVMAA_cm7 -DSDK_DEBUGCONSOLE=1 -DXIP_EXTERNAL_FLASH=1 -DXIP_BOOT_HEADER_ENABLE=1 -DMCUXPRESSO_SDK -DSERIAL_PORT_TYPE_UART=1 -DCR_INTEGER_PRINTF -DPRINTF_FLOAT_ENABLE=0 -D__MCUXPRESSO -D__USE_CMSIS -DDEBUG -I"/Users/andylithia/github/schlitzblende/NXP-Breakout/FW/evkmimxrt1170_iled_blinky_cm7/source" -I"/Users/andylithia/github/schlitzblende/NXP-Breakout/FW/evkmimxrt1170_iled_blinky_cm7/drivers" -I"/Users/andylithia/github/schlitzblende/NXP-Breakout/FW/evkmimxrt1170_iled_blinky_cm7/device" -I"/Users/andylithia/github/schlitzblende/NXP-Breakout/FW/evkmimxrt1170_iled_blinky_cm7/utilities" -I"/Users/andylithia/github/schlitzblende/NXP-Breakout/FW/evkmimxrt1170_iled_blinky_cm7/component/uart" -I"/Users/andylithia/github/schlitzblende/NXP-Breakout/FW/evkmimxrt1170_iled_blinky_cm7/component/serial_manager" -I"/Users/andylithia/github/schlitzblende/NXP-Breakout/FW/evkmimxrt1170_iled_blinky_cm7/component/lists" -I"/Users/andylithia/github/schlitzblende/NXP-Breakout/FW/evkmimxrt1170_iled_blinky_cm7/startup" -I"/Users/andylithia/github/schlitzblende/NXP-Breakout/FW/evkmimxrt1170_iled_blinky_cm7/xip" -I"/Users/andylithia/github/schlitzblende/NXP-Breakout/FW/evkmimxrt1170_iled_blinky_cm7/CMSIS" -I"/Users/andylithia/github/schlitzblende/NXP-Breakout/FW/evkmimxrt1170_iled_blinky_cm7/board" -O0 -fno-common -g3 -c -ffunction-sections -fdata-sections -ffreestanding -fno-builtin -fmerge-constants -fmacro-prefix-map="$(<D)/"= -mcpu=cortex-m7 -mfpu=fpv5-d16 -mfloat-abi=hard -mthumb -D__REDLIB__ -fstack-usage -specs=redlib.specs -MMD -MP -MF"$(@:%.o=%.d)" -MT"$(@:%.o=%.o)" -MT"$(@:%.o=%.d)" -o "$@" "$<"
	@echo 'Finished building: $<'
	@echo ' '


clean: clean-xip

clean-xip:
	-$(RM) ./xip/evkmimxrt1170_flexspi_nor_config.d ./xip/evkmimxrt1170_flexspi_nor_config.o ./xip/fsl_flexspi_nor_boot.d ./xip/fsl_flexspi_nor_boot.o

.PHONY: clean-xip

