def estimate_maf(rpm, temp, pressure, cc):
    """Estimate the mass aif flow"""

    # volumetric efficiency constant
    VE = 0.75
    # ideal gas constant
    R = 8.3144621
    # molar mass of dry air
    M_air = 28.9647 #g/mol
    
    # intake pressure from KPa to Pa
    pressure = pressure/1000
    # from C to K
    temp = temp + 273.15 
    
    # multiply by 1000 to convert from kg/s to g/s
    return (pressure * cc * M_air * VE * rpm)/(R * temp * 120)


def calc_emission_rate(maf, fuel_type):
    """Calculate the emission rate in g/s"""
    
    # constants for gasoline or alcohol fuel
    co2_per_liter = 2310 if fuel_type=='gasoline' else 1510       #g/L
    air_fuel_ratio = 14.7 if fuel_type=='gasoline' else 9.0
    density = 737 if fuel_type=='gasoline' else 789 #g/L
        
    rate = (maf*co2_per_liter)/(air_fuel_ratio*density) #g/s
    return rate


def convert_emission_rate(emission, speed):
    """Transform emission rate from g/s to g/km"""
    # km/h to km/s
    speed= speed* 0.000277778
    
    if speed == 0:
        speed = 0.1
    return emission/speed #g/km