using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;
using TMPro;

public class Cell_Pecas : MonoBehaviour
{
    [Header("Referências UI")]
    public TMP_Text txttipo;
    public TMP_Text txtserial;
    public TMP_Text txtdivergencia;
    public TMP_Text txtcomentario;
    public TMP_Text txtgarantia;
    public Button botaoAbrirMenuComentario;

    private List<Controle_Menus.PecaItem> pecas;
    private System.Action<List<Controle_Menus.PecaItem>> callbackMostrar;

    public void Configurar(
        string numero,
        string cliente,
        string chegada,
        string saida,
        System.Action<List<Controle_Menus.PecaItem>> callback
    )
    {
        txttipo.text = numero;
        txtserial.text = cliente;
        txtdivergencia.text = chegada;
        txtcomentario.text = saida;
        txtgarantia.text = "";

        callbackMostrar = callback;

        botaoAbrirMenuComentario.onClick.RemoveAllListeners();
        botaoAbrirMenuComentario.onClick.AddListener(() =>
        {
            callbackMostrar?.Invoke(pecas);
        });
    }
    public void DefinirPecas(List<Controle_Menus.PecaItem> lista)
    {
        pecas = lista;
    }

}