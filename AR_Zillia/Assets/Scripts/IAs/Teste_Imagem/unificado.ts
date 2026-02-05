// loop_otimizacao_ram.ts
// Uso: npx tsx loop_otimizacao_ram.ts
//
// Pastas esperadas:
//   ./imagens      -> imagens de entrada
//   ./gabaritos    -> arquivos .txt com JSON dentro (mesmo nome base da imagem)
// Saídas:
//   ./saida_txt                -> predições por imagem (última run sobrescreve por padrão; opcional separar por run)
//   ./resultados/_comparacao.csv
//   ./resultados/_tabela_runs.csv
//   ./resultados/_tabela_runs.jsonl
//   ./resultados/runs/run_<id>.json  -> guarda prompt + params + métricas completas do run

import * as fs from "fs";
import * as path from "path";
import { spawn } from "child_process";

// -------------------------------
// CONFIG (por ENV se quiser)
// -------------------------------
const OLLAMA_URL = process.env.OLLAMA_URL ?? "http://localhost:11434";

// Modelo que ANALISA as imagens (multimodal)
const MODEL_ANALYZER = process.env.OLLAMA_MODEL_ANALYZER ?? "gemma3:4b";

// Modelo que GERA prompt/params (text-only serve)
const MODEL_PROMPT_ENGINEER = process.env.OLLAMA_MODEL_PROMPT_ENGINEER ?? MODEL_ANALYZER;

// Pastas
const INPUT_DIR = path.resolve(process.cwd(), "imagens");
const GAB_DIR = path.resolve(process.cwd(), "gabaritos");

// Saídas por imagem (predições)
const OUTPUT_DIR = path.resolve(process.cwd(), "saida_txt");

// Resultados agregados
const RESULTS_DIR = path.resolve(process.cwd(), "resultados");
const RUNS_DIR = path.join(RESULTS_DIR, "runs");

const OUT_CSV = path.join(RESULTS_DIR, "_comparacao.csv");
const RUNS_TABLE_CSV = path.join(RESULTS_DIR, "_tabela_runs.csv");
const RUNS_TABLE_JSONL = path.join(RESULTS_DIR, "_tabela_runs.jsonl");

// Loop / critérios
const TARGET_STREAK = Number(process.env.TARGET_STREAK ?? "10"); // 10 acertos seguidos
const SLEEP_BETWEEN_RUNS_MS = Number(process.env.SLEEP_BETWEEN_RUNS_MS ?? "0"); // se quiser pausa
const MAX_RUNS = Number(process.env.MAX_RUNS ?? "0"); // 0 = infinito

// extensões aceitas
const IMAGE_EXTS = new Set([".png", ".jpg", ".jpeg", ".webp", ".bmp"]);

type Status = "SIM" | "NAO" | "INCONCLUSIVO";
type Phase = "ACCURACY" | "SPEED";

// -------------------------------
// OLLAMA TYPES
// -------------------------------
type OllamaGenerateRequest = {
  model: string;
  prompt: string;
  images?: string[]; // base64
  stream?: boolean;
  format?: "json";
  options?: Record<string, any>;
};

type OllamaGenerateResponse = {
  response: string;
  done: boolean;
  // outros campos podem existir
};

// -------------------------------
// Helpers FS
// -------------------------------
function ensureDir(dir: string) {
  fs.mkdirSync(dir, { recursive: true });
}

function listImages(dir: string): string[] {
  if (!fs.existsSync(dir)) return [];
  const files = fs.readdirSync(dir);
  return files
    .filter((f) => IMAGE_EXTS.has(path.extname(f).toLowerCase()))
    .map((f) => path.join(dir, f));
}

function toBase64(filePath: string): string {
  const buf = fs.readFileSync(filePath);
  return buf.toString("base64");
}

function safeBasenameNoExt(filePath: string): string {
  const base = path.basename(filePath);
  const ext = path.extname(base);
  return base.slice(0, -ext.length);
}

function sleep(ms: number) {
  return new Promise<void>((resolve) => setTimeout(resolve, ms));
}

