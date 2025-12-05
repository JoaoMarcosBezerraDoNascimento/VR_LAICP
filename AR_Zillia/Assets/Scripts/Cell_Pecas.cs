using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;
using TMPro;
using System;

public class Cell_Pecas : MonoBehaviour
{
    [Header("Referências UI")]
    public Sprite[] imagens;
    public string[] placas;

    public Image ImgTipo;
    public TMP_Text txtTipo;
    public TMP_Text txtserial;
    public TMP_Text txtdivergencia;
    public TMP_Text txtgarantia;
    public TMP_Text txtcomentario;
    public Button botaoAbrirMenuComentario;

    private List<Controle_Menus.PecaItem> pecas;
    private System.Action<List<Controle_Menus.PecaItem>> callbackMostrar;
    public GameObject menuComentario;
    private bool aberto = false;

    public void Configurar(
        string tipo,
        string serial,
        string divergencia,
        string garantia,
        string comentario
    )
    {
        int Inumero = 0;
        int.TryParse(tipo, out Inumero);

        Inumero -= 1;

        Debug.Log(
            $"[Cell_Pecas]\n" +
            $" numero='{tipo}'  (int={Inumero})\n" +
            $" imagens={imagens.Length}  placas={placas.Length}\n" +
            $" placas={placas[Inumero]}\n" +
            $" cliente='{serial}'\n" +
            $" comentario='{comentario}'\n" +
            $" garantia='{garantia}"
        );

        ImgTipo.overrideSprite = imagens[Inumero];
        txtTipo.text = placas[Inumero];

        txtserial.text = serial;
        txtdivergencia.text = divergencia;
        txtcomentario.text = comentario;
        txtgarantia.text = garantia;

        botaoAbrirMenuComentario.onClick.RemoveAllListeners();
        botaoAbrirMenuComentario.onClick.AddListener(() =>
        {
            aberto = !aberto;
            menuComentario.SetActive(aberto);
            Debug.Log("Botãoo comentario Apertado");
        });
    }

    public void DefinirPecas(List<Controle_Menus.PecaItem> lista)
    {
        pecas = lista;
    }
}
