def volumetric_efficiency_1_0L(engine_rpm, is_rpm_gt_3584):
    return (((0.0025 * engine_rpm) + 85) * abs(is_rpm_gt_3584 - 1)) + (((-0.0025 * engine_rpm) + 110) * is_rpm_gt_3584)

def volumetric_efficiency_1_6L(engine_rpm, is_rpm_gt_3584):
    return (((0.004 * engine_rpm) + 85) * abs(is_rpm_gt_3584 - 1)) + (((-0.004 * engine_rpm) + 110) * is_rpm_gt_3584)

def volumetric_efficiency_2_0L(engine_rpm, is_rpm_gt_3584):
    return (((0.005 * engine_rpm) + 81) * abs(is_rpm_gt_3584 - 1)) + (((-0.005 * engine_rpm) + 117) * is_rpm_gt_3584)

def instant_fuel_consumption(vss_kmh, rpm=None, map_value=None, iat=None, vdm=None, maf=None, mm=28.97, r=8.314, combustivel='gasolina'):
    """
    Calcula o consumo instantâneo de combustível, retornando o valor em quilômetros por litro (km/L).
    
    Parâmetros:
    vss_kmh (float): Velocidade do veículo (VSS) em quilômetros por hora (km/h).
    rpm (float): Rotação do motor em rotações por minuto (RPM), opcional se o MAF for fornecido.
    map_value (float): Pressão absoluta no coletor de admissão em quilopascal (MAP), opcional se o MAF for fornecido.
    iat (float): Temperatura do ar na admissão em Kelvin (IAT), opcional se o MAF for fornecido.
    cc (float): Cilindrada do motor em centímetros cúbicos (cc).
    vdm (float): Volume de deslocamento do motor em litros (VDM), opcional se o MAF for fornecido.
    maf (float): Taxa de massa de ar (MAF), opcional.
    mm (float): Massa molecular média do ar (padrão 28.97 g/mol).
    r (float): Constante universal dos gases (padrão 8.314 J/(mol*K)).
    combustivel (str): Tipo de combustível (gasolina ou etanol).

    Retorno:
    float: Consumo instantâneo de combustível em quilômetros por litro (km/L).
    
    Exceções:
    - ValueError: Lançada se nem o MAF nem o MAP forem fornecidos.
    """
    
    # Se nem MAF nem MAP forem fornecidos, levanta uma exceção
    if maf is None and (rpm is None or map_value is None or iat is None or vdm is None):
        raise ValueError("É necessário fornecer o MAF ou os parâmetros RPM, MAP, IAT, EV, e VDM para calcular o consumo de combustível.")
    
    # Converte a velocidade de km/h para mi/h
    vss_mih = vss_kmh / 1.60934

    if vss_mih == 0:
        vss_mih = 0.1

    # Se o MAF não foi fornecido, calcula-o a partir do MAP
    if maf is None:

        if iat < 273.15:
            iat = iat + 273.15

        # Calcula o valor de IMAP
        imap = (rpm * map_value) / (iat / 2)

        # verifica se o valor de rpm é maior que 3584
        is_rpm_gt_3584 = 1 if rpm > 3584 else 0
        
        # Verifica e ajusta a eficiência volumétrica (EV) se necessário
        ev = 0
        if vdm == 1.0:
            ev = volumetric_efficiency_1_0L(rpm, is_rpm_gt_3584)
        elif vdm == 1.6:
            ev = volumetric_efficiency_1_6L(rpm, is_rpm_gt_3584)
        elif vdm == 2.0:
            ev = volumetric_efficiency_2_0L(rpm, is_rpm_gt_3584)

        # Converte o valor de EV para porcentagem
        if ev > 1.0:
            ev = ev / 100
        
        # Calcula o valor do MAF
        maf = (imap / 60) * ev * vdm * mm / r

    # Atribui a constante de acordo com o tipo de combustível
    if combustivel == 'gasolina':
        constante = 7.107
    elif combustivel == 'etanol':
        constante = 8.56984
    else:
        raise ValueError("Tipo de combustível inválido. Use 'gasolina' ou 'etanol'.")

    if maf == 0:
        maf = 0.1
 
    # Calcula o MPG (milhas por galão)
    mpg = constante * (vss_mih / maf)
    
    # Converte MPG para km/L
    km_por_litro = mpg * 0.4251
    
    return km_por_litro
