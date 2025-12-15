using System.Collections.Generic;
using UnityEngine;
using TMPro;
using System.Collections;
using UnityEngine.UI;

public class Controle_Menus : MonoBehaviour
{
    [System.Serializable]
    public class PecaItem
    {
        public int tipo;
        public string serial;
        public bool garantia;
        public bool divergencia;
        public string comentario;
    }

    [System.Serializable]
    public class RmaItem
    {
        public string numero_pedido_rma;
        public string cliente;
        public string data_chegada;
        public string data_saida;
        public List<PecaItem> pecas;
    }

    [System.Serializable]
    public class RmaLista
    {
        public List<RmaItem> rmas;
    }

    public TextAsset jsonFile;

    [Header("RMA")]
    public GameObject rmaCellPrefab;
    public Transform rmaContentParent;
    public ScrollRect scrollPedidos;

    [Header("Peças")]
    public GameObject pecaCellPrefab;
    public Transform pecaContentParent;
    public ScrollRect scrollPecas;

    void Start()
    {
        CarregarHistorico();
    }

    void CarregarHistorico()
    {
        // Verifica se o prefab é o correto
        if (rmaCellPrefab.GetComponent<Cell_Pedidos>() == null)
        {
            Debug.LogError("O prefab atribuído em rmaCellPrefab NÃO possui Cell_Pedidos!");
        }

        // Carrega JSON
        RmaLista lista = JsonUtility.FromJson<RmaLista>(jsonFile.text);
        if (lista == null || lista.rmas == null)
        {
            Debug.LogError("Falha ao carregar JSON!");
            return;
        }

        // Limpa RMAs
        foreach (Transform child in rmaContentParent)
            Destroy(child.gameObject);

        // Limpa peças
        foreach (Transform child in pecaContentParent)
            Destroy(child.gameObject);

        // Cria células RMA
        foreach (var item in lista.rmas)
        {
            GameObject cellObj = Instantiate(rmaCellPrefab, rmaContentParent);

            Cell_Pedidos cell = cellObj.GetComponent<Cell_Pedidos>();

            if (cell == null)
            {
                Debug.LogError("Prefab instanciado NÃO possui Cell_Pedidos!");
                continue;
            }

            string chegada = item.data_chegada.Length >= 5 ? item.data_chegada.Substring(0, 5) : item.data_chegada;
            string saida = "A Finalizar";

            // Passa a lista de peças para a célula
            cell.DefinirPecas(item.pecas);

            // Configura célula
            cell.Configurar(
                item.numero_pedido_rma,
                item.cliente,
                chegada,
                saida,
                MostrarPecas
            );
        }
        StartCoroutine(VoltarScrollParaTopo());
    }

    void MostrarPecas(List<PecaItem> pecas)
    {
        foreach (Transform child in pecaContentParent)
            Destroy(child.gameObject);

        foreach (var p in pecas)
        {
            GameObject pecaObj = Instantiate(pecaCellPrefab, pecaContentParent);

            Cell_Pecas cell = pecaObj.GetComponent<Cell_Pecas>();

            if (cell != null)
            {
                cell.DefinirPecas(pecas);

                cell.Configurar(
                    p.tipo.ToString(),                   // numero (índice da imagem)
                    p.serial,                            // cliente
                    p.divergencia ? "Divergente" : "Normal",      // divergencia
                    p.garantia ? "Com Garantia" : "Sem Garantia",          // chegada
                    p.comentario
                );
            }
            else
            {
                Debug.LogError("Prefab pecaCellPrefab NÃO tem Cell_Pecas!");
            }
        }

        StartCoroutine(VoltarScrollParaTopo());
    }

    IEnumerator VoltarScrollParaTopo()
    {
        yield return null; // espera 1 frame
        scrollPecas.verticalNormalizedPosition = 1f;
        scrollPedidos.verticalNormalizedPosition = 1f;
    }


}
