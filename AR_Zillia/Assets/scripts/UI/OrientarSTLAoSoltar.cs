using UnityEngine;
using UnityEngine.XR.Interaction.Toolkit;

public class OrientarSTLAoSoltar : MonoBehaviour
{
    public enum EixoLocal
    {
        XPositivo,
        XNegativo,
        YPositivo,
        YNegativo,
        ZPositivo,
        ZNegativo
    }

    [Header("Orientação")]
    public EixoLocal eixoQueDeveFicarParaCima = EixoLocal.YPositivo;
    public bool manterRotacaoNoY = true;

    [Header("Ajuste de altura")]
    public bool encostarNoChaoAoSoltar = true;
    public float offsetDoChao = 0.0f;

    [Header("Referências")]
    public UnityEngine.XR.Interaction.Toolkit.Interactables.XRGrabInteractable grab = null;
    public Renderer rendererDoModelo = null;

    void Reset()
    {
        grab = GetComponent<UnityEngine.XR.Interaction.Toolkit.Interactables.XRGrabInteractable>();
        if (rendererDoModelo == null)
        {
            rendererDoModelo = GetComponentInChildren<Renderer>();
        }
    }

    void OnEnable()
    {
        if (grab == null)
        {
            grab = GetComponent<UnityEngine.XR.Interaction.Toolkit.Interactables.XRGrabInteractable>();
        }

        if (rendererDoModelo == null)
        {
            rendererDoModelo = GetComponentInChildren<Renderer>();
        }

        if (grab != null)
        {
            grab.selectExited.AddListener(AoSoltar);
        }
    }

    void OnDisable()
    {
        if (grab != null)
        {
            grab.selectExited.RemoveListener(AoSoltar);
        }
    }

    void AoSoltar(SelectExitEventArgs args)
    {
        Vector3 eixoLocal = Vector3.up;

        if (eixoQueDeveFicarParaCima == EixoLocal.XPositivo) eixoLocal = Vector3.right;
        if (eixoQueDeveFicarParaCima == EixoLocal.XNegativo) eixoLocal = Vector3.left;
        if (eixoQueDeveFicarParaCima == EixoLocal.YPositivo) eixoLocal = Vector3.up;
        if (eixoQueDeveFicarParaCima == EixoLocal.YNegativo) eixoLocal = Vector3.down;
        if (eixoQueDeveFicarParaCima == EixoLocal.ZPositivo) eixoLocal = Vector3.forward;
        if (eixoQueDeveFicarParaCima == EixoLocal.ZNegativo) eixoLocal = Vector3.back;

        Vector3 eixoAtualNoMundo = transform.TransformDirection(eixoLocal);
        Quaternion rotacaoParaFicarEmPe = Quaternion.FromToRotation(eixoAtualNoMundo, Vector3.up) * transform.rotation;

        if (manterRotacaoNoY)
        {
            Vector3 frenteProjetada = Vector3.ProjectOnPlane(rotacaoParaFicarEmPe * Vector3.forward, Vector3.up);

            if (frenteProjetada.sqrMagnitude > 0.0001f)
            {
                transform.rotation = Quaternion.LookRotation(frenteProjetada.normalized, Vector3.up);
            }
            else
            {
                transform.rotation = rotacaoParaFicarEmPe;
            }
        }
        else
        {
            transform.rotation = rotacaoParaFicarEmPe;
        }

        if (encostarNoChaoAoSoltar && rendererDoModelo != null)
        {
            Bounds b = rendererDoModelo.bounds;
            float subir = transform.position.y - b.min.y + offsetDoChao;
            transform.position = new Vector3(
                transform.position.x,
                transform.position.y + subir,
                transform.position.z
            );
        }

        Rigidbody rb = GetComponent<Rigidbody>();
        if (rb != null)
        {
            rb.linearVelocity = Vector3.zero;
            rb.angularVelocity = Vector3.zero;
        }
    }
}