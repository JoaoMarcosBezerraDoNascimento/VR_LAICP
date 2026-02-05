import os

PASTA_CODIGO = os.path.dirname(os.path.abspath(__file__))

def separar_json_e_sql(
    arquivo_entrada="registro.txt",
    arquivo_json_saida="registro_json.txt",
    arquivo_sql_saida="registro_SQL.txt",
    encoding="utf-8",
):
    import os
    import re
    import json

    # Regex para identificar início de SQL em linha solta
    sql_start_re = re.compile(
        r"^\s*(SELECT|WITH|INSERT|UPDATE|DELETE|CREATE|DROP|ALTER|PRAGMA)\b",
        re.IGNORECASE,
    )

    # Detecta se um texto "parece" JSON (heurística simples)
    def parece_json(texto: str) -> bool:
        t = texto.lstrip()
        return t.startswith("{") or t.startswith("[")

    # Extrai SQL(s) do JSON (se conseguir parsear)
    def extrair_sql_de_json(texto_json: str):
        encontrados = []
        try:
            obj = json.loads(texto_json)
        except Exception:
            return encontrados

        def walk(x):
            if isinstance(x, dict):
                for k, v in x.items():
                    if isinstance(k, str) and k.lower() == "sql" and isinstance(v, str):
                        encontrados.append(v)
                    else:
                        walk(v)
            elif isinstance(x, list):
                for item in x:
                    walk(item)

        walk(obj)
        return encontrados

    # Sanitiza nome de arquivo em caminho absoluto relativo ao script (se quiser)
    in_path = os.path.abspath(arquivo_entrada)
    out_json_path = os.path.abspath(arquivo_json_saida)
    out_sql_path = os.path.abspath(arquivo_sql_saida)

    # Estados de captura
    in_fence = False
    fence_lang = ""        # "json", "sql", "" (desconhecido)
    fence_lines = []

    # Para juntar SQL de várias linhas fora de fence (até ; ou linha vazia)
    in_sql_multiline = False
    sql_lines = []

    with open(in_path, "r", encoding=encoding, errors="replace") as fin, \
         open(out_json_path, "w", encoding=encoding, errors="replace") as fout_json, \
         open(out_sql_path, "w", encoding=encoding, errors="replace") as fout_sql:

        def flush_fence():
            nonlocal fence_lines, fence_lang

            bloco = "".join(fence_lines).strip("\n")
            if not bloco.strip():
                fence_lines = []
                fence_lang = ""
                return

            # Decide destino: json ou sql
            if fence_lang == "sql":
                fout_sql.write(bloco.strip() + "\n\n")
            elif fence_lang == "json":
                fout_json.write(bloco.strip() + "\n\n")
                # Tenta extrair SQL dentro do JSON para o arquivo SQL também
                for s in extrair_sql_de_json(bloco):
                    s2 = s.strip()
                    if s2:
                        fout_sql.write(s2 + ("\n" if s2.endswith(";") else ";\n") + "\n")
            else:
                # Fence sem linguagem: decide pelo conteúdo
                if parece_json(bloco):
                    fout_json.write(bloco.strip() + "\n\n")
                    for s in extrair_sql_de_json(bloco):
                        s2 = s.strip()
                        if s2:
                            fout_sql.write(s2 + ("\n" if s2.endswith(";") else ";\n") + "\n")
                elif sql_start_re.match(bloco):
                    fout_sql.write(bloco.strip() + "\n\n")

            fence_lines = []
            fence_lang = ""

        def flush_sql_multiline():
            nonlocal in_sql_multiline, sql_lines
            if not sql_lines:
                in_sql_multiline = False
                return
            bloco = "".join(sql_lines).strip()
            if bloco:
                # garante ; no final (opcional, mas ajuda)
                if not bloco.rstrip().endswith(";"):
                    bloco = bloco.rstrip() + ";"
                fout_sql.write(bloco + "\n\n")
            sql_lines = []
            in_sql_multiline = False

        for line in fin:
            # Detecta fence ```...
            fence_open = re.match(r"^\s*```(\w+)?\s*$", line)
            if fence_open:
                if not in_fence:
                    # abre fence
                    in_fence = True
                    fence_lang = (fence_open.group(1) or "").strip().lower()
                    fence_lines = []
                    # Se estava capturando SQL multiline solto, fecha
                    flush_sql_multiline()
                else:
                    # fecha fence
                    in_fence = False
                    flush_fence()
                continue

            if in_fence:
                fence_lines.append(line)
                continue

            # Fora de fence: captura SQL multiline se começou
            if in_sql_multiline:
                # Critérios de parada: linha vazia (se já tem algo) ou fim com ;
                if line.strip() == "" and sql_lines:
                    flush_sql_multiline()
                    continue
                sql_lines.append(line)
                if ";" in line:
                    flush_sql_multiline()
                continue

            # Começa SQL multiline se a linha parece SQL
            if sql_start_re.match(line):
                in_sql_multiline = True
                sql_lines = [line]
                if ";" in line:
                    flush_sql_multiline()
                continue

            # Extrai SQL inline do tipo: "sql": "...."
            # (funciona mesmo fora de blocos JSON, mas pode falhar com aspas escapadas complexas)
            m = re.search(r'"sql"\s*:\s*"([^"]+)"', line, flags=re.IGNORECASE)
            if m:
                s = m.group(1).strip()
                if s:
                    if not s.endswith(";"):
                        s += ";"
                    fout_sql.write(s + "\n\n")

        # flush final
        if in_fence:
            # fence não fechado: ainda tenta salvar o que tiver
            flush_fence()
        flush_sql_multiline()

