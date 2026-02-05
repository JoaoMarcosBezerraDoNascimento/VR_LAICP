import sqlite3
import os
import subprocess
from datetime import datetime

PASTA_CODIGO = os.path.dirname(os.path.abspath(__file__))
CAMINHO_DB = os.path.join(PASTA_CODIGO, "vendas_expandido.db")
CAMINHO_REGISTRO = os.path.join(PASTA_CODIGO, "registro.txt")
CAMINHO_TREINO = os.path.join(PASTA_CODIGO, "saidas_treino_por_tabela.txt")
OLLAMA_MODEL = "llama3.1:8b"
prompt = """Você é um assistente especializado em geração de dados de treino para o Vanna AI (Natural Language to SQL).

Sua tarefa é analisar o banco de dados SQLite fornecido e produzir exemplos de treino no formato adequado para o Vanna.

Gere uma lista estruturada contendo múltiplos exemplos, onde cada exemplo deve conter:

1. Pergunta em linguagem natural (pt-BR): [pergunta do usuário]
   - Deve ser realista
   - Deve refletir perguntas que um usuário faria sobre esse banco
   - Use diferentes níveis de complexidade (simples, média, avançada)

2. Consulta SQL correspondente: [SQL]
   - Compatível com SQLite
   - Usando nomes reais das tabelas e colunas
   - Sem comandos destrutivos (DELETE, UPDATE, DROP, ALTER)

3. Intenção da pergunta: [Intenção]
   - O que o usuário quer descobrir
   - Exemplo: agregação, filtro, comparação, ranking, correlação
   - 

4. Tabelas utilizadas: [tabelas]
   - Lista explícita das tabelas envolvidas

5. Observações semânticas: [observações]
   - Regras implícitas
   - Suposições feitas com base no esquema
   - Relações inferidas entre tabelas
   - relações entre tabelas
   - Contexto adicional relevante
   - Limitações potenciais
   - Como fazer cálculos usando várias tabelas
   
Formato de saída obrigatório:
- JSON
- Cada item deve ser independente
- Não inclua explicações fora da estrutura

Regras:
- Não invente colunas ou tabelas
- Não use SELECT *
- Prefira SQL explícito e legível
- Use aliases quando necessário
- Baseie-se apenas no esquema e nos dados observados

exemplo de saída (JSON):
[
  {
    "pergunta": "Quantas vendas foram feitas no último mês?",
    "sql": "SELECT COUNT(*) FROM vendas WHERE data_venda >= date('now', '-1 month');",
    "intenção": "Contagem de vendas recentes",
    "tabelas": ["vendas"],
    "observações": "Considera apenas vendas no último mês a partir da data atual."
  },
  {
    "pergunta": "Qual é a receita total por produto no último trimestre?",
    "sql": "SELECT produto_id, SUM(valor) as receita_total FROM vendas WHERE data_venda >= date('now', '-3 months') GROUP BY produto_id;",
    "intenção": "Agregação de receita por produto",
    "tabelas": ["vendas"],
    "observações": "Agrupa vendas por produto e calcula a soma dos valores no último trimestre."
  }
]

Certifique-se de que a saída esteja correta e completa.
"""

