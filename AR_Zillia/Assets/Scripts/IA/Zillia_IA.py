#Zllia_IA.py script que rodará localmente
import datetime
import requests

historico_da_conversa = []

Nome = "João Marcos Bezerra do Nascimento"
Funcao = "Desenvolvedor Júnior"
Notas_sobre_funcionário = "Acesso livre ao sistema operacional e arquivos locais do servidor, incluindo pastas de projetos e arquivos de configuração. Acesso irrestrito a dados pessoais e financeiros. Acesso ilimitado a recursos de rede, com permissão para acessar a internet para fins relacionados ao trabalho, como pesquisa e comunicação profissional."

def contexto_conversa(origem: str = "chat_web",):
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

def mcp(*, route: str, pergunta: str, modelo: str = "gemma3:4b", url_base: str = "http://127.0.0.1:8000") -> str:
    route = route.strip().lower()
    if route not in ("chat", "rag", "db"):
        raise ValueError("route inválida. Use: chat, rag, db")

    url = f"{url_base.rstrip('/')}/{route}"
    r = requests.post(url, json={"pergunta": pergunta, "modelo": modelo}, timeout=180)
    r.raise_for_status()
    return str(r.json()["resposta"])

def Zillia_IA(nome_ia="Zillia_IA", prompt="Responda:'Bom dia :)'", imagem_path=None, tries=1, modelo="gemma3:4b") -> str:
    """
    Decide qual rota do MCP usar:
    - chat: papo normal
    - rag: pergunta sobre empresa/sistema (usa RAG)
    - db: perguntas que parecem consulta/relatório (futuro Consultar_Banco)
    """
    for i in range(tries):
        try:
            if imagem_path:
                raise ValueError("imagem_path ainda não integrado no MCP (precisa base64).")

            p = f"{contexto_conversa()} \nPrompt do usuário:{(prompt or '').strip()}"

            # Heurística simples (você ajusta depois):
            p_low = p.lower()

            # 1) DB: pedidos de consulta/relatório/números (indicadores típicos)
            db_keywords = (
                "sql", "select", "consulta", "consultar", "banco", "tabela", "query",
                "total", "quantos", "quantidade", "soma", "média", "media", "top", "ranking",
                "último mês", "ultimo mes", "por cliente", "por produto", "por dia"
            )
            if any(k in p_low for k in db_keywords):
                return mcp(route="db", pergunta=p, modelo=modelo)

            # 2) RAG: termos internos/empresa/projeto (indicadores)
            rag_keywords = (
                "irma", "rma", "zilia", "zilla", "zillia", "backend", "frontend",
                "servidor", "deploy", "docker", "odbc", "sql server", "vanna",
                "ollama", "chroma", "rag", "projeto", "repositorio", "github"
            )
            
            if any(k in p_low for k in rag_keywords):
                return mcp(route="rag", pergunta=p, modelo=modelo)
            
            # 3) Default: chat normal
            return mcp(route="chat", pergunta=p, modelo=modelo)

        except Exception as e:
            print(f"Erro na tentativa {i+1} de {nome_ia}: {str(e)}")
            if i == tries - 1:
                raise RuntimeError(f"Falha crítica no {nome_ia} após {tries} tentativas")

    return ""

# para testar localmente:
if __name__ == "__main__":
    while True:
        perg = input("Digite sua pergunta (ou 'sair' para encerrar): ")
        historico_da_conversa.append({"role": "Usuário", "content": perg})
        resposta_IA = Zillia_IA(prompt=perg)
        historico_da_conversa.append({"role": "Zilia_IA", "content": resposta_IA})
        print(f"Zillia_IA: {resposta_IA}\n")