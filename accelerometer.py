from smbus2 import SMBus

def read_word_2c(bus, addr, reg):
    high = bus.read_byte_data(addr, reg)
    low = bus.read_byte_data(addr, reg + 1)
    val = (high << 8) + low
    if val >= 0x8000:
        val = -((65535 - val) + 1)
    return val

def read_acelerometer(dados):
    MPU_ADDR = 0x68
    PWR_MGMT_1 = 0x6B
    ACCEL_XOUT_H = 0x3B
    GYRO_XOUT_H  = 0x43

    with SMBus(1) as bus:
        # Acorda o sensor, se necessário
        bus.write_byte_data(MPU_ADDR, PWR_MGMT_1, 0)

        # Lê valores brutos do acelerômetro
        acc_x_raw = read_word_2c(bus, MPU_ADDR, ACCEL_XOUT_H)
        acc_y_raw = read_word_2c(bus, MPU_ADDR, ACCEL_XOUT_H + 2)
        acc_z_raw = read_word_2c(bus, MPU_ADDR, ACCEL_XOUT_H + 4)

        # Lê valores brutos do giroscópio
        gyro_x_raw = read_word_2c(bus, MPU_ADDR, GYRO_XOUT_H)
        gyro_y_raw = read_word_2c(bus, MPU_ADDR, GYRO_XOUT_H + 2)
        gyro_z_raw = read_word_2c(bus, MPU_ADDR, GYRO_XOUT_H + 4)

    # Converte acelerômetro para g (±2g → 16384 LSB/g)
    acc_x = acc_x_raw / 16384.0
    acc_y = acc_y_raw / 16384.0
    acc_z = acc_z_raw / 16384.0

    # Converte giroscópio para °/s (±250°/s → 131 LSB/°/s)
    gyro_x = gyro_x_raw / 131.0
    gyro_y = gyro_y_raw / 131.0
    gyro_z = gyro_z_raw / 131.0

    # Atualiza o dicionário
    dados["accel_x"] = acc_x
    dados["accel_y"] = acc_y
    dados["accel_z"] = acc_z
    dados["gyro_x"] = gyro_x
    dados["gyro_y"] = gyro_y
    dados["gyro_z"] = gyro_z

    return dados
