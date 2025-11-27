using UnityEngine;
using TMPro;
using UnityEngine.UI;
using Oculus.Voice.Dictation;

public class DictationManager : MonoBehaviour
{
    [Header("Componentes")]
    public AppDictationExperience dictationExperience;
    public TextMeshProUGUI targetText;
    public Image imagemBotaoGravar; // A imagem do botão de gravar para mudar de cor

    [Header("Configurações Visuais")]
    public Color corGravando = Color.red;
    public Color corParado = Color.white;

    // Variáveis Internas
    private string textoAcumulado = ""; 
    private string textoHipotese = "";
    private string textoPadraoInicial = ""; // Vai guardar sua frase "Aperte o botão..."

    void Start()
    {
        // 1. Salva o texto que você escreveu no Unity para usar depois ao limpar
        textoPadraoInicial = targetText.text;

        // 2. Configura os eventos do Wit.ai
        dictationExperience.DictationEvents.OnPartialTranscription.AddListener(OnHypothesis);
        dictationExperience.DictationEvents.OnFullTranscription.AddListener(OnResult);
    }

    void Update()
    {
        // Lógica Visual: Monitora se o microfone está ligado
        if (dictationExperience.MicActive)
        {
            imagemBotaoGravar.color = corGravando;
        }
        else
        {
            imagemBotaoGravar.color = corParado;
        }
    }

    // --- FUNÇÕES PARA OS BOTÕES (Ligue isso no OnClick do Unity) ---

    // Botão 1: Gravar / Pausar
    public void AlternarGravacao()
    {
        // Se o texto atual for o padrão ("Aperte o botão..."), limpamos ele antes de começar
        if (targetText.text == textoPadraoInicial)
        {
            targetText.text = "";
        }

        if (dictationExperience.MicActive)
        {
            dictationExperience.Deactivate(); // Para
        }
        else
        {
            dictationExperience.Activate(); // Começa
        }
    }

    // Botão 2: Limpar / Resetar
    public void LimparTexto()
    {
        // 1. Para a gravação se estiver ocorrendo
        if (dictationExperience.MicActive)
        {
            dictationExperience.Deactivate();
        }

        // 2. Limpa as variáveis de memória
        textoAcumulado = "";
        textoHipotese = "";

        // 3. Restaura o texto original
        targetText.text = textoPadraoInicial;
    }

    // --- EVENTOS DO DICTATION ---

    void OnHypothesis(string text)
    {
        textoHipotese = text;
        AtualizarTextoNaTela();
    }

    void OnResult(string text)
    {
        textoAcumulado += text + ". ";
        textoHipotese = "";
        AtualizarTextoNaTela();
    }

    void AtualizarTextoNaTela()
    {
        // Só atualiza se tivermos algo novo, senão mantemos o texto padrão (se estiver resetado)
        if (string.IsNullOrEmpty(textoAcumulado) && string.IsNullOrEmpty(textoHipotese))
        {
             // Se não tem nada gravado, não faz nada (deixa o LimparTexto cuidar disso)
             return;
        }

        targetText.text = textoAcumulado + textoHipotese;
    }
}