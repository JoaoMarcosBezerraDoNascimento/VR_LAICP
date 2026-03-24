using System;
using System.IO;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.Net.Http;
using UnityEngine;
using UnityEngine.UI;
using UnityEngine.InputSystem;

public class Stream_API : MonoBehaviour
{
    [Header("MJPEG URL (proxy)")]
    public string streamUrl => System_Config.IP_atual + "/stream";

    [Header("Click API URL")]
    public string clickUrl => System_Config.IP_atual + "/click";

    [Header("Render destino (use apenas UM)")]
    public Renderer targetRenderer;     // opcional
    public RawImage targetRawImage;     // opcional (UI)

    [Header("Origem do clique (TOP-LEFT)")]
    [Tooltip("Para RawImage: use o pr�prio RectTransform dela (ou um filho no TOP-LEFT).\nPara Quad: um GameObject no canto superior esquerdo do Quad.")]
    public Transform topLeftOrigin;

    [Header("Texture Settings")]
    public bool usePointFilter = false;

    [Header("Novo Input System (auto-cria se vazio)")]
    public InputActionAsset inputActions;
    public string actionMapName = "UI";
    public string clickActionName = "Click";
    public string pointerPositionActionName = "Point";

    private InputAction _clickAction;
    private InputAction _pointAction;

    private HttpClient _http;
    private CancellationTokenSource _cts;

    private Texture2D _tex;
    private byte[] _jpegBuffer;
    private volatile bool _hasNewFrame;
    private int _jpegLen;

    void Awake()
    {
        _http = new HttpClient();
        _http.Timeout = Timeout.InfiniteTimeSpan;

        SetupInputActions();
    }

    void OnEnable()
    {
        EnableInput();

        _cts = new CancellationTokenSource();
        _ = Task.Run(() => StreamLoop(_cts.Token), _cts.Token);
    }

    void OnDisable()
    {
        DisableInput();

        try { _cts?.Cancel(); } catch { }
        try { _cts?.Dispose(); } catch { }
        _cts = null;
    }

    void OnDestroy()
    {
        try { _cts?.Cancel(); } catch { }
        try { _http?.Dispose(); } catch { }
    }

    void Update()
    {
        HandleClick();

        if (!_hasNewFrame) return;

        int len = _jpegLen;
        if (len <= 0 || _jpegBuffer == null || _jpegBuffer.Length < len)
        {
            _hasNewFrame = false;
            return;
        }

        if (_tex == null)
        {
            _tex = new Texture2D(2, 2, TextureFormat.RGBA32, false, false);
            _tex.wrapMode = TextureWrapMode.Clamp;
            _tex.filterMode = usePointFilter ? FilterMode.Point : FilterMode.Bilinear;

            // Se RawImage foi atribu�do, renderiza nele
            if (targetRawImage != null)
                targetRawImage.texture = _tex;

            // Se Renderer foi atribu�do (fallback), renderiza no material
            if (targetRawImage == null && targetRenderer != null)
                targetRenderer.material.mainTexture = _tex;
        }

        byte[] jpg = new byte[len];
        Buffer.BlockCopy(_jpegBuffer, 0, jpg, 0, len);

        ImageConversion.LoadImage(_tex, jpg, false);
        _hasNewFrame = false;
    }

    private void SetupInputActions()
    {
        if (inputActions != null)
        {
            var map = inputActions.FindActionMap(actionMapName, true);
            _clickAction = map.FindAction(clickActionName, true);
            _pointAction = map.FindAction(pointerPositionActionName, true);
            return;
        }

        var mapRuntime = new InputActionMap("RuntimeUI");

        _clickAction = mapRuntime.AddAction("Click", InputActionType.Button);
        _clickAction.AddBinding("<Mouse>/leftButton");
        _clickAction.AddBinding("<Touchscreen>/primaryTouch/press");
        _clickAction.AddBinding("<Pen>/tip");

        _pointAction = mapRuntime.AddAction("Point", InputActionType.Value);
        _pointAction.AddBinding("<Mouse>/position");
        _pointAction.AddBinding("<Touchscreen>/primaryTouch/position");
        _pointAction.AddBinding("<Pen>/position");
    }

