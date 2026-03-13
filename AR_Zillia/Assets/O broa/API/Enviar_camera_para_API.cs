using System.Collections;
using UnityEngine;
using UnityEngine.Networking;

public class Enviar_camera_para_API : MonoBehaviour
{
    public Camera cameraDeCaptura;
    public int largura = 4000;
    public int altura = 4000;
    [Range(1, 100)] public int qualidadeJpg = 100;

    public string urlApi = "http://192.168.0.10:8000/";
    public float intervaloEnvio = 1.0f;
    public bool envioAutomatico = true;

    private RenderTexture renderTexture;
    private Texture2D textura;
    private bool enviando;

    private void Start()
    {
        renderTexture = new RenderTexture(largura, altura, 24);
        renderTexture.Create();

        textura = new Texture2D(largura, altura, TextureFormat.RGB24, false);

        if (envioAutomatico)
        {
            StartCoroutine(RotinaEnvio());
        }
    }

    private IEnumerator RotinaEnvio()
    {
        while (true)
        {
            if (!enviando)
            {
                yield return StartCoroutine(CapturarEEnviar());
            }

            yield return new WaitForSeconds(intervaloEnvio);
        }
    }

    public IEnumerator CapturarEEnviar()
    {
        if (cameraDeCaptura == null)
        {
            Debug.LogError("Camera de captura não foi atribuída.");
            yield break;
        }

        enviando = true;

        yield return new WaitForEndOfFrame();

        RenderTexture targetAnterior = cameraDeCaptura.targetTexture;
        RenderTexture activeAnterior = RenderTexture.active;

        cameraDeCaptura.targetTexture = renderTexture;
        cameraDeCaptura.Render();

        RenderTexture.active = renderTexture;
        textura.ReadPixels(new Rect(0, 0, largura, altura), 0, 0);
        textura.Apply();

        cameraDeCaptura.targetTexture = targetAnterior;
        RenderTexture.active = activeAnterior;

        byte[] imagemJpg = textura.EncodeToJPG(qualidadeJpg);

        WWWForm form = new WWWForm();
        form.AddBinaryData("image", imagemJpg, "ultima_imagem.jpg", "image/jpeg");

        using (UnityWebRequest request = UnityWebRequest.Post(urlApi, form))
        {
            request.timeout = 15;
            yield return request.SendWebRequest();

            if (request.result != UnityWebRequest.Result.Success)
            {
                Debug.LogError("Erro ao enviar imagem: " + request.error);
            }
            else
            {
                Debug.Log("Imagem enviada com sucesso: " + request.downloadHandler.text);
            }
        }

        enviando = false;
    }

    private void OnDestroy()
    {
        if (renderTexture != null)
        {
            renderTexture.Release();
            Destroy(renderTexture);
        }

        if (textura != null)
        {
            Destroy(textura);
        }
    }
}