import serial
import time

def parse_GPGGA(sentence):
    try:
        parts = sentence.split(",")
        if parts[2] == '' or parts[4] == '':
            return None, None

        # Latitude
        lat_deg = float(parts[2][:2])
        lat_min = float(parts[2][2:])
        lat_dir = parts[3]
        latitude = lat_deg + (lat_min / 60)
        if lat_dir == 'S':
            latitude = -latitude

        # Longitude
        lon_deg = float(parts[4][:3])
        lon_min = float(parts[4][3:])
        lon_dir = parts[5]
        longitude = lon_deg + (lon_min / 60)
        if lon_dir == 'W':
            longitude = -longitude

        return latitude, longitude
    except:
        return None, None

def get_gps_coordinates(port="/dev/ttyAMA0", baudrate=9600, timeout=1):
    with serial.Serial(port, baudrate, timeout=0.1) as ser:
        start_time = time.time()
        while time.time() - start_time < timeout:
            line = ser.readline().decode('ascii', errors='replace').strip()
            if line.startswith('$GPGGA'):
                lat, lon = parse_GPGGA(line)
                if lat is not None and lon is not None:
                    return lat, lon
        return None, None  # se não encontrar dentro do tempo