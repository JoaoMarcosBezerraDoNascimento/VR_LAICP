using UnityEngine;
using UnityEngine.UI;
using UnityEngine.XR.Hands;
using UnityEngine.XR;
using System.Collections.Generic;

public class PinchScrollVR_WithButton : MonoBehaviour
{
    [Header("UI")]
    public ScrollRect scroll;
    public Button pinchToggleButton;
    public Text pinchStatusText;

    [Header("Ajustes da Pinça")]
    public float distanciaLimite = 0.015f;
    public float sensibilidade = 0.5f;

    private XRHandSubsystem handSubsystem;

    private float ultimoY;
    private bool pinchAtivo = false;
    private bool pinchEnabled = false;

    void Start()
    {
        if (scroll == null)
            scroll = GetComponent<ScrollRect>();

        // pegar o subsistema XR Hands ativo
        var subsystems = new List<XRHandSubsystem>();
        SubsystemManager.GetSubsystems(subsystems);

        if (subsystems.Count > 0)
            handSubsystem = subsystems[0];

        // botão ativa/desativa
        pinchToggleButton.onClick.AddListener(TogglePinchMode);

        AtualizarTextoStatus();
    }

    void TogglePinchMode()
    {
        pinchEnabled = !pinchEnabled;
        AtualizarTextoStatus();
    }

    void AtualizarTextoStatus()
    {
        pinchStatusText.text = pinchEnabled ? "Pinça: ON" : "Pinça: OFF";
    }

    void Update()
    {
        if (!pinchEnabled) return;
        if (scroll == null || handSubsystem == null) return;

        var leftHand = handSubsystem.leftHand;
        if (!leftHand.isTracked) return;

        // pegar juntas modernas
        bool okIndex = leftHand.GetJoint(XRHandJointID.IndexTip, out XRHandJoint indexTip);
        bool okThumb = leftHand.GetJoint(XRHandJointID.ThumbTip, out XRHandJoint thumbTip);

        if (!okIndex || !okThumb) return;

        Vector3 indicadorPos = indexTip.Pose.position;
        Vector3 dedaoPos = thumbTip.Pose.position;

        float dist = Vector3.Distance(indicadorPos, dedaoPos);

        // ativa pinch quando os dedos encostam
        if (dist < distanciaLimite)
        {
            if (!pinchAtivo)
            {
                pinchAtivo = true;
                ultimoY = indicadorPos.y;
            }
        }
        else
        {
            pinchAtivo = false;
            return;
        }

        float movimentoY = indicadorPos.y - ultimoY;

        scroll.verticalNormalizedPosition += movimentoY * sensibilidade * -1;

        ultimoY = indicadorPos.y;
    }
}