// -------------------------------
// Ollama start
// -------------------------------
async function startOllama() {
  const url = `${OLLAMA_URL}/api/tags`;

  // 1) Se já estiver rodando, sai
  try {
    const res = await fetch(url);
    if (res.ok) return;
  } catch {
    // vamos iniciar
  }

  // 2) Tenta iniciar em background
  try {
    const proc = spawn("ollama", ["serve"], {
      stdio: "ignore",
      detached: true,
    });
    proc.unref();
  } catch (e: any) {
    throw new Error(
      `Falha ao iniciar o Ollama. Verifique se "ollama" está no PATH. Detalhes: ${e?.message ?? String(e)}`
    );
  }

  // 3) Aguarda subir
  const start = Date.now();
  while (Date.now() - start < 30_000) {
    try {
      const res = await fetch(url);
      if (res.ok) return;
    } catch {}
    await sleep(1_000);
  }

  throw new Error("Ollama não respondeu dentro do tempo limite");
}


// -------------------------------
// Ollama call
// -------------------------------
async function ollamaGenerate(req: OllamaGenerateRequest): Promise<OllamaGenerateResponse> {
  const res = await fetch(`${OLLAMA_URL}/api/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });

  if (!res.ok) {
    const txt = await res.text().catch(() => "");
    throw new Error(`Ollama HTTP ${res.status}: ${txt}`);
  }

  const data = (await res.json()) as OllamaGenerateResponse;
  return data;
}

type RamOut = {
  TIPO: "DIM" | "SODIM";
  Riscada: Status;
  Oxidada: Status;
  Batida: Status;
};

function isValidTipo(x: any): x is "DIM" | "SODIM" {
  return x === "DIM" || x === "SODIM";
}

function isValidStatus(x: any): x is Status {
  return x === "SIM" || x === "NAO" || x === "INCONCLUSIVO";
}

// Tenta "arrumar" um objeto parseado e validar.
// Retorna { ok:true, value } ou { ok:false, reason }.
function coerceAndValidateRamJson(obj: any): { ok: true; value: RamOut } | { ok: false; reason: string } {
  if (!obj || typeof obj !== "object") return { ok: false, reason: "nao_objeto" };

  // pega valores com tolerância de chaves (caso venha Tipo/tipo etc)
  const tipoRaw = getTipo(obj, ["TIPO", "Tipo", "tipo"]);
  const riscadaRaw = getStatus(obj, ["Riscada", "riscada", "RISCADA"]);
  const oxidadaRaw = getStatus(obj, ["Oxidada", "oxidada", "OXIDADA", "Oxidade", "oxidade"]);
  const batidaRaw = getStatus(obj, ["Batida", "batida", "BATIDA"]);

  // obrigatórios
  if (!tipoRaw) return { ok: false, reason: "faltou_TIPO" };
  if (!riscadaRaw) return { ok: false, reason: "faltou_Riscada" };
  if (!oxidadaRaw) return { ok: false, reason: "faltou_Oxidada" };
  if (!batidaRaw) return { ok: false, reason: "faltou_Batida" };

  // normaliza tipo para somente DIM/SODIM (sua normalizeTipo já faz DIMM->DIM etc)
  const tipo = tipoRaw === "DIM" ? "DIM" : tipoRaw === "SODIM" ? "SODIM" : undefined;
  if (!tipo) return { ok: false, reason: `TIPO_invalido:${String(tipoRaw)}` };

  const out: RamOut = {
    TIPO: tipo,
    Riscada: riscadaRaw,
    Oxidada: oxidadaRaw,
    Batida: batidaRaw,
  };

  // valida final
  if (!isValidTipo(out.TIPO)) return { ok: false, reason: "TIPO_invalido_final" };
  if (!isValidStatus(out.Riscada)) return { ok: false, reason: "Riscada_invalida" };
  if (!isValidStatus(out.Oxidada)) return { ok: false, reason: "Oxidada_invalida" };
  if (!isValidStatus(out.Batida)) return { ok: false, reason: "Batida_invalida" };

  return { ok: true, value: out };
}

function buildFixPrompt(badOutput: string, reason: string): string {
  return `
Você retornou um JSON inválido para o schema exigido (motivo: ${reason}).

Corrija AGORA e responda APENAS com JSON VÁLIDO no formato exato:
{"TIPO":"DIM|SODIM","Riscada":"SIM|NAO|INCONCLUSIVO","Oxidada":"SIM|NAO|INCONCLUSIVO","Batida":"SIM|NAO|INCONCLUSIVO"}

Regras:
- Nada de texto fora do JSON.
- Valores permitidos exatamente como acima.
- "TIPO" deve ser somente "DIM" ou "SODIM".

Saída inválida anterior (apenas para você corrigir):
${badOutput}
`.trim();
}

// -------------------------------
// JSON parsing robusto
// -------------------------------
function extractFirstJson(text: string): string | null {
  const trimmed = text.trim();
  const first = trimmed.indexOf("{");
  const last = trimmed.lastIndexOf("}");
  if (first >= 0 && last > first) return trimmed.slice(first, last + 1);
  return null;
}

function tryParseJson(raw: string): any | null {
  const trimmed = raw.trim();
  try {
    return JSON.parse(trimmed);
  } catch {}
  const slice = extractFirstJson(trimmed);
  if (!slice) return null;
  try {
    return JSON.parse(slice);
  } catch {
    return null;
  }
}

// -------------------------------
// Normalização (igual seu avaliador)
// -------------------------------
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

  // remove pontuação/espacos extras
  const y = x.replace(/[^A-Z0-9|]+/g, " ");

  // casos fortes
  if (y.includes("SO") && y.includes("DIM")) return "SODIM";
  if (y.includes("SODIMM")) return "SODIM";
  if (y.includes("NOTE") || y.includes("LAPTOP") || y.includes("NOTEBOOK")) return "SODIM";

  if (y.includes("DIMM")) return "DIM";
  if (y.includes("DESKTOP") || y.includes("PC")) return "DIM";
  if (y.includes("DIM")) return "DIM";

  // se vier "DIM|SODIM" ou algo assim, força undefined pra contar como missing
  if (y.includes("|")) return undefined;

  return undefined;
}

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

// -------------------------------
// Prompt base (fallback) + meta prompt
// -------------------------------
function baseAnalyzerPrompt(): string {
  return `
Você é um inspetor visual de módulos de memória RAM.
Analise a imagem e responda SOMENTE com JSON válido no formato exigido.

Regras críticas:
- Você deve retornar APENAS um JSON, sem texto extra.
- Se NÃO der para ver com segurança, use "INCONCLUSIVO" nos campos de defeito.
- O campo "TIPO" deve ser SEMPRE "DIM" ou "SODIM".

Critérios obrigatórios:

TIPO
"DIM": módulo longo, usado em desktops.
"SODIM": módulo curto, usado em notebooks.

Riscada
"SIM": riscos visíveis no PCB, contatos dourados ou encapsulamento dos chips.
"NAO": ausência total de riscos visíveis.
"INCONCLUSIVO": imagem desfocada/baixa luz/ângulo ruim impede confirmar.

Oxidada
"SIM": manchas escuras, esverdeadas, esbranquiçadas ou corrosão nos contatos/componentes.
"NAO": contatos limpos, metálicos e sem sinais.
"INCONCLUSIVO": não dá para ver claramente contatos/componentes.

Batida
"SIM": lascas no PCB, trincas, cantos quebrados, chips desalinhados, marcas claras de impacto.
"NAO": placa íntegra.
"INCONCLUSIVO": ângulo não mostra bordas/cantos ou falta nitidez.

FORMATO OBRIGATÓRIO (responda apenas o JSON):
{
  "TIPO": "DIM|SODIM",
  "Riscada": "SIM|NAO|INCONCLUSIVO",
  "Oxidada": "SIM|NAO|INCONCLUSIVO",
  "Batida":  "SIM|NAO|INCONCLUSIVO"
}
`.trim();
}

type Candidate = {
  prompt: string;
  options: Record<string, any>;
  engineer_comment?: string;
};

// Esse prompt manda a IA gerar o prompt final + params.
// Ela recebe: fase, histórico resumido, objetivo, e deve devolver JSON.
function buildPromptEngineerInstruction(args: {
  phase: Phase;
  lastRunSummary?: any;
  bestKnown?: any;
}): string {
  const { phase, lastRunSummary, bestKnown } = args;

  return `
Você é um "Prompt Engineer" e "Parameter Tuner" para um modelo do Ollama que analisa imagens de módulos de memória RAM.

Você deve produzir UM JSON (e somente JSON), com o formato:
{
  "prompt": "string",
  "options": { ... },
  "engineer_comment": "string curta"
}

Regras:
- O prompt gerado deve obrigar saída SOMENTE JSON no formato exigido.
- O prompt deve ser curto o bastante para ser eficiente, mas claro.
- "options" deve conter parâmetros seguros e realistas para Ollama, por exemplo:
  temperature, top_k, top_p, min_p, num_ctx, num_predict, repeat_penalty, seed
- Não invente campos fora desses 3 (prompt/options/engineer_comment).
- NUNCA inclua texto fora do JSON.

Objetivo por fase:
1) Fase ACCURACY:
   - Maximizar acurácia geral (TIPO+Riscada+Oxidada+Batida) até chegar em 100%.
   - Preferir configurações determinísticas (temperature baixo, seed fixo).
   - Permitir num_ctx maior se ajudar.
2) Fase SPEED:
   - Manter 100% de acurácia e reduzir tempo (principalmente reduzir num_ctx e num_predict).
   - Mudanças pequenas por iteração.

