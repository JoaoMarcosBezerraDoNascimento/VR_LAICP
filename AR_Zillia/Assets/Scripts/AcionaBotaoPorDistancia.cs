using UnityEngine;
using UnityEngine.UI;

public class AcionaBotaoPorDistancia : MonoBehaviour
{
    public string nomeDoIndicador = "XRHand_IndexTip";
    public float distanciaLimite = 0.04f;
    public float distanciaAtual;
    public Button botao;

    public float delayInicial = 1.0f;
    private float tempoDecorrido = 0f;

    private Transform indicador;

    // Controle de clique único
    private bool prontoParaDetectar = false;
    private bool jaCliquei = false;

    void Start()
    {
        indicador = GameObject.Find(nomeDoIndicador)?.transform;
    }

    void Update()
    {
        tempoDecorrido += Time.deltaTime;
        if (!prontoParaDetectar && tempoDecorrido >= delayInicial)
            prontoParaDetectar = true;

        if (!prontoParaDetectar) return;
        if (indicador == null) return;

        distanciaAtual = Vector3.Distance(transform.position, indicador.position);

        // Quando entra na zona e ainda não clicou
        if (distanciaAtual < distanciaLimite && !jaCliquei)
        {
            jaCliquei = true;
            Debug.Log("Botão Clicado");
            botao.onClick.Invoke();
        }

        // Quando sai da zona, libera para clicar de novo no futuro
        if (distanciaAtual >= distanciaLimite && jaCliquei)
        {
            jaCliquei = false;
        }
    }
}
