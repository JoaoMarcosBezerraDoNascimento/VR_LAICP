#rag_tools.py
from pathlib import Path
from typing import List, Dict, Union
import os
import json
import subprocess
import pandas as pd
from PyPDF2 import PdfReader
import chromadb
from sentence_transformers import SentenceTransformer
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import uuid
from nltk.tokenize import sent_tokenize
from sentence_transformers import SentenceTransformer
from PyPDF2 import PdfReader
import pandas as pd
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from datetime import datetime
from reportlab.lib.styles import ParagraphStyle
from sklearn.feature_extraction.text import CountVectorizer
from nltk.corpus import stopwords as nltk_stopwords
import nltk
import re
from chromadb import PersistentClient
from sentence_transformers import SentenceTransformer
from pathlib import Path
from typing import List, Dict, Union, Any
import json
import math
import numpy as np
from .env import *

#nltk.download('stopwords', quiet=True)
#nltk.download("punkt", quiet=True)
#nltk.download("punkt_tab", quiet=True)
#nltk.download("stopwords", quiet=True)

debug_mode = 0

# ============================
# Helpers gerais
# ============================

def extrair_texto(arquivo: Path) -> str:
    sufixo = arquivo.suffix.lower()

    # TEXTOS SIMPLES
    if sufixo in {".txt", ".md", ".log"}:
        return arquivo.read_text(encoding="utf-8", errors="ignore")

    # PDF
    if sufixo == ".pdf":
        try:
            import PyPDF2  # pip install PyPDF2
        except ImportError:
            print("Aviso: PyPDF2 não instalado, ignorando PDFs.")
            return ""

        try:
            texto_paginas = []
            with arquivo.open("rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    t = page.extract_text() or ""
                    texto_paginas.append(t)
            return "\n".join(texto_paginas)
        except Exception as e:
            print(f"Erro ao ler PDF {arquivo}: {e}")
            return ""

    # JSON
    if sufixo == ".json":
        import json
        try:
            data = json.loads(arquivo.read_text(encoding="utf-8", errors="ignore"))
            # transforma em texto legível
            return json.dumps(data, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Erro ao ler JSON {arquivo}: {e}")
            return ""

    # CSV / XLSX
    if sufixo in {".csv", ".xlsx", ".xls"}:
        try:
            import pandas as pd  # pip install pandas openpyxl
        except ImportError:
            print("Aviso: pandas não instalado, ignorando CSV/XLSX.")
            return ""

        try:
            if sufixo == ".csv":
                df = pd.read_csv(arquivo)
            else:
                df = pd.read_excel(arquivo)

            # converte para um texto tipo CSV, já é bem útil para RAG
            return df.to_csv(index=False)
        except Exception as e:
            print(f"Erro ao ler tabela {arquivo}: {e}")
            return ""

    # outros formatos: por enquanto ignora
    return ""

def chunk_text(text: str, chunk_size: int, overlap: int) -> List[str]:
    """
    Chunking simples por caracteres com overlap.
    """
    text = text.strip()
    n = len(text)
    if n == 0:
        return []

    if chunk_size <= 0:
        raise ValueError("chunk_size deve ser > 0")
    if overlap < 0:
        raise ValueError("overlap não pode ser negativo")
    if overlap >= chunk_size:
        raise ValueError("overlap deve ser menor que chunk_size")

    chunks = []
    step = chunk_size - overlap
    start = 0

    while start < n:
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        if end >= n:
            break
        start += step

    return chunks

# ============================
# RAG 1 – chunking por caracteres
# ============================

def criar_rag_chunking(
    pasta_data: Union[str, Path],
    chunk_size: int = 2000,
    overlap: int = 500,
) -> List[Dict[str, str]]:
    """
    Varre a pasta `pasta_data` recursivamente, extrai texto de vários formatos
    e cria chunks para RAG por caracteres.

    Retorna uma lista de dicts:
    {
        "id": "doc_0_chunk_0",
        "source": "subpasta/arquivo.ext",
        "chunk_index": 0,
        "text": "conteúdo do chunk..."
    }
    """
    base = Path(pasta_data).resolve()
    documentos: List[Dict[str, str]] = []
    doc_counter = 0

    for arquivo in base.rglob("*"):
        if not arquivo.is_file():
            continue

        texto = extrair_texto(arquivo)
        if not texto.strip():
            continue

        chunks = chunk_text(texto, chunk_size=chunk_size, overlap=overlap)
        rel_path = arquivo.relative_to(base)

        for idx, chunk in enumerate(chunks):
            documentos.append(
                {
                    "id": f"doc_{doc_counter}_chunk_{idx}",
                    "source": str(rel_path),
                    "chunk_index": idx,
                    "text": chunk,
                }
            )

        doc_counter += 1

    return documentos

# ============================
# RAG 2 – baseado em parágrafos (\n\n)
# ============================

def criar_rag_paragrafos(pasta_data: Union[str, Path],) -> List[Dict[str, str]]:
    """
    Varre a pasta `pasta_data` recursivamente, extrai texto e
    separa em parágrafos usando '\n\n' como delimitador.

    Retorna uma lista de dicts:
    {
        "id": "para_0_p_0",
        "source": "subpasta/arquivo.ext",
        "paragraph_index": 0,
        "text": "parágrafo..."
    }
    """
    base = Path(pasta_data).resolve()
    documentos: List[Dict[str, str]] = []
    doc_counter = 0

    for arquivo in base.rglob("*"):
        if not arquivo.is_file():
            continue

        texto = extrair_texto(arquivo)
        if not texto.strip():
            continue

        # normaliza quebras de linha
        texto_norm = texto.replace("\r\n", "\n").replace("\r", "\n")

        # quebra por parágrafos usando linha em branco como separador
        paragrafos = [p.strip() for p in texto_norm.split("\n\n") if p.strip()]

        if not paragrafos:
            continue

        rel_path = arquivo.relative_to(base)

        for idx, p in enumerate(paragrafos):
            documentos.append(
                {
                    "id": f"para_{doc_counter}_p_{idx}",
                    "source": str(rel_path),
                    "paragraph_index": idx,
                    "text": p,
                }
            )

        doc_counter += 1

    return documentos

# ============================
# Salvamento
# ============================

def salvar_rag(
    documentos: List[Dict[str, str]],
    nome_colecao: str,
    pasta_destino: Union[str, Path],
) -> Path:
    """
    Salva a lista de documentos do RAG em um arquivo .jsonl dentro da pasta_destino.
    Cada linha é um JSON com os campos do documento.
    """
    pasta_destino = Path(pasta_destino)
    pasta_destino.mkdir(parents=True, exist_ok=True)

    caminho_arquivo = pasta_destino / f"{nome_colecao}.jsonl"

    with caminho_arquivo.open("w", encoding="utf-8") as f:
        for doc in documentos:
            f.write(json.dumps(doc, ensure_ascii=False) + "\n")

    print(f"RAG salvo em: {caminho_arquivo.resolve()}")
    print(f"Total de registros: {len(documentos)}")
    return caminho_arquivo

# ============================
# Consultamento do RAG
# ============================

# ============================
# Carregamento de coleção
# ============================

def carregar_colecao(nome_colecao: str) -> List[Dict[str, Any]]:
    """
    Lê um arquivo .jsonl em PASTA_RAG e retorna uma lista de documentos.
    Cada linha do .jsonl precisa ser um JSON com pelo menos o campo "text".
    """
    caminho = Path(PASTA_RAG) / f"{nome_colecao}.jsonl"

    if not caminho.exists():
        raise FileNotFoundError(f"Coleção '{nome_colecao}' não encontrada em {caminho}")

    docs: List[Dict[str, Any]] = []
    with caminho.open("r", encoding="utf-8") as f:
        for linha in f:
            linha = linha.strip()
            if not linha:
                continue
            docs.append(json.loads(linha))

    return docs

# ============================
# Consulta lexical simples
# ============================

def _tokenizar(texto: str) -> List[str]:
    return texto.lower().split()

def consulta_lexical(
    consulta: str,
    colecao: str = "rag_simples",
    k: int = 5,
) -> List[Dict[str, Any]]:
    """
    Busca lexical simples por overlap de tokens (bag-of-words bem básico).
    Retorna os k documentos mais relevantes.
    """
    docs = carregar_colecao(colecao)
    if not docs:
        return []

    q_tokens = set(_tokenizar(consulta))

    def score(doc: Dict[str, Any]) -> float:
        d_tokens = set(_tokenizar(doc.get("text", "")))
        if not d_tokens:
            return 0.0
        inter = q_tokens.intersection(d_tokens)
        return len(inter) / math.sqrt(len(d_tokens) + 1e-9)

    scored = []
    for d in docs:
        s = score(d)
        if s > 0:
            d_copy = dict(d)
            d_copy["score"] = float(s)
            scored.append(d_copy)

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:k]

# ============================
# Consulta exata (substring)
# ============================

def consulta_exata(
    consulta: str,
    colecao: str = "rag_simples",
    k: int = 5,
) -> List[Dict[str, Any]]:
    """
    Busca exata: retorna docs onde a string de consulta aparece no texto.
    Ordena por comprimento do texto (menor primeiro).
    """
    docs = carregar_colecao(colecao)
    if not docs:
        return []

    consulta_low = consulta.lower()
    resultados = []

    for d in docs:
        texto = d.get("text", "")
        texto_low = texto.lower()
        if consulta_low in texto_low:
            d_copy = dict(d)
            d_copy["score"] = len(texto)  # menor texto = melhor
            resultados.append(d_copy)

    resultados.sort(key=lambda x: x["score"])
    return resultados[:k]

# ============================
# Consulta semântica
# ============================

# Carrega o modelo de embeddings uma vez
try:
    from sentence_transformers import SentenceTransformer
    import numpy as np

    _embed_model = SentenceTransformer(modelo_embed)
except Exception as e:
    _embed_model = None
    print(f"Aviso: não foi possível carregar SentenceTransformer ({e}). "
          f"consulta_semantica e consulta_hyde não irão funcionar sem isso.")

def _embeddar_textos(textos: List[str]):
    if _embed_model is None:
        raise RuntimeError("Modelo de embeddings não carregado. Verifique sentence-transformers e modelo_embed.")
    emb = _embed_model.encode(textos, convert_to_numpy=True, normalize_embeddings=True)
    return emb

def consulta_semantica(
    consulta: str,
    colecao: str = "rag_simples",
    k: int = 5,
) -> List[Dict[str, Any]]:
    """
    Busca semântica: calcula embeddings da consulta e dos textos e usa similaridade de cosseno.
    Retorna os k mais similares.
    """
    docs = carregar_colecao(colecao)
    if not docs:
        return []

    textos = [d.get("text", "") for d in docs]
    emb_docs = _embeddar_textos(textos)
    emb_q = _embeddar_textos([consulta])[0]

    # produto interno, pois já estão normalizados => cosseno
    scores = emb_docs @ emb_q

    # pega top-k índices
    idxs = np.argsort(-scores)[:k]

    resultados: List[Dict[str, Any]] = []
    for i in idxs:
        d = dict(docs[int(i)])
        d["score"] = float(scores[int(i)])
        resultados.append(d)

    return resultados

# ============================
# HyDE (Hypothetical Document Embeddings)
# ============================

def gerar_hyde_texto(consulta: str) -> str:
    """
    Gera um texto hipotético (HyDE) a partir da consulta.
    Aqui está um placeholder simples que você pode trocar
    por uma chamada à sua IA (Ollama, etc).
    """
    # Exemplo simplificado: você pode substituir isso por uma chamada de IA
    # que gere uma "resposta possível" para a pergunta.
    return f"Resposta hipotética detalhada para a pergunta: {consulta}"

def consulta_hyde(consulta: str,colecao: str = "rag_simples",k: int = 5,) -> List[Dict[str, Any]]:
    """
    HyDE:
    1. Gera um texto hipotético para a consulta.
    2. Usa esse texto como base para a busca semântica.
    3. (Opcional) combina com a própria consulta.
    """
    docs = carregar_colecao(colecao)
    if not docs:
        return []

    textos = [d.get("text", "") for d in docs]

    # 1) texto hipotético
    hyde_txt = gerar_hyde_texto(consulta)

    # 2) embeddar docs e query+hyde
    emb_docs = _embeddar_textos(textos)
    emb_q = _embeddar_textos([consulta])[0]
    emb_hyde = _embeddar_textos([hyde_txt])[0]

    # 3) combinação: média dos embeddings (pode ajustar peso)
    emb_combinado = (emb_q + emb_hyde) / 2.0

    scores = emb_docs @ emb_combinado
    idxs = np.argsort(-scores)[:k]

    resultados: List[Dict[str, Any]] = []
    for i in idxs:
        d = dict(docs[int(i)])
        d["score"] = float(scores[int(i)])
        resultados.append(d)

    return resultados

def _similaridade_cos_normalizada(v1: np.ndarray, v2: np.ndarray) -> float:
    """
    Retorna similaridade de cosseno normalizada para [0, 1].
    Como os vetores já são normalizados em _embeddar_textos,
    o dot product já é a própria cos(theta).
    """
    cos = float(np.dot(v1, v2))
    # garante que fique no intervalo [-1, 1]
    cos = max(min(cos, 1.0), -1.0)
    # normaliza para [0, 1]
    return (cos + 1.0) / 2.0

def similaridade_textual_semantica(texto1: str, texto2: str) -> float:
    """
    Calcula a similaridade semântica entre dois textos usando o modelo de embeddings.
    Retorna valor entre 0 e 1.
    """
    if not texto1.strip() or not texto2.strip():
        return 0.0

    emb = _embeddar_textos([texto1, texto2])
    v1, v2 = emb[0], emb[1]
    return _similaridade_cos_normalizada(v1, v2)

def avaliar_qualidade_rag(
    pergunta: str,
    contexto: str,
) -> float:
    """
    Avalia a qualidade do contexto retornado pelo RAG para uma pergunta.
    Retorna nota de 0 a 1 baseada na similaridade semântica entre
    a pergunta e o contexto completo.
    """
    if not contexto.strip():
        return 0.0

    # aqui usamos o contexto inteiro; se quiser, depois podemos ajustar para
    # média ou máximo por trecho
    score = similaridade_textual_semantica(pergunta, contexto)
    return score

def avaliar_resposta(
    resposta_ia: str,
    gabarito: str,
) -> float:
    """
    Avalia a qualidade da resposta da IA em relação ao gabarito (resposta esperada).
    Retorna nota de 0 a 1 baseada na similaridade semântica entre resposta e gabarito.
    """
    if not resposta_ia.strip() or not gabarito.strip():
        return 0.0

    score = similaridade_textual_semantica(resposta_ia, gabarito)
    return score

# ============================
# Execução principal
# ============================

if __name__ == "__main__":
    print(f"Gerando RAGs a partir da pasta: {PASTA_DATA}")

#    # Você pode descomentar as seções abaixo para gerar os RAGs conforme necessário.
#    # -------- RAG 1: chunking simples por caracteres --------
#    nome_colecao_simples = "rag_simples"
#    documentos_rag_simples = criar_rag_chunking(
#        pasta_data=PASTA_DATA,
#        chunk_size=2000,
#        overlap=500,
#    )
#    salvar_rag(
#        documentos=documentos_rag_simples,
#        nome_colecao=nome_colecao_simples,
#        pasta_destino=PASTA_RAG,
#    )
#
#    # -------- RAG 2: baseado em parágrafos --------
#    nome_colecao_paragrafos = "RAG_Paragrafos"
#    documentos_rag_paragrafos = criar_rag_paragrafos(
#        pasta_data=PASTA_DATA,
#    )
#    salvar_rag(
#        documentos=documentos_rag_paragrafos,
#        nome_colecao=nome_colecao_paragrafos,
#        pasta_destino=PASTA_RAG,
#    )
#
#    print("Pronto! Dois RAGs gerados: rag_simples e RAG_Paragrafos.")
