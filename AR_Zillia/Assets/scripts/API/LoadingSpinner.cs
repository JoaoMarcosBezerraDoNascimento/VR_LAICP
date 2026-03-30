using UnityEngine;

public class LoadingSpinner : MonoBehaviour
{
    public float velocidade = 200f;

    void Update()
    {
        transform.Rotate(0f, 0f, -velocidade * Time.deltaTime);
    }
}