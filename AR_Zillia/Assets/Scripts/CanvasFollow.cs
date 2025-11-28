using UnityEngine;

public class LookAtCameraOptimized : MonoBehaviour
{
    public float smoothSpeed =5f;     // Velocidade da rotação
    public float checkInterval = 1f;   // Intervalo em segundos

    private Transform camTransform;
    private Quaternion targetRotation;
    private float timer = 0f;

    void Start()
    {
        camTransform = Camera.main.transform;
        UpdateTargetRotation(); // inicializa a rotação
    }

    void Update()
    {
        // Atualiza a rotação alvo a cada checkInterval
        timer += Time.deltaTime;
        if (timer >= checkInterval)
        {
            UpdateTargetRotation();
            timer = 0f;
        }

        // Rotação suave contínua
        transform.rotation = Quaternion.Slerp(transform.rotation, targetRotation, Time.deltaTime * smoothSpeed);
    }

    void UpdateTargetRotation()
    {
        Vector3 direction = camTransform.position - transform.position;
        targetRotation = Quaternion.LookRotation(direction);
    }
}
