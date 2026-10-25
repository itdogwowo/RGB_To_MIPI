################################################################################
# Automatically-generated file. Do not edit!
################################################################################

# Add inputs and outputs from these tool invocations to the build variables 
C_SRCS += \
../startup/boot_multicore_slave.c \
../startup/startup_mimxrt1176_cm7.c 

C_DEPS += \
./startup/boot_multicore_slave.d \
./startup/startup_mimxrt1176_cm7.d 

OBJS += \
./startup/boot_multicore_slave.o \
./startup/startup_mimxrt1176_cm7.o 


# Each subdirectory must supply rules for building sources it contributes
startup/%.o: ../startup/%.c startup/subdir.mk
	@echo 'Building file: $<'
	@echo 'Invoking: MCU C Compiler'
	arm-none-eabi-gcc -std=gnu99 -D__REDLIB__ -DUSE_SDRAM=1 -DXIP_BOOT_HEADER_DCD_ENABLE=1 -DCPU_MIMXRT1176DVMAA -DCPU_MIMXRT1176DVMAA_cm7 -DSDK_DEBUGCONSOLE=1 -DXIP_EXTERNAL_FLASH=1 -DXIP_BOOT_HEADER_ENABLE=1 -DMCUXPRESSO_SDK -DSERIAL_PORT_TYPE_UART=1 -DCR_INTEGER_PRINTF -DPRINTF_FLOAT_ENABLE=0 -D__MCUXPRESSO -D__USE_CMSIS -DDEBUG -I"/Users/andylithia/github/schlitzblende/NXP-Breakout/FW/evkmimxrt1170_iled_blinky_cm7/source" -I"/Users/andylithia/github/schlitzblende/NXP-Breakout/FW/evkmimxrt1170_iled_blinky_cm7/drivers" -I"/Users/andylithia/github/schlitzblende/NXP-Breakout/FW/evkmimxrt1170_iled_blinky_cm7/device" -I"/Users/andylithia/github/schlitzblende/NXP-Breakout/FW/evkmimxrt1170_iled_blinky_cm7/utilities" -I"/Users/andylithia/github/schlitzblende/NXP-Breakout/FW/evkmimxrt1170_iled_blinky_cm7/component/uart" -I"/Users/andylithia/github/schlitzblende/NXP-Breakout/FW/evkmimxrt1170_iled_blinky_cm7/component/serial_manager" -I"/Users/andylithia/github/schlitzblende/NXP-Breakout/FW/evkmimxrt1170_iled_blinky_cm7/component/lists" -I"/Users/andylithia/github/schlitzblende/NXP-Breakout/FW/evkmimxrt1170_iled_blinky_cm7/startup" -I"/Users/andylithia/github/schlitzblende/NXP-Breakout/FW/evkmimxrt1170_iled_blinky_cm7/xip" -I"/Users/andylithia/github/schlitzblende/NXP-Breakout/FW/evkmimxrt1170_iled_blinky_cm7/CMSIS" -I"/Users/andylithia/github/schlitzblende/NXP-Breakout/FW/evkmimxrt1170_iled_blinky_cm7/board" -O0 -fno-common -g3 -c -ffunction-sections -fdata-sections -ffreestanding -fno-builtin -fmerge-constants -fmacro-prefix-map="$(<D)/"= -mcpu=cortex-m7 -mfpu=fpv5-d16 -mfloat-abi=hard -mthumb -D__REDLIB__ -fstack-usage -specs=redlib.specs -MMD -MP -MF"$(@:%.o=%.d)" -MT"$(@:%.o=%.o)" -MT"$(@:%.o=%.d)" -o "$@" "$<"
	@echo 'Finished building: $<'
	@echo ' '


clean: clean-startup

clean-startup:
	-$(RM) ./startup/boot_multicore_slave.d ./startup/boot_multicore_slave.o ./startup/startup_mimxrt1176_cm7.d ./startup/startup_mimxrt1176_cm7.o

.PHONY: clean-startup

