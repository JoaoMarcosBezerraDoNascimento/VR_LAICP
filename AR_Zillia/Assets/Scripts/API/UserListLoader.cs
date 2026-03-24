using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Networking;
using TMPro;
using UnityEngine.UI;

public class UserListLoader : MonoBehaviour
{
    [Header("Configuração do Servidor")]
    public string apiUrl => System_Config.IP_atual + "/usuarios-logados";

    [Header("UI")]
    public Transform content;             // Content do ScrollView
    public GameObject userButtonPrefab;   // Prefab de botão

    // Estrutura usada para deserializar JSON
    [System.Serializable]
    public class UsuariosResponse
    {
        public string[] usuarios;
    }

    // Chamado ao clicar no botão
    public void CarregarUsuarios()
    {
        Debug.Log("Buscando usuários na API...");
        StartCoroutine(GetUsuarios());
    }

    IEnumerator GetUsuarios()
    {
        using (UnityWebRequest www = UnityWebRequest.Get(apiUrl))
        {
            yield return www.SendWebRequest();

            if (www.result != UnityWebRequest.Result.Success)
            {
                Debug.LogError("Erro: " + www.error);
            }
            else
            {
                string json = www.downloadHandler.text;
                Debug.Log("JSON Recebido: " + json);

                UsuariosResponse data = JsonUtility.FromJson<UsuariosResponse>(json);

                // APAGA BOTÕES ANTIGOS
                foreach (Transform child in content)
                    Destroy(child.gameObject);

                // CRIA BOTÕES NOVOS
                CriarBotoes(data.usuarios);
            }
        }
    }

    void CriarBotoes(string[] usuarios)
    {
        Debug.Log("Criando botões para usuários...");

        foreach (string email in usuarios)
        {
            Debug.Log("Criando botão para: " + email);

            GameObject btn = Instantiate(userButtonPrefab, content);

            if (btn == null)
            {
                Debug.LogError("ERRO: Instanciação do prefab retornou NULL!");
                continue;
            }

            TMP_Text txt = btn.GetComponentInChildren<TMP_Text>();

            if (txt == null)
            {
                Debug.LogError("ERRO: botão não tem TMP_Text!", btn);
                continue;
            }

            txt.text = email;

            Button b = btn.GetComponentInChildren<Button>();
            if (b == null)
            {
                Debug.LogError("ERRO: botão não tem componente Button!", btn);
                continue;
            }

            b.onClick.AddListener(() => AoClicarNoUsuario(email));
        }
    }

    void AoClicarNoUsuario(string email)
    {
        Debug.Log("Clicou no usuário: " + email);

        // A partir daqui você faz:
        // → carregar outra cena
        // → enviar token ao servidor
        // → entrar no sistema
        // → abrir painel VR, etc.
    }
}
