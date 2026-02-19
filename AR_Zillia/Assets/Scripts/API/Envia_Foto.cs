using System;
using System.Collections;
using System.Security.Cryptography;
using System.Text;
using UnityEngine;
using UnityEngine.Networking;
using UnityEngine.UI;

#if UNITY_ANDROID
using UnityEngine.Android;
#endif

public class Envia_Foto : MonoBehaviour
{
    [Header("API")]
    public string apiUrl = "http://200.129.187.20:8555/ia/chat";

    [Header("AUTH")]
    public string token = "VR_2026";
    public bool useBearer = true; // true -> Authorization: Bearer VR_2026 | false -> x-token: VR_2026

    [Header("Quest Camera (WebCamTexture)")]
    [Tooltip("Deixe vazio para pegar o 1º device. Se quiser forçar, use um trecho do nome do device.")]
    public string deviceNameContains = "";
    public int requestedWidth = 1280;
    public int requestedHeight = 960; // Quest costuma suportar 1280x960 e (em versões mais novas) 1280x1280
    public int requestedFPS = 30;

    [Header("Encode")]
    public bool usePng = true;
    [Range(1, 100)] public int jpgQuality = 90;

    [Header("Preview UI (debug)")]
    public RawImage previewRawImage;
    public bool atualizarPreview = true;

    private WebCamTexture _webcam;
    private Texture2D _cpuTex;
    private Color32[] _pixels32;

    public void CaptureAndSend()
    {
        Debug.Log("[Envia_Foto] CaptureAndSend() chamado");
        StartCoroutine(CaptureAndSend_Coroutine());
    }

