using UnityEngine;
using TMPro;
using UnityEngine.UI;
using Oculus.Voice.Dictation;

public class ControleComentarioVoz : MonoBehaviour
{
    [Header("Dependências")]
    public AppDictationExperience dictationExperience;

    [Header("Paineis (UI)")]
    public GameObject painelDoMenuInteiro; // O "Pop-up" inteiro que contém tudo (Comentário + Botões)
    public GameObject painelTranscricao;   // O container da transcrição ao vivo

    [Header("Textos")]
    public TextMeshProUGUI tmpComentarioFinal;    // O texto principal (Histórico)
    public TextMeshProUGUI tmpTranscricaoAoVivo;  // O texto da voz (Ao vivo)

    [Header("Botões e Visuais")]
    public Image imagemBotaoRec;
    public Color corGravando = Color.red;
    public Color corParado = Color.white;

    // Variáveis de Controle
    private string textoAcumuladoSessao = ""; 
    private string textoHipotese = "";

    void Start()
    {
        // Configura eventos do Wit.ai
        dictationExperience.DictationEvents.OnPartialTranscription.AddListener(OnHypothesis);
        dictationExperience.DictationEvents.OnFullTranscription.AddListener(OnResult);
        
        // --- AQUI ESTÁ A CORREÇÃO ---
        // Remova as duas barras (//) da frente desta linha:
        if(painelDoMenuInteiro != null) painelDoMenuInteiro.SetActive(false);
        
        // Garante que a transcrição também comece escondida
        if(painelTranscricao != null) painelTranscricao.SetActive(false);
    }

    void Update()
    {
        // Só muda a cor se o menu estiver aberto
        if (painelDoMenuInteiro.activeSelf && dictationExperience.MicActive)
            imagemBotaoRec.color = corGravando;
        else
            imagemBotaoRec.color = corParado;
    }


    // Coloque esta função no "Botão em Branco"
    // Função para o Botão Quadrado Branco
    public void AlternarMenuComentarios()
    {
        if (painelDoMenuInteiro != null)
        {
            // Verifica como está agora (Aberto ou Fechado?)
            bool estaAberto = painelDoMenuInteiro.activeSelf;

            if (estaAberto)
            {
                // Se já está aberto, manda fechar
                FecharMenuComentarios();
            }
            else
            {
                // Se está fechado, manda abrir e reseta
                painelDoMenuInteiro.SetActive(true);
                Click_RESET();
            }
        }
    }

    // Coloque esta função num botão "X" ou "Voltar" se tiver
    public void FecharMenuComentarios()
    {
        // Se estiver gravando, para antes de fechar
        if (dictationExperience.MicActive) dictationExperience.Deactivate();

        if(painelDoMenuInteiro != null) 
        {
            painelDoMenuInteiro.SetActive(false);
        }
    }

    // --- FUNÇÕES DOS BOTÕES INTERNOS ---

    public void Click_REC()
    {
        if(painelTranscricao != null) painelTranscricao.SetActive(true);

        if (dictationExperience.MicActive)
            dictationExperience.Deactivate();
        else
            dictationExperience.Activate();
    }

    public void Click_RESET()
    {
        if (dictationExperience.MicActive) dictationExperience.Deactivate();

        textoAcumuladoSessao = "";
        textoHipotese = "";
        tmpTranscricaoAoVivo.text = "";
        
        if(painelTranscricao != null) painelTranscricao.SetActive(false);
    }

    public void Click_SEND()
    {
        if (dictationExperience.MicActive) dictationExperience.Deactivate();

        string textoParaEnviar = tmpTranscricaoAoVivo.text;

        if (!string.IsNullOrEmpty(textoParaEnviar))
        {
            // Se já tem texto, pula linha. Se não, só adiciona.
            if (string.IsNullOrEmpty(tmpComentarioFinal.text))
                tmpComentarioFinal.text = textoParaEnviar;
            else
                tmpComentarioFinal.text += "\n" + textoParaEnviar;
        }

        Click_RESET();
    }

    // --- EVENTOS WIT.AI ---

    void OnHypothesis(string text)
    {
        textoHipotese = text;
        AtualizarTextoTranscricao();
    }

    void OnResult(string text)
    {
        textoAcumuladoSessao += text + ". ";
        textoHipotese = "";
        AtualizarTextoTranscricao();
    }

    void AtualizarTextoTranscricao()
    {
        tmpTranscricaoAoVivo.text = textoAcumuladoSessao + textoHipotese;
    }
}