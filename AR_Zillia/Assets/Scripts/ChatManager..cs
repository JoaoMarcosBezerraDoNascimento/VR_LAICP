using UnityEngine;
using TMPro;
using UnityEngine.UI;
using System.Collections;
using System; // Para pegar a hora

public class ChatManager : MonoBehaviour
{
    [Header("Estrutura UI")]
    public Transform chatContent; // O 'Content' do ScrollView
    public ScrollRect scrollRect; // O ScrollView principal
    public TMP_InputField inputField;
    public Button btnSend;
    public Button btnRec;

    [Header("Prefabs")]
    public GameObject prefabBalaoUsuario; // Arraste o Prefab Azul (#212F99)
    public GameObject prefabBalaoIA;      // Arraste o Prefab Cinza (#989898)

    private bool aguardandoResposta = false;

    void Start()
    {
        btnSend.onClick.AddListener(OnClickSend);
        
        // Mensagem de boas vindas da IA (Opcional)
        CriarBalao(prefabBalaoIA, "Olá! Como posso ajudar com as peças hoje?", "IA");
    }

    void Update()
    {
        // Bloqueia o botão SEND se não tiver texto ou se a IA estiver pensando
        if(btnSend != null)
        {
            btnSend.interactable = !string.IsNullOrEmpty(inputField.text) && !aguardandoResposta;
        }
    }

    public void OnClickSend()
    {
        if (string.IsNullOrEmpty(inputField.text) || aguardandoResposta) return;

        // 1. Envia mensagem do Usuário
        string textoUser = inputField.text;
        CriarBalao(prefabBalaoUsuario, textoUser, "Você");

        // 2. Limpa Input e Bloqueia
        inputField.text = "";
        AlternarBloqueioInput(true);

        // 3. Simula (ou chama) a IA
        StartCoroutine(ProcessarRespostaIA());
    }

    // Função que cria o balão visualmente
    void CriarBalao(GameObject prefab, string mensagem, string nomeRemetente)
    {
        GameObject novoBalao = Instantiate(prefab, chatContent);

        // Pega os textos dentro do prefab (Assumindo ordem: 0=Mensagem, 1=Hora)
        // Se a ordem for diferente no seu prefab, inverta os índices abaixo
        TextMeshProUGUI[] textos = novoBalao.GetComponentsInChildren<TextMeshProUGUI>();

        if (textos.Length > 0)
        {
            // O primeiro TMP é a mensagem principal
            textos[0].text = mensagem;
            
            // O segundo TMP é o rodapé (Hora)
            if (textos.Length > 1)
            {
                string hora = DateTime.Now.ToString("HH:mm");
                textos[1].text = $"{nomeRemetente} • {hora}";
            }
        }

        // Força atualização do layout e rola para baixo
        LayoutRebuilder.ForceRebuildLayoutImmediate(chatContent.GetComponent<RectTransform>());
        StartCoroutine(RolarParaOFinal());
    }

    void AlternarBloqueioInput(bool bloqueado)
    {
        aguardandoResposta = bloqueado;
        inputField.interactable = !bloqueado;
        btnRec.interactable = !bloqueado; // Opcional: Bloquear gravação tbm
    }

    IEnumerator ProcessarRespostaIA()
    {
        // Simulação de tempo de resposta (aqui entraria sua integração real)
        yield return new WaitForSeconds(1.5f);

        string respostaIA = "Entendido. Localizei a peça solicitada no estoque.";
        
        CriarBalao(prefabBalaoIA, respostaIA, "IA");
        AlternarBloqueioInput(false);
    }

    IEnumerator RolarParaOFinal()
    {
        yield return new WaitForEndOfFrame();
        scrollRect.verticalNormalizedPosition = 0f; // Vai para o fundo
    }
}