using UnityEngine;
using UnityEngine.UI;

public class ImageSwitcher : MonoBehaviour
{
    public Image targetImage;        // O Image da UI onde a imagem será mostrada
    public Sprite[] imagens;         // Array de sprites (0 a 4)

    public void SetImagem(int id)
    {
        Debug.Log(id);
        if (id < 1 || id > imagens.Length) return;
        targetImage.sprite = imagens[id - 1];
    }
}
