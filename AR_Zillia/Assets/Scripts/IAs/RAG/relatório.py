import re
import csv
from datetime import datetime
from pathlib import Path

# caminhos (ajuste se precisar)
LOG_FILE = Path("logs") / "Teste_varios_RAGs.txt"
CSV_FILE = Path("logs") / "relatorio_teste_rag.csv"

# regex para linha inteira: timestamp | LEVEL | msg
line_re = re.compile(
    r"^(?P<ts>\d{4}-\d{2}-\d{2} "
    r"\d{2}:\d{2}:\d{2}) \s*\|\s*"
    r"(?P<level>[A-Z]+)\s*\|\s*(?P<msg>.*)$"
)

def detect_block(msg: str):
    """
    Descobre em qual 'modo' estamos com base nas linhas:
    - Iniciando Teste sem RAG
    - Iniciando Teste com RAG Simples
    - Iniciando Teste com RAG Estratégico (Parágrafos)
    - Iniciando Teste com RAG HyDE
    """
    if "Iniciando Teste sem RAG" in msg:
        return "sem_rag"
    if "Iniciando Teste com RAG Simples" in msg:
        return "rag_simples"
    if "Iniciando Teste com RAG Estratégico (Parágrafos)" in msg:
        return "rag_paragrafos"
    if "Iniciando Teste com RAG HyDE" in msg:
        return "rag_hyde"
    return None

# regex para extrair PERGUNTA, Qualidade_resposta e (opcional) Qualidade_RAG
# Exemplo de linha:
# PERGUNTA: X | RESPOSTA IA (Sem RAG): Y | Qualidade_resposta: 0.89
# PERGUNTA: X | RESPOSTA IA: Y | Qualidade_resposta: 0.88 | Qualidade_RAG: 0.91
qa_re = re.compile(
    r"PERGUNTA:\s*(?P<pergunta>.*?)\s*\|\s*"
    r"RESPOSTA IA(?:\s*\([^)]*\))?:\s*(?P<resposta>.*?)\s*\|\s*"
    r"Qualidade_resposta:\s*(?P<qresp>[0-9.]+)"
    r"(?:\s*\|\s*Qualidade_RAG:\s*(?P<qrag>[0-9.]+))?"
)

def processar_log():
    rows = []
    current_block = None
    # armazena o último timestamp de cada bloco, para calcular deltas
    last_ts_for_block = {}

    with LOG_FILE.open("r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line:
                continue

            m = line_re.match(line)
            if not m:
                continue

            ts_str = m.group("ts")
            msg = m.group("msg")
            ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")

            # Descobre se essa linha inicia um novo bloco de teste
            new_block = detect_block(msg)
            if new_block is not None:
                current_block = new_block
                # define o último timestamp do bloco no header de início
                last_ts_for_block[current_block] = ts
                continue

            # se ainda não entrou em nenhum bloco, ignora
            if current_block is None:
                continue

            # tenta extrair PERGUNTA / qualidade
            mqa = qa_re.search(msg)
            if not mqa:
                continue  # não é linha de resultado de pergunta

            pergunta = mqa.group("pergunta").strip()
            qresp = float(mqa.group("qresp"))
            qrag_str = mqa.group("qrag")
            qrag = float(qrag_str) if qrag_str is not None else None

            # calcula tempo desde a última linha desse bloco
            prev_ts = last_ts_for_block.get(current_block)
            if prev_ts is not None:
                delta_s = (ts - prev_ts).total_seconds()
            else:
                delta_s = None  # não deve acontecer, mas deixo por segurança

            # atualiza o último timestamp do bloco
            last_ts_for_block[current_block] = ts

            # prompt_usado: com o log atual, só temos a pergunta.
            # No teste sem RAG, isso é exato. Nos RAGs é uma aproximação.
            prompt_usado = pergunta

            rows.append({
                "timestamp": ts_str,
                "tipo_teste": current_block,
                "pergunta": pergunta,
                "prompt_usado": prompt_usado,
                "tempo_entre_linhas_s": delta_s,
                "qualidade_resposta": qresp,
                "qualidade_rag": qrag,
            })

    # grava o CSV
    with CSV_FILE.open("w", newline="", encoding="utf-8") as csvfile:
        fieldnames = [
            "timestamp",
            "tipo_teste",
            "pergunta",
            "prompt_usado",
            "tempo_entre_linhas_s",
            "qualidade_resposta",
            "qualidade_rag",
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    print(f"CSV gerado em: {CSV_FILE.resolve()}")

if __name__ == "__main__":
    processar_log()
