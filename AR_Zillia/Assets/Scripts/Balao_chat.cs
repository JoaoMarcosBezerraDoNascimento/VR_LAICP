using UnityEngine;
using TMPro;
using UnityEngine.UI;
using System;
public class Balao_chat : MonoBehaviour
{

    private TMP_Text TMP_Conteudo;
    private TMP_Text TMP_Horario;
    private Image Background_Balao;
    private Vector2 min_Size = new Vector2(90, 30);
    private Vector2 max_Size = new Vector2(350, 60);
    private void Awake()
    {
        Background_Balao = GetComponent<Image>();
    
        TMP_Conteudo = transform.Find("TMP_Conteudo").GetComponent<TMP_Text>();
        TMP_Horario = transform.Find("TMP_Horario").GetComponent<TMP_Text>();
    }
    public void Configurar_Balao(string texto, string user_ou_IA)
    {
        TMP_Conteudo.text = texto;
        TMP_Conteudo.fontSize = 12;
        TMP_Conteudo.fontStyle = FontStyles.Normal;

        TMP_Horario.text = DateTime.Now.ToString("HH:mm - dd/MM/yyyy");
        TMP_Horario.fontSize = 8;
        TMP_Horario.fontStyle = FontStyles.Italic;

        Definir_Cor(user_ou_IA);
        Alinhar_Balao(user_ou_IA);
        Configurar_Tamanho();
    }
    private void Definir_Cor(string comando)
    {
        string hex = "#FFFFFF";
        switch (comando.ToLower())
        {
            case "usuario":
            hex = "#5486f3";
            break;
            case "ia":
            hex = "#173987";
            break;
        }
        if (ColorUtility.TryParseHtmlString(hex, out Color nova_Cor))
        {
            Background_Balao.color = nova_Cor;
        }
    }
    private void Alinhar_Balao(string tipo)
    {
        RectTransform rect = GetComponent<RectTransform>();

        if (tipo.ToLower() == "usuario")
        {
            rect.pivot = new Vector2(1, 1);
            rect.anchorMin = new Vector2(1, 1);
            rect.anchorMax = new Vector2(1, 1);
            rect.anchoredPosition = new Vector2(-10, 0); 
        }
        else
        {
            rect.pivot = new Vector2(0, 1);
            rect.anchorMin = new Vector2(0, 1);
            rect.anchorMax = new Vector2(0, 1);
            rect.anchoredPosition = new Vector2(10, 0);
        }
    }
    private void Configurar_Tamanho()
    {
        RectTransform rect = GetComponent<RectTransform>();
        float largura_Texto = TMP_Conteudo.GetPreferredValues(TMP_Conteudo.text).x + 25; // +25 de margem interna
        float largura_Final = Mathf.Clamp(largura_Texto, min_Size.x, max_Size.x);
        rect.sizeDelta = new Vector2(largura_Final, rect.sizeDelta.y);
        LayoutRebuilder.ForceRebuildLayoutImmediate(rect);
        float altura_Texto = TMP_Conteudo.GetPreferredValues(TMP_Conteudo.text, largura_Final, float.MaxValue).y + 20;
        float altura_Final = Mathf.Clamp(altura_Texto, min_Size.y, float.MaxValue);
        rect.sizeDelta = new Vector2(largura_Final, altura_Final);
        if (transform.parent != null)
        {
            RectTransform rect_Pai = transform.parent.GetComponent<RectTransform>();
            if(rect_Pai != null)
            {
                 rect_Pai.sizeDelta = new Vector2(rect_Pai.sizeDelta.x, altura_Final + 10);
            }
        }
    }
}