    private IEnumerator CaptureAndSend_Coroutine()
    {
        Debug.Log("[Envia_Foto] Início coroutine");

#if UNITY_ANDROID
        // Runtime permission (CAMERA). Para passthrough no Quest, também precisa do HEADSET_CAMERA no Manifest.
        if (!Permission.HasUserAuthorizedPermission(Permission.Camera))
        {
            Debug.Log("[Envia_Foto] Solicitando permissão CAMERA...");
            Permission.RequestUserPermission(Permission.Camera);

            // Espera o usuário responder
            float t0 = Time.realtimeSinceStartup;
            while (!Permission.HasUserAuthorizedPermission(Permission.Camera))
            {
                if (Time.realtimeSinceStartup - t0 > 8f)
                {
                    Debug.LogError("[Envia_Foto] Permissão CAMERA não concedida (timeout). Abortando.");
                    yield break;
                }
                yield return null;
            }
        }
#endif

        // 1) Iniciar WebCamTexture (câmera do headset)
        if (_webcam == null)
        {
            var devices = WebCamTexture.devices;
            if (devices == null || devices.Length == 0)
            {
                Debug.LogError("[Envia_Foto] Nenhum WebCam device encontrado. (PCA não disponível / permissão / device).");
                yield break;
            }

            string chosenName = devices[0].name;

            if (!string.IsNullOrWhiteSpace(deviceNameContains))
            {
                for (int i = 0; i < devices.Length; i++)
                {
                    if (!string.IsNullOrEmpty(devices[i].name) &&
                        devices[i].name.IndexOf(deviceNameContains, StringComparison.OrdinalIgnoreCase) >= 0)
                    {
                        chosenName = devices[i].name;
                        break;
                    }
                }
            }

            Debug.Log("[Envia_Foto] WebCam escolhido: " + chosenName);

            _webcam = new WebCamTexture(chosenName, requestedWidth, requestedHeight, requestedFPS);
            _webcam.Play();
        }

        // 2) Esperar primeiro frame válido
        float startWait = Time.realtimeSinceStartup;
        while (_webcam != null && _webcam.isPlaying && (_webcam.width <= 16 || _webcam.height <= 16 || !_webcam.didUpdateThisFrame))
        {
            if (Time.realtimeSinceStartup - startWait > 8f)
            {
                Debug.LogError("[Envia_Foto] Timeout esperando frame da WebCamTexture. (tela preta costuma ser permissão/manifest/PCA).");
                yield break;
            }
            yield return null;
        }

        int w = _webcam.width;
        int h = _webcam.height;

        Debug.Log($"[Envia_Foto] Frame recebido: {w}x{h}");

        // 3) Copiar pixels para CPU (Texture2D)
        if (_cpuTex == null || _cpuTex.width != w || _cpuTex.height != h)
        {
            _cpuTex = new Texture2D(w, h, TextureFormat.RGBA32, false, false);
            _pixels32 = new Color32[w * h];
        }

        try
        {
            _webcam.GetPixels32(_pixels32);
            _cpuTex.SetPixels32(_pixels32);
            _cpuTex.Apply(false, false);
        }
        catch (Exception e)
        {
            Debug.LogError("[Envia_Foto] Erro ao copiar pixels da câmera: " + e);
            yield break;
        }

        // 3.1) Preview
        if (atualizarPreview && previewRawImage != null)
        {
            previewRawImage.texture = _cpuTex;
            Debug.Log("[Envia_Foto] Preview atualizado no RawImage");
        }

        // 4) Encode
        Debug.Log("[Envia_Foto] Encode imagem...");
        byte[] imgBytes = usePng ? _cpuTex.EncodeToPNG() : _cpuTex.EncodeToJPG(jpgQuality);
        string contentType = usePng ? "image/png" : "image/jpeg";

        if (imgBytes == null || imgBytes.Length == 0)
        {
            Debug.LogError("[Envia_Foto] ERRO: imagem inválida (null/0 bytes). Abortando.");
            yield break;
        }

        Debug.Log("[Envia_Foto] Bytes imagem: " + imgBytes.Length);

        // 5) SHA256
        string sha256Hex;
        using (SHA256 sha = SHA256.Create())
        {
            byte[] hash = sha.ComputeHash(imgBytes);
            StringBuilder sb = new StringBuilder(hash.Length * 2);
            for (int i = 0; i < hash.Length; i++) sb.Append(hash[i].ToString("x2"));
            sha256Hex = sb.ToString();
        }

        // 6) Base64
        string b64 = Convert.ToBase64String(imgBytes);
        string requestId = Guid.NewGuid().ToString("N");

        // 7) JSON
        string json =
            "{"
            + "\"request_id\":\"" + requestId + "\","
            + "\"content_type\":\"" + contentType + "\","
            + "\"width\":" + w + ","
            + "\"height\":" + h + ","
            + "\"sha256\":\"" + sha256Hex + "\","
            + "\"image_base64\":\"" + b64 + "\""
            + "}";

        byte[] bodyRaw = Encoding.UTF8.GetBytes(json);

        // 8) POST
        using (UnityWebRequest req = new UnityWebRequest(apiUrl, "POST"))
        {
            req.uploadHandler = new UploadHandlerRaw(bodyRaw);
            req.downloadHandler = new DownloadHandlerBuffer();
            req.SetRequestHeader("Content-Type", "application/json");

            if (!string.IsNullOrWhiteSpace(token))
            {
                if (useBearer) req.SetRequestHeader("Authorization", "Bearer " + token);
                else req.SetRequestHeader("x-token", token);
            }

            req.SetRequestHeader("x-pass-through", "true");
            req.timeout = 30;

            Debug.Log("[Envia_Foto] Enviando request para: " + apiUrl);
            yield return req.SendWebRequest();

            string respText = req.downloadHandler != null ? req.downloadHandler.text : "(no downloadHandler)";
            Debug.Log("[Envia_Foto] Finalizado. result=" + req.result + " code=" + req.responseCode);

            if (req.result != UnityWebRequest.Result.Success)
                Debug.LogError("[Envia_Foto] Falha: " + req.responseCode + " | " + req.error + " | " + respText);
            else
                Debug.Log("[Envia_Foto] OK: " + respText);
        }

        Debug.Log("[Envia_Foto] Fim coroutine");
    }

    private void OnDisable()
    {
        if (_webcam != null)
        {
            if (_webcam.isPlaying) _webcam.Stop();
            _webcam = null;
        }
    }
}
