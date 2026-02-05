using UnityEngine;
using UnityEngine.UI;

public class TabManager : MonoBehaviour
{
    public Image imgPedidos;
    public Image imgPecas;
    public Image imgAssistente;

    // O método Start é executado apenas uma vez quando o jogo inicia
    void Start()
    {
        // Chama a função que você já criou para marcar o 'pedidos'
        SelecionarBotao("pedidos");
    }

    public void SelecionarBotao(string nome)
    {
        // Resetar todos para 225 (aprox 0.88f)
        imgPedidos.color = new Color(imgPedidos.color.r, imgPedidos.color.g, imgPedidos.color.b, 0.88f);
        imgPecas.color = new Color(imgPecas.color.r, imgPecas.color.g, imgPecas.color.b, 0.88f);
        imgAssistente.color = new Color(imgAssistente.color.r, imgAssistente.color.g, imgAssistente.color.b, 0.88f);

        // Ativar o selecionado para 255 (1.0f)
        if (nome == "pedidos") imgPedidos.color = new Color(imgPedidos.color.r, imgPedidos.color.g, imgPedidos.color.b, 1f);
        if (nome == "pecas") imgPecas.color = new Color(imgPecas.color.r, imgPecas.color.g, imgPecas.color.b, 1f);
        if (nome == "assistente") imgAssistente.color = new Color(imgAssistente.color.r, imgAssistente.color.g, imgAssistente.color.b, 1f);
    }
}