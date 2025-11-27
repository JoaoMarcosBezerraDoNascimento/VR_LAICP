using UnityEngine;
using UnityEngine.UI;
using TMPro;
using UnityEngine.Windows.Speech;

public class DictationController : MonoBehaviour
{
    public Button startButton;          // Botão da UI que inicia a gravação
    public TextMeshProUGUI outputText;  // Campo TMP onde o texto será exibido

    private DictationRecognizer dictationRecognizer;

    void Start()
    {
        // Inicializa o DictationRecognizer
        dictationRecognizer = new DictationRecognizer();

        dictationRecognizer.DictationResult += (text, confidence) =>
        {
            outputText.text = text; // Atualiza o TMP com o texto reconhecido
        };

        dictationRecognizer.DictationHypothesis += (text) =>
        {
            outputText.text = text; // Exibe texto parcial enquanto fala
        };

        dictationRecognizer.DictationComplete += (completionCause) =>
        {
            if (completionCause != DictationCompletionCause.Complete)
            {
                Debug.LogError("Dictation error: " + completionCause);
            }
        };

        dictationRecognizer.DictationError += (error, hresult) =>
        {
            Debug.LogError("Dictation error: " + error + "; HResult = " + hresult);
        };

        // Associa o botão da UI à função que inicia a gravação
        startButton.onClick.AddListener(StartDictation);
    }

    public void StartDictation()
    {
        if (dictationRecognizer.Status == SpeechSystemStatus.Running)
        {
            dictationRecognizer.Stop();
        }
        else
        {
            dictationRecognizer.Start();
        }
    }

    private void OnDestroy()
    {
        dictationRecognizer.Dispose();
    }
}
