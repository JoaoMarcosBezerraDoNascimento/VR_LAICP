using UnityEngine;
using UnityEngine.UI;

public class PinchScrollVR : MonoBehaviour
{
    private ScrollRect scroll;

    public string nomeDoIndicador = "XRHand_IndexTip";
    public string nomeDoDedao = "XRHand_ThumbTip";

    public float distanciaLimite = 0.025f;
    public float sensibilidade = 0.5f;

    private Transform indicador;
    private Transform dedao;

    private float ultimoY;
    private bool pinchAtivo = false;

    void Start()
    {
        scroll = GetComponent<ScrollRect>();

        indicador = GameObject.Find(nomeDoIndicador)?.transform;
        dedao = GameObject.Find(nomeDoDedao)?.transform;
    }

    void Update()
    {
        if (scroll == null) return;
        if (indicador == null || dedao == null) return;

        float dist = Vector3.Distance(indicador.position, dedao.position);

        // ------------------------------
        // ATIVA A PINÇA QUANDO APROXIMA
        // ------------------------------
        if (dist < distanciaLimite)
        {
            if (!pinchAtivo)
            {
                pinchAtivo = true;
                ultimoY = indicador.position.y; // inicia o tracking
            }
        }
        else
        {
            pinchAtivo = false;
            return;
        }

        // ------------------------------
        // PASSO 2: SCROLL PELO MOVIMENTO REAL DO DEDO
        // ------------------------------

        float movimentoY = indicador.position.y - ultimoY;

        // inverte sentido para ficar natural (mão pra cima = scroll pra cima)
        scroll.verticalNormalizedPosition += movimentoY * sensibilidade * -1;

        ultimoY = indicador.position.y;
    }
}
