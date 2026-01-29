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
        //contente do scroll view
        Transform obj_scroll = transform.Find("Background/SCRLVW_Chat_History");
        SCRLVW_Chat_History_Content = obj_scroll.Find("Viewport/Content");

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
        TMP_Input_User.interactable = false;
        BTN_Send_Image.color = Cor_Hex("#28a745");
       TMP_Input_User.onValueChanged.RemoveListener(Verificar_Digitacao);
        TMP_Input_User.text = ""; 
        TMP_Input_User.onValueChanged.AddListener(Verificar_Digitacao);
        
        yield return new WaitForSeconds(0.5f);
        BTN_Send_Image.color = Cor_Hex("#ffffff");
        BTN_Rec.interactable = true;
        BTN_Rec_Image.color = Cor_Hex("#ffffff");
        TMP_Input_User.interactable = true;
        TMP_Input_User.text = "Enter text...";
    }
    void Verificar_Digitacao(string texto)
    {
        StartCoroutine(Rotina_Digitacao());
    }
    private IEnumerator Rotina_Digitacao()
    {
        BTN_Send.interactable = false;
        BTN_Send_Image.color = Cor_Hex("#ffffff50");
        yield return new WaitForSeconds(0.2f);
        BTN_Send.interactable = true;
        BTN_Send_Image.color = Cor_Hex("#ffffff");
    }
}