def expandir_sqlite(
    db_path="vendas.db",
    num_tabelas_extras=200,
    linhas_por_tabela=5000,
    seed=42,
):
    import sqlite3
    import random
    import string
    from datetime import datetime, timedelta

    random.seed(seed)

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    cur = conn.cursor()

    # --- Descobre tabelas existentes (exceto internas) ---
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    existentes = [r[0] for r in cur.fetchall()]

    # --- Cria tabelas base se não existirem (para garantir um núcleo rico) ---
    # Observação: seu banco já tem categoria/produto/venda. Aqui só garante.
    cur.execute("""
    CREATE TABLE IF NOT EXISTS categoria (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL UNIQUE
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS produto (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        preco REAL NOT NULL,
        categoria_id INTEGER NOT NULL,
        FOREIGN KEY (categoria_id) REFERENCES categoria(id)
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS venda (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        produto_id INTEGER NOT NULL,
        quantidade INTEGER NOT NULL,
        data TEXT NOT NULL,
        FOREIGN KEY (produto_id) REFERENCES produto(id)
    )
    """)
    conn.commit()

    # --- Funções internas (mantidas dentro para ser 100% autônomo) ---
    def rand_str(n=10):
        return "".join(random.choices(string.ascii_letters + string.digits, k=n))

    def rand_date(start_days_ago=900, end_days_ago=0):
        base = datetime.now() - timedelta(days=start_days_ago)
        delta = (start_days_ago - end_days_ago)
        d = base + timedelta(days=random.randint(0, max(0, delta)))
        return d.strftime("%Y-%m-%d")

    # --- Garante que existam categorias/produtos/vendas suficientes ---
    cur.execute("SELECT COUNT(*) FROM categoria")
    if cur.fetchone()[0] < 50:
        nomes = ["Roupas", "Eletrônicos", "Eletrodomésticos", "Calçados", "Livros"]
        # completa até 50
        while len(nomes) < 50:
            nomes.append("Cat_" + rand_str(8))
        cur.executemany("INSERT OR IGNORE INTO categoria(nome) VALUES (?)", [(n,) for n in nomes])

    cur.execute("SELECT id FROM categoria")
    cat_ids = [r[0] for r in cur.fetchall()]

    cur.execute("SELECT COUNT(*) FROM produto")
    if cur.fetchone()[0] < 5000:
        faltam = 5000
        batch = []
        for _ in range(faltam):
            batch.append((
                "Prod_" + rand_str(10),
                round(random.uniform(5.0, 15000.0), 2),
                random.choice(cat_ids),
            ))
            if len(batch) >= 1000:
                cur.executemany("INSERT INTO produto(nome,preco,categoria_id) VALUES (?,?,?)", batch)
                batch = []
        if batch:
            cur.executemany("INSERT INTO produto(nome,preco,categoria_id) VALUES (?,?,?)", batch)

    cur.execute("SELECT id, preco FROM produto")
    produtos = cur.fetchall()
    prod_ids = [p[0] for p in produtos]

    cur.execute("SELECT COUNT(*) FROM venda")
    if cur.fetchone()[0] < 20000:
        faltam = 20000
        batch = []
        for _ in range(faltam):
            pid = random.choice(prod_ids)
            r = random.random()
            if r < 0.6:          
                qtd = random.randint(500, 5000)
            elif r < 0.9:        
                qtd = random.randint(50, 500)
            else:                
                qtd = random.randint(5, 50)
            data = rand_date(365, 0)
            batch.append((pid, qtd, data))
            if len(batch) >= 2000:
                cur.executemany("INSERT INTO venda(produto_id,quantidade,data) VALUES (?,?,?)", batch)
                batch = []
        if batch:
            cur.executemany("INSERT INTO venda(produto_id,quantidade,data) VALUES (?,?,?)", batch)

    conn.commit()

    # --- Cria tabelas extras: dimensões, fatos, ponte e satélites ---
    # Vamos criar num_tabelas_extras tabelas, metade "dim_*" e metade "fact_*"
    # Além disso, para cada fact, criamos 1 ponte N:N e 1 satélite.
    # Cada tabela terá ~linhas_por_tabela linhas (facts podem ser mais densas).

    # Para garantir nomes únicos:
    def table_exists(nome):
        cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (nome,))
        return cur.fetchone() is not None

    created = 0
    dim_count = num_tabelas_extras // 2
    fact_count = num_tabelas_extras - dim_count

    # Cria dimensões
    for i in range(1, dim_count + 1):
        t = f"dim_{i:03d}"
        if table_exists(t):
            continue
        cur.execute(f"""
        CREATE TABLE {t} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            codigo TEXT NOT NULL UNIQUE,
            ativo INTEGER NOT NULL,
            criado_em TEXT NOT NULL
        )
        """)
        cur.execute(f"CREATE INDEX idx_{t}_ativo ON {t}(ativo)")
        cur.execute(f"CREATE INDEX idx_{t}_criado_em ON {t}(criado_em)")
        created += 1

    conn.commit()

    # Preenche dimensões
    for i in range(1, dim_count + 1):
        t = f"dim_{i:03d}"
        cur.execute(f"SELECT COUNT(*) FROM {t}")
        if cur.fetchone()[0] >= linhas_por_tabela:
            continue
        faltam = linhas_por_tabela
        batch = []
        for _ in range(faltam):
            batch.append((
                f"Nome_{rand_str(12)}",
                f"C{rand_str(14)}",
                1 if random.random() < 0.85 else 0,
                rand_date(1200, 0),
            ))
            if len(batch) >= 2000:
                cur.executemany(f"INSERT INTO {t}(nome,codigo,ativo,criado_em) VALUES (?,?,?,?)", batch)
                batch = []
        if batch:
            cur.executemany(f"INSERT INTO {t}(nome,codigo,ativo,criado_em) VALUES (?,?,?,?)", batch)

    conn.commit()

    # Lista ids das dimensões para FKs
    dim_ids = {}
    for i in range(1, dim_count + 1):
        t = f"dim_{i:03d}"
        cur.execute(f"SELECT id FROM {t} LIMIT 10000")
        dim_ids[t] = [r[0] for r in cur.fetchall()]  # amostra grande o suficiente

    # Cria e preenche facts
    for i in range(1, fact_count + 1):
        fact = f"fact_{i:03d}"
        sat = f"{fact}_sat"
        bridge = f"{fact}_bridge"

        # escolhe 3 dimensões para relacionar
        dims = random.sample([f"dim_{j:03d}" for j in range(1, dim_count + 1)], k=3)

        if not table_exists(fact):
            cur.execute(f"""
            CREATE TABLE {fact} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dim_a_id INTEGER NOT NULL,
                dim_b_id INTEGER NOT NULL,
                dim_c_id INTEGER NOT NULL,
                produto_id INTEGER NOT NULL,
                quantidade INTEGER NOT NULL,
                valor_unit REAL NOT NULL,
                data TEXT NOT NULL,
                status TEXT NOT NULL,
                FOREIGN KEY (dim_a_id) REFERENCES {dims[0]}(id),
                FOREIGN KEY (dim_b_id) REFERENCES {dims[1]}(id),
                FOREIGN KEY (dim_c_id) REFERENCES {dims[2]}(id),
                FOREIGN KEY (produto_id) REFERENCES produto(id)
            )
            """)
            cur.execute(f"CREATE INDEX idx_{fact}_data ON {fact}(data)")
            cur.execute(f"CREATE INDEX idx_{fact}_produto ON {fact}(produto_id)")
            cur.execute(f"CREATE INDEX idx_{fact}_dims ON {fact}(dim_a_id, dim_b_id, dim_c_id)")
            created += 1

        if not table_exists(sat):
            cur.execute(f"""
            CREATE TABLE {sat} (
                fact_id INTEGER PRIMARY KEY,
                observacao TEXT,
                origem TEXT,
                atualizado_em TEXT NOT NULL,
                FOREIGN KEY (fact_id) REFERENCES {fact}(id)
            )
            """)
            created += 1

        if not table_exists(bridge):
            # ponte N:N entre fact e venda (exemplo)
            cur.execute(f"""
            CREATE TABLE {bridge} (
                fact_id INTEGER NOT NULL,
                venda_id INTEGER NOT NULL,
                peso REAL NOT NULL,
                PRIMARY KEY (fact_id, venda_id),
                FOREIGN KEY (fact_id) REFERENCES {fact}(id),
                FOREIGN KEY (venda_id) REFERENCES venda(id)
            )
            """)
            cur.execute(f"CREATE INDEX idx_{bridge}_venda ON {bridge}(venda_id)")
            created += 1

        conn.commit()

        # Preenche fact
        cur.execute(f"SELECT COUNT(*) FROM {fact}")
        if cur.fetchone()[0] < linhas_por_tabela:
            faltam = linhas_por_tabela
            batch = []
            statuses = ["aberta", "paga", "cancelada", "estornada"]
            for _ in range(faltam):
                a = random.choice(dim_ids[dims[0]])
                b = random.choice(dim_ids[dims[1]])
                c = random.choice(dim_ids[dims[2]])
                pid = random.choice(prod_ids)
                qtd = random.randint(1, 15)
                valor = round(random.uniform(5.0, 15000.0), 2)
                data = rand_date(900, 0)
                st = random.choice(statuses)
                batch.append((a, b, c, pid, qtd, valor, data, st))
                if len(batch) >= 2000:
                    cur.executemany(
                        f"INSERT INTO {fact}(dim_a_id,dim_b_id,dim_c_id,produto_id,quantidade,valor_unit,data,status) "
                        f"VALUES (?,?,?,?,?,?,?,?)",
                        batch
                    )
                    batch = []
            if batch:
                cur.executemany(
                    f"INSERT INTO {fact}(dim_a_id,dim_b_id,dim_c_id,produto_id,quantidade,valor_unit,data,status) "
                    f"VALUES (?,?,?,?,?,?,?,?)",
                    batch
                )

        conn.commit()

        # Preenche satélite (1:1 com fact) para os últimos N facts inseridos
        cur.execute(f"SELECT id FROM {fact} ORDER BY id DESC LIMIT {linhas_por_tabela}")
        fact_ids = [r[0] for r in cur.fetchall()]
        cur.execute(f"SELECT COUNT(*) FROM {sat}")
        sat_count = cur.fetchone()[0]
        if sat_count < len(fact_ids):
            # insere apenas os que não existem
            batch = []
            for fid in fact_ids:
                batch.append((fid, "Obs_" + rand_str(30), "sistema_" + rand_str(6), rand_date(365, 0)))
                if len(batch) >= 2000:
                    cur.executemany(
                        f"INSERT OR IGNORE INTO {sat}(fact_id,observacao,origem,atualizado_em) VALUES (?,?,?,?)",
                        batch
                    )
                    batch = []
            if batch:
                cur.executemany(
                    f"INSERT OR IGNORE INTO {sat}(fact_id,observacao,origem,atualizado_em) VALUES (?,?,?,?)",
                    batch
                )

        conn.commit()

        # Preenche ponte fact<->venda
        cur.execute("SELECT id FROM venda ORDER BY id DESC LIMIT 50000")
        venda_ids = [r[0] for r in cur.fetchall()]
        cur.execute(f"SELECT COUNT(*) FROM {bridge}")
        if cur.fetchone()[0] < linhas_por_tabela:
            batch = []
            # cria ~1 ligação por fact (pode aumentar para mais densidade)
            for fid in fact_ids[:min(linhas_por_tabela, len(fact_ids))]:
                vid = random.choice(venda_ids)
                peso = round(random.random(), 4)
                batch.append((fid, vid, peso))
                if len(batch) >= 4000:
                    cur.executemany(
                        f"INSERT OR IGNORE INTO {bridge}(fact_id,venda_id,peso) VALUES (?,?,?)",
                        batch
                    )
                    batch = []
            if batch:
                cur.executemany(
                    f"INSERT OR IGNORE INTO {bridge}(fact_id,venda_id,peso) VALUES (?,?,?)",
                    batch
                )

        conn.commit()

    # --- Resultado final: contagem de tabelas/linhas ---
    cur.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    total_tabelas = cur.fetchone()[0]

    conn.close()

    return {
        "db_path": db_path,
        "tabelas_existentes_iniciais": existentes,
        "tabelas_criadas_ou_garantidas": created,
        "total_tabelas_agora": total_tabelas,
        "linhas_por_tabela_config": linhas_por_tabela,
        "num_tabelas_extras_config": num_tabelas_extras,
    }

