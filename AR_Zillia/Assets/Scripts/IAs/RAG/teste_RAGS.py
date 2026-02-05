from env import *
from logger import setup_logger
import logging
from rag_tools import consulta_semantica, consulta_lexical, consulta_exata, criar_rag_paragrafos_da_pasta_data, salvar_rag, avaliar_qualidade_rag, avaliar_resposta
import ollama
from pathlib import Path

logger = setup_logger(
    log_name="TesteRAG",
    log_file="Teste_varios_RAGs.txt",
    level=logging.DEBUG
)

caminho_complemento = Path(PASTA_DATA) / "Complemento_RAG.txt"

perguntas = [item["pergunta"] for item in faq_rma]
respostas = [item["resposta"] for item in faq_rma]

def executar_IA(nome_ia="IA_Genérica", prompt=" Resposta 'Bom dia :)'", imagem_path=None, tries=1, modelo=modelo_resposta):
    """
    Analisa uma imagem ou prompt e retorna a resposta da IA como STRING.
    """
    for i in range(tries):
        try:
            mensagem = {'role': 'user', 'content': prompt}
            
            if imagem_path:
                mensagem['images'] = [imagem_path]

            response = ollama.chat(model=modelo, messages=[mensagem])

            return response.message.content.strip()

        except Exception as e:
            logger.error(f"Erro na tentativa {i+1} de {nome_ia}: {str(e)}")
            if i == tries - 1:
                raise RuntimeError(f"Falha crítica no {nome_ia} após {tries} tentativas")

    return ""

# ============================
# Funções de RAG
# ============================

from typing import List, Dict, Any

def montar_contexto_rag(
    pergunta: str,
    colecao: str,
    k_sem: int = 10,
    k_lex: int = 10,
    k_exa: int = 10,
    max_trechos: int = 1000,
    max_chars: int = 400000,
) -> str:
    docs_sem = consulta_semantica(pergunta, colecao=colecao, k=k_sem) or []
    docs_lex = consulta_lexical(pergunta, colecao=colecao, k=k_lex) or []
    docs_exa = consulta_exata(pergunta, colecao=colecao, k=k_exa) or []

    todos_docs: List[Dict[str, Any]] = (
        list(docs_sem) +
        list(docs_lex) +
        list(docs_exa)
    )

    textos_vistos = set()
    trechos = []
    for d in todos_docs:
        t = d.get("text", "").strip()
        if not t:
            continue
        if t in textos_vistos:
            continue
        textos_vistos.add(t)
        trechos.append(t)
        if len(trechos) >= max_trechos:
            break

    if not trechos:
        return ""

    contexto = ""
    for idx, t in enumerate(trechos, start=1):
        bloco = f"[Trecho {idx}]\n{t}\n\n"
        if len(contexto) + len(bloco) > max_chars:
            break
        contexto += bloco

    return contexto.strip()

def montar_prompt_com_rag(pergunta: str, contexto: str) -> str:
    if not contexto:
        return pergunta

    return f"""Você é uma IA especialista no domínio abaixo.

Use APENAS as informações dos trechos a seguir para responder com precisão.

[CONTEXTOS DO RAG]
{contexto}

[PERGUNTA]
{pergunta}
"""

# ==========================
# Teste sem consulta do RAG
# ==========================

logger.info("="*50 + "\nIniciando Teste sem RAG\n" + "="*50)

for pergunta, resposta in zip(perguntas, respostas):
    resposta_ia = executar_IA(prompt=pergunta)
    qualidade = avaliar_resposta(resposta_ia, resposta)

    print(f"PERGUNTA: {pergunta} | RESPOSTA IA (Sem RAG): {resposta_ia} | Qualidade_resposta: {qualidade}")
    logger.info(f"PERGUNTA: {pergunta} | RESPOSTA IA (Sem RAG): {resposta_ia} | Qualidade_resposta: {qualidade}")

# ==========================
# Teste com o RAG simples
# ==========================

logger.info("="*50 + "\nIniciando Teste com RAG Simples\n" + "="*50)

