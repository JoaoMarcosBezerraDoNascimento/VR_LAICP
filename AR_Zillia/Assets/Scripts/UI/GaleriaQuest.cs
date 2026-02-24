using UnityEngine;
using UnityEngine.UI;

public class GaleriaQuest : MonoBehaviour
{
    [Header("UI")]
    public RawImage alvo;

    [Header("Limite (px) para reduzir RAM")]
    public int maxSize = 2048;

    [Header("Debug")]
    public bool debug = true;

    public void EscolherEExibir()
    {
        if (debug) Debug.Log("[GaleriaQuest] EscolherEExibir() chamado");

        if (alvo == null)
        {
            Debug.LogError("[GaleriaQuest] ERRO: RawImage 'alvo' está NULL.");
            return;
        }

        if (debug) Debug.Log("[GaleriaQuest] Abrindo picker NativeGallery...");

        NativeGallery.GetImageFromGallery((path) =>
        {
            if (debug) Debug.Log($"[GaleriaQuest] Callback retornou path = '{path}'");

            if (string.IsNullOrEmpty(path))
            {
                Debug.LogWarning("[GaleriaQuest] path vazio → usuário cancelou OU permissão negada.");
                return;
            }

            if (debug) Debug.Log("[GaleriaQuest] Carregando imagem do path...");

            Texture2D tex = NativeGallery.LoadImageAtPath(path, maxSize, false);

            if (tex == null)
            {
                Debug.LogError("[GaleriaQuest] ERRO: LoadImageAtPath retornou NULL.");
                return;
            }

            if (debug)
                Debug.Log($"[GaleriaQuest] Imagem carregada: {tex.width}x{tex.height} | {tex.format}");

            alvo.texture = tex;
            alvo.SetNativeSize();

            if (debug) Debug.Log("[GaleriaQuest] Imagem aplicada ao RawImage com sucesso.");
        },
        "Selecione uma imagem",
        "image/*");
    }
}