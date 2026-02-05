import * as fs from "fs";
import * as path from "path";

type Status = "SIM" | "NAO" | "INCONCLUSIVO";

const PRED_DIR = path.resolve(process.cwd(), "saida_txt");
const GAB_DIR = path.resolve(process.cwd(), "gabaritos");
const RESULTS_DIR = path.resolve(process.cwd(), "resultados");

const OUT_CSV = path.join(RESULTS_DIR, "_comparacao.csv");
const RUNS_TABLE_CSV = path.join(RESULTS_DIR, "_tabela_runs.csv");
const RUNS_TABLE_JSONL = path.join(RESULTS_DIR, "_tabela_runs.jsonl");

function stripDiacritics(s: string) {
  return s.normalize("NFD").replace(/[\u0300-\u036f]/g, "");
}

function normalizeStatus(v: any): Status | undefined {
  if (typeof v !== "string") return undefined;
  const x = stripDiacritics(v.trim().toUpperCase());
  if (x === "SIM") return "SIM";
  if (x === "NAO" || x === "NÃO") return "NAO";
  if (x === "INCONCLUSIVO") return "INCONCLUSIVO";
  return undefined;
}

function normalizeTipo(v: any): string | undefined {
  if (typeof v !== "string") return undefined;
  const x = stripDiacritics(v.trim().toUpperCase());
  if (x === "DIMM") return "DIM";
  if (x === "SODIMM" || x === "SO-DIMM") return "SODIM";
  if (x === "DIM") return "DIM";
  if (x === "SODIM") return "SODIM";
  return x;
}

function extractFirstJson(text: string): string | null {
  const trimmed = text.trim();
  const first = trimmed.indexOf("{");
  const last = trimmed.lastIndexOf("}");
  if (first >= 0 && last > first) return trimmed.slice(first, last + 1);
  return null;
}

function readJsonFromTxt(filePath: string): any | null {
  const txt = fs.readFileSync(filePath, "utf-8");
  const jsonStr = extractFirstJson(txt);
  if (!jsonStr) return null;
  try {
    return JSON.parse(jsonStr);
  } catch {
    return null;
  }
}

function listTxt(dir: string): string[] {
  if (!fs.existsSync(dir)) return [];
  return fs
    .readdirSync(dir)
    .filter((f) => f.toLowerCase().endsWith(".txt"))
    .map((f) => path.join(dir, f));
}

function baseName(filePath: string) {
  return path.basename(filePath);
}

function pct(x: number) {
  return `${(x * 100).toFixed(2)}%`;
}

type Row = {
  arquivo: string;

  // ground truth
  gtTIPO?: string;
  gtriscada?: Status;
  gtoxidada?: Status;
  gtbatida?: Status;

  // prediction
  prTIPO?: string;
  prriscada?: Status;
  proxyidada?: Status;
  prbatida?: Status;

  // hits
  hitTIPO?: boolean;
  hitriscada?: boolean;
  hitoxidada?: boolean;
  hitbatida?: boolean;

  duracaoMs?: number;

  // debug: faltas
  miss_gt?: string[];
  miss_pr?: string[];
};

function extractHeaderValue(txt: string, prefix: string): string | undefined {
  const lines = txt.split(/\r?\n/);
  const line = lines.find((l) => l.startsWith(prefix));
  if (!line) return undefined;
  return line.slice(prefix.length).trim();
}

function readDurationMsFromPred(filePath: string): number | undefined {
  const txt = fs.readFileSync(filePath, "utf-8");
  const v = extractHeaderValue(txt, "# duracao_ms:");
  if (!v) return undefined;
  const n = Number(v);
  return Number.isFinite(n) ? n : undefined;
}

function readModelFromPred(filePath: string): string | undefined {
  const txt = fs.readFileSync(filePath, "utf-8");
  const v = extractHeaderValue(txt, "# modelo:");
  return v?.trim();
}

function readTimestampFromPred(filePath: string): string | undefined {
  const txt = fs.readFileSync(filePath, "utf-8");
  const v = extractHeaderValue(txt, "# data:");
  return v?.trim();
}

