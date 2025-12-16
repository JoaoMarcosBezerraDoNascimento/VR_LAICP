using System.Collections;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using TMPro;
using UnityEngine;

public class MockIA_RMA : MonoBehaviour
{
    [Header("UI")]
    public TMP_Text inputPergunta;
    public TMP_Text textoResposta;

    [Header("Config")]
    public float delayResposta = 0f;

    [Header("Banco de Dados")]
    public TextAsset arquivoJson;

    RmaDatabase banco;

    void Start()
    {
        CarregarBanco();
    }

    void CarregarBanco()
    {
        if (arquivoJson == null)
        {
            Debug.LogError("[Mock IA] Arquivo JSON não atribuído no Inspector");
            return;
        }

        banco = JsonUtility.FromJson<RmaDatabase>(arquivoJson.text);

        if (banco == null || banco.rmas == null)
        {
            Debug.LogError("[Mock IA] Erro ao carregar banco de dados");
            banco = new RmaDatabase();
        }

        Debug.Log($"[Mock IA] Banco carregado com {banco.rmas.Count} RMAs");
    }

    public void AoClicarBotao()
    {
        if (banco == null)
        {
            textoResposta.text = "❌ Banco de dados não carregado.";
            return;
        }

        textoResposta.text = "🤖 Analisando informações...";
        StartCoroutine(ProcessarPergunta());
    }

    enum Intencao
    {
        DetalheRma,
        RmaHoje,
        TarefasHoje,
        ProcedimentosSeguranca,
        Epi,
        ResumoGarantia,
        ResumoDivergencias,
        Desconhecida
    }

    IEnumerator ProcessarPergunta()
    {
        yield return new WaitForSeconds(delayResposta);

        string pergunta = RemoverAcentos(inputPergunta.text.ToLower());
        string resposta = GerarResposta(pergunta);

        textoResposta.text = resposta;
    }

    string GerarResposta(string pergunta)
    {
        var intencao = DetectarIntencao(pergunta);

        switch (intencao)
        {
            case Intencao.DetalheRma:
                return DetalheRMA(pergunta);

            case Intencao.RmaHoje:
                return ResumoRmasHoje();

            case Intencao.ResumoGarantia:
                return ResumoGarantia();

            case Intencao.ResumoDivergencias:
                return ResumoDivergencias();

            case Intencao.TarefasHoje:
                return TarefasHoje();

            case Intencao.ProcedimentosSeguranca:
                return ProcedimentosSeguranca();

            case Intencao.Epi:
                return ListaEpis();

            default:
                return ResumoGeral();
        }
    }

    Intencao DetectarIntencao(string pergunta)
    {
        if (pergunta.Contains("rma") && pergunta.Any(char.IsDigit))
            return Intencao.DetalheRma;

        if (pergunta.Contains("rma") &&
            (pergunta.Contains("hoje") || pergunta.Contains("dia")))
            return Intencao.RmaHoje;

        if (pergunta.Contains("garantia"))
            return Intencao.ResumoGarantia;

        if (pergunta.Contains("divergencia"))
            return Intencao.ResumoDivergencias;

        if ((pergunta.Contains("tarefa") ||
             pergunta.Contains("fazer") ||
             pergunta.Contains("atividade")) &&
            (pergunta.Contains("hoje") || pergunta.Contains("dia")))
            return Intencao.TarefasHoje;

        if (pergunta.Contains("seguranca") ||
            pergunta.Contains("procedimento"))
            return Intencao.ProcedimentosSeguranca;

        if (pergunta.Contains("epi") ||
            pergunta.Contains("equipamento de protecao"))
            return Intencao.Epi;

        return Intencao.Desconhecida;
    }

    // ================== RESPOSTAS ==================

