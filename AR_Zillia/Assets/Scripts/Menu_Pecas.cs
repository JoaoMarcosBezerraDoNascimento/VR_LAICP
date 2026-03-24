using UnityEngine;

public class Menu_Pecas : MonoBehaviour
{
    public static Menu_Pecas instance;

    void Awake()
    {
        instance = this;
    }

    public void Abrir(string numeroRMA)
    {
        Debug.Log("Abrindo menu de peças do RMA: " + numeroRMA);

        // aqui você muda de menu/tela
        gameObject.SetActive(true);

        // aqui você carrega as peças desse RMA
        CarregarPecas(numeroRMA);
    }

    void CarregarPecas(string numeroRMA)
    {
        // coloque sua lógica para buscar JSON, BD, API, etc
    }
}
