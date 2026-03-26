using UnityEngine;

public class MouseTest : MonoBehaviour
{
    void Update()
    {
        if (Input.GetMouseButtonDown(0))
        {
            Debug.Log("CLICK ESQUERDO");
        }

        if (Input.GetMouseButtonDown(1))
        {
            Debug.Log("CLICK DIREITO");
        }
    }
}
