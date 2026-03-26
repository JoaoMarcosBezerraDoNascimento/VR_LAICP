using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using UnityEngine;
using UnityEngine.Android;
using UnityEngine.Networking;
using UnityEngine.UI;

public class QuestGalleryDCIMCamera : MonoBehaviour
{
    [Header("Display (use 1 ou os 2)")]
    public RawImage targetRawImage;          // UI RawImage
    public Renderer targetRenderer;          // Quad/Plane Renderer

    [Header("Load")]
    public bool loadFullResolution = false;  // false = tenta carregar menor (ainda pode vir grande, depende do device)
    public int maxTextureSize = 2048;        // limite para reduzir memória (se necessário)

    [Header("Debug")]
    public Text debugText;

    private readonly List<string> _contentUris = new List<string>();
    private int _index = 0;
    private Texture2D _currentTex;

    public void StartGallery()
    {
        StartCoroutine(StartGalleryCoroutine());
    }

    public void Next()
    {
        if (_contentUris.Count == 0) return;
        _index = (_index + 1) % _contentUris.Count;
        StartCoroutine(ShowCurrentCoroutine());
    }

    public void Prev()
    {
        if (_contentUris.Count == 0) return;
        _index = (_index - 1 + _contentUris.Count) % _contentUris.Count;
        StartCoroutine(ShowCurrentCoroutine());
    }

    private IEnumerator StartGalleryCoroutine()
    {
        Log("Iniciando: pedindo permissão e lendo MediaStore...");

#if UNITY_ANDROID && !UNITY_EDITOR
        string perm = GetReadImagesPermissionForThisAndroid();
        if (!Permission.HasUserAuthorizedPermission(perm))
        {
            Permission.RequestUserPermission(perm);

            float t = 0f;
            while (!Permission.HasUserAuthorizedPermission(perm) && t < 10f)
            {
                t += Time.unscaledDeltaTime;
                yield return null;
            }

            if (!Permission.HasUserAuthorizedPermission(perm))
            {
                Log("Permissão negada ou não concedida.");
                yield break;
            }
        }

        yield return StartCoroutine(QueryDcimCameraImagesCoroutine());

        if (_contentUris.Count == 0)
        {
            Log("Nenhuma imagem encontrada via MediaStore.");
            yield break;
        }

        _index = Mathf.Clamp(_index, 0, _contentUris.Count - 1);
        yield return StartCoroutine(ShowCurrentCoroutine());

#else
        Log("Este script só funciona no Android (Quest). No Editor não lista a galeria.");
        yield break;
#endif
    }

