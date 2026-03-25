using UnityEngine;

namespace UI
{
    public class MenuSummonerUI : MonoBehaviour
    {
        [Header("Alvos")]
        public Transform menuTransform;
        public Transform headCamera;

        [Header("Auto Pull")]
        [Tooltip("Se a distância menu↔câmera passar disso, reposiciona.")]
        public float distanciaMaxima = 0.5f;

        [Tooltip("Distância exata em frente da câmera quando puxar.")]
        public float distanciaAoPuxar = 0.3f;

        [Tooltip("Offset vertical aplicado na hora de puxar (0 = mesma altura da câmera).")]
        public float heightOffset = 0.0f;

        [Header("Rotação")]
        [Tooltip("Mantém o menu olhando para a câmera (somente no eixo Y).")]
        public bool olharParaCamera = true;

        private void Update()
        {
            if (menuTransform == null || headCamera == null) return;

            float d = Vector3.Distance(menuTransform.position, headCamera.position);

            // Se afastou mais do que o permitido, puxa para frente da câmera
            if (d > distanciaMaxima)
            {
                Vector3 targetPosition = headCamera.position + (headCamera.forward * distanciaAoPuxar);
                targetPosition.y = headCamera.position.y + heightOffset;

                menuTransform.position = targetPosition;

                if (olharParaCamera)
                {
                    Vector3 dir = headCamera.position - menuTransform.position;
                    dir.y = 0f;

                    if (dir.sqrMagnitude > 0.000001f)
                        menuTransform.rotation = Quaternion.LookRotation(dir);
                }
            }
        }
    }
}
