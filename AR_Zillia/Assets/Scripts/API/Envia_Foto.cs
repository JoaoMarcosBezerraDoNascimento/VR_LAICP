using System;
using System.Collections;
using System.Security.Cryptography;
using System.Text;
using UnityEngine;
using UnityEngine.Networking;
using UnityEngine.UI;

using Unity.Collections;
using UnityEngine.XR.ARFoundation;
using UnityEngine.XR.ARSubsystems;

public class Envia_Foto : MonoBehaviour
{
    [Header("API")]
    public string apiUrl = "http://200.129.187.20:8555/ia/chat";

    [Header("AUTH")]
    public string token = "VR_2026";
    public bool useBearer = true;

    [Header("PCA / AR Foundation Camera (Meta OpenXR)")]
    [Tooltip("Arraste o ARCameraManager (na mesma Camera do XR Origin).")]
    public ARCameraManager arCameraManager;

    [Tooltip("Se true, pega frame da câmera continuamente no Update (recomendado).")]
    public bool captureCameraContinuously = true;

    [Tooltip("Se false, o envio usa o último frame disponível; se true, espera um frame novo antes de enviar.")]
    public bool waitNewCameraFrameBeforeSend = true;

    [Header("3D Capture (Unity)")]
    public Camera captureCamera;
    public int captureWidth = 1280;
    public int captureHeight = 720;

    [Header("Encode")]
    public bool usePng = true;
    [Range(1, 100)] public int jpgQuality = 90;

    [Header("Preview UI (debug)")]
    public RawImage previewRawImage;
    public bool atualizarPreview = true;

    [Header("Composite Shader")]
    [Tooltip("Shader: Hidden/CompositeBG (o que eu te passei).")]
    public Shader compositeShader;

    // ---- Internals ----
    private RenderTexture _rt3D;
    private RenderTexture _rtComposite;

    private Texture2D _texCamera; // frame real da PCA (CPU image convertido)
    private Texture2D _texOut;    // resultado final (camera + 3D)
    private Material _mat;

    private byte[] _cameraRgbaBuffer;
    private int _camW, _camH;
    private volatile bool _hasCamFrame;
    private int _camFrameCounter;
    private int _camFrameCounterAtLastSend;

    private NativeArray<byte> _cpuConvertBuffer; // buffer reaproveitado (evita GC)
    private bool _cpuBufferAllocated;

    void Update()
    {
        if (!captureCameraContinuously) return;
        TryGrabCameraFrameCPU();
    }

    /// <summary>
    /// Captura um frame da câmera (PCA via AR Foundation) no CPU e converte para RGBA32.
    /// Requer: Meta Quest: Camera (Passthrough) + Camera Image Support habilitados.
    /// </summary>
    private void TryGrabCameraFrameCPU()
    {
        if (arCameraManager == null) return;
        if (!arCameraManager.enabled) return;

        if (!arCameraManager.TryAcquireLatestCpuImage(out XRCpuImage cpuImage))
            return;

        try
        {
            // Conversão para RGBA32 (espelhamento opcional pode ser ajustado aqui se precisar)
            var convParams = new XRCpuImage.ConversionParams
            {
                inputRect = new RectInt(0, 0, cpuImage.width, cpuImage.height),
                outputDimensions = new Vector2Int(cpuImage.width, cpuImage.height),
                outputFormat = TextureFormat.RGBA32,
                transformation = XRCpuImage.Transformation.None
            };

            int requiredSize = cpuImage.GetConvertedDataSize(convParams);

            if (!_cpuBufferAllocated || !_cpuConvertBuffer.IsCreated || _cpuConvertBuffer.Length != requiredSize)
            {
                if (_cpuConvertBuffer.IsCreated) _cpuConvertBuffer.Dispose();
                _cpuConvertBuffer = new NativeArray<byte>(requiredSize, Allocator.Persistent, NativeArrayOptions.UninitializedMemory);
                _cpuBufferAllocated = true;
            }

            cpuImage.Convert(convParams, _cpuConvertBuffer);

            _camW = cpuImage.width;
            _camH = cpuImage.height;

            if (_cameraRgbaBuffer == null || _cameraRgbaBuffer.Length != requiredSize)
                _cameraRgbaBuffer = new byte[requiredSize];

            _cpuConvertBuffer.CopyTo(_cameraRgbaBuffer);

            _hasCamFrame = true;
            _camFrameCounter++;
        }
        catch (Exception e)
        {
            Debug.LogError("[Envia_Foto] Erro convertendo CPU image: " + e);
        }
        finally
        {
            cpuImage.Dispose();
        }
    }

    public void CaptureAndSend()
    {
        StartCoroutine(CaptureAndSend_Coroutine());
    }

