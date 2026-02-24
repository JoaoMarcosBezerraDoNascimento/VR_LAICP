from fastapi import FastAPI, HTTPException, Request
import httpx 
import uvicorn

app = FastAPI(title="Ponte VR-PC-Servidor")

# --- ENDEREÇO DO SERVIDOR REAL ---
# Usando o IP que você forneceu. 
# Nota: Se o servidor exigir uma porta (ex: :5000) ou rota (ex: /comando), adicione ao final.
URL_SERVIDOR_REMOTO = "http://100.122.253.126" 

@app.get("/")
async def status():
    return {"status": "Ponte Ativa", "destino": URL_SERVIDOR_REMOTO}

@app.post("/enviar-comando")
async def ponte_vr_servidor(request: Request):
    try:
        # 1. Recebe o JSON do VR
        dados_recebidos = await request.json()
        
        # 2. Tenta repassar para o servidor via VPN
        async with httpx.AsyncClient() as client:
            # Enviamos com um timeout de 10 segundos para dar tempo da VPN responder
            resposta = await client.post(URL_SERVIDOR_REMOTO, json=dados_recebidos, timeout=10.0)
            
            # 3. Retorna o que o servidor respondeu
            return resposta.json()

    except httpx.ConnectTimeout:
        raise HTTPException(status_code=504, detail="Tempo esgotado: O servidor demorou a responder.")
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Erro de Conexão: Verifique se a VPN está ligada no PC.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro inesperado: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)