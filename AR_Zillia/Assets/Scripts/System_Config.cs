using UnityEngine;
using TMPro;
using UnityEngine.UI;
using System.Collections; 

public class System_Config : MonoBehaviour
{
    
    [Header("Input Field")]
    public TMP_InputField TIF_texto;
    
    [Header("Botão")]
    [SerializeField] private Button Btn_Send;
    [SerializeField] private Image Btn_Send_image;
    
    public static string IP_atual = "";
    private Sprite sprite_normal;
    private Sprite sprite_erro;
    void Start()
    {
        sprite_erro = Resources.Load<Sprite>("tick_off");
        sprite_normal = Resources.Load<Sprite>("tick_on");
        Btn_Send_image.color = Cor_Hex("#FFFFFF00");
        Btn_Send_image.sprite = sprite_normal;
        if (PlayerPrefs.HasKey("IP_Salvo"))
        {
            TIF_texto.text = PlayerPrefs.GetString("IP_Salvo");
            IP_atual = TIF_texto.text;
        }

        Btn_Send.onClick.AddListener(BT_clicado);    
    }
    
    private void BT_clicado()
    {
        if (string.IsNullOrWhiteSpace(TIF_texto.text))
        {
            Btn_Send_image.sprite = sprite_erro;
            Btn_Send_image.color = Cor_Hex("#ffffff");
            Debug.LogWarning("O campo de IP está vazio! Digite um IP válido.");
            StartCoroutine(Voltar_Sprite_Normal());            
            return; 
        }

        StartCoroutine(Salvar_IP());
    }

    private IEnumerator Salvar_IP()
    {
        IP_atual = TIF_texto.text;
        
        PlayerPrefs.SetString("IP_Salvo", IP_atual);
        PlayerPrefs.Save();

        Debug.Log("IP confirmado e salvo globalmente: " + IP_atual);
        Btn_Send_image.sprite = sprite_normal;
        Btn_Send_image.color = Cor_Hex("#FFFFFF"); 
        
        yield return new WaitForSeconds(0.5f);
        
        Btn_Send_image.color = Cor_Hex("#FFFFFF00"); 
    }
private IEnumerator Voltar_Sprite_Normal()
    {
        yield return new WaitForSeconds(1f); 
        if (sprite_normal != null) {
            Btn_Send_image.sprite = sprite_normal; 
            Btn_Send_image.color = Cor_Hex("#ffffff00");
            }
    }
    Color Cor_Hex(string hex)
    {
        Color Cor;
        if (ColorUtility.TryParseHtmlString(hex, out Cor))
        {
            return Cor;
        }
        return Color.white;
    }
}