using System.Collections;
using UnityEngine;
using UnityEngine.UI;

namespace UI.Animacoes
{
    [RequireComponent(typeof(Toggle))]
    public class CustomTogglePastel : MonoBehaviour
    {
        [Header("Referências")]
        [SerializeField] private Image background;
        [SerializeField] private RectTransform knob;

        [Header("Configurações do Knob")]
        [SerializeField] private float knobOffX = -20f;
        [SerializeField] private float knobOnX = 20f;
        [SerializeField] private float animationSpeed = 10f;

        [Header("Cores Pastéis")]
        [SerializeField] private Color offColor = new Color(0.95f, 0.65f, 0.65f);
        [SerializeField] private Color onColor = new Color(0.65f, 0.90f, 0.70f);

        private Toggle toggle;
        private Coroutine animationCoroutine;

        void Awake()
        {
            toggle = GetComponent<Toggle>();

            if (background == null || knob == null)
            {
                Debug.LogError($"[CustomTogglePastel] Referências não configuradas em {name}");
                enabled = false;
                return;
            }

            // Listener do Toggle
            toggle.onValueChanged.AddListener(OnToggleChanged);
        }

        void Start()
        {
            // Aplica o estado inicial imediatamente
            ApplyInstantState(toggle.isOn);
        }

        void OnDestroy()
        {
            if (toggle != null)
                toggle.onValueChanged.RemoveListener(OnToggleChanged);
        }

        private void OnToggleChanged(bool isOn)
        {
            // Debug para investigação (pode remover depois)
            Debug.Log($"[CustomTogglePastel] Toggle {name} mudou para: {isOn}");

            if (animationCoroutine != null)
                StopCoroutine(animationCoroutine);

            animationCoroutine = StartCoroutine(AnimateToggle(isOn));
        }

        private IEnumerator AnimateToggle(bool isOn)
        {
            float targetX = isOn ? knobOnX : knobOffX;
            Color targetColor = isOn ? onColor : offColor;

            while (Mathf.Abs(knob.anchoredPosition.x - targetX) > 0.05f)
            {
                float newX = Mathf.Lerp(
                    knob.anchoredPosition.x,
                    targetX,
                    Time.deltaTime * animationSpeed
                );

                knob.anchoredPosition = new Vector2(
                    newX,
                    knob.anchoredPosition.y
                );

                background.color = Color.Lerp(
                    background.color,
                    targetColor,
                    Time.deltaTime * animationSpeed
                );

                yield return null;
            }

            // Garante estado final exato
            knob.anchoredPosition = new Vector2(
                targetX,
                knob.anchoredPosition.y
            );

            background.color = targetColor;
        }

        private void ApplyInstantState(bool isOn)
        {
            float x = isOn ? knobOnX : knobOffX;
            knob.anchoredPosition = new Vector2(x, knob.anchoredPosition.y);
            background.color = isOn ? onColor : offColor;
        }
    }
}
