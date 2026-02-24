// PinchScrollVR.cs
using UnityEngine;
using UnityEngine.UI;
using System.Linq;

public class PinchScrollVR : MonoBehaviour
{
    [Header("Nomes dos indicadores (Transform)")]
    public string nomeIndexTip = "XRHand_IndexTip";
    public string nomeThumbTip = "XRHand_ThumbTip";

    [Header("Pinch")]
    public float distanciaLimite = 0.015f;
    public float sensibilidade = 0.5f;

    [Header("Delay inicial")]
    public float delayInicial = 1.0f;
    private float tempoDecorrido;
    private bool pronto;

    [Header("Auto-refresh (caso os hands apareçam depois)")]
    public float refreshIndicadoresSeg = 1.0f;
    private float proxRefresh;

    [Header("Debug")]
    public float distanciaAtual;
    [SerializeField] private Transform indexMaisProximo;
    [SerializeField] private Transform thumbCorrespondente;

    private ScrollRect scroll;

    private Transform[] indices = new Transform[0];
    private Transform[] thumbs = new Transform[0];

    private bool pinchAtivo;
    private float ultimoY;

    void Start()
    {
        scroll = GetComponent<ScrollRect>();
        AtualizarIndicadores();
        proxRefresh = Time.time + refreshIndicadoresSeg;
    }

    void AtualizarIndicadores()
    {
        var all = FindObjectsOfType<Transform>(true);
        indices = all.Where(t => t != null && t.name == nomeIndexTip).ToArray();
        thumbs = all.Where(t => t != null && t.name == nomeThumbTip).ToArray();
    }

    void Update()
    {
        if (scroll == null) return;

        tempoDecorrido += Time.deltaTime;
        if (!pronto && tempoDecorrido >= delayInicial) pronto = true;
        if (!pronto) return;

        if (Time.time >= proxRefresh)
        {
            proxRefresh = Time.time + refreshIndicadoresSeg;
            AtualizarIndicadores();
        }

        if (indices == null || thumbs == null || indices.Length == 0 || thumbs.Length == 0)
            return;

        // 1) acha o IndexTip mais perto do objeto (alvo)
        float menor = float.MaxValue;
        Transform idx = null;

        for (int i = 0; i < indices.Length; i++)
        {
            var t = indices[i];
            if (t == null) continue;

            float d = Vector3.Distance(transform.position, t.position);
            if (d < menor)
            {
                menor = d;
                idx = t;
            }
        }

        if (idx == null) return;

        // 2) tenta achar o ThumbTip da mesma mão (mesmo parent), senão pega o mais próximo do Index
        Transform th = null;

        var parent = idx.parent;
        if (parent != null)
        {
            for (int i = 0; i < thumbs.Length; i++)
            {
                var t = thumbs[i];
                if (t == null) continue;

                if (t.parent == parent)
                {
                    th = t;
                    break;
                }
            }
        }

        if (th == null)
        {
            float menorThumb = float.MaxValue;
            for (int i = 0; i < thumbs.Length; i++)
            {
                var t = thumbs[i];
                if (t == null) continue;

                float d = Vector3.Distance(idx.position, t.position);
                if (d < menorThumb)
                {
                    menorThumb = d;
                    th = t;
                }
            }
        }

        if (th == null) return;

        indexMaisProximo = idx;
        thumbCorrespondente = th;

        // 3) pinch = distância entre index e thumb
        float dist = Vector3.Distance(idx.position, th.position);
        distanciaAtual = dist;

        if (dist < distanciaLimite)
        {
            if (!pinchAtivo)
            {
                pinchAtivo = true;
                ultimoY = idx.position.y;
                return;
            }

            float deltaY = idx.position.y - ultimoY;

            scroll.verticalNormalizedPosition = Mathf.Clamp01(
                scroll.verticalNormalizedPosition + (deltaY * sensibilidade * -1f)
            );

            ultimoY = idx.position.y;
        }
        else
        {
            pinchAtivo = false;
        }
    }
}