    private IEnumerator CaptureAndSend_Coroutine()
    {
        if (captureCamera == null)
        {
            Debug.LogError("[Envia_Foto] captureCamera não setada.");
            yield break;
        }

        if (arCameraManager == null)
        {
            Debug.LogError("[Envia_Foto] arCameraManager não setado.");
            yield break;
        }

        if (compositeShader == null)
        {
            Debug.LogError("[Envia_Foto] compositeShader não setado (Hidden/CompositeBG).");
            yield break;
        }

        if (_mat == null) _mat = new Material(compositeShader);

        // Se não captura continuamente, tenta pegar 1 frame agora
        if (!captureCameraContinuously)
            TryGrabCameraFrameCPU();

        // Se precisa esperar frame novo antes de enviar, aguarda incrementar contador
        if (waitNewCameraFrameBeforeSend)
        {
            int startCounter = _camFrameCounter;
            float t0 = Time.realtimeSinceStartup;

            while (_camFrameCounter == startCounter)
            {
                if (!captureCameraContinuously)
                    TryGrabCameraFrameCPU();

                if (Time.realtimeSinceStartup - t0 > 2.0f)
                    break;

                yield return null;
            }
        }

        if (!_hasCamFrame || _cameraRgbaBuffer == null || _camW <= 0 || _camH <= 0)
        {
            Debug.LogError("[Envia_Foto] Sem frame da câmera (PCA). Verifique permissões + Camera Image Support + ARCameraManager habilitado.");
            yield break;
        }

        // Evita reenviar o mesmo frame (opcional)
        if (_camFrameCounterAtLastSend == _camFrameCounter)
        {
            Debug.LogWarning("[Envia_Foto] Enviando o mesmo frame (contador não mudou).");
        }
        _camFrameCounterAtLastSend = _camFrameCounter;

        // 1) Texture2D do frame real
        if (_texCamera == null || _texCamera.width != _camW || _texCamera.height != _camH)
            _texCamera = new Texture2D(_camW, _camH, TextureFormat.RGBA32, false, false);

        _texCamera.LoadRawTextureData(_cameraRgbaBuffer);
        _texCamera.Apply(false, false);

        // 2) Renderizar 3D com alpha 0 no fundo
        EnsureRTs();

        captureCamera.clearFlags = CameraClearFlags.SolidColor;
        Color bg = captureCamera.backgroundColor;
        captureCamera.backgroundColor = new Color(bg.r, bg.g, bg.b, 0f);

        var prevTarget = captureCamera.targetTexture;
        var prevActive = RenderTexture.active;

        captureCamera.targetTexture = _rt3D;
        captureCamera.Render();
        captureCamera.targetTexture = prevTarget;

        // 3) Compor câmera + 3D
        _mat.SetTexture("_BgTex", _texCamera);
        _mat.SetTexture("_FgTex", _rt3D);
        Graphics.Blit(null, _rtComposite, _mat);

        // 4) Ler composto em Texture2D final
        if (_texOut == null || _texOut.width != captureWidth || _texOut.height != captureHeight)
            _texOut = new Texture2D(captureWidth, captureHeight, TextureFormat.RGBA32, false, false);

        RenderTexture.active = _rtComposite;
        _texOut.ReadPixels(new Rect(0, 0, captureWidth, captureHeight), 0, 0, false);
        _texOut.Apply(false, false);
        RenderTexture.active = prevActive;

        if (atualizarPreview && previewRawImage != null)
            previewRawImage.texture = _texOut;

        // 5) Encode
        byte[] imgBytes = usePng ? _texOut.EncodeToPNG() : _texOut.EncodeToJPG(jpgQuality);
        string contentType = usePng ? "image/png" : "image/jpeg";

        if (imgBytes == null || imgBytes.Length == 0)
        {
            Debug.LogError("[Envia_Foto] Imagem final inválida.");
            yield break;
        }

        // 6) SHA256
        string sha256Hex;
        using (SHA256 sha = SHA256.Create())
        {
            byte[] hash = sha.ComputeHash(imgBytes);
            StringBuilder sb = new StringBuilder(hash.Length * 2);
            for (int i = 0; i < hash.Length; i++) sb.Append(hash[i].ToString("x2"));
            sha256Hex = sb.ToString();
        }

        // 7) Base64 + JSON
        string b64 = Convert.ToBase64String(imgBytes);
        string requestId = Guid.NewGuid().ToString("N");

        string json =
            "{"
            + "\"request_id\":\"" + requestId + "\","
            + "\"content_type\":\"" + contentType + "\","
            + "\"width\":" + captureWidth + ","
            + "\"height\":" + captureHeight + ","
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

            req.timeout = 30;
            yield return req.SendWebRequest();

            string respText = req.downloadHandler != null ? req.downloadHandler.text : "(no downloadHandler)";
            if (req.result != UnityWebRequest.Result.Success)
                Debug.LogError("[Envia_Foto] Falha: " + req.responseCode + " | " + req.error + " | " + respText);
            else
                Debug.Log("[Envia_Foto] OK: " + respText);
        }
    }

    private void EnsureRTs()
    {
        if (_rt3D == null || _rt3D.width != captureWidth || _rt3D.height != captureHeight)
        {
            if (_rt3D != null) { _rt3D.Release(); Destroy(_rt3D); }
            _rt3D = new RenderTexture(captureWidth, captureHeight, 24, RenderTextureFormat.ARGB32);
            _rt3D.Create();
        }

        if (_rtComposite == null || _rtComposite.width != captureWidth || _rtComposite.height != captureHeight)
        {
            if (_rtComposite != null) { _rtComposite.Release(); Destroy(_rtComposite); }
            _rtComposite = new RenderTexture(captureWidth, captureHeight, 0, RenderTextureFormat.ARGB32);
            _rtComposite.Create();
        }
    }

    private void OnDisable()
    {
        if (_rt3D != null) { _rt3D.Release(); Destroy(_rt3D); _rt3D = null; }
        if (_rtComposite != null) { _rtComposite.Release(); Destroy(_rtComposite); _rtComposite = null; }
        if (_mat != null) { Destroy(_mat); _mat = null; }

        if (_cpuConvertBuffer.IsCreated) _cpuConvertBuffer.Dispose();
        _cpuBufferAllocated = false;
    }
}