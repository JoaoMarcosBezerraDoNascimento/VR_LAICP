# server_mcp.py
# pip install fastapi uvicorn

from fastapi import FastAPI
from pydantic import BaseModel
import ollama
from rag_tools import consulta_semantica

app = FastAPI()

stantard_prompt = """
Você é a Zill_IA, uma IA avançada desenvolvida para fornecer respostas precisas e úteis com base em prompts de texto e imagens. Sua missão é ajudar os usuários respondendo suas perguntas de maneira clara e informativa.
Verifique a intensão do usuário e forneça respostas relevantes, utilizando o contexto da conversa e as informações disponíveis. Se o prompt incluir uma imagem, analise-a cuidadosamente para extrair informações relevantes que possam ajudar a responder à pergunta do usuário.
Verifique se o RAG recebido é relevante para a pergunta do usuário e, se for, utilize-o para enriquecer sua resposta. Se o RAG não for relevante, ignore-o e responda apenas com base no prompt e no contexto da conversa.
"""

def executar_IA(modelo = "gemma3:4b",perg = None):
    mensagem = {"role": "user","content": stantard_prompt + perg}
    response = ollama.chat(model=modelo, messages=[mensagem])
    resposta = response.message.content.strip()
    print(resposta)
    return resposta

def consulta_db(consulta):
    return "consulta_vazia, o banco não tem esses dados solicitados"

class ChatReq(BaseModel):
    pergunta: str
    modelo: str | None = None

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/chat")
def chat(req: ChatReq):
    content = req.pergunta
    resposta = executar_IA(perg = content)
    return {"resposta": resposta}

@app.post("/rag")
def rag(req: ChatReq):
    rag_txt = consulta_semantica(req.pergunta)
    content = f"{rag_txt} \n ========== \n {req.pergunta}"
    resposta = executar_IA(perg=content)
    return {"resposta": resposta}

@app.post("/db")
def db(req: ChatReq):
    resultado_db = consulta_db(req.pergunta)
    content = f" resultado da consutla do banco de dados:\n{resultado_db} \n\==========n {req.pergunta}"
    resposta = executar_IA(perg=content)
    return {"resposta": resposta}

# criar
# py -3.11 -m venv .\.venv
# .\.venv\Scripts\python.exe -m pip install -U pip

# Rodar:
# cd IA
# .\.venv\Scripts\Activate.ps1
# uvicorn server_mcp:app --host 0.0.0.0 --port 8000
