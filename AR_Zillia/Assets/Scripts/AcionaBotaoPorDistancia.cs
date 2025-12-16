using UnityEngine;
using UnityEngine.UI;
using System.Linq;

public class AcionaBotaoPorDistancia : MonoBehaviour
{
    [Header("Indicador")]
    public string nomeDoIndicador = "XRHand_IndexTip";
    public float distanciaLimite = 0.04f;
    public float distanciaAtual;

    [Header("UI (use apenas um)")]
    public Button botao;
    public Toggle toggle;

    [Header("Delay inicial")]
    public float delayInicial = 1.0f;
    float tempoDecorrido;

    [Header("Cooldown")]
    public float cooldownClique = 0.5f;
    float ultimoCliqueTime = -999f;

    [Header("Debug")]
    [SerializeField] Transform indicadorMaisProximo;

    Transform[] indicadores;
    bool prontoParaDetectar;

    void Start()
    {
        AtualizarIndicadores();
    }

    void AtualizarIndicadores()
    {
        indicadores = FindObjectsOfType<Transform>()
            .Where(t => t.name == nomeDoIndicador)
            .ToArray();
    }

    void Update()
    {
        tempoDecorrido += Time.deltaTime;
        if (!prontoParaDetectar && tempoDecorrido >= delayInicial)
            prontoParaDetectar = true;

        if (!prontoParaDetectar || indicadores.Length == 0)
            return;

        float menorDist = float.MaxValue;
        Transform maisProximo = null;

        foreach (var t in indicadores)
        {
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

        if (dentroDaZona && cooldownOk)
        {
            ultimoCliqueTime = Time.time;

            if (botao != null)
            {
                Debug.Log("[AcionaBotao] Clique em Button");
                botao.onClick.Invoke();
            }
            else if (toggle != null)
            {
                Debug.Log("[AcionaBotao] Toggle alternado");
                toggle.isOn = !toggle.isOn;
            }
        }
    }
}
