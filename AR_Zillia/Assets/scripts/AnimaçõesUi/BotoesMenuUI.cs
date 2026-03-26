using UnityEngine;
using System.Collections;

[RequireComponent(typeof(CanvasGroup))]
public class BotoesMenuUI : MonoBehaviour
{
    public float duracao = 0.5f;
    public float deslocamentoHorizontal = -0.2f; // Metros (VR)

    private CanvasGroup canvasGroup;
    private Vector3 posicaoFinal;
    private Vector3 posicaoInicial;

    void Awake()
    {
        canvasGroup = GetComponent<CanvasGroup>();
        canvasGroup.alpha = 0;

        posicaoFinal = transform.localPosition;
        posicaoInicial = posicaoFinal + new Vector3(deslocamentoHorizontal, 0, 0);

        transform.localPosition = posicaoInicial;
    }

    public void IniciarAnimacao()
    {
        StartCoroutine(AnimarEntrada());
    }

    IEnumerator AnimarEntrada()
    {
        float tempo = 0f;

        while (tempo < duracao)
        {
            tempo += Time.deltaTime;
            float t = tempo / duracao;

            // Ease Out
            t = t * (2 - t);

            transform.localPosition = Vector3.Lerp(posicaoInicial, posicaoFinal, t);
            canvasGroup.alpha = Mathf.Lerp(0, 1, t);

            yield return null;
        }

        // Garantia final
        transform.localPosition = posicaoFinal;
        canvasGroup.alpha = 1;
    }
}
