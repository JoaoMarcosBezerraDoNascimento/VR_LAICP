using UnityEngine;
using UnityEngine.UI;

[RequireComponent(typeof(Button))]
public class Toggle_Visibility : MonoBehaviour
{
    [Header("Objeto a ser alternado")]
    public GameObject Alvo;

    [Header("Estado inicial")]
    public bool Comecar_Visivel = true;

    private Button botao;

    void Awake()
    {
        botao = GetComponent<Button>();
        botao.onClick.RemoveListener(Toggle);
        botao.onClick.AddListener(Toggle);
    }

    void Start()
    {
        if (Alvo != null)
            Alvo.SetActive(Comecar_Visivel);
    }

    public void Toggle()
    {
        if (Alvo == null) return;

        Alvo.SetActive(!Alvo.activeSelf);
    }
}
