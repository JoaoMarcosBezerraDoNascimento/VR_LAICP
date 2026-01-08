# VR_LAICP
# 📦 Projeto_VR

Este documento explica **onde cada arquivo fica** e **Como o projeto está organizado**.

Ele foi feito para que **qualquer dev do time consiga rodar o projeto sem dor de cabeça**, tanto em desenvolvimento quanto já preparado para produção.

---

## 🎯 Visão geral do projeto

* Todos os devs rodam a **API localmente via python**
* Cada dev tem seu **banco de dados isolado ou copiado do principal**
* O App (VR / Front / Cliente) **nunca acessa o banco direto**, apenas via API
* O mesmo código roda em **DEV → HOMOLOG → PROD**, mudando apenas variáveis de ambiente

---

## 📁 Estrutura de pastas (IMPORTANTE)

No nosso projeto, tudo fica **dentro do app VR**, seguindo este padrão:

```text

App_VR/
└─ Assets/
   │  
   ├─ Textures/ # Pasta que recebe todas as imagens, gifs, animações, etc
   │
   ├─ Prefabs/ # Pastas com as telas e modelos padrões preparados para o VR
   │  ├─ Canvas_Login.prefab # Tela de Login feita em Unity
   │  ├─ Celula_pecas.prefab # Célula unitária de peças em Unity
   │  └─ etc.prefab # outros prefabs feitos em Unity
   │
   ├─ Scenes/ # cenas do projeto e modelos prontos para build
   │  ├─ dev/ 
   │  │  ├─ Cena_login.Unity # Cena apenas do menu login para testes
   │  │  ├─ Cena_pedidos.Unity # Cena de testes na tela de pedidos
   │  │  └─ etc.Unity
   │  │
   │  ├─ Cena_PC.Unity # Cena oficial para build no PC
   │  ├─ Cena_Mobile.Unity # Cena oficial para build no mobile
   │  ├─ Cena_VR.Unity # Cena oficial para build no VR
   │  └─ etc.Unity
   │
   ├─ Scripts/
   │  ├─ API/                  # ROOT DA API (Python / FastAPI)
   │  │   ├─ app/
   │  │   │  ├─ __init__.py
   │  │   │  ├─ main.py         # Sobe a API FastAPI
   │  │   │  ├─ routers.py        # Endpoints (GET, POST, etc)
   │  │   │  │
   │  │   │  ├─ services/       # Regras de negócio
   │  │   │  │  ├─ __init__.py
   │  │   │  │  ├─ login.py
   │  │   │  │  ├─ pedidos.py
   │  │   │  │  ├─ pecas_service.py
   │  │   │  │  └─ outros.py
   │  │   │  │
   │  │   │  ├─ database/       # Dados / persistência
   │  │   │  │  ├─ Pedidos.json
   │  │   │  │  ├─ Pecas.json
   │  │   │  │  ├─ Users.json
   │  │   │  │  └─ db_utils.py
   │  │   │  │
   │  │   │  ├─ models/         # Modelos (Pydantic)
   │  │   │  │  ├─ user.py
   │  │   │  │  ├─ pedido.py
   │  │   │  │  └─ peca.py
   │  │   │  │
   │  │   │  ├─ core/           # Configurações centrais
   │  │   │  │  ├─ config.py
   │  │   │  │  ├─ security.py
   │  │   │  │  └─ logger.py
   │  │   │  │
   │  │   │  └─ utils/          # Funções auxiliares
   │  │   │     ├─ helpers.py
   │  │   │     └─ validators.py
   │  │   │
   │  │   ├─ .env.example
   │  │   └─ requirements.txt
   │  │    
   │  ├── IA/   
   │  │   └─ Scripts.cs
   │  │ 
   │  ├── UI/   
   │  │   └─ Scripts.cs
   │  │
   │  └── UX/
   │       └─ Scripts.cs
   │  
   │  
   ├─ requirements.txt   # Pacotes python e outras bibliotecas necessárias para o projeto
   ├─ Settings/          # Configurações internas do Unity e de pacotes (Input, XR, Render Pipeline, etc)
   ├─ StreamingAssets/   # Arquivos acessíveis em tempo de execução (JSON, vídeos, configs sem compactação)
   ├─ TextMesh Pro/      # Assets e configurações do TextMesh Pro (fontes, materiais, fallback)
   ├─ _Recovery/         # Backups automáticos criados pelo Unity após travamentos ou falhas
   ├─ MetaXR/            # SDK da Meta para Quest (hand tracking, passthrough, recursos avançados)
   ├─ Oculus/            # SDK legado da Oculus (OVR, compatibilidade com projetos antigos)
   ├─ Plugins/           # Plugins nativos e bibliotecas externas (.dll, .aar, .so)
   ├─ Resources/         # Assets carregáveis via código (Resources.Load) – sempre incluídos no build
   ├─ XR/                # Configurações do sistema XR/OpenXR do Unity
   └─ XRI/               # XR Interaction Toolkit (interações, controllers, teleport, grab)

```

📌 **Tudo relacionado à API fica dentro de `Assets/Scripts/API`**.
📌 **Tudo relacionado à IA fica dentro de `Assets/Scripts/IA`**.
📌 **Esse sistema elimina a necessidade de ter vários repositórios para trabalhar no projeto`**.

---

## 🧩 Responsabilidade de cada camada

### 🔹 `routers.py`

* Define qual **rotas HTTP** chama qual função (wrapper)
* NÃO acessa banco
* NÃO contém regra de negócio

Exemplo:

```python

@app.post("/login")
Acessar_Banco.Fazer_Login():

```

```python

Class Acessar_Banco():
   def Fazer_login():
      #Lógica de negócio para coletar os dados dos JSONS

```

## 🔄 Fluxo de trabalho geral:

1. Criar modelo Mock para apresentações usando if(mockado = True)
2. Começar a trabalhar no modelo oficial, solicitando os dados da API
3. Testes no build do projeto rodando liso
4. Atualizar sua branch com a main (git merge main)
5. Abrir PR da sua branch para main

## 🧠 Frase-chave do projeto

> "Só faço o modelo oficial, se o mocado já tiver pronto"
