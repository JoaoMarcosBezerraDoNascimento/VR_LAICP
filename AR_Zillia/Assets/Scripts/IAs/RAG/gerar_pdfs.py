import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from pathlib import Path

# ============================
# CONFIGURAÇÕES
# ============================

CAMINHO_CSV = Path("logs") / "relatorio_teste_rag.csv"
PASTA_SAIDA = Path("logs") / "PDFs"

PASTA_SAIDA.mkdir(parents=True, exist_ok=True)

# Paleta de cores "instagramável" (azul, roxo, verde, laranja)
COR_TEMPO = "#2563EB"         # azul
COR_Q_RESP = "#7C3AED"        # roxo
COR_Q_RAG = "#10B981"         # verde
COR_SCATTER = "#F97316"       # laranja

COR_MIN = "#22C55E"           # verde para mínimo
COR_MAX = "#F97316"           # laranja para máximo
COR_MEDIA = "#6B7280"         # cinza para média
COR_MEDIANA = "#9CA3AF"       # cinza claro para mediana

# ============================
# CARREGAR E PREPARAR DADOS
# ============================

df = pd.read_csv(CAMINHO_CSV, sep=";")

# Garantir tipos numéricos
for col in ["tempo_entre_linhas_s", "qualidade_resposta", "qualidade_rag"]:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

# Converter timestamp pra datetime (só pra garantir ordenação)
df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

# ============================
# FUNÇÕES AUXILIARES
# ============================

def estilizar_axes(ax, titulo, xlabel, ylabel):
    """Aplica um visual mais clean e profissional aos gráficos."""
    ax.set_title(titulo, fontsize=14, fontweight="bold", pad=12)
    ax.set_xlabel(xlabel, fontsize=11)
    ax.set_ylabel(ylabel, fontsize=11)

    # Grid leve só no eixo y
    ax.grid(True, axis="y", linestyle="--", linewidth=0.7, alpha=0.4)

    # Deixa as bordas mais clean
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Ajuste de fonte dos ticks
    ax.tick_params(axis="both", labelsize=9)


def calcular_stats_outliers(serie: pd.Series):
    """
    Calcula estatísticas básicas e outliers via IQR.
    Retorna:
      - mask_outlier (Series booleana no índice original)
      - stats (dict com min, max, mean, median, std)
      - limites (lim_inf, lim_sup)
    """
    s = serie.dropna()
    if s.empty:
        mask_outlier = pd.Series(False, index=serie.index)
        stats = {"min": None, "max": None, "mean": None, "median": None, "std": None}
        return mask_outlier, stats, (None, None)

    q1 = s.quantile(0.25)
    q3 = s.quantile(0.75)
    iqr = q3 - q1
    lim_inf = q1 - 1.5 * iqr
    lim_sup = q3 + 1.5 * iqr

    mask_outlier = (serie < lim_inf) | (serie > lim_sup)

    s_sem_out = s[(s >= lim_inf) & (s <= lim_sup)]

    if s_sem_out.empty:
        # Se tudo foi considerado outlier, volta para os dados originais
        s_sem_out = s.copy()
        mask_outlier = pd.Series(False, index=serie.index)

    stats = {
        "min": float(s_sem_out.min()),
        "max": float(s_sem_out.max()),
        "mean": float(s_sem_out.mean()),
        "median": float(s_sem_out.median()),
        "std": float(s_sem_out.std(ddof=1)) if len(s_sem_out) > 1 else 0.0,
    }

    return mask_outlier, stats, (float(lim_inf), float(lim_sup))