function safeAppendCsvLine(filePath: string, headerLine: string, line: string) {
  const exists = fs.existsSync(filePath);
  if (!exists) {
    fs.writeFileSync(filePath, headerLine + "\n" + line + "\n", "utf-8");
  } else {
    fs.appendFileSync(filePath, line + "\n", "utf-8");
  }
}

// ---- helpers de aliases (MAIÚSCULO/minúsculo/typos) ----
function getAny(obj: any, keys: string[]) {
  if (!obj || typeof obj !== "object") return undefined;
  for (const k of keys) {
    if (k in obj) return obj[k];
  }
  return undefined;
}

function getStatus(obj: any, keys: string[]): Status | undefined {
  return normalizeStatus(getAny(obj, keys));
}

function getTipo(obj: any, keys: string[]): string | undefined {
  return normalizeTipo(getAny(obj, keys));
}

function main() {
  if (!fs.existsSync(RESULTS_DIR)) {
    fs.mkdirSync(RESULTS_DIR, { recursive: true });
  }
  if (!fs.existsSync(PRED_DIR)) {
    console.log(`Pasta de predições não existe: ${PRED_DIR}`);
    process.exit(1);
  }
  if (!fs.existsSync(GAB_DIR)) {
    console.log(`Pasta de gabaritos não existe: ${GAB_DIR}`);
    process.exit(1);
  }

  const predFiles = listTxt(PRED_DIR).filter((f) => {
    const bn = path.basename(f);
    return !bn.startsWith("_") && bn.toLowerCase().endsWith(".txt");
  });
  const gabFiles = listTxt(GAB_DIR);

  const predMap = new Map<string, string>();
  for (const f of predFiles) predMap.set(baseName(f), f);

  const gabMap = new Map<string, string>();
  for (const f of gabFiles) gabMap.set(baseName(f), f);

  const names = [...predMap.keys()].filter((k) => gabMap.has(k)).sort();
  const missingGab = [...predMap.keys()].filter((k) => !gabMap.has(k));
  const missingPred = [...gabMap.keys()].filter((k) => !predMap.has(k));

  if (names.length === 0) {
    console.log("Nenhum arquivo com nome igual entre saida_txt e gabaritos.");
    console.log("Exemplo esperado: saida_txt/imagem_ (1).txt e gabaritos/imagem_ (1).txt");
    return;
  }

  const rows: Row[] = [];

  for (const name of names) {
    const predPath = predMap.get(name)!;
    const gabPath = gabMap.get(name)!;

    const predObj = readJsonFromTxt(predPath);
    const gabObj = readJsonFromTxt(gabPath);

    const r: Row = { arquivo: name, miss_gt: [], miss_pr: [] };

    // ---- GT (gabarito) ----
    if (gabObj) {
      r.gtTIPO = getTipo(gabObj, ["TIPO", "Tipo", "tipo"]);
      r.gtriscada = getStatus(gabObj, ["riscada", "Riscada", "RISCADA"]);
      r.gtoxidada = getStatus(gabObj, ["oxidada", "Oxidada", "OXIDADA", "Oxidade", "oxidade"]);
      r.gtbatida = getStatus(gabObj, ["batida", "Batida", "BATIDA"]);
    }

    if (r.gtTIPO === undefined) r.miss_gt!.push("TIPO");
    if (r.gtriscada === undefined) r.miss_gt!.push("Riscada");
    if (r.gtoxidada === undefined) r.miss_gt!.push("Oxidada");
    if (r.gtbatida === undefined) r.miss_gt!.push("Batida");

    // ---- Pred (IA) ----
    if (predObj) {
      r.prTIPO = getTipo(predObj, ["TIPO", "Tipo", "tipo"]);
      r.prriscada = getStatus(predObj, ["riscada", "Riscada", "RISCADA"]);
      r.proxyidada = getStatus(predObj, ["oxidada", "Oxidada", "OXIDADA", "Oxidade", "oxidade"]);
      r.prbatida = getStatus(predObj, ["batida", "Batida", "BATIDA"]);
    }

    if (r.prTIPO === undefined) r.miss_pr!.push("TIPO");
    if (r.prriscada === undefined) r.miss_pr!.push("Riscada");
    if (r.proxyidada === undefined) r.miss_pr!.push("Oxidada");
    if (r.prbatida === undefined) r.miss_pr!.push("Batida");

    // ---- Hits (só conta se os dois lados existem) ----
    r.hitTIPO = r.gtTIPO !== undefined && r.prTIPO !== undefined ? r.gtTIPO === r.prTIPO : undefined;
    r.hitriscada = r.gtriscada !== undefined && r.prriscada !== undefined ? r.gtriscada === r.prriscada : undefined;
    r.hitoxidada = r.gtoxidada !== undefined && r.proxyidada !== undefined ? r.gtoxidada === r.proxyidada : undefined;
    r.hitbatida = r.gtbatida !== undefined && r.prbatida !== undefined ? r.gtbatida === r.prbatida : undefined;

    r.duracaoMs = readDurationMsFromPred(predPath);

    rows.push(r);
  }

  function acc(field: keyof Row): { hits: number; total: number; acc: number } {
    const vals = rows.map((r) => r[field]).filter((v) => typeof v === "boolean") as boolean[];
    const total = vals.length;
    const hits = vals.filter(Boolean).length;
    return { hits, total, acc: total ? hits / total : 0 };
  }

  const aTIPO = acc("hitTIPO");
  const aR = acc("hitriscada");
  const aO = acc("hitoxidada");
  const aB = acc("hitbatida");

  // acurácia geral (somente 3 defeitos)
  const perImage = rows.map((r) => {
    const comps: boolean[] = [];
    if (typeof r.hitriscada === "boolean") comps.push(r.hitriscada);
    if (typeof r.hitoxidada === "boolean") comps.push(r.hitoxidada);
    if (typeof r.hitbatida === "boolean") comps.push(r.hitbatida);
    const total = comps.length;
    const hits = comps.filter(Boolean).length;
    return { arquivo: r.arquivo, hits, total, score: total ? hits / total : 0 };
  });

  const totalComps = perImage.reduce((a, x) => a + x.total, 0);
  const totalHits = perImage.reduce((a, x) => a + x.hits, 0);
  const overall = totalComps ? totalHits / totalComps : 0;

  console.log(`Comparações feitas (arquivos com match): ${rows.length}`);

  console.log("\n--- Acurácia por campo ---");
  console.log(`TIPO:    ${aTIPO.hits}/${aTIPO.total} = ${pct(aTIPO.acc)}`);
  console.log(`Riscada: ${aR.hits}/${aR.total} = ${pct(aR.acc)}`);
  console.log(`Oxidada: ${aO.hits}/${aO.total} = ${pct(aO.acc)}`);
  console.log(`Batida:  ${aB.hits}/${aB.total} = ${pct(aB.acc)}`);

  console.log("\n--- Acurácia geral (Riscada+Oxidada+Batida) ---");
  console.log(`${totalHits}/${totalComps} = ${pct(overall)}`);

  // Tempo
  const tempos = rows.map((r) => r.duracaoMs).filter((x): x is number => typeof x === "number" && !Number.isNaN(x));
  let tMin: number | undefined;
  let tAvg: number | undefined;
  let tMax: number | undefined;

  if (tempos.length) {
    tMin = Math.min(...tempos);
    tMax = Math.max(...tempos);
    tAvg = tempos.reduce((a, b) => a + b, 0) / tempos.length;

    console.log("\n--- Tempos (ms) ---");
    console.log(`Amostras: ${tempos.length}`);
    console.log(`Mín: ${tMin} ms`);
    console.log(`Média: ${Math.round(tAvg)} ms`);
    console.log(`Máx: ${tMax} ms`);
  }

  if (missingGab.length) {
    console.log("\n⚠️ Sem gabarito para:");
    for (const n of missingGab) console.log(" - " + n);
  }
  if (missingPred.length) {
    console.log("\n⚠️ Sem predição para:");
    for (const n of missingPred) console.log(" - " + n);
  }

  // Aviso de campos faltantes (pra não inflar acurácia sem querer)
  const gtMissingCount = rows.filter((r) => (r.miss_gt?.length ?? 0) > 0).length;
  const prMissingCount = rows.filter((r) => (r.miss_pr?.length ?? 0) > 0).length;

  if (gtMissingCount || prMissingCount) {
    console.log("\n⚠️ Campos ausentes detectados (isso pode reduzir TOTAL e inflar % se você não perceber):");
    console.log(` - Arquivos com campo faltando no GABARITO: ${gtMissingCount}`);
    console.log(` - Arquivos com campo faltando na PREDIÇÃO: ${prMissingCount}`);
    console.log("   (Veja o CSV detalhado para identificar quais.)");
  }

  // ✅ CSV detalhado (por imagem)
  const header = [
    "arquivo",
    "gtTIPO","prTIPO","hitTIPO",
    "gtRiscada","prRiscada","hitRiscada",
    "gtOxidada","prOxidada","hitOxidada",
    "gtBatida","prBatida","hitBatida",
    "duracaoMs",
    "faltas_gt",
    "faltas_pred"
  ].join(";");

  const body = rows.map((r) => [
    r.arquivo,
    r.gtTIPO ?? "", r.prTIPO ?? "", typeof r.hitTIPO === "boolean" ? (r.hitTIPO ? "1" : "0") : "",
    r.gtriscada ?? "", r.prriscada ?? "", typeof r.hitriscada === "boolean" ? (r.hitriscada ? "1" : "0") : "",
    r.gtoxidada ?? "", r.proxyidada ?? "", typeof r.hitoxidada === "boolean" ? (r.hitoxidada ? "1" : "0") : "",
    r.gtbatida ?? "", r.prbatida ?? "", typeof r.hitbatida === "boolean" ? (r.hitbatida ? "1" : "0") : "",
    r.duracaoMs ?? "",
    (r.miss_gt ?? []).join(","),
    (r.miss_pr ?? []).join(",")
  ].join(";")).join("\n");

  fs.writeFileSync(OUT_CSV, header + "\n" + body, "utf-8");
  console.log(`\n✅ CSV detalhado salvo em: ${OUT_CSV}`);

  // ✅ -------------- SALVAR "TABELA" (histórico por RUN) --------------
  const runTs = new Date().toISOString();

  // tenta pegar modelo/data do primeiro arquivo de predição
  const firstPredPath = predMap.get(names[0])!;
  const modelo = readModelFromPred(firstPredPath) ?? "";
  const predData = readTimestampFromPred(firstPredPath) ?? "";

  const runHeader = [
    "run_timestamp",
    "pred_data",
    "modelo",
    "imagens_match",
    "acc_geral",
    "acc_tipo",
    "acc_riscada",
    "acc_oxidada",
    "acc_batida",
    "tempo_min_ms",
    "tempo_avg_ms",
    "tempo_max_ms"
  ].join(";");

  const runLine = [
    runTs,
    predData,
    modelo,
    String(rows.length),
    overall.toFixed(6),
    aTIPO.acc.toFixed(6),
    aR.acc.toFixed(6),
    aO.acc.toFixed(6),
    aB.acc.toFixed(6),
    (tMin ?? "").toString(),
    (tAvg !== undefined ? Math.round(tAvg).toString() : ""),
    (tMax ?? "").toString(),
  ].join(";");

  safeAppendCsvLine(RUNS_TABLE_CSV, runHeader, runLine);

  const runObj = {
    run_timestamp: runTs,
    pred_data: predData,
    modelo,
    imagens_match: rows.length,
    acc: {
      geral: overall,
      tipo: aTIPO.acc,
      riscada: aR.acc,
      oxidada: aO.acc,
      batida: aB.acc
    },
    tempo_ms: tempos.length
      ? { min: tMin, avg: Math.round(tAvg!), max: tMax, amostras: tempos.length }
      : { amostras: 0 }
  };

  fs.appendFileSync(RUNS_TABLE_JSONL, JSON.stringify(runObj) + "\n", "utf-8");

  console.log(`\n✅ Tabela de runs atualizada: ${RUNS_TABLE_CSV}`);
  console.log(`✅ Log de runs (jsonl) atualizado: ${RUNS_TABLE_JSONL}`);
}

main();
