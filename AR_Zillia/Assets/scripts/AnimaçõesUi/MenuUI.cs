using UnityEngine;
using System.Collections;

[RequireComponent(typeof(CanvasGroup))]
public class EfeitoMenuUI : MonoBehaviour
{
    public float atrasoInicial = 1f;
    public float duracao = 0.8f;
    public float deslocamentoVertical = -0.5f; // Metros (VR)

    private CanvasGroup canvasGroup;
    private Vector3 posicaoFinal;
    private Vector3 posicaoInicial;

    void Awake()
    {
        canvasGroup = GetComponent<CanvasGroup>();
        canvasGroup.alpha = 0;

        posicaoFinal = transform.localPosition;
        posicaoInicial = posicaoFinal + new Vector3(0, deslocamentoVertical, 0);
        transform.localPosition = posicaoInicial;
    }

    void Start()
    {
        StartCoroutine(SequenciaDeEntrada());
    }

    IEnumerator SequenciaDeEntrada()
    {
        // 1. Espera o tempo inicial
        yield return new WaitForSeconds(atrasoInicial);

        // 2. Animação de subir e aparecer
        float tempo = 0;
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

        // Garante valores finais
        transform.localPosition = posicaoFinal;
        canvasGroup.alpha = 1f;

        // 3. Chama animação dos botões
        yield return new WaitForSeconds(0.5f);
        BotoesMenu[] itens = GetComponentsInChildren<BotoesMenu>();
        foreach (var item in itens)
        {
            item.IniciarAnimacao();
        }

        // 4. DESATIVA O SCRIPT
        this.enabled = false;
    }
}
