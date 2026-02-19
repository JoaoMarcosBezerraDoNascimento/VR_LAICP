using UnityEngine;

public class MenuFollowHeadHeight : MonoBehaviour
{
    public Transform cameraTransform;

    [Header("Distância frontal")]
    public float distanciaFrontal = 0.4f;
    public float minDistancia = 0.01f;
    public float maxDistancia = 1.0f;

    [Header("Altura")]
    public float toleranciaAltura = 0.3f;
    public float offsetAltura = -0.3f; // valor padrão (ex: menu um pouco abaixo do olhar)

    [Header("Referência de Spawn")]
    public Transform objetoReferencia;      // Objeto que define a altura (Y)
    public float distanciaExataCamera = 0.4f; // 30 cm à frente da câmera

    void Update()
    {
        if (cameraTransform == null) return;

        float dist = Vector3.Distance(transform.position, cameraTransform.position);
        float diferencaAltura = Mathf.Abs(transform.position.y - AlturaReferencia());

        if (dist < minDistancia || dist > maxDistancia || diferencaAltura > toleranciaAltura)
        {
            AtualizarPosicao();
        }
    }

    void AtualizarPosicao()
    {
        Vector3 posCamera = cameraTransform.position;

        // Sempre exatamente à frente da câmera (30cm por exemplo)
        Vector3 novaPos = posCamera + cameraTransform.forward * distanciaExataCamera;

        // Mantém o Y do objeto de referência
        novaPos.y = AlturaReferencia();

        transform.position = novaPos;

        // Olha para o usuário apenas no eixo Y
        transform.LookAt(cameraTransform);
        transform.rotation = Quaternion.Euler(0, transform.rotation.eulerAngles.y, 0);
    }

    float AlturaReferencia()
    {
        float alturaBase;

        // Se existir objeto de referência, usa o Y dele
        if (objetoReferencia != null)
            alturaBase = objetoReferencia.position.y;
        else
            alturaBase = cameraTransform.position.y;

        // Aplica offset padrão
        return alturaBase + offsetAltura;
    }

}
