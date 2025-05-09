import csv
import os
import time
import joblib
import threading
import asyncio
import json
import random
import uvicorn
import numpy as np
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import threading
from pydub import AudioSegment
import pyttsx3

from outlier_detection import TEDA
from mmcloud import MMCloud
from emissions import *
from consumption import instant_fuel_consumption
from accelerometer import read_acelerometer
from gps import get_gps_coordinates

from agent_module import run_llm, check_incidents, get_last_driver_behavior

# Inicializa os modelos
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
) 

connections = set()
queue = asyncio.Queue()

teda = TEDA()
mmcloud = MMCloud(dimension=2, max_clusters=3)
connections = set()

# Nome do arquivo CSV
csv_file = "obd_data.csv"

data_to_send = {}

# Mock flags
test_mode = True
mock_acc = True

start_time = time.time()

# Mock de sensores OBD
def gerar_dados_mock():
    return {
        # Campos já existentes
        "speed": random.uniform(0, 120),
        "rpm": random.uniform(800, 4000),
        "engine_load": random.uniform(20, 80),
        "coolant_temp": random.uniform(70, 105),
        "timing_advance": random.uniform(-10, 40),
        "intake_temp": random.uniform(20, 60),
        "maf": random.uniform(2, 20),
        "throttle": random.uniform(10, 90),
        "fuel_level": random.uniform(10, 90),
        "ethanol_percentagem": random.uniform(0, 100),

        # Novos campos da interface TypeScript
        "bateria": random.uniform(12, 14),
        "temperaturaMotor": random.uniform(70, 105),
        "tipoCombustivel": random.choice(["Gasolina", "Etanol", "Diesel"]),
        "tipoVia": random.choice(["Urbana", "Rodovia"]),
        "bussola": random.choice(["N", "S", "L", "O"]),
        "co2": random.uniform(100, 300),
        "perfilMotorista": random.choice(["Calmo", "Agressivo"]),
        "velocidade": random.uniform(0, 120),
        # "tempTotal": random.uniform(20, 80),
        "eco": random.choice([True, False]),
        "notaImetro": random.choice(["A", "B", "C"]),
        "tempAmbiente": random.uniform(15, 35),
        "consumo": random.uniform(5, 15),
        "distancia": random.uniform(0, 500)
    }

def mock_acelerometer(dados):
    dados["accel_x"] = 0.5
    dados["accel_y"] = 0.5
    dados["accel_z"] = 0.5
    dados["gyro_x"] = 0.5
    dados["gyro_y"] = 0.5
    dados["gyro_z"] = 0.5

    return dados

def gerar_e_tocar_audio(texto, arquivo_wav='saida.wav', arquivo_mp3='saida.mp3'):
    try:
        # Inicializa pyttsx3
        engine = pyttsx3.init()
        engine.setProperty('rate', 150)
        engine.setProperty('volume', 0.5)
        voices = engine.getProperty('voices')
        engine.setProperty('voice', voices[0].id)

        # Salva em WAV
        engine.save_to_file(texto, arquivo_wav)
        engine.runAndWait()

        # Converte para MP3
        sound = AudioSegment.from_wav(arquivo_wav)
        sound.export(arquivo_mp3, format="mp3")
        print(f"✅ Áudio salvo como {arquivo_mp3}")

        # Reproduz o áudio (opcional: comentável)
        engine.say(texto)
        engine.runAndWait()
        print("✅ Áudio reproduzido")
    except Exception as e:
        print(f"❌ Erro ao gerar ou tocar áudio: {e}")

def calculate_radar_area(data):
    # Normaliza o RPM
    rpm = data['rpm'] / 100
    speed = data['speed']
    throttle = data['throttle']
    engine = data['engine_load']

    values = [rpm, speed, throttle, engine]

    # Fórmula da área do polígono
    angle = 2 * np.pi / len(values)
    area = 0.5 * np.abs(np.dot(values, np.roll(values, 1)) * np.sin(angle))
    
    return area

