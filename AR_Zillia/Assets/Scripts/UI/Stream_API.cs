using System;
using System.IO;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.Net.Http;
using UnityEngine;

public class Stream_API : MonoBehaviour
{
    [Header("MJPEG URL (proxy)")]
    public string streamUrl = "http://localhost:8555/remote/JONH_PC/stream";

    [Header("Target Quad (Renderer)")]
    public Renderer targetRenderer; // arraste o Quad aqui

    [Header("Texture Settings")]
    public bool usePointFilter = false;

    private HttpClient _http;
    private CancellationTokenSource _cts;

    private Texture2D _tex;
    private byte[] _jpegBuffer;
    private volatile bool _hasNewFrame;
    private int _jpegLen;

    void Awake()
    {
        if (targetRenderer == null) targetRenderer = GetComponent<Renderer>();
        _http = new HttpClient();
        _http.Timeout = Timeout.InfiniteTimeSpan;
    }

    void OnEnable()
    {
        _cts = new CancellationTokenSource();
        _ = Task.Run(() => StreamLoop(_cts.Token), _cts.Token);
    }

    void OnDisable()
    {
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
        if (!_hasNewFrame) return;

        // pega frame "atomico" (cópia local)
        int len = _jpegLen;
        if (len <= 0 || _jpegBuffer == null || _jpegBuffer.Length < len) { _hasNewFrame = false; return; }

        if (_tex == null)
        {
            _tex = new Texture2D(2, 2, TextureFormat.RGBA32, false, false);
            _tex.wrapMode = TextureWrapMode.Clamp;
            _tex.filterMode = usePointFilter ? FilterMode.Point : FilterMode.Bilinear;

            if (targetRenderer != null)
                targetRenderer.material.mainTexture = _tex;
        }

        // decodifica JPEG -> textura
        // (usa o buffer inteiro, mas só até "len")
        // ImageConversion.LoadImage precisa do array exato; então copiamos somente o tamanho do JPEG.
        byte[] jpg = new byte[len];
        Buffer.BlockCopy(_jpegBuffer, 0, jpg, 0, len);

        bool ok = ImageConversion.LoadImage(_tex, jpg, false);
        _hasNewFrame = false;

        if (!ok)
        {
            // se falhar, mantém a última imagem e segue
        }
    }

    private async Task StreamLoop(CancellationToken ct)
    {
        using var req = new HttpRequestMessage(HttpMethod.Get, streamUrl);
        using var resp = await _http.SendAsync(req, HttpCompletionOption.ResponseHeadersRead, ct);
        resp.EnsureSuccessStatusCode();

        using Stream s = await resp.Content.ReadAsStreamAsync();

        // Lê como MJPEG multipart:
        // --frame\r\n
        // Content-Type: image/jpeg\r\n
        // Content-Length: N\r\n
        // \r\n
        // <N bytes JPEG>
        // \r\n
        while (!ct.IsCancellationRequested)
        {
            // 1) sincroniza no boundary "--frame"
            if (!await ReadUntilBoundary(s, ct)) break;

            // 2) lê headers até linha vazia
            int contentLength = await ReadHeadersGetContentLength(s, ct);
            if (contentLength <= 0) continue;

            // 3) lê exatamente N bytes do JPEG
            EnsureBuffer(contentLength);
            int readTotal = 0;
            while (readTotal < contentLength && !ct.IsCancellationRequested)
            {
                int n = await s.ReadAsync(_jpegBuffer, readTotal, contentLength - readTotal, ct);
                if (n <= 0) break;
                readTotal += n;
            }
            if (readTotal != contentLength) break;

            // 4) consome CRLF final (se vier)
            await ConsumeOptionalCrlf(s, ct);

            // publica frame pro Update()
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
        // procura a sequência "\r\n--frame" ou "--frame" no começo.
        // estratégia: varre linhas até achar uma que começa com "--frame"
        while (!ct.IsCancellationRequested)
        {
            string line = await ReadLineAscii(s, ct);
            if (line == null) return false;

            line = line.Trim();
            if (line.StartsWith("--frame", StringComparison.Ordinal)) return true;
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

            // linha vazia = fim dos headers
            if (line == "\r\n" || line == "\n" || line.Trim().Length == 0) break;

            // Content-Length
            // ex: "Content-Length: 12345"
            int idx = line.IndexOf(':');
            if (idx > 0)
            {
                string key = line.Substring(0, idx).Trim();
                if (key.Equals("Content-Length", StringComparison.OrdinalIgnoreCase))
                {
                    string val = line.Substring(idx + 1).Trim();
                    if (int.TryParse(val, out int n) && n > 0) contentLength = n;
                }
            }
        }

        return contentLength;
    }

    private async Task ConsumeOptionalCrlf(Stream s, CancellationToken ct)
    {
        // tenta ler \r\n sem travar: se não for, “devolve” não dá em Stream.
        // então fazemos um read pequeno e ignoramos se vier.
        if (!s.CanRead) return;

        byte[] tmp = new byte[2];
        s.ReadTimeout = Timeout.Infinite;

        // usa ReadAsync com timeout via cancellation
        int n1 = await s.ReadAsync(tmp, 0, 1, ct);
        if (n1 <= 0) return;

        if (tmp[0] == (byte)'\r')
        {
            int n2 = await s.ReadAsync(tmp, 1, 1, ct);
            return;
        }

        // se não era \r, era byte já do próximo boundary/linha.
        // não dá pra "unread" num Stream normal; porém como o boundary vem em linha,
        // o parser ReadLineAscii vai se realinhar (vai pegar o resto daquela linha).
    }

    private async Task<string> ReadLineAscii(Stream s, CancellationToken ct)
    {
        // lê até '\n' (inclui '\n' na string), ASCII
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
}
