import pandas as pd
import numpy as np
from sklearn.neighbors import BallTree
from langchain_community.llms import LlamaCpp
from langchain_core.callbacks import CallbackManager, StreamingStdOutCallbackHandler
import asyncio

# LLM config
callback_manager = CallbackManager([StreamingStdOutCallbackHandler()])
llm = LlamaCpp(
    model_path="./models/Qwen2.5-0.5B.Q4_K_M.gguf",
    temperature=0.0,
    max_tokens=25,
    top_p=1,
    callback_manager=callback_manager,
    verbose=False,
)

# Prompt builder
def build_prompt(context, question):
    q = question.lower()
    if "sinistro" in q or "multa" in q:
        example = "Exemplo: Multas ou sinistros próximos detectados no caminho."
    else:
        example = "Exemplo: Você está dirigindo de forma ..."
    return f"""Você é um assistente automotivo. Com base no contexto, responda de forma amigável e curta.

Contexto: {context}
Pergunta: {question}
{example}
Resposta:"""

# Acidentes / multas
acidentes = pd.read_csv('acidentes_processado.csv')
multas = pd.read_csv('multas_processado.csv')
acidentes_coords = np.radians(acidentes[['latitude', 'longitude']].values)
multas_coords = np.radians(multas[['latitude', 'longitude']].values)
acidentes_tree = BallTree(acidentes_coords, metric='haversine')
multas_tree = BallTree(multas_coords, metric='haversine')
RAIO_METROS = 500
RAIO_RADIANOS = RAIO_METROS / 6371000

def get_last_driver_behavior(last_value):
    try:
        behavior_map = {
            "cautious": "Você está dirigindo de forma cautelosa. Ótimo para segurança e economia!",
            "normal": "Você está dirigindo de forma normal. Continue atento à estrada.",
            "aggressive": "Você está dirigindo de forma agressiva. Recomendo reduzir a velocidade e dirigir com mais cuidado."
        }
        return behavior_map.get(last_value.lower(), "Comportamento desconhecido.")
    except Exception as e:
        return f"Erro ao ler o arquivo: {e}"

def check_incidents(latitude, longitude):
    coord_atual = np.radians([[latitude, longitude]])
    acidentes_idx = acidentes_tree.query_radius(coord_atual, r=RAIO_RADIANOS)[0]
    multas_idx = multas_tree.query_radius(coord_atual, r=RAIO_RADIANOS)[0]
    summary = ""
    if len(acidentes_idx) > 0:
        summary += f"⚠️ {len(acidentes_idx)} sinistros próximos detectados. "
    if len(multas_idx) > 0:
        summary += f"🚓 {len(multas_idx)} multas registradas próximas. "
    if summary == "":
        summary = "✅ Nenhum sinistro ou multa próximo."
    return summary

async def run_llm(question, context):
    import time, psutil, asyncio

    loop = asyncio.get_event_loop()
    prompt = build_prompt(context, question)

    start_time = time.perf_counter()
    process = psutil.Process()
    cpu_before = psutil.cpu_percent(interval=None)
    mem_before = process.memory_info().rss / (1024 * 1024)  # MB

    result = await loop.run_in_executor(None, llm.invoke, prompt)

    end_time = time.perf_counter()
    elapsed = end_time - start_time
    cpu_after = psutil.cpu_percent(interval=None)
    mem_after = process.memory_info().rss / (1024 * 1024)  # MB

    metrics = {
        "inference_time_s": round(elapsed, 2),
        "memory_before_mb": round(mem_before, 2),
        "memory_after_mb": round(mem_after, 2),
        "cpu_before_percent": round(cpu_before, 2),
        "cpu_after_percent": round(cpu_after, 2),
    }

    if hasattr(llm, 'n_tokens'):
        n_tokens = llm.n_tokens
        tokens_per_sec = n_tokens / elapsed
        metrics["tokens_generated"] = n_tokens
        metrics["tokens_per_sec"] = round(tokens_per_sec, 2)

    return result, metrics

