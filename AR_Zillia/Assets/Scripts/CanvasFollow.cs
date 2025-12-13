using UnityEngine;

public class LookAtCameraOptimized : MonoBehaviour
{
    public float smoothSpeed = 5f;
    public float checkInterval = 1f;
    public Vector3 rotationOffset; // <--- ADICIONE ISTO

    private Transform camTransform;
    private Quaternion targetRotation;
    private float timer = 0f;

    void Start()
    {
        camTransform = Camera.main.transform;
        UpdateTargetRotation();
    }
    void Update()
    {
        timer += Time.deltaTime;
        if (timer >= checkInterval)
        {
            UpdateTargetRotation();
            timer = 0f;
        }

        transform.rotation = Quaternion.Slerp(transform.rotation, targetRotation, Time.deltaTime * smoothSpeed);
    }
    void UpdateTargetRotation()
    {
        Vector3 direction = camTransform.position - transform.position;

        // Zera o eixo Y da direção da câmera para evitar inclinação
        direction.y = 0;

        Quaternion lookRot = Quaternion.LookRotation(direction);
        targetRotation = lookRot;
    }
}
