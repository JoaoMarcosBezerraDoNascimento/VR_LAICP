using UnityEngine;
public class CanvasFollow : MonoBehaviour
{
    public Transform alvo;         // Objeto que o Canvas vai seguir
    public Vector3 offset;         // Posição relativa
    public float anguloLimite = 45f; // Ângulo em que o Canvas deita
    public bool olharParaCamera = true; // Se deve sempre mirar na câmera

    void LateUpdate()
    {
        if (alvo == null) return;

        // Segue a posição
        transform.position = alvo.position + offset;

        // Calcula o ângulo do objeto em relação à vertical (Y)
        float anguloX = Mathf.Abs(alvo.eulerAngles.x);
        anguloX = (anguloX > 180) ? 360 - anguloX : anguloX; // Normaliza para 0-180

        // Decide se mantém reto ou deita
        if (anguloX > anguloLimite)
        {
            // Deita 90° no eixo X
            transform.rotation = Quaternion.Euler(90, transform.eulerAngles.y, transform.eulerAngles.z);
        }
        else
        {
            // Mantém reto em relação à gravidade
            transform.rotation = Quaternion.Euler(0, transform.eulerAngles.y, 0);
        }

        // Opcional: sempre olhar para a câmera (em Y, mantendo X fixo)
        if (olharParaCamera)
        {
            Vector3 dir = transform.position - Camera.main.transform.position;
            dir.y = 0; // Ignora altura
            if (dir.sqrMagnitude > 0.001f)
                transform.rotation = Quaternion.LookRotation(dir);
        }
    }
}
