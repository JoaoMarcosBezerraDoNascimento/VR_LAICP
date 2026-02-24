// PinchScrollRect.cs
using UnityEngine;
using UnityEngine.UI;
using System.Linq;

public class PinchScrollRect : MonoBehaviour
{
    [Header("Nomes dos indicadores (Meta/OVR/XR Hands)")]
    public string nomeIndicadorIndexTip = "XRHand_IndexTip";
    public string nomePolegarTip = "XRHand_ThumbTip";

    [Header("Scroll")]
    public ScrollRect scrollRect;
    [Tooltip("Quanto o movimento em metros vira scroll. Ex: 2.0 = move 1cm -> 0.02*2 = 0.04 de scroll")]
    public float sensibilidade = -2.0f;
    [Tooltip("Inverte o sentido do scroll")]
    public bool inverter = false;

    [Header("Pinça (histerese)")]
    [Tooltip("Distância em metros para considerar PINÇA FECHADA")]
    public float pinchFechado = 0.025f;
    [Tooltip("Distância em metros para considerar PINÇA ABERTA (deve ser maior que fechado)")]
    public float pinchAberto = 0.035f;

    [Header("Delay inicial")]
    public float delayInicial = 1.0f;
    private float tempoDecorrido;

    [Header("Auto-refresh (hands podem aparecer depois)")]
    public float refreshIndicadoresSeg = 1.0f;
    private float proxRefresh;

    [Header("Debug")]
    public bool debugLogs = true;
    public float distanciaPinchAtual;
    [SerializeField] private Transform indexTipMaisProximo;
    [SerializeField] private Transform thumbTipMaisProximo;
    public bool pinçando;

    private Transform[] indexTips = new Transform[0];
    private Transform[] thumbTips = new Transform[0];

    private bool pronto;
    private Vector3 posIndexNoInicioPinch;
    private float scrollNoInicioPinch;

    void Start()
    {
        AtualizarIndicadores();
        proxRefresh = Time.time + refreshIndicadoresSeg;

        if (scrollRect == null)
            scrollRect = GetComponentInChildren<ScrollRect>(true);
    }

    void AtualizarIndicadores()
    {
        var all = FindObjectsOfType<Transform>(true);
        indexTips = all.Where(t => t != null && t.name == nomeIndicadorIndexTip).ToArray();
        thumbTips = all.Where(t => t != null && t.name == nomePolegarTip).ToArray();
    }

    Transform AcharMaisProximo(Transform[] arr)
    {
        if (arr == null || arr.Length == 0) return null;

        float menor = float.MaxValue;
        Transform best = null;

        for (int i = 0; i < arr.Length; i++)
        {
            var t = arr[i];
            if (t == null) continue;

            float d = Vector3.Distance(transform.position, t.position);
            if (d < menor)
            {
                menor = d;
                best = t;
            }
        }

        return best;
    }

    void Update()
    {
        tempoDecorrido += Time.deltaTime;
        if (!pronto && tempoDecorrido >= delayInicial) pronto = true;
        if (!pronto) return;

        if (Time.time >= proxRefresh)
        {
            proxRefresh = Time.time + refreshIndicadoresSeg;
            AtualizarIndicadores();
        }

        if (scrollRect == null || scrollRect.content == null)
            return;

        indexTipMaisProximo = AcharMaisProximo(indexTips);
        thumbTipMaisProximo = AcharMaisProximo(thumbTips);

        if (indexTipMaisProximo == null || thumbTipMaisProximo == null)
            return;

        distanciaPinchAtual = Vector3.Distance(indexTipMaisProximo.position, thumbTipMaisProximo.position);

        // estado da pinça com histerese (evita flicker)
        if (!pinçando)
        {
            if (distanciaPinchAtual <= pinchFechado)
            {
                pinçando = true;
                posIndexNoInicioPinch = indexTipMaisProximo.position;
                scrollNoInicioPinch = scrollRect.verticalNormalizedPosition;

                if (debugLogs) Debug.Log("[PinchScroll] Pinça começou");
            }
        }
        else
        {
            if (distanciaPinchAtual >= pinchAberto)
            {
                pinçando = false;
                if (debugLogs) Debug.Log("[PinchScroll] Pinça terminou");
                return;
            }

            // enquanto pinçando: movimento do dedo -> scroll
            float deltaY = indexTipMaisProximo.position.y - posIndexNoInicioPinch.y;
            float deltaScroll = deltaY * sensibilidade;
            if (inverter) deltaScroll = -deltaScroll;

            float novo = scrollNoInicioPinch + deltaScroll;

            // clamp 0..1 (ScrollRect usa normalized)
            if (novo < 0f) novo = 0f;
            if (novo > 1f) novo = 1f;

            scrollRect.verticalNormalizedPosition = novo;
        }
    }
}