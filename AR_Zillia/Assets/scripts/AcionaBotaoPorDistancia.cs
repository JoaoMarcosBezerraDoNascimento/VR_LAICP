// AcionaBotaoPorDistancia.cs
using UnityEngine;
using UnityEngine.UI;
using System.Linq;

public class AcionaBotaoPorDistancia : MonoBehaviour
{
    [Header("Modo 1: Clique por distância (ponteira -> este objeto)")]
    public bool habilitarCliquePorDistancia = true;

    [Tooltip("Nome do Transform do indicador (ex: XRHand_IndexTip)")]
    public string nomeDoIndicador = "XRHand_IndexTip";

    [Tooltip("Distância máxima para acionar clique/toggle")]
    public float distanciaLimite = 0.04f;

    [Tooltip("Distância atual (debug)")]
    public float distanciaAtual;

    [Header("UI (use apenas um)")]
    public Button botao;
    public Toggle toggle;

    [Header("Delay inicial (ambos os modos)")]
    public float delayInicial = 1.0f;
    private float tempoDecorrido;

    [Header("Cooldown (apenas clique por distância)")]
    public float cooldownClique = 0.5f;
    private float ultimoCliqueTime = -999f;

    [Header("Auto-refresh (hands podem aparecer depois)")]
    public float refreshIndicadoresSeg = 1.0f;
    private float proxRefresh;

    [Header("Debug (clique por distância)")]
    [SerializeField] private Transform indicadorMaisProximo;
    private Transform[] indicadores = new Transform[0];

    // =========================
    // Modo 2: Scroll por pinça
    // =========================
    [Header("Modo 2: Scroll por pinça")]
    public bool habilitarScrollPorPinca = true;

    [Header("Nomes dos indicadores (pinça)")]
    public string nomeIndicadorIndexTip = "XRHand_IndexTip";
    public string nomePolegarTip = "XRHand_ThumbTip";

    [Header("Scroll")]
    public ScrollRect scrollRect;

    [Tooltip("Quanto o movimento em metros vira scroll (deltaY * sensibilidade)")]
    public float sensibilidade = -2.0f;

    [Tooltip("Inverte o sentido do scroll")]
    public bool inverter = false;

    [Header("Pinça (histerese)")]
    [Tooltip("Distância (m) para considerar PINÇA FECHADA")]
    public float pinchFechado = 0.025f;

    [Tooltip("Distância (m) para considerar PINÇA ABERTA (maior que fechado)")]
    public float pinchAberto = 0.035f;

    [Header("Debug (pinça)")]
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

    // ==== Bloqueio do clique enquanto pinça ====
    [Header("Bloqueio (pinça x clique)")]
    public bool bloquearCliqueDurantePinca = true;

    [Tooltip("Tempo extra (s) para continuar bloqueando o clique após soltar a pinça")]
    public float bloqueioAposSoltarSeg = 0.15f;
    private float bloquearCliqueAte = -999f;
    void Start()
    {
        if (scrollRect == null)
            scrollRect = GetComponentInChildren<ScrollRect>(true);

        AtualizarIndicadores();
        proxRefresh = Time.time + refreshIndicadoresSeg;
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

        if (habilitarScrollPorPinca)
            RodarScrollPorPinca();

        bool cliqueBloqueado = bloquearCliqueDurantePinca && Time.time < bloquearCliqueAte;

        if (habilitarCliquePorDistancia && !cliqueBloqueado)
            RodarCliquePorDistancia();
    }

    void AtualizarIndicadores()
    {
        var all = FindObjectsOfType<Transform>(true);

        // Clique por distância: qualquer Transform com o nome nomeDoIndicador
        indicadores = all.Where(t => t != null && t.name == nomeDoIndicador).ToArray();

        // Pinça: index e polegar
        indexTips = all.Where(t => t != null && t.name == nomeIndicadorIndexTip).ToArray();
        thumbTips = all.Where(t => t != null && t.name == nomePolegarTip).ToArray();
    }

    void RodarCliquePorDistancia()
    {
        if (indicadores == null || indicadores.Length == 0)
            return;

        float menorDist = float.MaxValue;
        Transform maisProximo = null;

        for (int i = 0; i < indicadores.Length; i++)
        {
            var t = indicadores[i];
            if (t == null) continue;

            float d = Vector3.Distance(transform.position, t.position);
            if (d < menorDist)
            {
                menorDist = d;
                maisProximo = t;
            }
        }

        distanciaAtual = menorDist;
        indicadorMaisProximo = maisProximo;

        bool dentroDaZona = menorDist < distanciaLimite;
        bool cooldownOk = Time.time >= ultimoCliqueTime + cooldownClique;

        if (!dentroDaZona || !cooldownOk)
            return;

        ultimoCliqueTime = Time.time;

        if (botao != null)
        {
            if (debugLogs) Debug.Log("[AcionaBotao] Clique em Button");
            botao.onClick.Invoke();
        }
        else if (toggle != null)
        {
            if (debugLogs) Debug.Log("[AcionaBotao] Toggle alternado");
            toggle.isOn = !toggle.isOn;
        }
    }

    void RodarScrollPorPinca()
    {
        if (scrollRect == null || scrollRect.content == null)
            return;

        indexTipMaisProximo = AcharMaisProximo(indexTips);
        thumbTipMaisProximo = AcharMaisProximo(thumbTips);

        if (indexTipMaisProximo == null || thumbTipMaisProximo == null)
            return;

        distanciaPinchAtual = Vector3.Distance(indexTipMaisProximo.position, thumbTipMaisProximo.position);

        // estado da pinça com histerese
        if (!pinçando)
        {
            if (distanciaPinchAtual <= pinchFechado)
            {
                pinçando = true;
                posIndexNoInicioPinch = indexTipMaisProximo.position;
                scrollNoInicioPinch = scrollRect.verticalNormalizedPosition;

                if (bloquearCliqueDurantePinca)
                    bloquearCliqueAte = Mathf.Max(bloquearCliqueAte, Time.time + 999f); // bloqueia enquanto pinça

                if (debugLogs) Debug.Log("[PinchScroll] Pinça começou");
            }
            return;
        }

        if (distanciaPinchAtual >= pinchAberto)
        {
            pinçando = false;

            if (bloquearCliqueDurantePinca)
                bloquearCliqueAte = Mathf.Max(bloquearCliqueAte, Time.time + bloqueioAposSoltarSeg);

            if (debugLogs) Debug.Log("[PinchScroll] Pinça terminou");
            return;
        }

        // Enquanto pinçando: movimento do index -> scroll
        float deltaY = indexTipMaisProximo.position.y - posIndexNoInicioPinch.y;
        float deltaScroll = deltaY * sensibilidade;
        if (inverter) deltaScroll = -deltaScroll;

        float novo = scrollNoInicioPinch + deltaScroll;

        if (novo < 0f) novo = 0f;
        if (novo > 1f) novo = 1f;

        scrollRect.verticalNormalizedPosition = novo;
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
}