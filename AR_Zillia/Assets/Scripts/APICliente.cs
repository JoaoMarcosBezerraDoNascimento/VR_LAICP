using UnityEngine;
using TMPro;
using UnityEngine.UI;
using UnityEngine.Networking;
using System.Text;
using System.Collections;

public class APICliente : MonoBehaviour
{
    [Header("Referências")]
    public TMP_Text campoEntrada;
    public TMP_Text campoResposta;
    public Button botaoEnviar;

    // Use o IP da sua máquina
    private const string URL = "http://192.168.0.10:8000/processar";

    void Start()
    {
        botaoEnviar.onClick.AddListener(Enviar);
    }

    void Enviar()
    {
        string texto = campoEntrada.text;
        StartCoroutine(ChamarAPI(texto));
    }

    IEnumerator ChamarAPI(string texto)
    {
        // JSON correto para FastAPI
        string json = "{\"prompt\":\"" + texto + "\"}";

        UnityWebRequest request = new UnityWebRequest(URL, "POST");
        byte[] bodyRaw = Encoding.UTF8.GetBytes(json);

        request.uploadHandler = new UploadHandlerRaw(bodyRaw);
        request.downloadHandler = new DownloadHandlerBuffer();
        request.SetRequestHeader("Content-Type", "application/json");

        yield return request.SendWebRequest();

        if (request.result != UnityWebRequest.Result.Success)
        {
            campoResposta.text = "Erro: " + request.error;
        }
        else
        {
            RespostaAPI resposta = JsonUtility.FromJson<RespostaAPI>(request.downloadHandler.text);
            campoResposta.text = resposta.resposta;
        }
    }
}

[System.Serializable]
public class RespostaAPI
{
    public string resposta;
}