def expandir_sqlite_com_nomes_reais(
    db_path="vendas.db",
    seed=42,
    num_marcas=40,
    num_fornecedores=80,
    num_clientes=5000,
    num_produtos=20000,
    num_pedidos=60000,
    max_itens_por_pedido=1000,
    reset_db=False,
):
    import os
    import sqlite3
    import random
    from datetime import datetime, timedelta

    random.seed(seed)

    # 1) RESET opcional: cria banco do zero
    if reset_db and os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    cur = conn.cursor()

    # Helpers internos
    def table_exists(nome):
        cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (nome,))
        return cur.fetchone() is not None

    def colunas_da_tabela(nome):
        cur.execute(f"PRAGMA table_info({nome})")
        return [r[1] for r in cur.fetchall()]  # name

    def rand_date(dias_atras_ini=900, dias_atras_fim=0):
        hoje = datetime.now()
        ini = hoje - timedelta(days=dias_atras_ini)
        delta = dias_atras_ini - dias_atras_fim
        d = ini + timedelta(days=random.randint(0, max(0, delta)))
        return d.strftime("%Y-%m-%d")

    def gen_cnpj_unico(i):
        base = f"{i:012d}"
        return f"{base[0:2]}.{base[2:5]}.{base[5:8]}/{base[8:12]}-00"

    def pick(lst):
        return lst[random.randint(0, len(lst) - 1)]

    def sku(i):
        return f"SKU-{i:08d}"

    # 2) Esquema base (sem assumir que produto já está correto)
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS categoria (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL UNIQUE
    );

    CREATE TABLE IF NOT EXISTS subcategoria (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        categoria_id INTEGER NOT NULL,
        nome TEXT NOT NULL,
        UNIQUE (categoria_id, nome),
        FOREIGN KEY (categoria_id) REFERENCES categoria(id)
    );

    CREATE TABLE IF NOT EXISTS marca (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL UNIQUE
    );

    CREATE TABLE IF NOT EXISTS fornecedor (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        cnpj TEXT NOT NULL UNIQUE,
        cidade TEXT NOT NULL,
        uf TEXT NOT NULL
    );
    """)
    conn.commit()

    # 3) MIGRAÇÃO: se produto existe mas não tem subcategoria_id, recria e migra
    if table_exists("produto"):
        cols = colunas_da_tabela("produto")
        if "subcategoria_id" not in cols:
            # Garante subcategoria "Geral" para cada categoria existente
            cur.execute("SELECT id, nome FROM categoria")
            cats = cur.fetchall()
            for cid, _ in cats:
                cur.execute(
                    "INSERT OR IGNORE INTO subcategoria(categoria_id, nome) VALUES (?, ?)",
                    (cid, "Geral")
                )
            conn.commit()

            # Marca/Fornecedor padrões para preencher NOT NULL
            cur.execute("INSERT OR IGNORE INTO marca(nome) VALUES (?)", ("Sem Marca",))
            cur.execute("SELECT id FROM marca WHERE nome=?", ("Sem Marca",))
            marca_padrao_id = cur.fetchone()[0]

            cur.execute("""
                INSERT OR IGNORE INTO fornecedor(nome, cnpj, cidade, uf)
                VALUES (?, ?, ?, ?)
            """, ("Fornecedor Padrão", "00.000.000/0000-00", "São Paulo", "SP"))
            conn.commit()
            cur.execute("SELECT id FROM fornecedor WHERE cnpj=?", ("00.000.000/0000-00",))
            fornecedor_padrao_id = cur.fetchone()[0]

            # Mapa categoria_id -> subcategoria_id ("Geral")
            cur.execute("""
                SELECT c.id, s.id
                FROM categoria c
                JOIN subcategoria s ON s.categoria_id = c.id AND s.nome = 'Geral'
            """)
            map_cat_sub = {cid: sid for cid, sid in cur.fetchall()}

            # Renomeia produto antigo e cria novo produto
            cur.execute("ALTER TABLE produto RENAME TO produto_old")
            conn.commit()

            cur.executescript("""
            CREATE TABLE produto (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                preco REAL NOT NULL,
                categoria_id INTEGER NOT NULL,
                subcategoria_id INTEGER NOT NULL,
                marca_id INTEGER NOT NULL,
                fornecedor_id INTEGER NOT NULL,
                sku TEXT NOT NULL UNIQUE,
                FOREIGN KEY (categoria_id) REFERENCES categoria(id),
                FOREIGN KEY (subcategoria_id) REFERENCES subcategoria(id),
                FOREIGN KEY (marca_id) REFERENCES marca(id),
                FOREIGN KEY (fornecedor_id) REFERENCES fornecedor(id)
            );
            """)
            conn.commit()

            # Copia dados antigos para novo produto (gera sku e preenche defaults)
            cur.execute("SELECT id, nome, preco, categoria_id FROM produto_old")
            antigos = cur.fetchall()

            batch = []
            for pid, nome, preco, categoria_id in antigos:
                sub_id = map_cat_sub.get(categoria_id)
                if sub_id is None:
                    # se existir produto com categoria_id inválido, cria uma categoria fallback
                    cur.execute("INSERT OR IGNORE INTO categoria(nome) VALUES (?)", ("Geral",))
                    conn.commit()
                    cur.execute("SELECT id FROM categoria WHERE nome='Geral'")
                    cat_fallback = cur.fetchone()[0]
                    cur.execute(
                        "INSERT OR IGNORE INTO subcategoria(categoria_id, nome) VALUES (?, ?)",
                        (cat_fallback, "Geral")
                    )
                    conn.commit()
                    cur.execute("""
                        SELECT id FROM subcategoria WHERE categoria_id=? AND nome='Geral'
                    """, (cat_fallback,))
                    sub_id = cur.fetchone()[0]
                    categoria_id = cat_fallback

                batch.append((
                    pid, nome, float(preco), int(categoria_id), int(sub_id),
                    int(marca_padrao_id), int(fornecedor_padrao_id),
                    f"SKU-MIG-{pid:08d}"
                ))

            cur.executemany("""
                INSERT INTO produto(id, nome, preco, categoria_id, subcategoria_id, marca_id, fornecedor_id, sku)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, batch)
            conn.commit()

            # Limpa tabela antiga
            cur.execute("DROP TABLE produto_old")
            conn.commit()

    # 4) Agora cria o restante do esquema dependente de produto (com índice correto)
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS cliente (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        cidade TEXT NOT NULL,
        uf TEXT NOT NULL,
        criado_em TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS pedido (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente_id INTEGER NOT NULL,
        data TEXT NOT NULL,
        status TEXT NOT NULL,
        canal TEXT NOT NULL,
        FOREIGN KEY (cliente_id) REFERENCES cliente(id)
    );

    CREATE TABLE IF NOT EXISTS item_pedido (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pedido_id INTEGER NOT NULL,
        produto_id INTEGER NOT NULL,
        quantidade INTEGER NOT NULL,
        preco_unit REAL NOT NULL,
        desconto REAL NOT NULL,
        FOREIGN KEY (pedido_id) REFERENCES pedido(id),
        FOREIGN KEY (produto_id) REFERENCES produto(id)
    );

    CREATE TABLE IF NOT EXISTS estoque (
        produto_id INTEGER PRIMARY KEY,
        saldo INTEGER NOT NULL,
        estoque_min INTEGER NOT NULL,
        FOREIGN KEY (produto_id) REFERENCES produto(id)
    );

    CREATE TABLE IF NOT EXISTS movimentacao_estoque (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        produto_id INTEGER NOT NULL,
        tipo TEXT NOT NULL,
        quantidade INTEGER NOT NULL,
        data TEXT NOT NULL,
        referencia TEXT,
        FOREIGN KEY (produto_id) REFERENCES produto(id)
    );

    CREATE TABLE IF NOT EXISTS avaliacao (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        produto_id INTEGER NOT NULL,
        cliente_id INTEGER NOT NULL,
        nota INTEGER NOT NULL,
        comentario TEXT,
        data TEXT NOT NULL,
        FOREIGN KEY (produto_id) REFERENCES produto(id),
        FOREIGN KEY (cliente_id) REFERENCES cliente(id)
    );
                      
    CREATE TABLE IF NOT EXISTS categoria (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL UNIQUE
    );

    CREATE TABLE IF NOT EXISTS subcategoria (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        categoria_id INTEGER NOT NULL,
        nome TEXT NOT NULL,
        UNIQUE (categoria_id, nome),
        FOREIGN KEY (categoria_id) REFERENCES categoria(id)
    );
                      
    CREATE TABLE IF NOT EXISTS marca (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL UNIQUE
    );
                                  
    CREATE TABLE IF NOT EXISTS fornecedor (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        cnpj TEXT NOT NULL UNIQUE,
        cidade TEXT NOT NULL,
        uf TEXT NOT NULL
    );
                      
    CREATE TABLE IF NOT EXISTS produto (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    preco REAL NOT NULL,
    categoria_id INTEGER NOT NULL,
    subcategoria_id INTEGER NOT NULL,
    marca_id INTEGER NOT NULL,
    fornecedor_id INTEGER NOT NULL,
    sku TEXT NOT NULL UNIQUE,
    FOREIGN KEY (categoria_id) REFERENCES categoria(id),
    FOREIGN KEY (subcategoria_id) REFERENCES subcategoria(id),
    FOREIGN KEY (marca_id) REFERENCES marca(id),
    FOREIGN KEY (fornecedor_id) REFERENCES fornecedor(id)
    );

    CREATE INDEX IF NOT EXISTS idx_produto_cat ON produto(categoria_id, subcategoria_id);
    CREATE INDEX IF NOT EXISTS idx_pedido_cliente_data ON pedido(cliente_id, data);
    CREATE INDEX IF NOT EXISTS idx_item_pedido_pedido ON item_pedido(pedido_id);
    CREATE INDEX IF NOT EXISTS idx_item_pedido_produto ON item_pedido(produto_id);
    CREATE INDEX IF NOT EXISTS idx_mov_prod_data ON movimentacao_estoque(produto_id, data);
    CREATE INDEX IF NOT EXISTS idx_av_prod_data ON avaliacao(produto_id, data);
    """)
    conn.commit()

    # ----------------------------
    # 2) Vocabulário (palavras reais)
    # ----------------------------
    categorias = {
        "Eletrônicos": [
            "TV", "Home Theater", "Fones de Ouvido", "Caixas de Som", "Smartwatch", "Câmeras"
        ],
        "Informática": [
            "Notebook", "Desktop", "Monitor", "Teclado", "Mouse", "Impressora"
        ],
        "Componentes": [
            "Memória RAM", "SSD", "HD", "Placa de Vídeo", "Processador", "Placa-mãe", "Fonte", "Cooler"
        ],
        "Redes": [
            "Roteador", "Switch", "Placa de Rede", "Repetidor", "Cabo de Rede"
        ],
        "Acessórios": [
            "Cabo HDMI", "Carregador", "Adaptador", "Hub USB", "Case", "Suporte"
        ],
    }

    marcas_reais = [
        "Samsung", "Kingston", "Corsair", "Crucial", "ADATA", "Seagate", "Western Digital",
        "Intel", "AMD", "NVIDIA", "ASUS", "Gigabyte", "MSI", "Lenovo", "Dell", "HP",
        "Logitech", "Razer", "TP-Link", "Xiaomi", "LG", "Sony", "SanDisk"
    ]

    cidades_uf = [
        ("São Paulo", "SP"), ("Campinas", "SP"), ("Rio de Janeiro", "RJ"), ("Niterói", "RJ"),
        ("Belo Horizonte", "MG"), ("Curitiba", "PR"), ("Florianópolis", "SC"),
        ("Porto Alegre", "RS"), ("Salvador", "BA"), ("Recife", "PE"), ("Fortaleza", "CE"),
        ("Brasília", "DF"), ("Goiânia", "GO"), ("Manaus", "AM"), ("Belém", "PA")
    ]

    nomes = [
        "João", "Maria", "Ana", "Pedro", "Lucas", "Mariana", "Gabriel", "Beatriz",
        "Rafael", "Larissa", "Bruno", "Carolina", "Felipe", "Juliana", "Thiago",
        "Camila", "Diego", "Amanda", "Gustavo", "Isabela"
    ]
    sobrenomes = [
        "Silva", "Santos", "Oliveira", "Souza", "Pereira", "Lima", "Ferreira", "Costa",
        "Rodrigues", "Almeida", "Nascimento", "Gomes", "Martins", "Araújo", "Ribeiro"
    ]

    # ----------------------------
    # 3) Helpers internos
    # ----------------------------
    def rand_date(dias_atras_ini=900, dias_atras_fim=0):
        hoje = datetime.now()
        ini = hoje - timedelta(days=dias_atras_ini)
        delta = dias_atras_ini - dias_atras_fim
        d = ini + timedelta(days=random.randint(0, max(0, delta)))
        return d.strftime("%Y-%m-%d")

    def gen_cnpj_unico(i):
        # CNPJ fake, mas válido no formato (não valida dígito)
        base = f"{i:012d}"
        return f"{base[0:2]}.{base[2:5]}.{base[5:8]}/{base[8:12]}-00"

    def pick(lst):
        return lst[random.randint(0, len(lst) - 1)]

    def sku(i):
        return f"SKU-{i:08d}"

    # nome de produto coerente por subcategoria
    def gerar_nome_produto(cat, sub):
        if sub == "Memória RAM":
            tipo = pick(["DDR3", "DDR4", "DDR5"])
            cap = pick(["8GB", "16GB", "32GB", "64GB"])
            freq = pick(["2666MHz", "3200MHz", "3600MHz", "5200MHz"])
            return f"Memória RAM {tipo} {cap} {freq}"
        if sub == "SSD":
            tipo = pick(["SATA", "NVMe"])
            cap = pick(["240GB", "480GB", "500GB", "1TB", "2TB", "4TB"])
            return f"SSD {tipo} {cap}"
        if sub == "HD":
            cap = pick(["1TB", "2TB", "4TB", "6TB", "8TB", "12TB"])
            rpm = pick(["5400RPM", "7200RPM"])
            return f"HD {cap} {rpm}"
        if sub == "Placa de Vídeo":
            linha = pick(["RTX", "GTX", "RX"])
            modelo = pick(["3050", "3060", "4060", "4070", "6600", "6700 XT", "7600"])
            vram = pick(["8GB", "12GB", "16GB"])
            return f"Placa de Vídeo {linha} {modelo} {vram}"
        if sub == "Processador":
            linha = pick(["Intel Core i5", "Intel Core i7", "AMD Ryzen 5", "AMD Ryzen 7"])
            ger = pick(["10ª", "11ª", "12ª", "13ª", "7000"])
            return f"Processador {linha} {ger}"
        if sub == "Placa-mãe":
            chipset = pick(["B450", "B550", "X570", "B660", "Z690", "B760"])
            socket = pick(["AM4", "AM5", "LGA1200", "LGA1700"])
            return f"Placa-mãe {chipset} {socket}"
        if sub == "Fonte":
            w = pick(["500W", "650W", "750W", "850W"])
            cert = pick(["80 Plus Bronze", "80 Plus Gold", "80 Plus Platinum"])
            return f"Fonte {w} {cert}"
        if sub == "Cooler":
            tipo = pick(["Air Cooler", "Water Cooler 120mm", "Water Cooler 240mm", "Water Cooler 360mm"])
            return f"Cooler {tipo}"
        if sub == "Roteador":
            wifi = pick(["Wi-Fi 5", "Wi-Fi 6", "Wi-Fi 6E"])
            vel = pick(["1200Mbps", "1800Mbps", "3000Mbps", "5400Mbps"])
            return f"Roteador {wifi} {vel}"
        if sub == "Switch":
            portas = pick(["5 portas", "8 portas", "16 portas", "24 portas"])
            return f"Switch Gigabit {portas}"
        if sub == "Notebook":
            tela = pick(["14\"", "15.6\"", "16\""])
            ram = pick(["8GB", "16GB", "32GB"])
            ssd = pick(["256GB", "512GB", "1TB"])
            return f"Notebook {tela} {ram} RAM SSD {ssd}"
        if sub == "Monitor":
            tam = pick(["24\"", "27\"", "32\""])
            hz = pick(["60Hz", "75Hz", "144Hz", "165Hz"])
            res = pick(["Full HD", "QHD", "4K"])
            return f"Monitor {tam} {res} {hz}"
        if sub == "Mouse":
            dpi = pick(["8000 DPI", "12000 DPI", "16000 DPI", "20000 DPI"])
            return f"Mouse Gamer {dpi}"
        if sub == "Teclado":
            tipo = pick(["Mecânico", "Membrana", "Mecânico RGB"])
            return f"Teclado {tipo}"
        if sub == "TV":
            pol = pick(["43\"", "50\"", "55\"", "65\"", "75\""])
            tipo = pick(["4K", "4K QLED", "4K OLED"])
            return f"TV {pol} {tipo}"
        if sub == "Fones de Ouvido":
            tipo = pick(["Bluetooth", "Com fio", "Bluetooth ANC"])
            return f"Fone de Ouvido {tipo}"
        if sub == "Cabo HDMI":
            ver = pick(["2.0", "2.1"])
            tam = pick(["1m", "2m", "3m", "5m"])
            return f"Cabo HDMI {ver} {tam}"
        if sub == "Hub USB":
            portas = pick(["4 portas", "7 portas"])
            tipo = pick(["USB 3.0", "USB-C"])
            return f"Hub {tipo} {portas}"
        # fallback
        return f"{sub} {pick(['Modelo', 'Série', 'Edição'])} {random.randint(100, 9999)}"

    # Preço coerente por categoria/subcategoria
    def gerar_preco(sub):
        faixas = {
            "Memória RAM": (120, 1400),
            "SSD": (150, 2500),
            "HD": (250, 1800),
            "Placa de Vídeo": (900, 12000),
            "Processador": (500, 4500),
            "Placa-mãe": (400, 2500),
            "Fonte": (200, 1200),
            "Cooler": (80, 900),
            "Roteador": (120, 1500),
            "Switch": (120, 2500),
            "Notebook": (2000, 12000),
            "Monitor": (500, 6000),
            "Mouse": (50, 900),
            "Teclado": (80, 1200),
            "TV": (1500, 15000),
            "Fones de Ouvido": (60, 2500),
            "Cabo HDMI": (20, 200),
            "Hub USB": (40, 600),
        }
        lo, hi = faixas.get(sub, (50, 5000))
        return round(random.uniform(lo, hi), 2)

    # ----------------------------
    # 4) Popula categorias/subcategorias
    # ----------------------------
    for cat_nome in categorias.keys():
        cur.execute("INSERT OR IGNORE INTO categoria(nome) VALUES (?)", (cat_nome,))
    conn.commit()

    cur.execute("SELECT id, nome FROM categoria")
    cat_map = {nome: cid for cid, nome in cur.fetchall()}

    for cat_nome, subs in categorias.items():
        cid = cat_map[cat_nome]
        for sub in subs:
            cur.execute(
                "INSERT OR IGNORE INTO subcategoria(categoria_id,nome) VALUES (?,?)",
                (cid, sub),
            )
    conn.commit()

    cur.execute("SELECT id, categoria_id, nome FROM subcategoria")
    sub_rows = cur.fetchall()

    # ----------------------------
    # 5) Popula marcas
    # ----------------------------
    # completa lista até num_marcas
    marcas = marcas_reais[:]
    while len(marcas) < num_marcas:
        marcas.append(f"Marca {len(marcas)+1}")
    for m in marcas[:num_marcas]:
        cur.execute("INSERT OR IGNORE INTO marca(nome) VALUES (?)", (m,))
    conn.commit()

    cur.execute("SELECT id FROM marca")
    marca_ids = [r[0] for r in cur.fetchall()]

    # ----------------------------
    # 6) Fornecedores
    # ----------------------------
    cur.execute("SELECT COUNT(*) FROM fornecedor")
    faltam = max(0, num_fornecedores - cur.fetchone()[0])
    if faltam > 0:
        batch = []
        base_i = random.randint(1000, 10_000_000)
        for i in range(faltam):
            cidade, uf = pick(cidades_uf)
            nome = f"Fornecedor {cidade} {uf} {i+1}"
            batch.append((nome, gen_cnpj_unico(base_i + i), cidade, uf))
            if len(batch) >= 2000:
                cur.executemany("INSERT INTO fornecedor(nome,cnpj,cidade,uf) VALUES (?,?,?,?)", batch)
                batch = []
        if batch:
            cur.executemany("INSERT INTO fornecedor(nome,cnpj,cidade,uf) VALUES (?,?,?,?)", batch)
    conn.commit()

    cur.execute("SELECT id FROM fornecedor")
    fornecedor_ids = [r[0] for r in cur.fetchall()]

    # ----------------------------
    # 7) Clientes
    # ----------------------------
    cur.execute("SELECT COUNT(*) FROM cliente")
    faltam = max(0, num_clientes - cur.fetchone()[0])
    if faltam > 0:
        batch = []
        base = random.randint(1_000_000, 9_999_999)
        for i in range(faltam):
            n = pick(nomes)
            s = pick(sobrenomes)
            cidade, uf = pick(cidades_uf)
            email = f"{n.lower()}.{s.lower()}{base+i}@exemplo.com"
            criado = rand_date(1500, 0)
            batch.append((f"{n} {s}", email, cidade, uf, criado))
            if len(batch) >= 5000:
                cur.executemany("INSERT INTO cliente(nome,email,cidade,uf,criado_em) VALUES (?,?,?,?,?)", batch)
                batch = []
        if batch:
            cur.executemany("INSERT INTO cliente(nome,email,cidade,uf,criado_em) VALUES (?,?,?,?,?)", batch)
    conn.commit()

    cur.execute("SELECT id FROM cliente")
    cliente_ids = [r[0] for r in cur.fetchall()]

    # ----------------------------
    # 8) Produtos (nomes reais)
    # ----------------------------
    cur.execute("SELECT COUNT(*) FROM produto")
    existentes = cur.fetchone()[0]
    faltam = max(0, num_produtos - existentes)
    if faltam > 0:
        batch = []
        start_index = existentes + 1
        for i in range(start_index, start_index + faltam):
            sub_id, cat_id, sub_nome = None, None, None
            (sub_id, cat_id, sub_nome) = pick(sub_rows)

            # descobre nome da categoria (para regra de nome)
            # (cat_id -> nome)
            # para evitar query a cada linha, usamos cat_map invertido:
            cat_nome = None
            for k, v in cat_map.items():
                if v == cat_id:
                    cat_nome = k
                    break

            nome_prod = gerar_nome_produto(cat_nome or "Geral", sub_nome)
            preco = gerar_preco(sub_nome)
            mid = pick(marca_ids)
            fid = pick(fornecedor_ids)
            batch.append((nome_prod, preco, cat_id, sub_id, mid, fid, sku(i)))

            if len(batch) >= 5000:
                cur.executemany(
                    "INSERT INTO produto(nome,preco,categoria_id,subcategoria_id,marca_id,fornecedor_id,sku) "
                    "VALUES (?,?,?,?,?,?,?)",
                    batch
                )
                batch = []
        if batch:
            cur.executemany(
                "INSERT INTO produto(nome,preco,categoria_id,subcategoria_id,marca_id,fornecedor_id,sku) "
                "VALUES (?,?,?,?,?,?,?)",
                batch
            )
    conn.commit()

    cur.execute("SELECT id, preco FROM produto")
    produtos = cur.fetchall()
    produto_ids = [p[0] for p in produtos]

    # ----------------------------
    # 9) Pedidos + Itens
    # ----------------------------
    cur.execute("SELECT COUNT(*) FROM pedido")
    existentes = cur.fetchone()[0]
    faltam = max(0, num_pedidos - existentes)
    if faltam > 0:
        statuses = ["aberto", "pago", "enviado", "cancelado", "estornado"]
        canais = ["site", "app", "loja_fisica", "marketplace"]
        batch_ped = []
        start = existentes + 1

        # cria pedidos
        for i in range(start, start + faltam):
            cid = pick(cliente_ids)
            data = rand_date(900, 0)
            st = pick(statuses)
            canal = pick(canais)
            batch_ped.append((cid, data, st, canal))
            if len(batch_ped) >= 5000:
                cur.executemany("INSERT INTO pedido(cliente_id,data,status,canal) VALUES (?,?,?,?)", batch_ped)
                batch_ped = []
        if batch_ped:
            cur.executemany("INSERT INTO pedido(cliente_id,data,status,canal) VALUES (?,?,?,?)", batch_ped)
    conn.commit()

    # pega ids dos pedidos para gerar itens
    cur.execute("SELECT id, cliente_id, data, status FROM pedido ORDER BY id DESC LIMIT ?", (num_pedidos,))
    pedidos = cur.fetchall()
    pedido_ids = [r[0] for r in pedidos]

    # Itens (gera para TODOS pedidos que ainda não tenham itens)
    # Heurística: para não consultar 1 a 1, checa total e aproxima.
    cur.execute("SELECT COUNT(*) FROM item_pedido")
    itens_exist = cur.fetchone()[0]
    # alvo aproximado: média de 2.2 itens por pedido
    alvo = int(num_pedidos * 2.2)
    faltam_itens = max(0, alvo - itens_exist)

    if faltam_itens > 0:
        batch_itens = []
        for _ in range(faltam_itens):
            pid = pick(pedido_ids)
            prod_id, preco_base = pick(produtos)
            qtd = random.randint(1, max_itens_por_pedido)
            desconto = round(random.choice([0, 0, 0, 0.05, 0.10, 0.15]), 2)
            batch_itens.append((pid, prod_id, qtd, float(preco_base), float(desconto)))
            if len(batch_itens) >= 10000:
                cur.executemany(
                    "INSERT INTO item_pedido(pedido_id,produto_id,quantidade,preco_unit,desconto) VALUES (?,?,?,?,?)",
                    batch_itens
                )
                batch_itens = []
        if batch_itens:
            cur.executemany(
                "INSERT INTO item_pedido(pedido_id,produto_id,quantidade,preco_unit,desconto) VALUES (?,?,?,?,?)",
                batch_itens
            )
    conn.commit()

    # ----------------------------
    # 10) Estoque + Movimentações
    # ----------------------------
    # Estoque para todos produtos (se não existir)
    cur.execute("SELECT COUNT(*) FROM estoque")
    if cur.fetchone()[0] < len(produto_ids):
        # insere apenas ausentes
        batch = []
        for prod_id in produto_ids:
            saldo = random.randint(0, 500)
            estoque_min = random.randint(5, 30)
            batch.append((prod_id, saldo, estoque_min))
            if len(batch) >= 10000:
                cur.executemany("INSERT OR IGNORE INTO estoque(produto_id,saldo,estoque_min) VALUES (?,?,?)", batch)
                batch = []
        if batch:
            cur.executemany("INSERT OR IGNORE INTO estoque(produto_id,saldo,estoque_min) VALUES (?,?,?)", batch)
    conn.commit()

    # Movimentações (gera algumas por produto)
    cur.execute("SELECT COUNT(*) FROM movimentacao_estoque")
    mov_exist = cur.fetchone()[0]
    alvo_mov = max(mov_exist, len(produto_ids) * 3)  # ~3 por produto
    faltam_mov = max(0, alvo_mov - mov_exist)
    if faltam_mov > 0:
        tipos = ["entrada", "saida", "ajuste"]
        batch = []
        for _ in range(faltam_mov):
            prod_id = pick(produto_ids)
            tipo = pick(tipos)
            qtd = random.randint(1, 50) * (1 if tipo != "saida" else 1)
            data = rand_date(900, 0)
            ref = pick(["compra_fornecedor", "venda_pedido", "inventario", "devolucao"])
            batch.append((prod_id, tipo, qtd, data, ref))
            if len(batch) >= 20000:
                cur.executemany(
                    "INSERT INTO movimentacao_estoque(produto_id,tipo,quantidade,data,referencia) VALUES (?,?,?,?,?)",
                    batch
                )
                batch = []
        if batch:
            cur.executemany(
                "INSERT INTO movimentacao_estoque(produto_id,tipo,quantidade,data,referencia) VALUES (?,?,?,?,?)",
                batch
            )
    conn.commit()

    # ----------------------------
    # 11) Avaliações
    # ----------------------------
    cur.execute("SELECT COUNT(*) FROM avaliacao")
    av_exist = cur.fetchone()[0]
    alvo_av = int(num_pedidos * 0.25)  # ~25% dos pedidos viram avaliação
    faltam_av = max(0, alvo_av - av_exist)
    if faltam_av > 0:
        comentarios = [
            "Produto excelente.", "Chegou rápido.", "Bom custo-benefício.", "Qualidade ok.",
            "Não atendeu minhas expectativas.", "Recomendo.", "Muito bom.", "Poderia ser melhor."
        ]
        batch = []
        for _ in range(faltam_av):
            prod_id = pick(produto_ids)
            cid = pick(cliente_ids)
            nota = random.randint(1, 5)
            com = None if random.random() < 0.35 else pick(comentarios)
            data = rand_date(900, 0)
            batch.append((prod_id, cid, nota, com, data))
            if len(batch) >= 20000:
                cur.executemany(
                    "INSERT INTO avaliacao(produto_id,cliente_id,nota,comentario,data) VALUES (?,?,?,?,?)",
                    batch
                )
                batch = []
        if batch:
            cur.executemany(
                "INSERT INTO avaliacao(produto_id,cliente_id,nota,comentario,data) VALUES (?,?,?,?,?)",
                batch
            )
    conn.commit()

    # ----------------------------
    # 12) Métrica final
    # ----------------------------
    cur.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    total_tabelas = cur.fetchone()[0]

    # Contagem aproximada de linhas relevantes
    tabelas = ["categoria","subcategoria","marca","fornecedor","produto","cliente","pedido","item_pedido","estoque","movimentacao_estoque","avaliacao"]
    contagens = {}
    for t in tabelas:
        cur.execute(f"SELECT COUNT(*) FROM {t}")
        contagens[t] = cur.fetchone()[0]

    total_tabelas = cur.fetchone()[0]
    conn.close()
    return {
        "db_path": db_path,
        "total_tabelas": total_tabelas,
        "reset_db": reset_db,
        "contagens": contagens
    }

info = expandir_sqlite_com_nomes_reais(db_path="vendas.db",reset_db=True)
print(info)

#info = expandir_sqlite("vendas.db", num_tabelas_extras=300, linhas_por_tabela=3000, seed=123)
#print(info)
#separar_json_e_sql("registro.txt", "registro_json.txt", "registro_SQL.txt")
