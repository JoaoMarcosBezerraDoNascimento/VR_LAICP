from fastapi import FastAPI
from pydantic import BaseModel
import logging
import uvicorn
import threading, json, os, time, subprocess
import base64, tempfile
from memoria_rag import MemoriaRAG

# ------------------ Inicialização da memória RAG ------------------
memoria = MemoriaRAG()

# ------------------ Configuração de Log ------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

app = FastAPI()

# ------------------ Modelo de dados ------------------
class Dados(BaseModel):
    texto: str = None
    imagem_base64: str = None
    
# -------------- Decisão de uso do LLava --------------
def deve_usar_llava(texto: str, caminho_imagem: str = None) -> bool:
    # 1. Se não houver imagem, não usa LLaVA
    if not caminho_imagem:
        return False

    # 2. Verifica palavras-chave no texto
    palavras_chave = ['foto', 'imagem', 'figura', 'mostre', 'cor', 'analisar', 'detalhe']
    if any(p.lower() in texto.lower() for p in palavras_chave):
        return True

    # 3. Análise rápida da imagem (proporção de pixels relevantes)
    import cv2, numpy as np
    img = cv2.imread(caminho_imagem, cv2.IMREAD_GRAYSCALE)
    if img is None:
        return False
    proporcao = np.count_nonzero(img) / img.size
    if proporcao < 0.05:  # imagem praticamente vazia
        return False

    # 4. Se texto curto e imagem com informação suficiente → usa LLaVA
    if len(texto) < 50 and proporcao > 0.1:
        return True

    return False

# ------------------ Endpoint principal ------------------
@app.post("/processar")
# ------------------ Endpoint principal ------------------
@app.post("/processar")
def processar(dados: Dados):
    logging.info(f"📦 Recebido: {dados.dict()}")

    os.environ["OLLAMA_USE_GPU"] = "1"

    contexto = ""
    if dados.texto:
        similares = memoria.buscar(dados.texto)
        if similares:
            contexto = "\n".join(similares)

    tem_imagem = bool(dados.imagem_base64)
    tem_texto = bool(dados.texto)

    caminho_imagem = None
    if tem_imagem:
        img_data = base64.b64decode(dados.imagem_base64)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_file:
            tmp_file.write(img_data)
            caminho_imagem = tmp_file.name

    prompt_image = f"""
    Base de conhecimento (relevante ao assunto):
    {contexto}

    Você é um assistente técnico especializado em eletrônica e análise de imagens industriais.
    Analise cuidadosamente a imagem localizada em {caminho_imagem} e a mensagem do usuário: "{dados.texto}".

    Responda em português do Brasil de forma direta e técnica:
    1. Descreva brevemente o que aparece na imagem (máximo 1 frase).
    2. Informe se a mão na imagem está usando luva ESD (sim ou não).
    3. Diga se a memória RAM aparenta ter algum defeito visível (sim, não ou indeterminado).
    4. Não use linguagem genérica ou floreada — seja objetivo.
    """

    prompt_text = f"""
    Base de conhecimento (relevante ao assunto):
    {contexto}

    Mensagem do usuário: "{dados.texto}"

    Responda de forma natural, curta e direta, em português do Brasil.
    Se for uma pergunta técnica, responda com precisão e sem explicações desnecessárias.
    Se for uma saudação ou comentário simples, responda de forma educada e objetiva.
    """

    start_time = time.time()
    resposta = ""

    usar_llava = deve_usar_llava(dados.texto or "", caminho_imagem)
    logging.info(f"[DEBUG] usar_llava = {usar_llava}")

    try:
        if usar_llava:
            result1 = subprocess.run(
                ["ollama", "run", "llava"],
                input=prompt_image,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=120
            )
            result2 = subprocess.run(
                ["ollama", "run", "llama2"],
                input=prompt_text,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=120
            )
            resposta = f"{result1.stdout.strip()} {result2.stdout.strip()}"
        else:
            result2 = subprocess.run(
                ["ollama", "run", "llama2"],
                input=prompt_text,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=120
            )
            resposta = result2.stdout.strip()
    except subprocess.TimeoutExpired:
        resposta = "[ERRO] Timeout — IA demorou demais para responder."

    elapsed = time.time() - start_time
    logging.info(f"[DEBUG] Tempo de execução: {elapsed:.2f}s")
    logging.info(f"[DEBUG] Resposta final: {resposta}")

    # Atualiza base RAG
    if dados.texto:
        memoria.adicionar(dados.texto, origem="usuario")
    if resposta:
        memoria.adicionar(resposta, origem="ia")

    # Remove arquivo temporário
    if caminho_imagem and os.path.exists(caminho_imagem):
        os.remove(caminho_imagem)

    return {"resposta": resposta}

# ------------------ Inicialização do servidor ------------------
def iniciar_api():
    uvicorn.run("API_IA:app", host="0.0.0.0", port=8000, reload=False)

if __name__ == "__main__":
    iniciar_api()