    private IEnumerator QueryDcimCameraImagesCoroutine()
    {
        _contentUris.Clear();

#if UNITY_ANDROID && !UNITY_EDITOR
        try
        {
            using (AndroidJavaClass unityPlayer = new AndroidJavaClass("com.unity3d.player.UnityPlayer"))
            using (AndroidJavaObject activity = unityPlayer.GetStatic<AndroidJavaObject>("currentActivity"))
            using (AndroidJavaObject contentResolver = activity.Call<AndroidJavaObject>("getContentResolver"))
            using (AndroidJavaClass mediaStoreFiles = new AndroidJavaClass("android.provider.MediaStore$Files"))
            using (AndroidJavaObject externalUri = mediaStoreFiles.CallStatic<AndroidJavaObject>("getContentUri", "external"))
            using (AndroidJavaClass buildVersion = new AndroidJavaClass("android.os.Build$VERSION"))
            {
                
                int sdk = buildVersion.GetStatic<int>("SDK_INT");

                string colId = "_id";
                string colRelPath = "relative_path";
                string colData = "_data";
                string colName = "_display_name";

                string[] projection;

                string selection = null;
                string[] selectionArgs = null;
                string colMime = "mime_type";

                if (sdk >= 29)
                {
                    projection = new string[] { colId, colRelPath, colName, colMime };
                    selection = colMime + " LIKE ? AND (" + colRelPath + "=? OR " + colRelPath + "=?)";
                    selectionArgs = new string[] { "image/%", "DCIM/Camera/", "Oculus/Screenshots/" };
                }
                else
                {
                    projection = new string[] { colId, colData, colName, colMime };
                    selection = colMime + " LIKE ? AND (" + colData + " LIKE ? OR " + colData + " LIKE ?)";
                    selectionArgs = new string[] { "image/%", "%/DCIM/Camera/%", "%/Oculus/Screenshots/%" };
                }
                string sortOrder = "date_added DESC";

                // cursor = contentResolver.query(uri, projection, selection, selectionArgs, sortOrder)
                using (AndroidJavaObject cursor = contentResolver.Call<AndroidJavaObject>(
                    "query",
                    externalUri,
                    projection,
                    selection,
                    selectionArgs,
                    sortOrder
                ))
                {
                    if (cursor == null)
                    {
                        Log("Cursor null (query falhou).");
                        yield break;
                    }

                    int count = cursor.Call<int>("getCount");
                    Log("Encontradas (query): " + count);

                    int idxId = cursor.Call<int>("getColumnIndex", colId);
                    int idxName = cursor.Call<int>("getColumnIndex", colName);
                    int idxRel = sdk >= 29 ? cursor.Call<int>("getColumnIndex", colRelPath) : -1;
                    int idxMime = cursor.Call<int>("getColumnIndex", colMime);

                    while (cursor.Call<bool>("moveToNext"))
                    {
                        long id = cursor.Call<long>("getLong", idxId);
                        string name = idxName >= 0 ? cursor.Call<string>("getString", idxName) : "";
                        string rel = (sdk >= 29 && idxRel >= 0) ? cursor.Call<string>("getString", idxRel) : "";
                        string mime = idxMime >= 0 ? cursor.Call<string>("getString", idxMime) : "";

                        Log("RELATIVE_PATH=" + rel + " | MIME=" + mime + " | NAME=" + name);
                        using (AndroidJavaClass contentUris = new AndroidJavaClass("android.content.ContentUris"))
                        using (AndroidJavaObject contentUriObj = contentUris.CallStatic<AndroidJavaObject>("withAppendedId", externalUri, id))
                        {
                            string contentUriStr = contentUriObj.Call<string>("toString");
                            _contentUris.Add(contentUriStr);
                        }
                    }
                }
            }
        }
        catch (Exception e)
        {
            Log("Erro na query MediaStore: " + e.Message);
            yield break;
        }
#else
        yield break;
#endif

        yield return null;
    }

    private IEnumerator ShowCurrentCoroutine()
    {
        if (_contentUris.Count == 0) yield break;

        string uri = _contentUris[_index];
        Log($"Mostrando {_index + 1}/{_contentUris.Count}: {uri}");

#if UNITY_ANDROID && !UNITY_EDITOR
        byte[] bytes = null;

        try
        {
            bytes = ReadAllBytesFromContentUri(uri);
        }
        catch (Exception e)
        {
            Log("Falha ao ler bytes: " + e.Message);
            yield break;
        }

        if (bytes == null || bytes.Length == 0)
        {
            Log("Bytes vazios ao ler a imagem.");
            yield break;
        }

        // Limpa textura anterior
        if (_currentTex != null)
        {
            Destroy(_currentTex);
            _currentTex = null;
        }

        // Carrega Texture2D
        _currentTex = new Texture2D(2, 2, TextureFormat.RGBA32, false, false);
        bool ok = _currentTex.LoadImage(bytes, markNonReadable: false);

        if (!ok)
        {
            Log("LoadImage falhou para este arquivo.");
            yield break;
        }

        // Opcional: limitar tamanho (reduz memória)
        if (!loadFullResolution && (Mathf.Max(_currentTex.width, _currentTex.height) > maxTextureSize))
        {
            Texture2D scaled = ScaleDownToMax(_currentTex, maxTextureSize);
            Destroy(_currentTex);
            _currentTex = scaled;
        }

        ApplyTexture(_currentTex);

#else
        yield break;
#endif

        yield return null;
    }

#if UNITY_ANDROID && !UNITY_EDITOR
    private string GetReadImagesPermissionForThisAndroid()
    {
        int sdk = 0;
        using (AndroidJavaClass buildVersion = new AndroidJavaClass("android.os.Build$VERSION"))
            sdk = buildVersion.GetStatic<int>("SDK_INT");

        // Android 13+ => READ_MEDIA_IMAGES
        if (sdk >= 33) return "android.permission.READ_MEDIA_IMAGES";

        // Android 12- => READ_EXTERNAL_STORAGE
        return Permission.ExternalStorageRead;
    }