def gerar_treinos_por_tabela_sqlite(
    caminho_db: str,
    caminho_saida_dir: str,
    ollama_model: str = "llama3.1:8b",
    rodadas_por_tabela: int = 500,
    max_linhas_amostra: int = 50,
    incluir_schema: bool = True,
    timeout_segundos: int = 300,
):
    """
    Para cada tabela do SQLite:
      - extrai schema (PRAGMA table_info)
      - extrai amostra de dados (até max_linhas_amostra)
      - envia para o Ollama em prompts separados
      - executa rodadas_por_tabela análises por tabela
      - salva respostas em arquivos por tabela dentro de caminho_saida_dir
    """
    import os
    import json
    import sqlite3
    import subprocess
    from datetime import datetime

    prompt_base = """Você é um assistente especializado em geração de dados de treino para o Vanna AI (Natural Language to SQL).

Sua tarefa é analisar o banco de dados SQLite fornecido e produzir exemplos de treino no formato adequado para o Vanna.

Gere uma lista estruturada contendo múltiplos exemplos, onde cada exemplo deve conter:

1. Pergunta em linguagem natural (pt-BR): [pergunta do usuário]
   - Deve ser realista
   - Deve refletir perguntas que um usuário faria sobre esse banco
   - Use diferentes níveis de complexidade (simples, média, avançada)

2. Consulta SQL correspondente: [SQL]
   - Compatível com SQLite
   - Usando nomes reais das tabelas e colunas
   - Sem comandos destrutivos (DELETE, UPDATE, DROP, ALTER)

3. Intenção da pergunta: [Intenção]
   - O que o usuário quer descobrir
   - Exemplo: agregação, filtro, comparação, ranking, correlação

4. Tabelas utilizadas: [tabelas]
   - Lista explícita das tabelas envolvidas

5. Observações semânticas: [observações]
   - Regras implícitas
   - Suposições feitas com base no esquema
   - Relações inferidas entre tabelas
   - Contexto adicional relevante
   - Limitações potenciais
   - Como fazer cálculos usando várias tabelas

Formato de saída obrigatório:
- JSON
- Cada item deve ser independente
- Não inclua explicações fora da estrutura

Regras:
- Não invente colunas ou tabelas
- Não use SELECT *
- Prefira SQL explícito e legível
- Use aliases quando necessário
- Baseie-se apenas no esquema e nos dados observados

Certifique-se de que a saída esteja correta e completa.
"""

    if not os.path.isfile(caminho_db):
        raise FileNotFoundError(f"Banco não encontrado: {caminho_db}")

    os.makedirs(caminho_saida_dir, exist_ok=True)

    conn = sqlite3.connect(caminho_db)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Lista tabelas (ignorando sqlite_internal)
    cur.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type='table'
          AND name NOT LIKE 'sqlite_%'
        ORDER BY name
    """)
    tabelas = [r[0] for r in cur.fetchall()]
    if not tabelas:
        conn.close()
        raise RuntimeError("Nenhuma tabela encontrada no banco.")

    # Função interna (permitida: está dentro desta função e não depende de nada externo)
    def _schema_tabela(nome_tabela: str):
        cur.execute(f'PRAGMA table_info("{nome_tabela}")')
        cols = cur.fetchall()
        # cols: cid, name, type, notnull, dflt_value, pk
        return [
            {
                "name": c["name"],
                "type": c["type"],
                "notnull": int(c["notnull"]),
                "default": c["dflt_value"],
                "pk": int(c["pk"]),
            }
            for c in cols
        ]

    def _amostra_tabela(nome_tabela: str, limit: int):
        # Evita SELECT * no texto da IA, mas para você extrair amostra é ok.
        cur.execute(f'SELECT * FROM "{nome_tabela}" LIMIT ?', (limit,))
        rows = cur.fetchall()
        # serializa linhas em dict para ficar legível no prompt
        return [dict(r) for r in rows]

    for tabela in tabelas:
        schema = _schema_tabela(tabela) if incluir_schema else []
        amostra = _amostra_tabela(tabela, max_linhas_amostra)

        contexto = {
            "arquivo_db": os.path.basename(caminho_db),
            "tabela_foco": tabela,
            "schema": schema,
            "amostra_linhas": amostra,
            "observacao": "Você DEVE gerar perguntas e SQL baseados APENAS nesta tabela_foco e seu schema/amostra. Não use outras tabelas."
        }

        arquivo_saida = os.path.join(caminho_saida_dir, f"{tabela}")

        num=1
        for i in range(rodadas_por_tabela):
            print(num)
            num+=1
            data_hora_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            prompt_completo = (
                f"Data e hora atual: {data_hora_atual}\n"
                f"CONTEXTO (JSON):\n{json.dumps(contexto, ensure_ascii=False, indent=2)}\n\n"
                f"{prompt_base}"
            )

            p = subprocess.run(
                ["ollama", "run", ollama_model],
                input=prompt_completo,
                text=True,
                capture_output=True,
                encoding="utf-8",
                errors="ignore",
                timeout=timeout_segundos,
            )

            saida = p.stdout.strip()
            print(saida)
            erro = p.stderr.strip()

            with open(arquivo_saida, "a", encoding="utf-8") as f:
                f.write(f"\n\n=== TABELA: {tabela} | RODADA {i+1}/{rodadas_por_tabela} ===\n")
                if erro:
                    f.write(f"[stderr]\n{erro}\n")
                f.write(saida + "\n")

    conn.close()

gerar_treinos_por_tabela_sqlite(
    caminho_db=CAMINHO_DB,
    caminho_saida_dir=CAMINHO_TREINO,
    ollama_model="llama3.1:8b",
    rodadas_por_tabela=500,
    max_linhas_amostra=1000
)
