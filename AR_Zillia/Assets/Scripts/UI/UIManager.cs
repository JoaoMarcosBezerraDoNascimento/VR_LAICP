using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;

public class UIManager : MonoBehaviour
{
    public static UIManager instance;

    [Header("Todas as telas/menus que o UIManager controla")]
    [SerializeField] private List<GameObject> telas = new();

    [Header("Tela inicial (opcional)")]
    [SerializeField] private GameObject telaInicial;

    [Header("Botões do menu (alinhado com os menus)")]
    [SerializeField] private List<Graphic> imagens = new(); 

    [Header("Cores")]
    public Color corPadrao; // 183987
    public Color corSelecionada; //5387FF

    void Awake()
    {
        instance = this;

        if (telaInicial != null)
            MostrarTela(telaInicial);
        else
            OcultarTodas();
    }

    public void Registrar(GameObject tela)
    {
        if (tela == null) return;
        if (!telas.Contains(tela)) telas.Add(tela);
    }

    public void OcultarTodas()
    {
        Debug.Log("Ocultando Telas...");
        for (int i = 0; i < telas.Count; i++)
        {
            if (telas[i] != null)
                telas[i].SetActive(false);
        }
    }

    public void CorPadrao()
    {
        Debug.Log("Setando cores...");
        for (int i = 0; i < imagens.Count; i++)
        {
            if (imagens[i] != null)
                imagens[i].color = corPadrao;
        }
    }


    public void Mostrar_Tela_Por_indice(int index)
    {
        if (index < 0 || index >= telas.Count)
        {
            Debug.LogError("Índice inválido: " + index);
            return;
        }

        OcultarTodas();
        CorPadrao();

        telas[index].SetActive(true);

        if (index < imagens.Count && imagens[index] != null)
            imagens[index].color = corSelecionada;
    }

    public void MostrarTela(GameObject tela)
    {
        OcultarTodas();
        CorPadrao();

        tela.SetActive(true);
    }  
}
