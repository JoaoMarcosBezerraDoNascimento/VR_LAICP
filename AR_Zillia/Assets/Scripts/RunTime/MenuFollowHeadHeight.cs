using UnityEngine;

public class MenuFollowHeadHeight : MonoBehaviour
{
    public Transform cameraTransform;
    public float distanciaFrontal = 1.5f;

    public float minDistancia = 1.0f;   // muito perto → reposiciona
    public float maxDistancia = 2.0f;   // muito longe → reposiciona

    void Update()
    {
        if (cameraTransform == null) return;

        float dist = Vector3.Distance(transform.position, cameraTransform.position);

        // Só atualiza a posição se estiver muito perto ou muito longe
        if (dist < minDistancia || dist > maxDistancia)
        {
            AtualizarPosicao();
        }
    }

    void AtualizarPosicao()
    {
        Vector3 pos = cameraTransform.position;

        // Posição na frente da câmera
        Vector3 novaPos = pos + cameraTransform.forward * distanciaFrontal;

        // Ajusta altura do menu para a altura dos olhos
        novaPos.y = pos.y;

        transform.position = novaPos;

        // Faz o menu olhar para o usuário, mas mantendo alinhamento apenas no eixo Y
        transform.LookAt(cameraTransform);
        transform.rotation = Quaternion.Euler(0, transform.rotation.eulerAngles.y, 0);
    }
}
