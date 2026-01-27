import json
import logging
from http import HTTPStatus
from datetime import date
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Depends, Header, Query
from pydantic import BaseModel

# ==============================================================================
# 1. CONFIGURAÇÕES GERAIS E INICIALIZAÇÃO
# ==============================================================================

# Configuração do Logger: Tudo o que for alterado ou deletado será salvo aqui.
# IMPORTANTE PARA A EQUIPA: Se um utilizador reclamar que algo sumiu, olhem este arquivo.
logging.basicConfig(
    filename='sistema_rma.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Inicialização da API. O 'title' e 'description' aparecem na documentação automática (/docs).
app = FastAPI(
    title="Sistema de RMA API",
    description="API para gestão de peças e RMAs. Recebe requisições HTTP do Front-end e persiste em JSON.",
    version="1.0.0"
)

# Nome do arquivo que simula o nosso banco de dados.
DB_FILE = "database.json"

# Token de autenticação.
# FRONT-END: Lembrem-se de enviar este token no Header das requisições com a chave 'x-token'.
API_TOKEN = "segredo-super-seguro-123"

# ==============================================================================
# 2. SCHEMAS (MODELOS DE DADOS - PYDANTIC)
# Contratos de dados. Eles garantem que o Front-end envia os dados no formato certo.
# ==============================================================================


class PecaSchema(BaseModel):
    """Representa uma peça individual dentro de um RMA."""
    nome: str
    codigo: str
    comentario: Optional[str] = None  # Campo não obrigatório


class RmaSchema(BaseModel):
    """
    Modelo de ENTRADA (Input).
    O que a API espera receber do Front-end ao criar ou atualizar um RMA.
    Nota: Não tem 'id' nem 'data_criacao' porque a própria API gera isso.
    """
    empresa: str
    defeito_relatado: str
    pecas: List[PecaSchema] = []  # Uma lista de peças baseada no modelo acima
    status: str = "Pendente"  # Se o front-end não enviar status, assume "Pendente"


class RmaPublic(RmaSchema):
    """
    Modelo de SAÍDA (Output).
    O que a API devolve para o Front-end.
    Herda os campos do RmaSchema e adiciona os campos gerados pelo sistema.
    """
    id: int
    data_criacao: str


class RmaList(BaseModel):
    """Modelo para devolver uma lista de RMAs no formato {"rmas": [...] }"""
    rmas: List[RmaPublic]


class Message(BaseModel):
    """Modelo para respostas simples de texto (ex: sucesso, erro)."""
    message: str

# ==============================================================================
# 3. CAMADA DE PERSISTÊNCIA (BANCO DE DADOS EM JSON)
# Funções para ler e escrever no arquivo JSON.
# ==============================================================================


def read_db() -> List[dict]:
    """
    Abre o JSON e converte para lista do Python.
    Se o arquivo não existir ou estiver corrompido, devolve uma lista vazia.
    """
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_db(data: List[dict]):
    """
    Recebe a lista de dados atualizada e sobrescreve o arquivo JSON.
    'ensure_ascii=False' garante que acentos fiquem corretos (ex: ç, ã).
    """
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# ==============================================================================
# 4. CAMADA DE SEGURANÇA (AUTENTICAÇÃO)
# ==============================================================================


def get_current_user(x_token: str = Header(default=None)):
    """
    Verifica se o Front-end enviou o cabeçalho 'x-token' correto.
    Se o token estiver errado ou ausente, a API recusa a conexão imediatamente (Erro 401).
    """
    if x_token != API_TOKEN:
        raise HTTPException(
            status_code=HTTPStatus.UNAUTHORIZED,
            detail="Token de acesso inválido ou não fornecido."
        )
    return x_token

# ==============================================================================
# 5. ROTAS (ENDPOINTS - CRUD)
# Os pontos de contato onde o Front-end faz as requisições.
# ==============================================================================


@app.get("/", status_code=HTTPStatus.OK, response_model=Message)
def root():
    """Rota de teste de conexão (Health Check)."""
    return {"message": "API de RMA online! Acesse /docs para documentação."}

# [ CREATE ] - Rota para CRIAR um novo RMA


@app.post("/rmas/", status_code=HTTPStatus.CREATED, response_model=RmaPublic)
def create_rma(rma: RmaSchema, token: str = Depends(get_current_user)):
    """
    FRONT-END: Enviar um JSON no corpo da requisição seguindo o 'RmaSchema'.
    A API vai gerar o ID e a Data automaticamente.
    """
    db = read_db()

    # Lógica de Auto-incremento do ID (Pega o maior ID atual e soma 1)
    new_id = 1
    if db:
        new_id = max(item["id"] for item in db) + 1

    # Junta os dados gerados (id, data) com os dados recebidos do Front-end (model_dump)
    rma_with_id = {
        "id": new_id,
        # Pega a data de hoje no formato YYYY-MM-DD
        "data_criacao": date.today().isoformat(),
        **rma.model_dump()
    }

    # Adiciona o novo RMA à lista e salva no JSON
    db.append(rma_with_id)
    save_db(db)

    return rma_with_id

# [ READ ] - Rota para LISTAR os RMAs (Com filtros opcionais)


@app.get("/rmas/", status_code=HTTPStatus.OK, response_model=RmaList)
def read_rmas(
    empresa: Optional[str] = Query(
        None, description="Filtrar por nome da empresa"),
    data_criacao: Optional[str] = Query(
        None, description="Filtrar por data (YYYY-MM-DD)"),
    defeito: Optional[str] = Query(
        None, description="Filtrar por tipo de defeito"),
    token: str = Depends(get_current_user)
):
    """
    FRONT-END: Para filtrar, adicione na URL: /rmas/?empresa=NomeDaEmpresa
    Se não enviar filtros, devolve todos os dados.
    """
    db = read_db()
    resultado = db

    # Aplicação dos filtros em cascata (ignora maiúsculas e minúsculas com .lower())
    if empresa:
        resultado = [r for r in resultado if empresa.lower()
                     in r["empresa"].lower()]
    if data_criacao:
        resultado = [r for r in resultado if r["data_criacao"] == data_criacao]
    if defeito:
        resultado = [r for r in resultado if defeito.lower()
                     in r["defeito_relatado"].lower()]

    return {"rmas": resultado}

# [ READ BY ID ] - Rota para BUSCAR UM ÚNICO RMA pelo ID


@app.get("/rmas/{rma_id}", status_code=HTTPStatus.OK, response_model=RmaPublic)
def read_rma_by_id(rma_id: int, token: str = Depends(get_current_user)):
    """Busca os detalhes de um RMA específico."""
    db = read_db()
    for rma in db:
        if rma["id"] == rma_id:
            return rma

    # Se o ID não existir, devolve Erro 404
    raise HTTPException(status_code=HTTPStatus.NOT_FOUND,
                        detail="RMA não encontrado")

# [ UPDATE ] - Rota para ATUALIZAR UM RMA


@app.put("/rmas/{rma_id}", status_code=HTTPStatus.OK, response_model=RmaPublic)
def update_rma(rma_id: int, rma_atualizado: RmaSchema, token: str = Depends(get_current_user)):
    """
    FRONT-END: Envia o JSON completo com os novos dados. 
    O ID e a Data de Criação originais são mantidos pela API por segurança.
    """
    db = read_db()
    for i, item in enumerate(db):
        if item["id"] == rma_id:
            # Reconstrói o objeto mantendo ID e Data originais, substituindo o resto
            novo_item = {
                "id": rma_id,
                "data_criacao": item["data_criacao"],
                **rma_atualizado.model_dump()
            }
            db[i] = novo_item
            save_db(db)

            # Registra no log que houve uma alteração
            logging.info(f"UPDATE: RMA ID {rma_id} atualizado.")
            return novo_item

    raise HTTPException(status_code=HTTPStatus.NOT_FOUND,
                        detail="RMA não encontrado")

# [ DELETE ] - Rota para DELETAR UM RMA


@app.delete("/rmas/{rma_id}", status_code=HTTPStatus.OK, response_model=Message)
def delete_rma(rma_id: int, token: str = Depends(get_current_user)):
    """Remove o RMA do banco de dados e gera um Log de segurança."""
    db = read_db()

    # Verifica se o ID existe antes de tentar deletar
    exists = any(r["id"] == rma_id for r in db)
    if not exists:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND,
                            detail="RMA não encontrado")

    # Cria uma nova lista sem o item que queremos deletar
    novo_db = [r for r in db if r["id"] != rma_id]
    save_db(novo_db)

    # Registra no log a exclusão para auditoria
    logging.warning(f"DELETE: RMA ID {rma_id} removido do sistema.")
    return {"message": "RMA deletado com sucesso"}
