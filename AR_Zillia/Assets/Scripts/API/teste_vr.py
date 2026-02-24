import requests

# Endereço local do seu PC (onde a API está rodando)
URL_API = "http://localhost:8000/enviar-comando"

# Simulação de um JSON que o VR enviaria (ex: mover o controle)
dados_vr = {
    "dispositivo": "Oculus_Quest_2",
    "comando": "mover_ponteiro",
    "eixo_x": 120,
    "eixo_y": -45
}

print(f"Enviando dados para a ponte: {dados_vr}")

try:
    # Envia o teste para a tua API_nova_rota.py
    resposta = requests.post(URL_API, json=dados_vr)
    print(f"Status da Resposta: {resposta.status_code}")
    print(f"Resposta que veio do Servidor via VPN: {resposta.json()}")
except Exception as e:
    print(f"Erro ao testar: {e}")