import ollama
import logging
import logging
import os
from pathlib import Path
import datetime
from RAG import rag_tools
from utils.logger import setup_logger
from utils.env import *

historico_da_conversa = []

stantard_prompt = """
Você é a Zill_IA, uma IA avançada desenvolvida para fornecer respostas precisas e úteis com base em prompts de texto e imagens. Sua missão é ajudar os usuários respondendo suas perguntas de maneira clara e informativa.
"""
Nome = "João Marcos Bezerra do Nascimento"
Funcao = "Desenvolvedor Júnior"
Notas_sobre_funcionário = "Acesso livre ao sistema operacional e arquivos locais do servidor, incluindo pastas de projetos e arquivos de configuração. Acesso irrestrito a dados pessoais e financeiros. Acesso ilimitado a recursos de rede, com permissão para acessar a internet para fins relacionados ao trabalho, como pesquisa e comunicação profissional."

logger = setup_logger(
    log_name="Zillia_IA",
    log_file="Zillia_IA.txt",
    level=logging.DEBUG
)

def contexto_conversa(
    origem: str = "chat_web",
):
    agora = datetime.datetime.now()

    texto_contexto = f"""
CONTEXTO DA CONVERSA:
- Data: {agora.strftime('%d/%m/%Y')}
- Hora: {agora.strftime('%H:%M:%S')}
- Fuso horário: Manaus-AM (Brasil) (UTC-4)

USUÁRIO:
- Nome: {None}
- Função: {Funcao}
- Notas sobre funcionário: {Notas_sobre_funcionário}

MAQUINA:
- Sistema: Windoes 11 Pro / Linux Mint 21.1 : Tela inicial do app
- Host: Zilia Technologies,(https://ziliatech.com), Servidor local (localhost)
""".strip()

    return texto_contexto

def Zillia_IA(nome_ia="Zillia_IA", prompt=" Responda:'Bom dia :)'", imagem_path=None, tries=1, modelo=modelo_resposta):
    """
    Analisa uma imagem ou prompt e retorna a resposta da IA como STRING.
    """
    for i in range(tries):
        try:
            rag = rag_tools.consulta_semantica(prompt)
            mensagem = {'role': 'user', 'content': stantard_prompt + rag + prompt + contexto_conversa()}
            
            if imagem_path:
                mensagem['images'] = [imagem_path]

            response = ollama.chat(model=modelo, messages=[mensagem])

            return response.message.content.strip()

        except Exception as e:
            logger.error(f"Erro na tentativa {i+1} de {nome_ia}: {str(e)}")
            if i == tries - 1:
                raise RuntimeError(f"Falha crítica no {nome_ia} após {tries} tentativas")

    return ""

if __name__ == "__main__":
    while True:
        perg = input("Digite sua pergunta (ou 'sair' para encerrar): ")
        historico_da_conversa.append({"role": "Usuário", "content": perg})
        resposta_IA = Zillia_IA(prompt=perg)
        historico_da_conversa.append({"role": "Zilia_IA", "content": resposta_IA})
        print(f"Zillia_IA: {resposta_IA}\n")