#env.py (usado ao longo do projeto)
import os
from pathlib import Path
import datetime
import datetime
import locale
import platform
import socket
import getpass
import ollama

# ===============================
# PATHS (RAIZ DO PROJETO IA)
# ===============================

PASTA_RAIZ = os.path.dirname(os.path.abspath(__file__))

# Agora o "projeto" é a própria pasta do env.py
PASTA_PROJETO = PASTA_RAIZ

PASTA_RAG = os.path.join(PASTA_PROJETO, "RAG")
PASTA_DATA = os.path.join(PASTA_PROJETO, "data")
PASTA_LOG = os.path.join(PASTA_PROJETO, "Logs")

# ===============================
# Variáveis de ambiente
# ===============================

#modelo de embedis para o RAG:
modelo_embed = "all-MiniLM-L6-v2"

#modelo de resposta:
modelo_resposta = "gemma3:4b"

def contexto_conversa(
    usuario: str = None,
    funcao: str = None,
    origem: str = "chat_web",
    local: str = None
):
    agora = datetime.datetime.now()

    nome_usuario = usuario or getpass.getuser()
    funcao_usuario = funcao or "não informada"
    local_usuario = local or "não informado"

    texto_contexto = f"""
CONTEXTO DA CONVERSA:
- Data: {agora.strftime('%d/%m/%Y')}
- Hora: {agora.strftime('%H:%M:%S')}
- Fuso horário: {agora.astimezone().tzname()}

USUÁRIO:
- Nome: {nome_usuario}
- Função: {funcao_usuario}
- Local: {local_usuario}

AMBIENTE:
- Sistema: {platform.system()}
- Host: {socket.gethostname()}
- Origem: {origem}
""".strip()

    return texto_contexto


