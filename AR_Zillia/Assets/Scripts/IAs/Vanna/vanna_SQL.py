import subprocess
import requests
import json
import os

pergs = [
    "Quais tabelas existem no banco de dados?",
    "Quais colunas existem na tabela pedido?",
    "Quantos pedidos existem no total?",
    "Quantos pedidos foram feitos por mês?",
    "Qual é o faturamento total da empresa?",
    "Qual foi o faturamento por mês no último ano?",
    "Quais são os 10 produtos mais vendidos?",
    "Quais são os 10 produtos com maior faturamento?",
    "Quais categorias de produtos mais vendem em quantidade?",
    "Quais categorias geram mais faturamento?",
    "Quantos pedidos existem por status?",
    "Liste todos os pedidos com status pendente.",
    "Quais clientes fizeram mais pedidos?",
    "Quais clientes geraram maior faturamento?",
    "Qual é o valor médio por pedido?",
    "Qual é o ticket médio por cliente?",
    "Quantos itens, em média, existem por pedido?",
    "Quais produtos nunca foram vendidos?",
    "Quais pedidos tiveram desconto aplicado?",
    "Qual foi o maior pedido já realizado (valor total)?"
]

def vanna_sql_only(pergunta: str) -> str:
    """
    Recebe a pergunta e retorna SOMENTE o SQL (string).
    Baseado na sua função, mas normalizando o retorno do generate_sql().
    Totalmente autônoma.
    """
    import re

    # --- Importações do Vanna (Ollama + ChromaDB) ---
    try:
        from vanna.ollama import Ollama
        from vanna.chromadb import ChromaDB_VectorStore
    except Exception as e:
        raise RuntimeError(f"Erro importando vanna 0.x: {repr(e)}")

    DB_PATH = "vendas.db"

    class MyVanna(ChromaDB_VectorStore, Ollama):
        def __init__(self, config=None):
            ChromaDB_VectorStore.__init__(self, config=config)
            Ollama.__init__(self, config=config)

    # --- Cache ---
    if not hasattr(vanna_sql_only, "_vn"):
        vn = MyVanna(config={"model": "gemma3:4b"})
        vn.connect_to_sqlite(DB_PATH)

        df_ddl = vn.run_sql("SELECT type, sql FROM sqlite_master WHERE sql is not null")
        if hasattr(df_ddl, "columns") and "sql" in df_ddl.columns:
            for ddl in df_ddl["sql"].to_list():
                if ddl:
                    vn.train(ddl=ddl)
        vn.train(documentation=os.path.join(os.path.dirname(__file__), "treino.txt"))
        vanna_sql_only._vn = vn

    vn = vanna_sql_only._vn
    raw = vn.generate_sql(question=pergunta, allow_llm_to_see_data=True)
    return raw

if __name__ == "__main__":
    while True:
        for pergunta in pergs:
            out = vanna_sql_only(pergunta)
            print("\n Pergunta:")
            print(pergunta)
            print("\n Resultado:")
            print(out)
            print("=" * 40)
            print("=" * 40)
            print("=" * 40)
            print("=" * 40)
            print("=" * 40)

