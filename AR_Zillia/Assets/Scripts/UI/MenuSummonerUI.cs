using UnityEngine;
using UnityEngine.InputSystem;

namespace UI
{
    public class MenuSummonerUI : MonoBehaviour
    {
        [Header("Alvos")]
        public Transform menuTransform;
        public Transform headCamera;

        [Header("Configuração de Posição")]
        public float distanceFromFace = 1.5f;
        public float heightOffset = -0.1f;

        [Header("Controles")]
        public InputActionProperty leftHandSummon;
        public InputActionProperty rightHandSummon;

        private void OnEnable()
        {
            if (leftHandSummon.action != null)
                leftHandSummon.action.Enable();

            if (rightHandSummon.action != null)
                rightHandSummon.action.Enable();
        }

        private void OnDisable()
        {
            if (leftHandSummon.action != null)
                leftHandSummon.action.Disable();

            if (rightHandSummon.action != null)
                rightHandSummon.action.Disable();
        }

        private void Update()
        {
            bool leftTriggered =
                leftHandSummon.action != null &&
                leftHandSummon.action.WasPerformedThisFrame();

            bool rightTriggered =
                rightHandSummon.action != null &&
                rightHandSummon.action.WasPerformedThisFrame();

            if (leftTriggered || rightTriggered)
                SummonMenu();
        }

        private void SummonMenu()
        {
            if (headCamera == null || menuTransform == null)
                return;

            Vector3 targetPosition =
                headCamera.position + (headCamera.forward * distanceFromFace);

            targetPosition.y = headCamera.position.y + heightOffset;
            menuTransform.position = targetPosition;

            Vector3 directionToHead = headCamera.position - menuTransform.position;
            directionToHead.y = 0;

            if (directionToHead != Vector3.zero)
                menuTransform.rotation = Quaternion.LookRotation(-directionToHead);
        }
    }
}