def calcular_heading(dados, delta_t=1.0):
    """
    Atualiza e calcula o heading (bússola aproximada) com base no gyro_z.
    Retorna uma string: 'N', 'S', 'L', 'O'.
    """
    # Mapeamento de direção cardinal para graus
    mapa_direcao_para_graus = {
        "N": 0.0,
        "L": 90.0,
        "S": 180.0,
        "O": 270.0
    }

    # Se não existir heading, inicializa em 0.0
    if "bussola" not in dados:
        dados["bussola"] = 0.0
    else:
        # Se bussola for string (direção), converte para grau
        if isinstance(dados["bussola"], str):
            dados["bussola"] = mapa_direcao_para_graus.get(dados["bussola"], 0.0)

    # Atualiza o bussola acumulado
    dados["bussola"] += dados["gyro_z"] * delta_t

    # Normaliza para 0–360°
    dados["bussola"] %= 360

    # Determina a direção cardinal
    angle = dados["bussola"]
    if angle >= 315 or angle < 45:
        direcao = "Norte"
    elif angle < 135:
        direcao = "Leste"
    elif angle < 225:
        direcao = "Sul"
    else:
        direcao = "Oeste"

    return direcao


def identify_fuel_type(dados):
    if "fuel_type" in dados:
        prob = 1.0
        return dados["fuel_type"], prob
    elif "ethanol_percentage" in dados:
        model = joblib.load("./models/ethanol_model_rf.pkl")
        X = [dados["ethanol_percentage"],
             dados["speed"],
             dados["rpm"],
             dados["engine_load"],
             dados["throttle"],
             dados["timing_advance"]]
        X = np.array(X).reshape(1, -1)
        fuel_type = model.predict(X)[0]
        prob = model.predict_proba(X)[0]
        return fuel_type, prob
    # else:
    #     pass
    return "gasolina", 1.0
        
def identify_city_highway(dados):
    model = joblib.load("models/city_highway_rf.pkl")
    X = [dados["speed"],
         dados["rpm"],
         dados["engine_load"],
         dados["throttle"],
         dados["timing_advance"],
         dados["accel_magnitude"]
         ]
    X = np.array(X).reshape(1, -1)
    city_highway = model.predict(X)[0]
    prob = model.predict_proba(X)[0]
    return city_highway, prob

def calculate_emissions_maf_afr(dados):
    # if maf not in dados
    if "maf" not in dados:
        dados["maf"] = estimate_maf(dados["rpm"], dados["intake_temp"], dados["intake_pressure"], dados["cc"])
    
    # calculate emission rate
    dados["co2_emission"] = calc_emission_rate(dados["maf"], dados["fuel_type"])

    # print(dados["co2_emission"])
    # calculate emission rate per km
    dados["co2"] = convert_emission_rate(dados["co2_emission"], dados["speed"])

    return dados

# Inicializa sensores reais se não estiver em modo de teste
if not test_mode:
    import obd
    connection = obd.OBD()
    sensors = {
        "speed": obd.commands.SPEED,
        "rpm": obd.commands.RPM,
        "engine_load": obd.commands.ENGINE_LOAD,
        "coolant_temp": obd.commands.COOLANT_TEMP,
        "timing_advance": obd.commands.TIMING_ADVANCE,
        "intake_temp": obd.commands.INTAKE_TEMP,
        "maf": obd.commands.MAF,
        "throttle": obd.commands.THROTTLE_POS,
        "fuel_level": obd.commands.FUEL_LEVEL,
        "ethanol_percentage": obd.commands.ETHANOL_PERCENT,
        "tempAmbiente": obd.commands.AMBIANT_AIR_TEMP,
        "bateria": obd.commands.CONTROL_MODULE_VOLTAGE,
        "temperaturaMotor": obd.commands.COOLANT_TEMP,
    }