Informações:
- Formato de saída exigido pelo analisador:
  {
    "TIPO": "DIM|SODIM",
    "Riscada": "SIM|NAO|INCONCLUSIVO",
    "Oxidada": "SIM|NAO|INCONCLUSIVO",
    "Batida":  "SIM|NAO|INCONCLUSIVO"
  }

Histórico resumido do último run (pode ser vazio):
${JSON.stringify(lastRunSummary ?? {}, null, 2)}

Melhor configuração conhecida até agora (pode ser vazio):
${JSON.stringify(bestKnown ?? {}, null, 2)}

Agora gere a PRÓXIMA proposta conforme a fase: ${phase}
`.trim();
}

// -------------------------------
// Leitura/Escrita predição .txt por imagem
// -------------------------------
function writePredTxt(outPath: string, content: string) {
  fs.writeFileSync(outPath, content, "utf-8");
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

// -------------------------------
// CSV append safe
// -------------------------------
function safeAppendCsvLine(filePath: string, headerLine: string, line: string) {
  const exists = fs.existsSync(filePath);
  if (!exists) {
    fs.writeFileSync(filePath, headerLine + "\n" + line + "\n", "utf-8");
  } else {
    fs.appendFileSync(filePath, line + "\n", "utf-8");
  }
}

// -------------------------------
// ANALISAR (gera saida_txt/*.txt)
// -------------------------------
async function analyzeImages(candidate: Candidate) {
  ensureDir(OUTPUT_DIR);

  const images = listImages(INPUT_DIR);
  if (images.length === 0) {
    throw new Error(`Nenhuma imagem encontrada em: ${INPUT_DIR}`);
  }

  const perImageDurations: number[] = [];

  for (const imgPath of images) {
    const filename = path.basename(imgPath);
    const outName = safeBasenameNoExt(imgPath) + ".txt";
    const outPath = path.join(OUTPUT_DIR, outName);

    const b64 = toBase64(imgPath);
    const req: OllamaGenerateRequest = {
      model: MODEL_ANALYZER,
      prompt: candidate.prompt,
      images: [b64],
      stream: false,
      format: "json",
      options: candidate.options,
    };

    const stamp = new Date().toISOString();
    const t0 = Date.now();

try {
  // 1) tentativa normal
  const resp1 = await ollamaGenerate(req);
  const duracaoMs1 = Date.now() - t0;

  let parsed1 = tryParseJson(resp1.response);
  let val1 = parsed1 ? coerceAndValidateRamJson(parsed1) : ({ ok: false, reason: "json_parse_fail" } as const);

  // Se válido, salva e continua
  if (val1.ok) {
    perImageDurations.push(duracaoMs1);

    const header =
      `# arquivo: ${filename}\n` +
      `# data: ${stamp}\n` +
      `# modelo: ${MODEL_ANALYZER}\n` +
      `# duracao_ms: ${duracaoMs1}\n\n`;

    writePredTxt(outPath, header + JSON.stringify(val1.value, null, 2) + "\n");
    continue;
  }

  // 2) retry com prompt de correção (barato)
  const fixPrompt = buildFixPrompt(resp1.response, val1.reason);

  const req2: OllamaGenerateRequest = {
    ...req,
    prompt: fixPrompt,
    options: {
      ...candidate.options,
      // mantém determinístico e tenta ser mais "curto"
      temperature: 0,
      seed: candidate.options.seed ?? 42,
      num_predict: Math.min(Number(candidate.options.num_predict ?? 400), 300),
    },
  };

  const t1 = Date.now();
  const resp2 = await ollamaGenerate(req2);
  const duracaoMs2 = duracaoMs1 + (Date.now() - t1);

  const parsed2 = tryParseJson(resp2.response);
  const val2 = parsed2 ? coerceAndValidateRamJson(parsed2) : ({ ok: false, reason: "json_parse_fail_retry" } as const);

  perImageDurations.push(duracaoMs2);

  const header =
    `# arquivo: ${filename}\n` +
    `# data: ${stamp}\n` +
    `# modelo: ${MODEL_ANALYZER}\n` +
    `# duracao_ms: ${duracaoMs2}\n\n`;

  if (val2.ok) {
    writePredTxt(outPath, header + JSON.stringify(val2.value, null, 2) + "\n");
  } else {
    // falhou mesmo: salva raw com contexto
    writePredTxt(
      outPath,
      header +
        `__RAW_OUTPUT__\n` +
        `# first_fail_reason: ${val1.reason}\n` +
        `# retry_fail_reason: ${val2.reason}\n` +
        `# first_output:\n${resp1.response.trim()}\n\n` +
        `# retry_output:\n${resp2.response.trim()}\n`
    );
  }
}catch (err: any) {
      const msg = err?.message ?? String(err);
      const fail =
        `# arquivo: ${filename}\n` +
        `# data: ${stamp}\n` +
        `# modelo: ${MODEL_ANALYZER}\n\n` +
        `ERRO:\n${msg}\n`;
      writePredTxt(outPath, fail);
    }
  }

  return { imagesCount: images.length, perImageDurations };
}

