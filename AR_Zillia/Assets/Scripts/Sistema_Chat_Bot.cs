using UnityEngine;

public class Sistema_Chat_Bot : MonoBehaviour
{
    [Header("--- ÁREA DO CHAT ---")]
    public Transform contentDoScroll;   // O objeto 'Content' dentro do Scroll View
    public GameObject prefabDoBalao;    // O Prefab do balão (que tem o script ChatBubble)
    public TMP_InputField campoDeTexto; // O InputField onde o texto aparece
    public Button botaoEnviar;          // Botão do aviãozinho
    public ScrollRect scrollRect;       // O componente ScrollRect principal

    [Header("--- ÁREA DE VOZ (DICTATION) ---")]
    public AppDictationExperience dictationExperience; // Componente do Wit.ai/Oculus
    public Image imagemBotaoMic;        // A imagem do botão de microfone (para ficar vermelho)
    public Button botaoMic;             // O botão de microfone em si

    [Header("--- CONFIGURAÇÕES VISUAIS ---")]
    public Color corGravando = Color.red;
    public Color corParado = Color.white;

    // Variáveis de controle interno
    private bool aguardandoIA = false;
    private bool estaGravando = false;

    void Start()
    {
        // 1. Configurar Botão Enviar
        botaoEnviar.onClick.AddListener(EnviarMensagem);

        // 2. Configurar Botão Microfone
        botaoMic.onClick.AddListener(AlternarGravacao);

        // 3. Configurar Eventos do Dictation (Voz)
        if (dictationExperience != null)
        {
            dictationExperience.DictationEvents.OnFullTranscription.AddListener(AoReceberTextoVoz);
            dictationExperience.DictationEvents.OnStopped.AddListener((a) => PararVisualGravacao());
            dictationExperience.DictationEvents.OnError.AddListener((e, s) => PararVisualGravacao());
        }
        else
        {
            Debug.LogError("ERRO: O componente 'App Dictation Experience' não foi arrastado para o script!");
        }

        // Opcional: Enviar com Enter
        campoDeTexto.onSubmit.AddListener((val) => { 
            if(!string.IsNullOrWhiteSpace(val)) EnviarMensagem(); 
        });
    }

    void Update()
    {
        // Regra: Só pode enviar se tiver texto e a IA não estiver pensando
        botaoEnviar.interactable = !string.IsNullOrWhiteSpace(campoDeTexto.text) && !aguardandoIA;
        
        // Regra: Só pode gravar se a IA não estiver pensando
        botaoMic.interactable = !aguardandoIA;
    }

    // =================================================================================
    // LÓGICA DO CHAT
    // =================================================================================

    public void EnviarMensagem()
    {
        string texto = campoDeTexto.text;
        if (string.IsNullOrWhiteSpace(texto) || aguardandoIA) return;

        // 1. Cria balão do usuário (Direita)
        CriarBalao(texto, true);

        // 2. Limpa e Bloqueia
        campoDeTexto.text = "";
        aguardandoIA = true;
        campoDeTexto.interactable = false; // Bloqueia digitação manual
        PararVisualGravacao(); // Garante que parou de gravar se enviou

        // 3. Simula IA
        StartCoroutine(SimularRespostaIA());
    }

    void CriarBalao(string texto, bool isUser)
    {
        GameObject novaBolha = Instantiate(prefabDoBalao, contentDoScroll);
        
        // Chama o script ChatBubble que corrigimos o nome
        if(novaBolha.TryGetComponent(out ChatBubble bubbleScript))
        {
            bubbleScript.Setup(texto, isUser);
        }

        // Rola para baixo
        StartCoroutine(ForcarScrollBaixo());
    }

    IEnumerator SimularRespostaIA()
    {
        yield return new WaitForSeconds(1.5f); // Delay falso

        // --- RESPOSTA DA IA ---
        string resposta = "Pedido localizado. Iniciando processo de separação de peças.";
        
        CriarBalao(resposta, false); // Cria balão da IA (Esquerda)

        // Libera tudo
        aguardandoIA = false;
        campoDeTexto.interactable = true;
        campoDeTexto.ActivateInputField();
    }

    IEnumerator ForcarScrollBaixo()
    {
        yield return new WaitForEndOfFrame();
        scrollRect.verticalNormalizedPosition = 0f;
    }

    // =================================================================================
    // LÓGICA DE VOZ (DICTATION)
    // =================================================================================

    void AlternarGravacao()
    {
        if (aguardandoIA) return;

        if (estaGravando)
        {
            dictationExperience.Deactivate();
            PararVisualGravacao();
        }
        else
        {
            dictationExperience.Activate();
            IniciarVisualGravacao();
        }
    }

    void IniciarVisualGravacao()
    {
        estaGravando = true;
        if(imagemBotaoMic) imagemBotaoMic.color = corGravando;
    }

    void PararVisualGravacao()
    {
        estaGravando = false;
        if(imagemBotaoMic) imagemBotaoMic.color = corParado;
    }

    void AoReceberTextoVoz(string textoFalado)
    {
        // Lógica Híbrida: Junta o texto falado com o que já existe no input
        if (campoDeTexto.text.Length > 0 && !campoDeTexto.text.EndsWith(" "))
        {
            campoDeTexto.text += " ";
        }

        campoDeTexto.text += textoFalado;
        
        // Coloca o cursor no fim
        campoDeTexto.caretPosition = campoDeTexto.text.Length;
    }
}