# Processamento dos dados
def processar_dados(dados):
    global start_time
    elapsed_time = time.time() - start_time
    dados["tempTotal"] = elapsed_time
    # Soft-Sensor 1: Área do Radar
    dados["radar_area"] = calculate_radar_area({
        "rpm": dados["rpm"],
        "speed": dados["speed"],
        "throttle": dados["throttle"],
        "engine_load": dados["engine_load"]
    })
    
    # Soft-Sensor 2: Magnitude do Acelerômetro
    if mock_acc:
        dados = mock_acelerometer(dados)
    else:
        dados = read_acelerometer(dados)
    dados["accel_magnitude"] = np.sqrt(
        dados["accel_x"]**2 + dados["accel_y"]**2 + dados["accel_z"]**2
    )

    # Coletar dados do GPS
    dados["latitude"], dados["longitude"] = get_gps_coordinates()

    if dados["latitude"] is None:
        dados["latitude"] = -5.7945
    if dados["longitude"] is None:
        dados["longitude"] = -35.211

    # Detecção de Outlier com o TEDA
    dados["teda_flag"] = teda.run([dados["radar_area"]])

    # Identificação do tipo de combustível
    dados["fuel_type"], dados["fuel_type_prob"] = identify_fuel_type(dados)

    # Análise de Comportamento do Motorista
    dados["driver_behavior"] = mmcloud.process_point([dados["radar_area"], dados["engine_load"]], 1)

    # Define ECO automaticamente
    if dados["driver_behavior"] == "cautious":
        dados["eco"] = True
    else:
        dados["eco"] = False

    # Identificação do tipo de via
    dados["city_highway"], dados["city_highway_prob"] = identify_city_highway(dados)

    # Cálculo de Emissões
    dados = calculate_emissions_maf_afr(dados)

    # Cálculo de Consumo Instantâneo
    dados["instant_fuel_consumption"] = instant_fuel_consumption(dados["speed"], maf=dados["maf"], combustivel=dados["fuel_type"])

    # DISTÂNCIA ACUMULADA
    if "distancia_total" not in dados:
        dados["distancia_total"] = 0.0
    dados["distancia_total"] += dados["speed"] / 3600

    # CONSUMO MÉDIO
    if "consumo_total" not in dados:
        dados["consumo_total"] = 0.0
        dados["contagem_consumo"] = 0

    dados["consumo_total"] += dados["instant_fuel_consumption"]
    dados["contagem_consumo"] += 1
    dados["consumo_medio"] = dados["consumo_total"] / dados["contagem_consumo"]

    dados["bussola"] = calcular_heading(dados)

    return dados

# Salvamento dos dados
# def save_data_to_csv(data):
#     print(data)
#     file_exists = os.path.isfile(csv_file)
#     with open(csv_file, mode='a', newline='') as file:
#         writer = csv.writer(file)
#         if not file_exists:
#             writer.writerow(list(data.keys()))
#         writer.writerow(list(data.values()))

def clean_value(value):
    if isinstance(value, str):
        value = value.replace('\n', ' ').replace(',', ';').strip()
    return value

def save_data_to_csv(data, csv_file):
    print(data)
    file_exists = os.path.isfile(csv_file)

    # Separa a resposta do modelo
    model_response = clean_value(data.get('model_response', ''))
    
    # Remove a resposta do dicionário antes de gravar as outras colunas
    data_no_response = {k: v for k, v in data.items() if k != 'model_response'}
    
    with open(csv_file, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)

        # Garante a coluna model_response no cabeçalho
        if not file_exists:
            headers = list(data_no_response.keys()) + ['model_response']
            writer.writerow(headers)
        
        # Limpa os valores e adiciona a resposta como última coluna
        cleaned_values = [clean_value(v) for v in data_no_response.values()]
        cleaned_values.append(model_response)
        
        writer.writerow(cleaned_values)

