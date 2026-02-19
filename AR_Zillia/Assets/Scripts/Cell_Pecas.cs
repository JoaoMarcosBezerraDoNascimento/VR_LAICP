using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;
using TMPro;

public class Cell_Pecas : MonoBehaviour
{
    [Header("Referências UI")]
    public Sprite[] imagens;
    public string[] placas;

    public Image ImgTipo;
    public TMP_Text txtTipo;
    public TMP_Text txtSerial;
    public TMP_Text txtComentario;

    [Header("Garantia")]
    public Toggle toggleGarantia;

    [Header("Divergência")]
    public Toggle toggleDivergencia;

    [Header("Menu Comentário")]
    public Button botaoAbrirMenuComentario;
    public GameObject menuComentario;

    private bool aberto = false;

    // 🔴 CONTROLE GLOBAL (apenas um menu aberto)
    private static Cell_Pecas menuAbertoAtual;

    public void Configurar(
        int tipo,
        string serial,
        bool garantia,
        bool divergencia,
        string comentario
    )
    {
        int index = tipo - 1;

        if (index < 0 || index >= imagens.Length)
        {
            Debug.LogError($"[Cell_Pecas] Tipo inválido: {tipo}");
            return;
        }

        ImgTipo.overrideSprite = imagens[index];
        txtTipo.text = placas[index];

        txtSerial.text = serial;
        txtComentario.text = comentario;

        toggleGarantia.isOn = garantia;
        toggleDivergencia.isOn = divergencia;

        // Garante que inicia fechado
        menuComentario.SetActive(false);
        aberto = false;

        botaoAbrirMenuComentario.onClick.RemoveAllListeners();
        botaoAbrirMenuComentario.onClick.AddListener(ToggleMenuComentario);
    }

    private void ToggleMenuComentario()
    {
        // Se outro menu estiver aberto, fecha ele
        if (menuAbertoAtual != null && menuAbertoAtual != this)
        {
            menuAbertoAtual.FecharMenu();
        }

        // Alterna o menu atual
        aberto = !aberto;
        menuComentario.SetActive(aberto);

        menuAbertoAtual = aberto ? this : null;
    }

    private void FecharMenu()
    {
        aberto = false;
        menuComentario.SetActive(false);
    }
}
