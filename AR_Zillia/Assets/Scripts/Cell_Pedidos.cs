using UnityEngine;
using UnityEngine.UI;
using TMPro;
using System.Collections.Generic;

public class Cell_Pedidos : MonoBehaviour
{
    public TMP_Text txtNumero;
    public TMP_Text txtCliente;
    public TMP_Text txtChegada;
    public TMP_Text txtSaida;

    public Button btnAbrir;

    private List<Controle_Menus.PecaItem> pecas;
    private System.Action<List<Controle_Menus.PecaItem>> callbackMostrar;

    public void DefinirPecas(List<Controle_Menus.PecaItem> lista)
    {
        pecas = lista;
    }

    public void Configurar(
        string numero,
        string cliente,
        string chegada,
        string saida,
        System.Action<List<Controle_Menus.PecaItem>> callback
    )
    {
        // Atribuição direta sem prefixos ou interpolação extra
        txtNumero.text = numero; 
        txtCliente.text = cliente;
        txtChegada.text = chegada;
        txtSaida.text = saida;

        callbackMostrar = callback;

        btnAbrir.onClick.RemoveAllListeners();
        btnAbrir.onClick.AddListener(() =>
        {
            // Primeiro mostra lista de peças
            callbackMostrar?.Invoke(pecas);

            // Depois troca a tela
            if (UIManager.instance != null)
            {
                UIManager.instance.MostrarTelaPecas();
            }
        });
    }
}