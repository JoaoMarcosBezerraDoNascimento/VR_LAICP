using UnityEngine;
using UnityEngine.InputSystem; 

public class MenuSummoner : MonoBehaviour
{
    // --- Configurações do Alvo ---
    [Header("Alvos")]
    [Tooltip("O objeto do Canvas ou Menu que será movido.")]
    public Transform menuTransform;
    
    [Tooltip("A câmera principal (Headset/XR Rig Camera).")]
    public Transform headCamera;

    // --- Posicionamento ---
    [Header("Configuração de Posição")]
    [Tooltip("Distância em metros à frente do operador.")]
    public float distanceFromFace = 1.5f;

    [Tooltip("Ajuste de altura (positivo = para cima, negativo = para baixo).")]
    public float heightOffset = -0.1f;

    // --- Configuração dos Inputs (Mão Esquerda e Direita) ---
    [Header("Controles")]
    [Tooltip("Botão ou Gesto da Mão ESQUERDA.")]
    public InputActionProperty leftHandSummon;

    [Tooltip("Botão ou Gesto da Mão DIREITA.")]
    public InputActionProperty rightHandSummon;

    private void OnEnable()
    {
        // Ativa os inputs se eles tiverem sido definidos
        if (leftHandSummon.action != null) leftHandSummon.action.Enable();
        if (rightHandSummon.action != null) rightHandSummon.action.Enable();
    }

    private void OnDisable()
    {
        if (leftHandSummon.action != null) leftHandSummon.action.Disable();
        if (rightHandSummon.action != null) rightHandSummon.action.Disable();
    }

    private void Update()
    {
        // Verifica se a Esquerda FOI acionada...
        bool leftTriggered = leftHandSummon.action != null && leftHandSummon.action.WasPerformedThisFrame();
        
        // ...OU se a Direita FOI acionada
        bool rightTriggered = rightHandSummon.action != null && rightHandSummon.action.WasPerformedThisFrame();

        // Se qualquer uma das duas for verdadeira, chama o menu
        if (leftTriggered || rightTriggered)
        {
            SummonMenu();
        }
    }

    private void SummonMenu()
    {
        if (headCamera == null || menuTransform == null) return;

        // Define a posição
        Vector3 targetPosition = headCamera.position + (headCamera.forward * distanceFromFace);
        targetPosition.y = headCamera.position.y + heightOffset;

        menuTransform.position = targetPosition;

        // Define a rotação
        Vector3 directionToHead = headCamera.position - menuTransform.position;
        directionToHead.y = 0; 

        if (directionToHead != Vector3.zero)
        {
            menuTransform.rotation = Quaternion.LookRotation(-directionToHead);
        }
    }
}