def plot_serie_com_stats(
    ax,
    grupo: pd.DataFrame,
    coluna: str,
    cor_linha: str,
    y_label: str,
    titulo: str,
    limitar_01: bool = False,
):
    """
    Plota uma série (tempo / qualidade / etc) com:
    - outliers removidos do gráfico (IQR)
    - média e mediana como linhas
    - mínimo e máximo destacados
    - legenda com resumo de outliers
    """
    serie = grupo[coluna]

    mask_outlier, stats, (lim_inf, lim_sup) = calcular_stats_outliers(serie)

    # Série para plot (outliers como NaN)
    serie_plot = serie.mask(mask_outlier)

    # Índice de interação
    x = grupo["indice"]

    # Linha principal
    ax.plot(
        x,
        serie_plot,
        marker="o",
        linewidth=2.2,
        markersize=6,
        color=cor_linha,
        label=f"{y_label} (sem outliers)",
    )

    # Min / Max (nos dados sem outliers)
    serie_sem_out = serie_plot.dropna()
    if not serie_sem_out.empty:
        idx_min = serie_sem_out.idxmin()
        idx_max = serie_sem_out.idxmax()
        x_min = grupo.loc[idx_min, "indice"]
        x_max = grupo.loc[idx_max, "indice"]
        y_min = serie_sem_out.min()
        y_max = serie_sem_out.max()

        ax.scatter(
            x_min,
            y_min,
            color=COR_MIN,
            s=60,
            zorder=3,
            label=f"Mínimo {y_min:.2f}",
        )
        ax.scatter(
            x_max,
            y_max,
            color=COR_MAX,
            s=60,
            zorder=3,
            label=f"Máximo {y_max:.2f}",
        )

    # Média e Mediana
    if stats["mean"] is not None:
        ax.axhline(
            stats["mean"],
            color=COR_MEDIA,
            linestyle="--",
            linewidth=1.5,
            alpha=0.9,
            label=f"Média {stats['mean']:.2f}",
        )
    if stats["median"] is not None:
        ax.axhline(
            stats["median"],
            color=COR_MEDIANA,
            linestyle=":",
            linewidth=1.3,
            alpha=0.9,
            label=f"Mediana {stats['median']:.2f}",
        )

    # Limite 0–1 para métricas de qualidade
    if limitar_01:
        ax.set_ylim(0, 1.05)

    # Texto de outliers para legenda
    outliers_df = grupo.loc[mask_outlier & serie.notna(), ["indice", coluna]]
    if not outliers_df.empty:
        if len(outliers_df) <= 5:
            exemplos = ", ".join(
                f"{int(row.indice)}({row[coluna]:.2f})"
                for _, row in outliers_df.iterrows()
            )
            texto_out = f"Outliers removidos (n={len(outliers_df)}): {exemplos}"
        else:
            primeiros = outliers_df.head(3)
            exemplos = ", ".join(
                f"{int(row.indice)}({row[coluna]:.2f})"
                for _, row in primeiros.iterrows()
            )
            texto_out = (
                f"Outliers removidos (n={len(outliers_df)}), exemplos: {exemplos} ..."
            )
    else:
        texto_out = "Sem outliers (IQR)"

    # Handle fake só pra aparecer na legenda
    ax.scatter(
        [],
        [],
        marker="x",
        color="red",
        label=texto_out,
    )

    estilizar_axes(ax, titulo, "Interação", y_label)

    # Legenda
    ax.legend(loc="best", fontsize=8)


# ============================
# FUNÇÃO PARA GERAR PDF POR TIPO
# ============================

