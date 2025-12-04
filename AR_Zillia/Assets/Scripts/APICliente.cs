using UnityEngine;
using UnityEngine.UI;
using TMPro;
using UnityEngine.Networking;
using System.Text;
using System.Collections;

public class APICliente : MonoBehaviour
{
    public GameObject campoEntrada;
    public GameObject campoResposta;
    public Button botaoEnviar;
    public string IP;
    public string Porta;
    public string Rota;

    private string URL;

    void Start()
    {
        URL = "http://" + IP + ":" + Porta + "/" + Rota;
        Debug.Log("URL usada: " + URL);

        botaoEnviar.onClick.AddListener(Enviar);
    }

    public void Enviar()
    {
        string texto = campoEntrada.GetComponent<TMP_Text>().text;
        Debug.Log("Texto coletado: " + texto);

        StartCoroutine(ChamarAPI(texto));
    }

    IEnumerator ChamarAPI(string texto)
    {
        string json = "{\"prompt\":\"" + texto + "\"}";

        UnityWebRequest request = new UnityWebRequest(URL, "POST");
        byte[] bodyRaw = Encoding.UTF8.GetBytes(json);

        request.uploadHandler = new UploadHandlerRaw(bodyRaw);
        request.downloadHandler = new DownloadHandlerBuffer();
        request.SetRequestHeader("Content-Type", "application/json");
        //request.timeout = 30; // Timeout em segundos, deixe 0 para ser infinito
        request.SendWebRequest();
        float tempoPassado = 0f;

        while (!request.isDone)
        {
            if (tempoPassado >= 999999)
            {
                request.Abort();
                campoResposta.GetComponent<TMP_Text>().text =
                    "Erro: Timeout atingido (" + 999999 + "s)";
                yield break;
            }

            tempoPassado += Time.deltaTime;
            yield return null;
        }

        if (request.result != UnityWebRequest.Result.Success)
        {
            campoResposta.GetComponent<TMP_Text>().text = "Erro: " + request.error;
        }
        else
        {
            campoResposta.GetComponent<TMP_Text>().text = request.downloadHandler.text;
        }
    }
}