using UnityEngine;

public class LookAtCameraOptimized : MonoBehaviour
{
    public float smoothSpeed = 5f;
    public float checkInterval = 1f;

    [Header("Distância mínima para girar")]
    public float distanciaMinima = 0.2f; // Ex: 40 cm

    public Vector3 rotationOffset;

    private Transform camTransform;
    private Quaternion targetRotation;
    private float timer = 0f;
    private bool podeGirar = true;

    void Start()
    {
        camTransform = Camera.main.transform;
        UpdateTargetRotation();
    }

    void Update()
    {
        if (camTransform == null) return;

        float distancia = Vector3.Distance(transform.position, camTransform.position);
        podeGirar = distancia > distanciaMinima;

        timer += Time.deltaTime;
        if (timer >= checkInterval && podeGirar)
        {
            UpdateTargetRotation();
            timer = 0f;
        }

        if (podeGirar)
        {
            transform.rotation = Quaternion.Slerp(
                transform.rotation,
                targetRotation,
                Time.deltaTime * smoothSpeed
            );
        }
    }

    void UpdateTargetRotation()
    {
        Vector3 direction = camTransform.position - transform.position;
        direction.y = 0;

        Quaternion lookRot = Quaternion.LookRotation(direction);

        // Aplica offset de rotação
        lookRot *= Quaternion.Euler(rotationOffset);

        targetRotation = lookRot;
    }
}