    private void EnableInput()
    {
        try { _clickAction?.Enable(); } catch { }
        try { _pointAction?.Enable(); } catch { }
        try { inputActions?.Enable(); } catch { }
    }

    private void DisableInput()
    {
        try { _clickAction?.Disable(); } catch { }
        try { _pointAction?.Disable(); } catch { }
        try { inputActions?.Disable(); } catch { }
    }

    private async Task StreamLoop(CancellationToken ct)
    {
        using var req = new HttpRequestMessage(HttpMethod.Get, streamUrl);
        using var resp = await _http.SendAsync(req, HttpCompletionOption.ResponseHeadersRead, ct);
        resp.EnsureSuccessStatusCode();

        using Stream s = await resp.Content.ReadAsStreamAsync();

        while (!ct.IsCancellationRequested)
        {
            if (!await ReadUntilBoundary(s, ct)) break;

            int contentLength = await ReadHeadersGetContentLength(s, ct);
            if (contentLength <= 0) continue;

            EnsureBuffer(contentLength);

            int readTotal = 0;
            while (readTotal < contentLength && !ct.IsCancellationRequested)
            {
                int n = await s.ReadAsync(_jpegBuffer, readTotal, contentLength - readTotal, ct);
                if (n <= 0) break;
                readTotal += n;
            }

            if (readTotal != contentLength) break;

            await ConsumeOptionalCrlf(s, ct);

            _jpegLen = contentLength;
            _hasNewFrame = true;
        }
    }

    private void EnsureBuffer(int needed)
    {
        if (_jpegBuffer == null || _jpegBuffer.Length < needed)
            _jpegBuffer = new byte[needed];
    }

    private async Task<bool> ReadUntilBoundary(Stream s, CancellationToken ct)
    {
        while (!ct.IsCancellationRequested)
        {
            string line = await ReadLineAscii(s, ct);
            if (line == null) return false;

            line = line.Trim();
            if (line.StartsWith("--frame", StringComparison.Ordinal))
                return true;
        }
        return false;
    }

    private async Task<int> ReadHeadersGetContentLength(Stream s, CancellationToken ct)
    {
        int contentLength = -1;

        while (!ct.IsCancellationRequested)
        {
            string line = await ReadLineAscii(s, ct);
            if (line == null) return -1;

            if (line == "\r\n" || line == "\n" || line.Trim().Length == 0)
                break;

            int idx = line.IndexOf(':');
            if (idx > 0)
            {
                string key = line.Substring(0, idx).Trim();
                if (key.Equals("Content-Length", StringComparison.OrdinalIgnoreCase))
                {
                    string val = line.Substring(idx + 1).Trim();
                    if (int.TryParse(val, out int n) && n > 0)
                        contentLength = n;
                }
            }
        }

        return contentLength;
    }

    private async Task ConsumeOptionalCrlf(Stream s, CancellationToken ct)
    {
        if (!s.CanRead) return;

        byte[] tmp = new byte[2];
        int n1 = await s.ReadAsync(tmp, 0, 1, ct);
        if (n1 <= 0) return;

        if (tmp[0] == (byte)'\r')
            await s.ReadAsync(tmp, 1, 1, ct);
    }

    private async Task<string> ReadLineAscii(Stream s, CancellationToken ct)
    {
        using var ms = new MemoryStream(256);
        byte[] one = new byte[1];

        while (!ct.IsCancellationRequested)
        {
            int n = await s.ReadAsync(one, 0, 1, ct);
            if (n <= 0)
            {
                if (ms.Length == 0) return null;
                break;
            }

            ms.WriteByte(one[0]);
            if (one[0] == (byte)'\n') break;
        }

        return Encoding.ASCII.GetString(ms.ToArray());
    }

