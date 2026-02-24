using System;
using System.Collections.Generic;
using UnityEngine;

public class UIManager : MonoBehaviour
{
    public static UIManager instance;

    [Header("Todas as telas/menus que o UIManager controla")]
    [SerializeField] private List<GameObject> telas = new();

    [Header("Tela inicial (opcional)")]
    [SerializeField] private GameObject telaInicial;

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

    public void MostrarTela(GameObject telaParaMostrar)
    {
        Debug.Log("Trocando de Tela...");
        if (telaParaMostrar == null) return;

        // Garante que ela está registrada
        Registrar(telaParaMostrar);

        // Oculta tudo
        OcultarTodas();

        // Mostra só a desejada
        telaParaMostrar.SetActive(true);
    }
    public void Mostrar_Tela_Por_indice(int index)
    {
        Debug.Log("Trocando de Tela...");

        if (index < 0 || index >= telas.Count)
        {
            Debug.LogError("Índice inválido: " + index);
            return;
        }

        GameObject tela = telas[index];
        if (tela == null)
        {
            Debug.LogError("Tela no índice " + index + " é NULL");
            return;
        }

        OcultarTodas();
        tela.SetActive(true);
    }

    public void Mostrar_Tela_Indice_Fixo()
    {
        Debug.Log("Trocando para Tela 1...");

        int index = 1;

        if (index < 0 || index >= telas.Count)
        {
            Debug.LogError("Índice inválido: " + index);
            return;
        }

        GameObject tela = telas[index];
        if (tela == null)
        {
            Debug.LogError("Tela no índice " + index + " é NULL");
            return;
        }

        OcultarTodas();
        tela.SetActive(true);
    }

}
