using System.Collections.Generic;
using UnityEngine;
using TMPro;

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

    [Header("Peças")]
    public GameObject pecaCellPrefab;
    public Transform pecaContentParent;

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
            string saida = item.data_saida.Length >= 5 ? item.data_saida.Substring(0, 5) : item.data_saida;

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
    }

    void MostrarPecas(List<PecaItem> pecas)
    {
        // Limpa lista atual
        foreach (Transform child in pecaContentParent)
            Destroy(child.gameObject);

        // Cria cada peça
        foreach (var p in pecas)
        {
            GameObject pecaObj = Instantiate(pecaCellPrefab, pecaContentParent);

            TMP_Text tipoTMP = pecaObj.transform.Find("tipo")?.GetComponent<TMP_Text>();
            TMP_Text serialTMP = pecaObj.transform.Find("serial")?.GetComponent<TMP_Text>();
            TMP_Text garantiaTMP = pecaObj.transform.Find("garantia")?.GetComponent<TMP_Text>();
            TMP_Text divergenciaTMP = pecaObj.transform.Find("divergencia")?.GetComponent<TMP_Text>();
            TMP_Text comentarioTMP = pecaObj.transform.Find("comentario")?.GetComponent<TMP_Text>();

            if (tipoTMP != null) tipoTMP.text = p.tipo.ToString();
            if (serialTMP != null) serialTMP.text = p.serial;
            if (garantiaTMP != null) garantiaTMP.text = p.garantia ? "Sim" : "Não";
            if (divergenciaTMP != null) divergenciaTMP.text = p.divergencia ? "Sim" : "Não";
            if (comentarioTMP != null) comentarioTMP.text = p.comentario;
        }
    }
}