    private byte[] ReadAllBytesFromContentUri(string contentUriStr)
    {
        using (AndroidJavaClass unityPlayer = new AndroidJavaClass("com.unity3d.player.UnityPlayer"))
        using (AndroidJavaObject activity = unityPlayer.GetStatic<AndroidJavaObject>("currentActivity"))
        using (AndroidJavaObject contentResolver = activity.Call<AndroidJavaObject>("getContentResolver"))
        using (AndroidJavaClass uriClass = new AndroidJavaClass("android.net.Uri"))
        using (AndroidJavaObject uriObj = uriClass.CallStatic<AndroidJavaObject>("parse", contentUriStr))
        using (AndroidJavaObject inputStream = contentResolver.Call<AndroidJavaObject>("openInputStream", uriObj))
        {
            if (inputStream == null) return null;

            // Lê tudo em ByteArrayOutputStream
            using (AndroidJavaObject baos = new AndroidJavaObject("java.io.ByteArrayOutputStream"))
            {
                byte[] buffer = new byte[64 * 1024];

                using (AndroidJavaObject jBuffer = new AndroidJavaObject("byte[]", buffer.Length))
                {
                    while (true)
                    {
                        int read = inputStream.Call<int>("read", jBuffer);
                        if (read <= 0) break;

                        // extrai bytes do jBuffer para um array C# temporário com o tamanho "read"
                        byte[] tmp = AndroidJNIHelper.ConvertFromJNIArray<byte[]>(jBuffer.GetRawObject());
                        if (tmp.Length != buffer.Length)
                        {
                            // segurança: garante tamanho esperado
                            Array.Resize(ref tmp, buffer.Length);
                        }

                        baos.Call("write", tmp, 0, read);
                    }
                }

                byte[] outBytes = AndroidJNIHelper.ConvertFromJNIArray<byte[]>(baos.Call<AndroidJavaObject>("toByteArray").GetRawObject());
                return outBytes;
            }
        }
    }
#endif

    private void ApplyTexture(Texture2D tex)
    {
        if (targetRawImage != null)
        {
            targetRawImage.texture = tex;
            targetRawImage.SetNativeSize();
        }

        if (targetRenderer != null)
        {
            targetRenderer.material.mainTexture = tex;
        }
    }

    private Texture2D ScaleDownToMax(Texture2D src, int maxSize)
    {
        int w = src.width;
        int h = src.height;

        float scale = 1f;
        int maxDim = Mathf.Max(w, h);
        if (maxDim > maxSize) scale = (float)maxSize / maxDim;

        int nw = Mathf.Max(2, Mathf.RoundToInt(w * scale));
        int nh = Mathf.Max(2, Mathf.RoundToInt(h * scale));

        RenderTexture rt = RenderTexture.GetTemporary(nw, nh, 0, RenderTextureFormat.ARGB32);
        Graphics.Blit(src, rt);

        RenderTexture prev = RenderTexture.active;
        RenderTexture.active = rt;

        Texture2D dst = new Texture2D(nw, nh, TextureFormat.RGBA32, false, false);
        dst.ReadPixels(new Rect(0, 0, nw, nh), 0, 0);
        dst.Apply();

        RenderTexture.active = prev;
        RenderTexture.ReleaseTemporary(rt);

        return dst;
    }

    private void Log(string msg)
    {
        Debug.Log("[QuestGalleryDCIMCamera] " + msg);
        if (debugText != null) debugText.text = msg;
    }
}