def gerar_pdf_por_tipo(tipo_teste: str, grupo: pd.DataFrame):
    # Ordena por timestamp e cria índice de interação
    grupo = grupo.sort_values("timestamp").reset_index(drop=True)
    grupo["indice"] = range(1, len(grupo) + 1)

    caminho_pdf = PASTA_SAIDA / f"Resultados_{tipo_teste}.pdf"

    with PdfPages(caminho_pdf) as pdf:
        # ---------- Gráfico 1: Tempo entre linhas ----------
        fig, ax = plt.subplots(figsize=(8, 5))
        plot_serie_com_stats(
            ax=ax,
            grupo=grupo,
            coluna="tempo_entre_linhas_s",
            cor_linha=COR_TEMPO,
            y_label="Tempo entre linhas (s)",
            titulo=f"Tempo entre interações ({tipo_teste})",
            limitar_01=False,
        )
        fig.tight_layout()
        pdf.savefig(fig)
        plt.close(fig)

        # ---------- Gráfico 2: Qualidade da resposta ----------
        fig, ax = plt.subplots(figsize=(8, 5))
        plot_serie_com_stats(
            ax=ax,
            grupo=grupo,
            coluna="qualidade_resposta",
            cor_linha=COR_Q_RESP,
            y_label="Qualidade da resposta",
            titulo=f"Qualidade da resposta ({tipo_teste})",
            limitar_01=True,
        )
        fig.tight_layout()
        pdf.savefig(fig)
        plt.close(fig)

        # ---------- Gráfico 3: Qualidade do RAG (se existir) ----------
        if grupo["qualidade_rag"].notna().any():
            fig, ax = plt.subplots(figsize=(8, 5))
            plot_serie_com_stats(
                ax=ax,
                grupo=grupo,
                coluna="qualidade_rag",
                cor_linha=COR_Q_RAG,
                y_label="Qualidade do RAG",
                titulo=f"Qualidade do RAG ({tipo_teste})",
                limitar_01=True,
            )
            fig.tight_layout()
            pdf.savefig(fig)
            plt.close(fig)

        # ---------- Gráfico 4: Dispersão Tempo x Qualidade ----------
        fig, ax = plt.subplots(figsize=(8, 5))

        # Outliers para tempo e qualidade (para filtrar do scatter)
        mask_out_tempo, stats_tempo, _ = calcular_stats_outliers(
            grupo["tempo_entre_linhas_s"]
        )
        mask_out_q, stats_q, _ = calcular_stats_outliers(
            grupo["qualidade_resposta"]
        )
        mask_keep = ~(mask_out_tempo | mask_out_q)

        scatter_data = grupo[mask_keep]

        ax.scatter(
            scatter_data["tempo_entre_linhas_s"],
            scatter_data["qualidade_resposta"],
            s=40,
            alpha=0.85,
            color=COR_SCATTER,
            edgecolors="white",
            linewidth=0.7,
            label="Pontos (sem outliers)",
        )

        # Linhas de média de tempo (vertical) e qualidade (horizontal)
        if stats_tempo["mean"] is not None:
            ax.axvline(
                stats_tempo["mean"],
                color=COR_MEDIA,
                linestyle="--",
                linewidth=1.3,
                alpha=0.9,
                label=f"Média tempo {stats_tempo['mean']:.1f}s",
            )
        if stats_q["mean"] is not None:
            ax.axhline(
                stats_q["mean"],
                color=COR_MEDIANA,
                linestyle="--",
                linewidth=1.3,
                alpha=0.9,
                label=f"Média qualidade {stats_q['mean']:.2f}",
            )

        # Informações de outliers no scatter
        n_out_tempo = int(mask_out_tempo.sum())
        n_out_q = int(mask_out_q.sum())
        texto_out = f"Outliers removidos (tempo: {n_out_tempo}, qualidade: {n_out_q})"

        ax.scatter([], [], marker="x", color="red", label=texto_out)

        estilizar_axes(
            ax,
            f"Tempo x Qualidade da resposta ({tipo_teste})",
            "Tempo entre linhas (s)",
            "Qualidade da resposta",
        )
        ax.set_ylim(0, 1.05)
        ax.legend(loc="best", fontsize=8)

        fig.tight_layout()
        pdf.savefig(fig)
        plt.close(fig)

    print(f"PDF gerado: {caminho_pdf}")


# ============================
# GERAR PDFs PARA CADA TIPO
# ============================

for tipo, grupo in df.groupby("tipo_teste"):
    gerar_pdf_por_tipo(tipo, grupo)