    private void HandleClick()
    {
        if (_clickAction == null || _pointAction == null) return;
        if (!_clickAction.WasPressedThisFrame()) return;

        Vector2 screenPos = _pointAction.ReadValue<Vector2>();

        // Caso UI (RawImage)
        if (targetRawImage != null)
        {
            RectTransform rt = targetRawImage.rectTransform;
            Camera uiCam = null;

            // Se Canvas for ScreenSpace-Camera/WorldSpace, precisa de camera
            var canvas = targetRawImage.canvas;
            if (canvas != null && canvas.renderMode != RenderMode.ScreenSpaceOverlay)
                uiCam = canvas.worldCamera != null ? canvas.worldCamera : Camera.main;

            if (!RectTransformUtility.ScreenPointToLocalPointInRectangle(rt, screenPos, uiCam, out Vector2 local))
                return;

            Rect r = rt.rect;

            // local: centro = (0,0). Converter para 0..1 com origem TOP-LEFT
            float x = Mathf.InverseLerp(r.xMin, r.xMax, local.x);      // 0..1 esquerda->direita
            float y = 1f - Mathf.InverseLerp(r.yMin, r.yMax, local.y); // 0..1 cima->baixo

            x = Mathf.Clamp01(x);
            y = Mathf.Clamp01(y);

            _ = SendClick(x, y);
            return;
        }

        // Caso 3D (Renderer/Quad)
        if (targetRenderer == null) return;
        if (topLeftOrigin == null)
        {
            Debug.LogWarning("topLeftOrigin n�o foi atribu�do (canto superior esquerdo).");
            return;
        }

        Camera cam = Camera.main;
        if (cam == null) return;

        Ray ray = cam.ScreenPointToRay(screenPos);

        if (!Physics.Raycast(ray, out RaycastHit hit)) return;
        if (hit.collider.gameObject != targetRenderer.gameObject) return;

        Vector3 down = -targetRenderer.transform.up;
        Vector3 right = targetRenderer.transform.right;

        float widthWorld, heightWorld;
        GetTargetWorldSize(out widthWorld, out heightWorld);
        if (widthWorld <= 0.000001f || heightWorld <= 0.000001f)
        {
            Debug.LogWarning("N�o foi poss�vel calcular o tamanho do target (width/height).");
            return;
        }

        Vector3 delta = hit.point - topLeftOrigin.position;

        float x3d = Vector3.Dot(delta, right) / widthWorld;
        float y3d = Vector3.Dot(delta, down) / heightWorld;

        x3d = Mathf.Clamp01(x3d);
        y3d = Mathf.Clamp01(y3d);

        _ = SendClick(x3d, y3d);
    }

    private void GetTargetWorldSize(out float widthWorld, out float heightWorld)
    {
        widthWorld = 0f;
        heightWorld = 0f;

        var mf = targetRenderer.GetComponent<MeshFilter>();
        if (mf != null && mf.sharedMesh != null)
        {
            Vector3 localSize = mf.sharedMesh.bounds.size;
            Vector3 scale = targetRenderer.transform.lossyScale;

            widthWorld = Mathf.Abs(localSize.x * scale.x);
            heightWorld = Mathf.Abs(localSize.y * scale.y);

            if (heightWorld <= 0.000001f && Mathf.Abs(localSize.z * scale.z) > 0.000001f)
                heightWorld = Mathf.Abs(localSize.z * scale.z);

            return;
        }

        Bounds b = targetRenderer.bounds;
        widthWorld = Mathf.Max(b.size.x, b.size.y, b.size.z);
        heightWorld = widthWorld;
    }

    private async Task SendClick(float x, float y)
    {
        try
        {
            x = Mathf.Clamp01(x);
            y = Mathf.Clamp01(y);

            // garante ponto decimal no JSON (compat�vel com FastAPI/Pydantic)
            string xs = x.ToString("0.######", System.Globalization.CultureInfo.InvariantCulture);
            string ys = y.ToString("0.######", System.Globalization.CultureInfo.InvariantCulture);

            string json = $"{{\"x\":{xs},\"y\":{ys}}}";
            StringContent content = new StringContent(json, Encoding.UTF8, "application/json");

            HttpResponseMessage resp = await _http.PostAsync(clickUrl, content);

            // opcional: log em caso de erro (ex: 422)
            if (!resp.IsSuccessStatusCode)
            {
                string body = await resp.Content.ReadAsStringAsync();
                Debug.LogWarning($"Click HTTP {(int)resp.StatusCode}: {body}");
            }
        }
        catch (Exception e)
        {
            Debug.LogWarning("Erro ao enviar clique: " + e.Message);
        }
    }
}