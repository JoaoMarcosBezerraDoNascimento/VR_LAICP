using UnityEngine;

public class PassthroughControl : MonoBehaviour
{
    public OVRPassthroughLayer passthroughLayer;

    void Start()
    {
        if (passthroughLayer != null)
            passthroughLayer.hidden = false; // ativa o Passthrough
    }
}
