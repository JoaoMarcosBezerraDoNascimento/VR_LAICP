using UnityEngine;
using UnityEngine.UI;
using TMPro;

public class ChatBubble : MonoBehaviour
{
    public Image backgroundBubble;
    public TextMeshProUGUI messageText;

    // Cores definidas no seu pedido
    private Color userColor = new Color32(33, 47, 153, 255); // #212F99
    private Color aiColor = new Color32(152, 152, 152, 255); // #989898

    public void Setup(string text, bool isUser)
    {
        messageText.text = text;
        backgroundBubble.color = isUser ? userColor : aiColor;

        // Lógica de Alinhamento via Pivot
        // User = Direita | IA = Esquerda
        RectTransform rect = GetComponent<RectTransform>();
        if (isUser)
        {
            rect.pivot = new Vector2(1, 0.5f); // Pivô na direita
            messageText.alignment = TextAlignmentOptions.Left; // Texto interno
        }
        else
        {
            rect.pivot = new Vector2(0, 0.5f); // Pivô na esquerda
            messageText.alignment = TextAlignmentOptions.Left;
        }
    }
}