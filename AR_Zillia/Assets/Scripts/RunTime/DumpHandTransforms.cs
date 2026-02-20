using UnityEngine;

public class DumpHandTransforms : MonoBehaviour
{
    void Start()
    {
        var all = FindObjectsOfType<Transform>();
        foreach (var t in all)
        {
            if (t.name.ToLower().Contains("Index_Tip") ||
                t.name.ToLower().Contains("Thumb_Tip"))
            {
                Debug.Log(t.name + " | path: " + GetPath(t));
            }
        }
    }

    string GetPath(Transform t)
    {
        string path = t.name;
        while (t.parent != null)
        {
            t = t.parent;
            path = t.name + "/" + path;
        }
        return path;
    }
}