    string ResumoGeral()
    {
        return
$@"📊 RESUMO OPERACIONAL

• RMAs ativos: {banco.rmas.Count}
• Peças registradas: {banco.rmas.Sum(r => r.pecas.Count)}
• Peças em garantia: {banco.rmas.Sum(r => r.pecas.Count(p => p.garantia))}
• Peças com divergência: {banco.rmas.Sum(r => r.pecas.Count(p => p.divergencia))}

👉 Sugestão:
Priorizar peças com divergência e garantia ativa.";
    }

    string ResumoRmasHoje()
    {
        return
@"📦 RMAs RECEBIDOS HOJE

• RMA 49928413802 – Empresa_378
• RMA 84686695358 – Empresa_634
• RMA 50072622230 – Empresa_255
• RMA 77767544399 – Empresa_710 

Status:
• Aguardando triagem técnica.";
    }

    string TarefasHoje()
    {
        return
@"🗂️ TAREFAS DO DIA

• Conferir RMAs recebidos
• Analisar peças em garantia
• Registrar divergências
• Atualizar sistema

✔ Prioridade: Alta";
    }

    string ProcedimentosSeguranca()
    {
        return
@"⚠️ PROCEDIMENTOS DE SEGURANÇA

• Uso obrigatório de EPI
• Área de teste sinalizada
• Equipamentos desligados
• Seguir NR-12 e NR-06

Em caso de dúvida:
Consulte o manual interno.";
    }

    string ListaEpis()
    {
        return
@"🦺 EPIs OBRIGATÓRIOS

• Luvas de proteção
• Óculos de segurança
• Calçado de segurança
• Avental técnico

Uso obrigatório durante a operação.";
    }

    string ResumoGarantia()
    {
        int total = banco.rmas.Sum(r => r.pecas.Count(p => p.garantia));

        return
$@"🛡️ PEÇAS EM GARANTIA

• Total: {total}
• RMAs afetados: {banco.rmas.Count(r => r.pecas.Any(p => p.garantia))}

👉 Ação:
Priorizar análise técnica.";
    }

    string ResumoDivergencias()
    {
        int total = banco.rmas.Sum(r => r.pecas.Count(p => p.divergencia));

        return
$@"⚠️ DIVERGÊNCIAS

• Total: {total}
• RMAs com inconsistência: {banco.rmas.Count(r => r.pecas.Any(p => p.divergencia))}

👉 Recomendação:
Validar documentação.";
    }

    string DetalheRMA(string pergunta)
    {
        string numero = new string(pergunta.Where(char.IsDigit).ToArray());

        if (string.IsNullOrEmpty(numero))
            return "⚠️ Informe o número do RMA.";

        var rma = banco.rmas.FirstOrDefault(r =>
            r.numero_pedido_rma.TrimStart('0') == numero.TrimStart('0')
        );

        if (rma == null)
            return $"❌ RMA {numero} não encontrado.";

        return
$@"📦 DETALHES DO RMA {rma.numero_pedido_rma}

Cliente: {rma.cliente}
Data: {rma.data_chegada}
Peças: {rma.pecas.Count}

✔ Análise técnica em andamento.";
    }

    string RemoverAcentos(string texto)
    {
        var normalized = texto.Normalize(NormalizationForm.FormD);
        var sb = new StringBuilder();

        foreach (var c in normalized)
        {
            if (System.Globalization.CharUnicodeInfo.GetUnicodeCategory(c)
                != System.Globalization.UnicodeCategory.NonSpacingMark)
                sb.Append(c);
        }

        return sb.ToString().Normalize(NormalizationForm.FormC);
    }
}

// ================== MODELOS ==================

[System.Serializable]
public class RmaDatabase
{
    public List<Rma> rmas = new List<Rma>();
}

[System.Serializable]
public class Rma
{
    public string numero_pedido_rma;
    public string cliente;
    public string data_chegada;
    public string finalizado;
    public List<Peca> pecas = new List<Peca>();
}

[System.Serializable]
public class Peca
{
    public int tipo;
    public string serial;
    public bool garantia;
    public bool divergencia;
    public string comentario;
}
