using System.Text;
using UnityEngine;
using TMPro;

public class DebugLogToCanvas : MonoBehaviour
{
    [Header("UI")]
    public TMP_Text output;

    [Header("Config")]
    public int maxChars = 12000;
    public int maxLines = 200;
    public bool showStackTraceOnErrors = true;
    public bool includeTimestamps = true;

    private readonly StringBuilder _sb = new StringBuilder(16000);

    void OnEnable()
    {
        Application.logMessageReceived += OnLog;
    }

    void OnDisable()
    {
        Application.logMessageReceived -= OnLog;
    }

    void Start()
    {
        if (output != null) output.text = "";
    }

    void OnLog(string condition, string stackTrace, LogType type)
    {
        if (output == null) return;

        string prefix = includeTimestamps ? $"[{System.DateTime.Now:HH:mm:ss}] " : "";
        string typeTag = type == LogType.Log ? "" : $"[{type}] ";

        _sb.Append(prefix).Append(typeTag).AppendLine(condition);

        if (showStackTraceOnErrors && (type == LogType.Error || type == LogType.Exception))
        {
            if (!string.IsNullOrWhiteSpace(stackTrace))
            {
                _sb.AppendLine(stackTrace);
            }
        }

        // limita linhas (simples: corta do início)
        int lines = 0;
        for (int i = _sb.Length - 1; i >= 0; i--)
        {
            if (_sb[i] == '\n')
            {
                lines++;
                if (lines > maxLines)
                {
                    _sb.Remove(0, i + 1);
                    break;
                }
            }
        }

        // limita caracteres
        if (_sb.Length > maxChars)
        {
            _sb.Remove(0, _sb.Length - maxChars);
        }

        output.text = _sb.ToString();
    }
}
