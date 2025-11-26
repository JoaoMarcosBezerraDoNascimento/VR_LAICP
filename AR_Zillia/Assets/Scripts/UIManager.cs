using UnityEngine;

public class UIManager : MonoBehaviour
{
    public static UIManager instance;

    public GameObject telaPedidos;
    public GameObject telaPecas;
    public GameObject telaAssistente;

    void Awake()
    {
        instance = this;
        MostrarTelaPedidos();
    }

    public void MostrarTelaPedidos()
    {
        telaPedidos.SetActive(true);
        telaPecas.SetActive(false);
        telaAssistente.SetActive(false);
    }

    public void MostrarTelaPecas()
    {
        telaPedidos.SetActive(false);
        telaPecas.SetActive(true);
        telaAssistente.SetActive(false);
    }

    public void MostrarTelaAssistente()
    {
        telaPedidos.SetActive(false);
        telaPecas.SetActive(false);
        telaAssistente.SetActive(true);
    }
}
