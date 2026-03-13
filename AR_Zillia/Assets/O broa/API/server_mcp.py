# servidor/server_mcp.py
import os
import base64
import ollama
import base64
import requests
import tempfile
from ultralytics import YOLO
from pydantic import BaseModel
from fastapi import HTTPException
from IA.rag_tools import consulta_semantica
from fastapi import APIRouter, UploadFile, File, Form

#app = FastAPI()
router = APIRouter(prefix="/ia", tags=["IA"])

#modelo YOLO
YOLO_MODEL = YOLO(r"/home/adrianonobre/IA_VR/IA/YOLOV8s_Barcode_Detection.pt")

stantard_prompt = """
Você é a Zill_IA, uma IA avançada desenvolvida para fornecer respostas precisas e úteis com base em prompts de texto e imagens. Sua missão é ajudar os usuários respondendo suas perguntas de maneira clara e informativa.
Verifique a intensão do usuário e forneça respostas relevantes, utilizando o contexto da conversa e as informações disponíveis. Se o prompt incluir uma imagem, analise-a cuidadosamente para extrair informações relevantes que possam ajudar a responder à pergunta do usuário.
Verifique se o RAG recebido é relevante para a pergunta do usuário e, se for, utilize-o para enriquecer sua resposta. Se o RAG não for relevante, ignore-o e responda apenas com base no prompt e no contexto da conversa.
"""

def executar_IA(modelo: str = "llama3.1:8b",perg: str | None = None,imagem_path: str | None = None,):
    mensagem = {"role": "user","content": stantard_prompt + (perg or ""),}
    if imagem_path:mensagem["images"] = [imagem_path] 
    response = ollama.chat(model=modelo,messages=[mensagem],)
    resposta = response["message"]["content"].strip()
    print(resposta)
    return resposta

def consulta_db(consulta):
    return "consulta_vazia, o banco não tem esses dados solicitados ou a conexão não foi estavelecida"

class ChatReq(BaseModel):
    pergunta: str
    modelo: str | None = None

@router.get("/health")
def health():
    return {"Tô saudável!": True}

@router.post("/chat")
def chat(req: ChatReq):
    content = req.pergunta
    resposta = executar_IA(perg = content)
    return {"resposta": resposta}

@router.post("/rag")
def rag(req: ChatReq):
    rag_txt = consulta_semantica(req.pergunta)
    content = f"{rag_txt} \n ========== \n {req.pergunta}"
    resposta = executar_IA(perg=content)
    return {"resposta": resposta}

@router.post("/db")
def db(req: ChatReq):
    resultado_db = consulta_db(req.pergunta)
    content = f" resultado da consutla do banco de dados:\n{resultado_db} \n\==========n {req.pergunta}"
    resposta = executar_IA(perg=content)
    return {"resposta": resposta}

@router.post("/analisar_PCP")
def analisar_pcp(
    imagem: UploadFile = File(...),
    prompt: str = Form(
        "Você é um assistente profissional de análise de placas de circuito impresso.\n"
        "Analise a imagem e responda APENAS com um JSON válido (sem texto extra) exatamente neste formato:\n"
        "{\n"
        "  \"Resto_Solda_GoldFinger\": \"SIM/NAO\",\n"
        "  \"Arranhoes_Placa_Trilhas\": \"SIM/NAO\",\n"
        "  \"Residuos_Cola_Sujeira_Manchas\": \"SIM/NAO\",\n"
        "  \"Falta_Componentes\": \"SIM/NAO\",\n"
        "  \"tiqueta_Zilia_Smart_Falha_Leitura\": \"SIM/NAO\"\n"
        "}\n\n"
        "Regras:\n"
        "- Use somente \"SIM\" ou \"NAO\" (maiúsculo, sem acento).\n"
        "- Se não tiver certeza, responda \"NAO\"."
    ),
    ollama_url: str = Form("http://localhost:11434"),
    model: str = Form("llama3.1:8b"),
    timeout: int = Form(180),
    temperature: float = Form(0.0),
    top_k: int = Form(40),
    top_p: float = Form(0.9),
    min_p: float = Form(0.0),
    num_ctx: int = Form(2048),
    num_predict: int = Form(1024),
    repeat_penalty: float = Form(1.1),
    seed: int = Form(42),
) -> str:
    img_bytes = imagem.file.read()
    img_b64 = base64.b64encode(img_bytes).decode("utf-8")

    params = {
        "temperature": float(temperature),
        "top_k": int(top_k),
        "top_p": float(top_p),
        "min_p": float(min_p),
        "num_ctx": int(num_ctx),
        "num_predict": int(num_predict),
        "repeat_penalty": float(repeat_penalty),
        "seed": int(seed),
    }

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt, "images": [img_b64]}],
        "stream": False,
        "options": params,
    }

    r = requests.post(f"{ollama_url.rstrip('/')}/api/chat", json=payload, timeout=timeout)
    r.raise_for_status()
    data = r.json()

    msg = data.get("message")
    if isinstance(msg, dict):
        return msg.get("content", "") or ""
    return data.get("response", "") or ""

class DigitalizarDocumentoIn(BaseModel):
    image_b64: str  # pode vir puro ou como "data:image/jpeg;base64,...."

@router.post("/digitalizar_documento")
def digitalizar_documento_foto(payload: DigitalizarDocumentoIn) -> dict:
    img_b64 = (payload.image_b64 or "").strip()
    if not img_b64:
        raise HTTPException(status_code=400, detail="image_b64 vazio.")

    # aceita data URL também
    if "base64," in img_b64:
        img_b64 = img_b64.split("base64,", 1)[1].strip()

    try:
        img_bytes = base64.b64decode(img_b64, validate=True)
    except Exception:
        raise HTTPException(status_code=400, detail="image_b64 inválido (base64).")

    # salva temporário para o Ollama ler por caminho
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as f:
            f.write(img_bytes)
            tmp_path = f.name

        resposta1 = ollama.chat(
            model="llama3.1:8b",
            messages=[{
                "role": "user",
                "content": (
                    "Fale tudo oq pode ser coletado de texto no documento recebido, "
                    "ele passará para um OCR após isso e nele será feito um loop de coleta de texto, "
                    "ele vai rodar loops inifinatamente até ter 100% do texto que você disser que existe no documento"
                ),
                "images": [tmp_path],
            }],
        )

        texto1 = resposta1.get("message", {}).get("content", "")

        resposta2 = ollama.chat(
            model="llama3.1:8b",
            messages=[{
                "role": "user",
                "content": f"Organize os campos em um JSON Estruturado e veja se falta algo:\n{texto1}",
                "images": [tmp_path],
            }],
        )

        texto2 = resposta2.get("message", {}).get("content", "")

        json_str = ""
        coletando = False
        for linha in texto2.splitlines():
            s = linha.strip()
            if s.startswith("```json"):
                coletando = True
                continue
            if coletando and s.startswith("```"):
                break
            if coletando:
                json_str += linha + "\n"

        json_str = json_str.strip()
        if not json_str:
            # fallback: se o modelo não colocou em bloco ```json
            json_str = texto2.strip()

        return {"json": json_str, "raw": texto2}

    finally:
        if tmp_path and os.path.isfile(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass

