using UnityEngine;
using TMPro;
using UnityEngine.UI;
using Oculus.Voice.Dictation;
using System.Collections;

public class Controle_Menu_IA : MonoBehaviour
{
    private AppDictationExperience Dictation_Experience;
    private TMP_InputField TMP_Input_User;
    private Button BTN_Rec;
    private Image BTN_Rec_Image;
    private Button BTN_Send;
    private Image BTN_Send_Image;
    private Transform SCRLVW_Chat_History_Content;
    private ScrollRect SCRLVW_Chat_History_ScrollRect;
    private Coroutine coroutine_digitacao_atual;
    private GameObject Prefab_balao_chat;
    private string user = "usuario";
    private string ia = "ia";
    private int iterador = 0;
    private string resposta;
    
    void Start()
    {
        //dictation
        GameObject obj_dictation = transform.Find("AppDictationExperience").gameObject;
        Dictation_Experience = obj_dictation.GetComponent<AppDictationExperience>();
        Dictation_Experience.DictationEvents.OnFullTranscription.AddListener(Texto_final_recebido);
        //input field
        GameObject obj_tmp_input = transform.Find("Background/Header_txt_btn/TMP_Input_User").gameObject;
        TMP_Input_User = obj_tmp_input.GetComponent<TMP_InputField>();
        TMP_Input_User.onValueChanged.AddListener(Verificar_Digitacao);
        //botao rec
        GameObject obj_btn_rec = transform.Find("Background/Header_txt_btn/BTN_Rec").gameObject;
        BTN_Rec = obj_btn_rec.GetComponent<Button>();
        BTN_Rec.onClick.AddListener(Gravando);
        //imagem botao rec
        BTN_Rec_Image= obj_btn_rec.GetComponent<Image>();
        BTN_Rec_Image.color = Cor_Hex("#ffffff");
        //botao send
        GameObject obj_btn_send = transform.Find("Background/Header_txt_btn/BTN_Send").gameObject;
        BTN_Send = obj_btn_send.GetComponent<Button>();
        BTN_Send.onClick.AddListener(Enviar);
        //imagem botao send
        BTN_Send_Image= obj_btn_send.GetComponent<Image>();
        BTN_Send_Image.color = Cor_Hex("#ffffff");
        //content do scroll view e scrollrect
        Transform obj_scroll = transform.Find("Background/SCRLVW_Chat_History");
        SCRLVW_Chat_History_Content = obj_scroll.Find("Viewport/Content");
        SCRLVW_Chat_History_ScrollRect = obj_scroll.GetComponent<ScrollRect>();
        //prefab balao
        Prefab_balao_chat = Resources.Load<GameObject>("Balao_chat");

    }
    //padrão de mudança de cor de botoes por codigo hexadecimal
    Color Cor_Hex(string hex)
    {
        Color Cor;
        if (ColorUtility.TryParseHtmlString(hex, out Cor))
        {
            return Cor;
        }
        return Color.white;
    }
    //função do dictation de gravar quando aperta o botao
    private void Gravando()
    {
        if (Dictation_Experience.MicActive)
        {   
            Dictation_Experience.Deactivate();
            BTN_Rec_Image.color = Cor_Hex("#ffffff");
            BTN_Send.interactable = true;
            BTN_Send_Image.color = Cor_Hex("#ffffff");
        }
        else
        {
            Dictation_Experience.Activate();
            BTN_Rec_Image.color = Cor_Hex("#C00000");
            BTN_Send.interactable = false;
            BTN_Send_Image.color = Cor_Hex("#ffffff50");
        }
    }

    void Texto_final_recebido(string texto_falado)
    {
        if(TMP_Input_User.text == "Enter text...") TMP_Input_User.text = texto_falado;
        else TMP_Input_User.text += texto_falado;
        BTN_Rec_Image.color = Cor_Hex("#ffffff");  
        BTN_Send.interactable = true;
        BTN_Send_Image.color = Cor_Hex("#ffffff");     
    }

    private void Enviar()
    {
        StartCoroutine(Rotina_envio());
    }

    private IEnumerator Rotina_envio()
    {
        BTN_Rec.interactable = false;
        BTN_Rec_Image.color = Cor_Hex("#ffffff50");
        Gerar_Balão(TMP_Input_User.text, user);
        Resposta_da_IA();
        TMP_Input_User.interactable = false;
        BTN_Send_Image.color = Cor_Hex("#28a745");
        TMP_Input_User.onValueChanged.RemoveListener(Verificar_Digitacao);
        TMP_Input_User.text = ""; 
        
        yield return new WaitForSeconds(0.5f);
        BTN_Send_Image.color = Cor_Hex("#ffffff");
        BTN_Rec.interactable = true;
        BTN_Rec_Image.color = Cor_Hex("#ffffff");
        TMP_Input_User.interactable = true;
        TMP_Input_User.text = "Enter text...";
        TMP_Input_User.onValueChanged.AddListener(Verificar_Digitacao);
    }
    void Verificar_Digitacao(string texto)
    {
        BTN_Send.interactable = false;
        BTN_Send_Image.color = Cor_Hex("#ffffff50");
        if (coroutine_digitacao_atual != null)
        {
            StopCoroutine(coroutine_digitacao_atual);
        }
        coroutine_digitacao_atual = StartCoroutine(Rotina_Digitacao());
    }
    private IEnumerator Rotina_Digitacao()
    {
        yield return new WaitForSeconds(0.5f);
        BTN_Send.interactable = true;
        BTN_Send_Image.color = Cor_Hex("#ffffff");
        if(TMP_Input_User.text != "" && TMP_Input_User.text != "Enter text...")
        {
            BTN_Send.interactable = true;
            BTN_Send_Image.color = Cor_Hex("#ffffff");
        }
        coroutine_digitacao_atual = null;
    }

    public void Gerar_Balão(string mensagem, string tipo)
    {
        GameObject container = new GameObject("Container_Msg");
        container.transform.SetParent(SCRLVW_Chat_History_Content, false);
        RectTransform rect_Container = container.AddComponent<RectTransform>();
        rect_Container.localScale = Vector3.one;
        GameObject novo_Balao = Instantiate(Prefab_balao_chat, container.transform);
        Balao_chat script = novo_Balao.GetComponent<Balao_chat>();
        if (script != null)
        {
            script.Configurar_Balao(mensagem, tipo);
        }
        StartCoroutine(RolarParaOFinal());
    }
    private void Resposta_da_IA()
    {
        
        switch (iterador)
        {
            case 0: resposta = "Ola, bom dia pra voce tambem";
            break;
            case 1: resposta = "A sua peça é a peça 1924u88299102u4ji9829421, ela apresenta defeito na memoria alocada 5.9 onde apresenta um erro de solda que causou curto circuito na memoria RAM, mande novamente para a assistencia da fabrica para que possam efetuar a troca da peça";
            break;
            case 2: resposta = "Por nada, tenha um bom trabalho, qualquer coisa e so chamar novamente que te ajudo com o que precisar.";
            break;
        }
        if (iterador == 2) iterador = 0;
        else iterador += 1;
        Gerar_Balão(resposta, ia);
    }   
    private IEnumerator RolarParaOFinal()
    {
        yield return new WaitForEndOfFrame(); 
        Canvas.ForceUpdateCanvases();
        if (SCRLVW_Chat_History_ScrollRect != null)
        {
            SCRLVW_Chat_History_ScrollRect.verticalNormalizedPosition = 0f;
        }
    }
}
