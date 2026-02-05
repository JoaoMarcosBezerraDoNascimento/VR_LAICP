import os
LOCAL_PATH = os.path.dirname(os.path.abspath(__file__))

def gerar_inferencias_db_para_txt(
    db_path: str = os.path.join(LOCAL_PATH, "vendas.db"),
    out_txt_path: str = os.path.join(LOCAL_PATH, "inferencias_db.txt"),
    ollama_model: str = "llama3.1:8b",
    sample_rows: int = 50,
    max_text_len: int = 2000,
    timeout_sec: int = 600,
) -> str:
    """
    1) Lê o schema do SQLite + contagens + amostras pequenas (sem dump completo).
    2) Chama o Ollama para inferir: visão geral, relações, dicionário de dados, métricas comuns e joins recomendados.
    3) Salva tudo em um .txt pronto para ser usado como "documentação" no Vanna.
    Retorna o caminho do arquivo gerado.
    """
    import os
    import sqlite3
    import subprocess
    import textwrap
    from datetime import datetime

    def trunc(v: object) -> str:
        s = "" if v is None else str(v)
        s = s.replace("\n", "\\n").replace("\r", "\\r")
        if len(s) > max_text_len:
            return s[:max_text_len] + "…"
        return s

    def gerar_resumo_banco_sqlite_interno() -> str:
        partes = []
        partes.append(f"DB: {db_path}")
        partes.append(f"Existe: {os.path.exists(db_path)}")
        if not os.path.exists(db_path):
            return "\n".join(partes)

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """)
        tabelas = [r["name"] for r in cur.fetchall()]
        partes.append(f"Tabelas ({len(tabelas)}): {tabelas}")

        for t in tabelas:
            partes.append(f"\n=== TABELA: {t} ===")

            # DDL
            try:
                cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name = ?", (t,))
                ddl = (cur.fetchone() or {}).get("sql")
                if ddl:
                    partes.append("DDL: " + " ".join(str(ddl).split()))
            except Exception:
                pass

            # Colunas
            cur.execute(f"PRAGMA table_info({t})")
            cols = cur.fetchall()
            col_desc = []
            for c in cols:
                col_desc.append(
                    f"{c['name']} {c['type']}"
                    f"{' NOT NULL' if c['notnull'] else ''}"
                    f"{' PK' if c['pk'] else ''}"
                    f"{(' DEFAULT ' + str(c['dflt_value'])) if c['dflt_value'] is not None else ''}"
                )
            partes.append("COLUNAS: " + " | ".join(col_desc))

            # FKs
            cur.execute(f"PRAGMA foreign_key_list({t})")
            fks = cur.fetchall()
            if fks:
                fk_desc = []
                for fk in fks:
                    fk_desc.append(f"{fk['from']} -> {fk['table']}.{fk['to']}")
                partes.append("FOREIGN KEYS: " + " | ".join(fk_desc))
            else:
                partes.append("FOREIGN KEYS: (nenhuma)")

            # Índices
            cur.execute(f"PRAGMA index_list({t})")
            idxs = cur.fetchall()
            if idxs:
                idx_desc = []
                for idx in idxs:
                    idx_name = idx["name"]
                    cur.execute(f"PRAGMA index_info({idx_name})")
                    idx_cols = [r["name"] for r in cur.fetchall()]
                    idx_desc.append(f"{idx_name}({', '.join(idx_cols)})")
                partes.append("INDICES: " + " | ".join(idx_desc))
            else:
                partes.append("INDICES: (nenhum)")

            # Contagem
            try:
                cur.execute(f"SELECT COUNT(*) AS n FROM {t}")
                n = cur.fetchone()["n"]
            except Exception:
                n = "desconhecido"
            partes.append(f"LINHAS: {n}")

            # Amostra
            try:
                cur.execute(f"SELECT * FROM {t} LIMIT {int(sample_rows)}")
                rows = cur.fetchall()
                if rows:
                    header = rows[0].keys()
                    partes.append("AMOSTRA:")
                    partes.append(" | ".join(header))
                    for r in rows:
                        partes.append(" | ".join(trunc(r[h]) for h in header))
                else:
                    partes.append("AMOSTRA: (vazia)")
            except Exception as e:
                partes.append(f"AMOSTRA: erro ao ler ({e})")

        conn.close()
        return "\n".join(partes)

    def run_ollama(prompt: str) -> str:
        print(prompt)
        p = subprocess.run(
            ["ollama", "run", ollama_model],
            input=prompt,
            text=True,
            capture_output=True,
            encoding="utf-8",
            errors="ignore",
            timeout=timeout_sec,
        )
        out = (p.stdout or "").strip()
        err = (p.stderr or "").strip()
        if not out and err:
            out = f"[ERRO ollama]\n{err}"
        return out

    resumo = gerar_resumo_banco_sqlite_interno()

    prompt_master = f"""
Você é um especialista em modelagem de dados e SQL (SQLite).
Considere SOMENTE o conteúdo entre <DB> e </DB>.
NÃO invente tabelas/colunas. Se algo não estiver no <DB>, diga "não identificado".

<DB>
{resumo}
</DB>

Tarefa:
Gerar frases de documentação semântica para treinar um modelo de NL→SQL.

Regras obrigatórias:
- Use SOMENTE informações presentes no DDL.
- NÃO invente colunas, tabelas ou significados.
- Gere uma frase por tabela.
- Gere frases adicionais apenas para relacionamentos explícitos (FOREIGN KEY).
- Seja direto, técnico e objetivo.
- Não explique o que está fazendo.
- Faça pelo menos 30 frases sobre o banco de dados.

Formato de saída:
Uma lista de frases, cada frase em uma linha, em português.

Exemplo de estilo (não copiar conteúdo):
"A tabela 'exemplo' contém informações sobre ..."

""".strip()

    inferencias = run_ollama(prompt_master)

    # Monta TXT final
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conteudo = []
    conteudo.append(f"ARQUIVO: {out_txt_path}")
    conteudo.append(f"GERADO_EM: {agora}")
    conteudo.append(f"DB_PATH: {db_path}")
    conteudo.append(f"MODEL: {ollama_model}")
    conteudo.append("\n" + "=" * 80 + "\n")
    conteudo.append("## RESUMO_DO_SCHEMA (AUTO)\n")
    conteudo.append(resumo)
    conteudo.append("\n" + "=" * 80 + "\n")
    conteudo.append("## INFERENCIAS_DA_IA\n")
    conteudo.append(inferencias)
    conteudo.append("\n")

    os.makedirs(os.path.dirname(out_txt_path), exist_ok=True)
    with open(out_txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(conteudo))

    return out_txt_path

if __name__ == "__main__":
    caminho = gerar_inferencias_db_para_txt(
        ollama_model="llama3.1:8b",
        sample_rows=50,
        max_text_len=2000,
        timeout_sec=600,
    )
    print(caminho)
