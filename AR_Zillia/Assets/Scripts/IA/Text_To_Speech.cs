using UnityEngine;
using TMPro;

#if UNITY_ANDROID && !UNITY_EDITOR
using Meta.XR.Voice.TextToSpeech;
#endif

public class Text_To_Speech : MonoBehaviour
{
    [Header("TMP Monitor")]
    [SerializeField] private TMP_Text tmpText;

    [Header("Configurações")]
    [SerializeField] private float cooldown = 0.5f;
    [SerializeField] private int minCaracteres = 2;

#if UNITY_ANDROID && !UNITY_EDITOR
    [Header("Meta Quest")]
    [SerializeField] private TextToSpeech metaTTS;
#endif

    private string lastSpokenText = "";
    private float lastSpeakTime = -999f;

    void Update()
    {
        if (tmpText == null) return;

        string currentText = tmpText.text;

        if (string.IsNullOrWhiteSpace(currentText)) return;
        if (currentText.Length < minCaracteres) return;
        if (currentText == lastSpokenText) return;
        if (Time.time - lastSpeakTime < cooldown) return;

        Speak(currentText);
    }

    void Speak(string text)
    {
        lastSpokenText = text;
        lastSpeakTime = Time.time;

#if UNITY_ANDROID && !UNITY_EDITOR
        if (metaTTS != null)
        {
            metaTTS.Speak(text);
        }
        else
        {
            Debug.LogWarning("Meta TextToSpeech não atribuído.");
        }
#else
        // 🔹 Editor / outras plataformas
        Debug.Log($"[TTS SIMULADO] {text}");
#endif
    }
}