# Coleta dos dados
def clean_data_for_json(obj, seen=None):
    if seen is None:
        seen = set()
    obj_id = id(obj)
    if obj_id in seen:
        return "CIRCULAR_REF"
    seen.add(obj_id)

    if isinstance(obj, dict):
        return {k: clean_data_for_json(v, seen) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [clean_data_for_json(v, seen) for v in obj]
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, np.generic):
        return round(obj.item(), 0) if np.issubdtype(obj, np.floating) else int(obj.item())
    elif isinstance(obj, float):
        return round(obj, 0)
    elif isinstance(obj, int):
        return int(obj)
    else:
        return obj

# WebSocket
# @app.websocket("/ws")
# async def websocket_endpoint(websocket: WebSocket):
#     await websocket.accept()
#     connections.add(websocket)
#     try:
#         while True:
#             await asyncio.sleep(1)
#             # envia um oi
#             # await websocket.send_text("oi")
#             # envia os dados mais recentes para o cliente
#             data_to_send = collect_obd_data()
#             # transforma os dados em JSON
#             data_to_send = {k: clean_data_for_json(v) for k, v in data_to_send.items()}
#             # envia para o cliente
#             print(data_to_send)
#             # envia os dados para o cliente
#             await websocket.send_json(data_to_send)
#     except Exception as e:
#         print(f"WebSocket error: {e}")
#     finally:
#         connections.remove(websocket)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    first_time = True
    last_call_time = time.time()
    tool_toggle = 0   # 0 = comportamento, 1 = acidentes/multas
    try:
        while True:
            # await asyncio.sleep(1)

            # Seu código OBD, TEDA, etc.
            data_to_send = collect_obd_data()
            print("🚀 Coletou OBD:", data_to_send)

            # TEDA outlier → agora checando corretamente
            if data_to_send.get("teda_flag", False):
                context = get_last_driver_behavior(data_to_send["driver_behavior"])
                response, metrics = await run_llm("Como estou dirigindo?", context)
                data_to_send["alerta_outlier"] = response
                data_to_send.update({f"outlier_{k}": v for k, v in metrics.items()})
                print("✅ Outlier detectado e processado")
                print("🧠 Resposta do modelo (outlier):", response)


            # Alternância de tools por tempo
            current_time = time.time()
            if first_time:
                last_call_time = current_time
                first_time = False

            if current_time - last_call_time >= 10:
                if tool_toggle == 0:
                    context = get_last_driver_behavior(data_to_send["driver_behavior"])
                    question = "Como estou dirigindo?"
                    tool_toggle = 1
                else:
                    context = check_incidents(data_to_send["latitude"], data_to_send["longitude"])
                    question = "Acidentes ou multas?"
                    tool_toggle = 0

                response, metrics = await run_llm(question, context)
                data_to_send["alerta_periodica"] = response
                data_to_send.update({f"periodica_{k}": v for k, v in metrics.items()})
                last_call_time = current_time
                print(f"✅ Tool alternada ({question}) executada")
                print("🧠 Resposta do modelo (periodica):", response)


            save_data_to_csv(data_to_send, csv_file)
            print("💾 Dados salvos no CSV")

            data_to_send = {k: clean_data_for_json(v) for k, v in data_to_send.items()}
            print("📤 Enviando pelo WebSocket:", data_to_send)
            await websocket.send_json(data_to_send)
    except Exception as e:
        print(f"❌ Erro no WebSocket: {e}")

def collect_obd_data():
    # while True:
    if test_mode:
        latest_data = gerar_dados_mock()
    else:
        latest_data = {}
        for key, cmd in sensors.items():
            response = connection.query(cmd)
            if response and response.value is not None:
                try:
                    latest_data[key] = float(str(response.value).split(" ")[0])
                except:
                    pass
    
    # print("Recebendo dados do OBD:", latest_data)
    latest_data = processar_dados(latest_data)
    # save_data_to_csv(latest_data)

    # 🔥 Envia para a fila, não diretamente para o WebSocket
    return latest_data
        # asyncio.run_coroutine_threadsafe(queue.put(latest_data), loop)
        # time.sleep(1)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    threading.Thread(target=collect_obd_data, daemon=True).start()
    # loop.create_task(sender_loop())
    uvicorn.run(app, host="localhost", port=8000)