// -------------------------------
// AVALIAR (compara saida_txt vs gabaritos)
// -------------------------------
type Row = {
  arquivo: string;

  gtTIPO?: string;
  gtriscada?: Status;
  gtoxidada?: Status;
  gtbatida?: Status;

  prTIPO?: string;
  prriscada?: Status;
  proxyidada?: Status;
  prbatida?: Status;

  hitTIPO?: boolean;
  hitriscada?: boolean;
  hitoxidada?: boolean;
  hitbatida?: boolean;

  duracaoMs?: number;

  miss_gt?: string[];
  miss_pr?: string[];
};

function listTxt(dir: string): string[] {
  if (!fs.existsSync(dir)) return [];
  return fs
    .readdirSync(dir)
    .filter((f) => f.toLowerCase().endsWith(".txt"))
    .map((f) => path.join(dir, f));
}

function pct(x: number) {
  return `${(x * 100).toFixed(2)}%`;
}

function evaluateAndSaveCSVs() {
  ensureDir(RESULTS_DIR);

  if (!fs.existsSync(OUTPUT_DIR)) {
    throw new Error(`Pasta de predições não existe: ${OUTPUT_DIR}`);
  }
  if (!fs.existsSync(GAB_DIR)) {
    throw new Error(`Pasta de gabaritos não existe: ${GAB_DIR}`);
  }

  const predFiles = listTxt(OUTPUT_DIR).filter((f) => {
    const bn = path.basename(f);
    return !bn.startsWith("_") && bn.toLowerCase().endsWith(".txt");
  });
  const gabFiles = listTxt(GAB_DIR);

  const predMap = new Map<string, string>();
  for (const f of predFiles) predMap.set(path.basename(f), f);

  const gabMap = new Map<string, string>();
  for (const f of gabFiles) gabMap.set(path.basename(f), f);

  const names = [...predMap.keys()].filter((k) => gabMap.has(k)).sort();
  const missingGab = [...predMap.keys()].filter((k) => !gabMap.has(k));
  const missingPred = [...gabMap.keys()].filter((k) => !predMap.has(k));

  if (names.length === 0) {
    throw new Error(
      `Nenhum arquivo com nome igual entre saida_txt e gabaritos.
Exemplo esperado: saida_txt/imagem_ (1).txt e gabaritos/imagem_ (1).txt`
    );
  }

  const rows: Row[] = [];

  for (const name of names) {
    const predPath = predMap.get(name)!;
    const gabPath = gabMap.get(name)!;

    const predObj = readJsonFromTxt(predPath);
    const gabObj = readJsonFromTxt(gabPath);

    const r: Row = { arquivo: name, miss_gt: [], miss_pr: [] };

    // GT
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

    // Pred
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

    // Hits
    r.hitTIPO = r.gtTIPO !== undefined && r.prTIPO !== undefined ? r.gtTIPO === r.prTIPO : undefined;
    r.hitriscada =
      r.gtriscada !== undefined && r.prriscada !== undefined ? r.gtriscada === r.prriscada : undefined;
    r.hitoxidada =
      r.gtoxidada !== undefined && r.proxyidada !== undefined ? r.gtoxidada === r.proxyidada : undefined;
    r.hitbatida =
      r.gtbatida !== undefined && r.prbatida !== undefined ? r.gtbatida === r.prbatida : undefined;

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

  // geral (3 defeitos)
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

  // tempos
  const tempos = rows.map((r) => r.duracaoMs).filter((x): x is number => typeof x === "number" && !Number.isNaN(x));
  const tMin = tempos.length ? Math.min(...tempos) : undefined;
  const tMax = tempos.length ? Math.max(...tempos) : undefined;
  const tAvg = tempos.length ? tempos.reduce((a, b) => a + b, 0) / tempos.length : undefined;

  // CSV detalhado por imagem
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

  const gtMissingCount = rows.filter((r) => (r.miss_gt?.length ?? 0) > 0).length;
  const prMissingCount = rows.filter((r) => (r.miss_pr?.length ?? 0) > 0).length;

  return {
    rows,
    missingGab,
    missingPred,
    acc: {
      geral: overall,
      tipo: aTIPO.acc,
      riscada: aR.acc,
      oxidada: aO.acc,
      batida: aB.acc,
    },
    tempo_ms: {
      amostras: tempos.length,
      min: tMin,
      avg: tAvg ? Math.round(tAvg) : undefined,
      max: tMax,
    },
    warnings: {
      gtMissingCount,
      prMissingCount,
    },
    pretty: {
      geral: pct(overall),
      tipo: pct(aTIPO.acc),
      riscada: pct(aR.acc),
      oxidada: pct(aO.acc),
      batida: pct(aB.acc),
    }
  };
}

// -------------------------------
// Histórico de runs (ler melhor conhecido)
// -------------------------------
type RunRecord = {
  run_id: string;
  run_timestamp: string;
  phase: Phase;

  candidate: Candidate;

  imagens_match: number;

  acc: {
    geral: number;
    tipo: number;
    riscada: number;
    oxidada: number;
    batida: number;
  };

  tempo_ms: {
    amostras: number;
    min?: number;
    avg?: number;
    max?: number;
  };

  streak_after: number;

  notes?: {
    missingGab?: string[];
    missingPred?: string[];
    gtMissingCount?: number;
    prMissingCount?: number;
  };
};

function readJsonl(filePath: string): any[] {
  if (!fs.existsSync(filePath)) return [];
  const txt = fs.readFileSync(filePath, "utf-8").trim();
  if (!txt) return [];
  return txt.split(/\r?\n/).map((line) => {
    try { return JSON.parse(line); } catch { return null; }
  }).filter(Boolean);
}

function pickBestKnown(history: any[], phase: Phase) {
  // melhor conhecido = maior acc geral; em empate, menor tempo avg
  const ok = history
    .filter((r) => r && r.acc && typeof r.acc.geral === "number")
    .filter((r) => (phase === "SPEED" ? r.acc.geral === 1 : true));

  if (!ok.length) return null;

  ok.sort((a, b) => {
    if (b.acc.geral !== a.acc.geral) return b.acc.geral - a.acc.geral;
    const ta = a.tempo_ms?.avg ?? Number.POSITIVE_INFINITY;
    const tb = b.tempo_ms?.avg ?? Number.POSITIVE_INFINITY;
    return ta - tb;
  });

  return ok[0];
}

// -------------------------------
// Gerar próximo candidate via IA (com fallback)
// -------------------------------
async function proposeNextCandidate(args: {
  phase: Phase;
  lastRun?: RunRecord | null;
  bestKnown?: any | null;
}): Promise<Candidate> {
  const instruction = buildPromptEngineerInstruction({
    phase: args.phase,
    lastRunSummary: args.lastRun
      ? {
          phase: args.lastRun.phase,
          acc: args.lastRun.acc,
          tempo_ms: args.lastRun.tempo_ms,
          streak_after: args.lastRun.streak_after,
          engineer_comment: args.lastRun.candidate.engineer_comment ?? "",
          options: args.lastRun.candidate.options,
        }
      : {},
    bestKnown: args.bestKnown
      ? {
          acc: args.bestKnown.acc,
          tempo_ms: args.bestKnown.tempo_ms,
          options: args.bestKnown.candidate?.options,
        }
      : {},
  });

  // pede JSON direto
  const req: OllamaGenerateRequest = {
    model: MODEL_PROMPT_ENGINEER,
    prompt: instruction,
    stream: false,
    format: "json",
    options: {
      temperature: 0,
      seed: 42,
      num_ctx: 2048,
      num_predict: 800,
    },
  };

  try {
    const resp = await ollamaGenerate(req);
    const obj = tryParseJson(resp.response);

    if (obj && typeof obj.prompt === "string" && obj.options && typeof obj.options === "object") {
      return {
        prompt: obj.prompt.trim(),
        options: obj.options,
        engineer_comment: typeof obj.engineer_comment === "string" ? obj.engineer_comment.trim() : "",
      };
    }
  } catch {
    // cai pro fallback
  }

  // fallback determinístico (se IA falhar)
  if (args.phase === "ACCURACY") {
    return {
      prompt: baseAnalyzerPrompt(),
      options: {
        temperature: 0,
        seed: 42,
        top_k: 1,
        top_p: 0.95,
        min_p: 0.05,
        repeat_penalty: 1.05,
        num_ctx: 1024,
        num_predict: 400,
      },
      engineer_comment: "fallback_accuracy",
    };
  }

  // SPEED fallback: tenta diminuir contexto/predict
  const bestOpt = args.bestKnown?.candidate?.options ?? {};
  return {
    prompt: (args.bestKnown?.candidate?.prompt as string) ?? baseAnalyzerPrompt(),
    options: {
      ...bestOpt,
      temperature: 0,
      seed: 42,
      num_ctx: Math.max(256, Number(bestOpt.num_ctx ?? 1024) - 128),
      num_predict: Math.max(200, Number(bestOpt.num_predict ?? 400) - 50),
    },
    engineer_comment: "fallback_speed_reduce_ctx_predict",
  };
}

// -------------------------------
// Persistência: tabela runs (CSV + JSONL + JSON detalhado por run)
// -------------------------------
function writeRunArtifacts(run: RunRecord) {
  ensureDir(RESULTS_DIR);
  ensureDir(RUNS_DIR);

  // JSON detalhado por run (com prompt e params)
  const runJsonPath = path.join(RUNS_DIR, `run_${run.run_id}.json`);
  fs.writeFileSync(runJsonPath, JSON.stringify(run, null, 2), "utf-8");

  // CSV “tabela runs”
  const runHeader = [
    "run_timestamp",
    "run_id",
    "phase",
    "modelo_analyzer",
    "modelo_engineer",
    "imagens_match",
    "streak_after",
    "acc_geral",
    "acc_tipo",
    "acc_riscada",
    "acc_oxidada",
    "acc_batida",
    "tempo_min_ms",
    "tempo_avg_ms",
    "tempo_max_ms",
    "engineer_comment"
  ].join(";");

  const runLine = [
    run.run_timestamp,
    run.run_id,
    run.phase,
    MODEL_ANALYZER,
    MODEL_PROMPT_ENGINEER,
    String(run.imagens_match),
    String(run.streak_after),
    run.acc.geral.toFixed(6),
    run.acc.tipo.toFixed(6),
    run.acc.riscada.toFixed(6),
    run.acc.oxidada.toFixed(6),
    run.acc.batida.toFixed(6),
    (run.tempo_ms.min ?? "").toString(),
    (run.tempo_ms.avg ?? "").toString(),
    (run.tempo_ms.max ?? "").toString(),
    (run.candidate.engineer_comment ?? "").replaceAll("\n", " ").slice(0, 200)
  ].join(";");

  safeAppendCsvLine(RUNS_TABLE_CSV, runHeader, runLine);

  // JSONL (histórico)
  fs.appendFileSync(RUNS_TABLE_JSONL, JSON.stringify(run) + "\n", "utf-8");
}

// -------------------------------
// MAIN LOOP
// -------------------------------
async function main() {
  ensureDir(OUTPUT_DIR);
  ensureDir(RESULTS_DIR);
  ensureDir(RUNS_DIR);

  await startOllama();

  // valida pastas mínimas
  if (!fs.existsSync(INPUT_DIR)) throw new Error(`Pasta ./imagens não existe: ${INPUT_DIR}`);
  if (!fs.existsSync(GAB_DIR)) throw new Error(`Pasta ./gabaritos não existe: ${GAB_DIR}`);

  const history = readJsonl(RUNS_TABLE_JSONL);

  let phase: Phase = "ACCURACY";

  // streak: conta quantos runs seguidos com 100% geral (defeitos)
  let streak = 0;

  // se já existe histórico, restaura último estado e melhor conhecido
  if (history.length) {
    const last = history[history.length - 1];
    if (last && typeof last.streak_after === "number") streak = last.streak_after;

    // Se já tinha atingido alvo, entra em SPEED
    if (streak >= TARGET_STREAK) phase = "SPEED";
  }

  let iter = 0;

  while (true) {
    iter++;
    if (MAX_RUNS > 0 && iter > MAX_RUNS) {
      console.log(`MAX_RUNS=${MAX_RUNS} atingido. Encerrando.`);
      break;
    }

    // atualiza history/bestKnown a cada loop (do arquivo)
    const histNow = readJsonl(RUNS_TABLE_JSONL);
    const bestKnown = pickBestKnown(histNow, phase);
    const lastRun = histNow.length ? (histNow[histNow.length - 1] as RunRecord) : null;

    // gera candidate (prompt+params)
    const candidate = await proposeNextCandidate({
      phase,
      lastRun,
      bestKnown,
    });

    const run_id = `${new Date().toISOString().replaceAll(":", "-")}_${Math.random().toString(16).slice(2, 8)}`;
    const run_timestamp = new Date().toISOString();

    console.log(`\n==============================`);
    console.log(`RUN ${iter} | phase=${phase} | streak=${streak}/${TARGET_STREAK}`);
    console.log(`run_id=${run_id}`);
    console.log(`engineer_comment=${candidate.engineer_comment ?? ""}`);
    console.log(`options=${JSON.stringify(candidate.options)}`);

    // 1) analisar imagens
    const analysis = await analyzeImages(candidate);

    // 2) avaliar e salvar CSVs
    const evalRes = evaluateAndSaveCSVs();

    // atualiza streak
    const isPerfect = evalRes.acc.geral === 1 && evalRes.acc.tipo === 1;
    if (isPerfect) streak++;
    else streak = 0;

    // transição de fase
    if (phase === "ACCURACY" && streak >= TARGET_STREAK) {
      console.log(`\n🎯 Atingiu ${TARGET_STREAK} runs seguidos com 100%. Entrando em fase SPEED.`);
      phase = "SPEED";
    }

    // monta record do run (inclui prompt + params + métricas)
    const runRecord: RunRecord = {
      run_id,
      run_timestamp,
      phase: (phase === "SPEED" && streak >= TARGET_STREAK) ? "SPEED" : (phase as Phase),

      candidate: {
        prompt: candidate.prompt,
        options: candidate.options,
        engineer_comment: candidate.engineer_comment,
      },

      imagens_match: evalRes.rows.length,

      acc: evalRes.acc,

      tempo_ms: evalRes.tempo_ms,

      streak_after: streak,

      notes: {
        missingGab: evalRes.missingGab,
        missingPred: evalRes.missingPred,
        gtMissingCount: evalRes.warnings.gtMissingCount,
        prMissingCount: evalRes.warnings.prMissingCount,
      },
    };

    // 3) persistir “tabela de runs” + json do run
    writeRunArtifacts(runRecord);

    console.log(`✅ Acurácia geral: ${evalRes.pretty.geral} | tipo: ${evalRes.pretty.tipo}`);
    console.log(`✅ Tempos avg(ms): ${runRecord.tempo_ms.avg ?? "?"} | min: ${runRecord.tempo_ms.min ?? "?"} | max: ${runRecord.tempo_ms.max ?? "?"}`);
    console.log(`✅ Logs: ${RUNS_TABLE_CSV} | ${RUNS_TABLE_JSONL} | runs/run_${run_id}.json`);
    console.log(`✅ CSV detalhado por imagem: ${OUT_CSV}`);

    if (SLEEP_BETWEEN_RUNS_MS > 0) {
      await sleep(SLEEP_BETWEEN_RUNS_MS);
    }
  }
}

main().catch((e) => {
  console.error("Erro fatal:", e);
  process.exit(1);
});
