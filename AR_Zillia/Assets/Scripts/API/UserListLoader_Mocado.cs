using System.Collections;
using UnityEngine;
using TMPro;
using UnityEngine.UI;

public class UserListLoader_Mocado : MonoBehaviour
{
    [Header("UI")]
    public Transform content;              // Content do ScrollView
    public GameObject userButtonPrefab;    // Prefab COM Button configurado

    [Header("Menus")]
    public GameObject menuLogin;            // Tela de login
    public GameObject menuPedidos;          // Tela de pedidos

    private string[] usuariosMockados =
    {
        "João Marcos"
    };

    // Chamado pelo botão "Entrar" ou Start()
    public void CarregarUsuarios()
    {
        CriarBotoes(usuariosMockados);
    }

    void CriarBotoes(string[] usuarios)
    {
        // Limpa botões antigos
        foreach (Transform child in content)
            Destroy(child.gameObject);

        foreach (string nome in usuarios)
        {
            // Instancia o prefab
            GameObject btnObj = Instantiate(userButtonPrefab, content);

            // Texto
            TMP_Text txt = btnObj.GetComponentInChildren<TMP_Text>(true);
            if (txt != null)
                txt.text = nome;

            // 🔴 BUSCA CORRETA DO BUTTON (filhos inclusos)
            Button btn = btnObj.GetComponentInChildren<Button>(true);

            if (btn == null)
            {
                Debug.LogError("❌ Button não encontrado no prefab!");
                return;
            }

            btn.onClick.RemoveAllListeners();
            btn.onClick.AddListener(() =>
            {
                Debug.Log("🖱 Clique detectado: " + nome);
                StartCoroutine(MockLogin(nome));
            });
        }
    }

    IEnumerator MockLogin(string usuario)
    {
        Debug.Log("⏳ Simulando login...");

        yield return new WaitForSeconds(0.4f);

        Debug.Log("🔄 Trocando menus...");

        if (menuLogin != null)
            menuLogin.SetActive(false);
        else
            Debug.LogError("❌ menuLogin não atribuído!");

        if (menuPedidos != null)
            menuPedidos.SetActive(true);
        else
            Debug.LogError("❌ menuPedidos não atribuído!");
    }
}
