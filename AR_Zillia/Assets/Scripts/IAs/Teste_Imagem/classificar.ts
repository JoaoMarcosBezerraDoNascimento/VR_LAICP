// rank_runs.ts
// Uso: npx tsx rank_runs.ts
// (ou: RUNS_JSONL=./resultados/_tabela_runs.jsonl OUT_PREFIX=./resultados/_runs_ranked npx tsx rank_runs.ts)

import * as fs from "fs";
import * as path from "path";

const RUNS_JSONL = process.env.RUNS_JSONL ?? path.resolve(process.cwd(), "resultados", "_tabela_runs.jsonl");
const OUT_PREFIX = process.env.OUT_PREFIX ?? path.resolve(process.cwd(), "resultados", "_runs_ranked");

type RunRecord = {
  run_id?: string;
  run_timestamp?: string;
  phase?: string;
  imagens_match?: number;
  streak_after?: number;
  tempo_ms?: { min?: number; avg?: number; max?: number };
  acc?: { geral?: number; tipo?: number; riscada?: number; oxidada?: number; batida?: number };
  candidate?: { options?: Record<string, any>; engineer_comment?: string; prompt?: string };
};

function safeNumber(x: any): number | undefined {
  const n = Number(x);
  return Number.isFinite(n) ? n : undefined;
}

function recomputeOverall(acc?: RunRecord["acc"]) {
  const tipo = safeNumber(acc?.tipo);
  const riscada = safeNumber(acc?.riscada);
  const oxidada = safeNumber(acc?.oxidada);
  const batida = safeNumber(acc?.batida);

  const parts = [tipo, riscada, oxidada, batida].filter((v): v is number => typeof v === "number");
  if (!parts.length) return undefined;

  const sum = parts.reduce((a, b) => a + b, 0);
  return sum / parts.length; // média (desconsidera ausentes)
}

function readJsonl(filePath: string): any[] {
  if (!fs.existsSync(filePath)) throw new Error(`Arquivo não existe: ${filePath}`);
  const txt = fs.readFileSync(filePath, "utf-8").trim();
  if (!txt) return [];
  return txt
    .split(/\r?\n/)
    .map((line) => {
      try {
        return JSON.parse(line);
      } catch {
        return null;
      }
    })
    .filter(Boolean);
}

function toPct(x: number | undefined) {
  if (typeof x !== "number") return "";
  return (x * 100).toFixed(2) + "%";
}

function main() {
  const rows = readJsonl(RUNS_JSONL) as RunRecord[];
  if (!rows.length) {
    console.log("Nenhum run encontrado no JSONL.");
    return;
  }

  // Enriquecer com geral_recalc
  const enriched = rows.map((r) => {
    const geral_recalc = recomputeOverall(r.acc);
    return { ...r, geral_recalc };
  });

  // Ordenação:
  // 1) maior geral_recalc
  // 2) maior tipo (pra desempatar)
  // 3) menor tempo médio (se existir)
  // tell: se ainda empatar, mais recente
  enriched.sort((a: any, b: any) => {
    const ga = safeNumber(a.geral_recalc) ?? -1;
    const gb = safeNumber(b.geral_recalc) ?? -1;
    if (gb !== ga) return gb - ga;

    const ta = safeNumber(a.acc?.tipo) ?? -1;
    const tb = safeNumber(b.acc?.tipo) ?? -1;
    if (tb !== ta) return tb - ta;

    const tma = safeNumber(a.tempo_ms?.avg) ?? Number.POSITIVE_INFINITY;
    const tmb = safeNumber(b.tempo_ms?.avg) ?? Number.POSITIVE_INFINITY;
    if (tma !== tmb) return tma - tmb;

    const da = Date.parse(a.run_timestamp ?? "") || 0;
    const db = Date.parse(b.run_timestamp ?? "") || 0;
    return db - da;
  });

  // Saídas
  const outJsonl = `${OUT_PREFIX}.jsonl`;
  const outCsv = `${OUT_PREFIX}.csv`;

  // JSONL ordenado (mantém tudo + geral_recalc)
  fs.writeFileSync(outJsonl, enriched.map((x) => JSON.stringify(x)).join("\n") + "\n", "utf-8");

  // CSV ordenado (colunas mais úteis)
  const header = [
    "rank",
    "run_timestamp",
    "run_id",
    "phase",
    "imagens_match",
    "streak_after",
    "geral_recalc",
    "acc_tipo",
    "acc_riscada",
    "acc_oxidada",
    "acc_batida",
    "tempo_avg_ms",
    "tempo_min_ms",
    "tempo_max_ms",
    "engineer_comment",
    "options",
  ].join(";");

  const lines = enriched.map((r: any, i: number) => {
    const optionsStr = r.candidate?.options ? JSON.stringify(r.candidate.options) : "";
    const engineer = (r.candidate?.engineer_comment ?? "").replaceAll("\n", " ").slice(0, 220);
    return [
      String(i + 1),
      r.run_timestamp ?? "",
      r.run_id ?? "",
      r.phase ?? "",
      String(r.imagens_match ?? ""),
      String(r.streak_after ?? ""),
      typeof r.geral_recalc === "number" ? r.geral_recalc.toFixed(6) : "",
      typeof r.acc?.tipo === "number" ? r.acc.tipo.toFixed(6) : "",
      typeof r.acc?.riscada === "number" ? r.acc.riscada.toFixed(6) : "",
      typeof r.acc?.oxidada === "number" ? r.acc.oxidada.toFixed(6) : "",
      typeof r.acc?.batida === "number" ? r.acc.batida.toFixed(6) : "",
      String(r.tempo_ms?.avg ?? ""),
      String(r.tempo_ms?.min ?? ""),
      String(r.tempo_ms?.max ?? ""),
      engineer,
      optionsStr,
    ].join(";");
  });

  fs.writeFileSync(outCsv, header + "\n" + lines.join("\n") + "\n", "utf-8");

  // Top 20 no console
  console.log(`\n✅ Rank gerado!`);
  console.log(`- JSONL: ${outJsonl}`);
  console.log(`- CSV : ${outCsv}\n`);

  console.log(`TOP 20 (por geral_recalc):`);
  for (let i = 0; i < Math.min(20, enriched.length); i++) {
    const r: any = enriched[i];
    console.log(
      `${String(i + 1).padStart(3, " ")} | ${r.run_timestamp ?? "?"} | geral=${toPct(r.geral_recalc)} | tipo=${toPct(
        r.acc?.tipo
      )} R=${toPct(r.acc?.riscada)} O=${toPct(r.acc?.oxidada)} B=${toPct(r.acc?.batida)} | t_avg=${r.tempo_ms?.avg ?? "?"}ms | ${r.run_id ?? ""}`
    );
  }
}

main();
