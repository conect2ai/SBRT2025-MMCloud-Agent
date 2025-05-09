from smbus2 import SMBus
import time

MPU_ADDR = 0x68
PWR_MGMT_1 = 0x6B
ACCEL_XOUT_H = 0x3B
GYRO_XOUT_H = 0x43

with SMBus(1) as bus:
    bus.write_byte_data(MPU_ADDR, PWR_MGMT_1, 0)  # acorda o sensor

    def read_word_2c(reg):
        high = bus.read_byte_data(MPU_ADDR, reg)
        low = bus.read_byte_data(MPU_ADDR, reg + 1)
        val = (high << 8) + low
        return val - 65536 if val & 0x8000 else val

    while True:
        # Acelerômetro bruto
        ax_raw = read_word_2c(ACCEL_XOUT_H)
        ay_raw = read_word_2c(ACCEL_XOUT_H + 2)
        az_raw = read_word_2c(ACCEL_XOUT_H + 4)

        # Giroscópio bruto
        gx_raw = read_word_2c(GYRO_XOUT_H)
        gy_raw = read_word_2c(GYRO_XOUT_H + 2)
        gz_raw = read_word_2c(GYRO_XOUT_H + 4)

        # Conversão: acelerômetro para g (±2g → 16384 LSB/g)
        ax = ax_raw / 16384.0
        ay = ay_raw / 16384.0
        az = az_raw / 16384.0

        # Conversão: giroscópio para °/s (±250°/s → 131 LSB/°/s)
        gx = gx_raw / 131.0
        gy = gy_raw / 131.0
        gz = gz_raw / 131.0

        print(f"Acc X={ax:.2f}g Y={ay:.2f}g Z={az:.2f}g | Gyro X={gx:.2f}°/s Y={gy:.2f}°/s Z={gz:.2f}°/s")
        time.sleep(0.5)
