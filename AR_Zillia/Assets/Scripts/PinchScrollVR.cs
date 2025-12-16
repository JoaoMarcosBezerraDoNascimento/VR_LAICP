using UnityEngine;
using UnityEngine.UI;

public class PinchScrollPorRigidBody : MonoBehaviour
{
    [Header("Referências")]
    public ScrollRect scroll;

    [Tooltip("GameObject do dedo indicador")]
    public GameObject indicador;

    [Tooltip("GameObject do dedo polegar")]
    public GameObject polegar;

    [Header("Configuração do Pinch")]
    public float distanciaLimite = 0.04f;
    public float sensibilidade = 0.6f;

    Rigidbody rbIndicador;
    Rigidbody rbPolegar;

    bool pinchAtivo;
    float ultimoY;

    void Awake()
    {
        // Busca automaticamente os rigidbodys
        if (indicador != null)
            rbIndicador = indicador.GetComponent<Rigidbody>();

        if (polegar != null)
            rbPolegar = polegar.GetComponent<Rigidbody>();

        if (rbIndicador == null || rbPolegar == null)
        {
            Debug.LogError("❌ Um dos GameObjects não possui Rigidbody.");
            enabled = false;
        }
    }

    void Update()
    {
        if (scroll == null) return;

        float distancia = Vector3.Distance(
            rbIndicador.position,
            rbPolegar.position
        );

        if (distancia < distanciaLimite)
        {
            if (!pinchAtivo)
            {
                pinchAtivo = true;
                ultimoY = rbIndicador.position.y;
            }

            float deltaY = rbIndicador.position.y - ultimoY;

            scroll.verticalNormalizedPosition -= deltaY * sensibilidade;
            scroll.verticalNormalizedPosition =
                Mathf.Clamp01(scroll.verticalNormalizedPosition);

            ultimoY = rbIndicador.position.y;
        }
        else
        {
            pinchAtivo = false;
        }
    }
}