for pergunta, resposta in zip(perguntas, respostas):
    contexto = montar_contexto_rag(pergunta=pergunta, colecao="rag_simples")
    prompt_rag = montar_prompt_com_rag(pergunta, contexto)
    resposta_ia = executar_IA(prompt=prompt_rag)

    qualidade = avaliar_resposta(resposta_ia, resposta)
    qualidade_rag = avaliar_qualidade_rag(pergunta, contexto)

    print(f"PERGUNTA: {pergunta} | RESPOSTA IA: {resposta_ia} | Qualidade_resposta: {qualidade} | Qualidade_RAG: {qualidade_rag}")
    logger.info(f"PERGUNTA: {pergunta} | RESPOSTA IA: {resposta_ia} | Qualidade_resposta: {qualidade} | Qualidade_RAG: {qualidade_rag}")

# ==========================
# Teste com o RAG por Parágrafos
# ==========================

logger.info("="*50 + "\nIniciando Teste com RAG Estratégico (Parágrafos)\n" + "="*50)

for pergunta, resposta in zip(perguntas, respostas):
    contexto = montar_contexto_rag(pergunta=pergunta, colecao="RAG_Paragrafos")
    prompt_rag = montar_prompt_com_rag(pergunta, contexto)
    resposta_ia = executar_IA(prompt=prompt_rag)

    qualidade = avaliar_resposta(resposta_ia, resposta)
    qualidade_rag = avaliar_qualidade_rag(pergunta, contexto)

    print(f"PERGUNTA: {pergunta} | RESPOSTA IA: {resposta_ia} | Qualidade_resposta: {qualidade} | Qualidade_RAG: {qualidade_rag}")
    logger.info(f"PERGUNTA: {pergunta} | RESPOSTA IA: {resposta_ia} | Qualidade_resposta: {qualidade} | Qualidade_RAG: {qualidade_rag}")

# =================================
# Gerar TXT para complemento do RAG
# =================================

with caminho_complemento.open("w", encoding="utf-8") as f_out:
    for pergunta in perguntas:
        # monta contexto RAG com duas fontes
        contexto_parag = montar_contexto_rag(pergunta, colecao="RAG_Paragrafos") or ""
        contexto_simples = montar_contexto_rag(pergunta, colecao="rag_simples") or ""

        contexto = ""
        if contexto_parag:
            contexto += contexto_parag + "\n\n"
        if contexto_simples:
            contexto += contexto_simples

        # prompt especial para gerar um parágrafo HyDE
        prompt_pergunta = (
            f"{pergunta}\n"
            "Gere um parágrafo longo que responda satisfatoriamente a pergunta "
            "com base nos contextos fornecidos."
        )

        prompt_rag = montar_prompt_com_rag(prompt_pergunta, contexto)
        resposta_ia = executar_IA(prompt=prompt_rag)

        # mostra no console
        print(f"Pergunta\n{pergunta}")
        print(f"Resposta\n{resposta_ia}\n{'-'*40}\n")

        # salva no arquivo único
        f_out.write(f"PERGUNTA:\n{pergunta}\n")
        f_out.write(f"RESPOSTA:\n{resposta_ia}\n")
        f_out.write(f"{'-'*40}\n\n")

print(f"\nArquivo gerado em: {caminho_complemento.resolve()}")

nome_colecao_paragrafos = "RAG_HyDE"
documentos_rag_paragrafos = criar_rag_paragrafos_da_pasta_data(
    pasta_data=PASTA_DATA,
)
salvar_rag(
    documentos=documentos_rag_paragrafos,
    nome_colecao=nome_colecao_paragrafos,
    pasta_destino=PASTA_RAG,
)

# ==========================
# Teste com o RAG HyDE
# ==========================

logger.info("="*50 + "\nIniciando Teste com RAG HyDE\n" + "="*50)

for pergunta, resposta in zip(perguntas, respostas):
    contexto = montar_contexto_rag(pergunta=pergunta, colecao="RAG_HyDE")
    prompt_rag = montar_prompt_com_rag(pergunta, contexto)
    resposta_ia = executar_IA(prompt=prompt_rag)

    qualidade = avaliar_resposta(resposta_ia, resposta)
    qualidade_rag = avaliar_qualidade_rag(pergunta, contexto)

    print(f"PERGUNTA: {pergunta} | RESPOSTA IA (RAG HyDE): {resposta_ia} | Qualidade_resposta: {qualidade} | Qualidade_RAG: {qualidade_rag}")
    logger.info(f"PERGUNTA: {pergunta} | RESPOSTA IA (RAG HyDE): {resposta_ia} | Qualidade_resposta: {qualidade} | Qualidade_RAG: {qualidade_rag}")
