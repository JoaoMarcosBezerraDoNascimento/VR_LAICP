// analisa_imagens_ollama.ts
// Uso: npx tsx analisa_imagens_ollama.ts
// Pasta de entrada: ./imagens
// Saída: ./saida_txt

import * as fs from "fs";
import * as path from "path";
import { spawn } from "child_process";

type OllamaGenerateRequest = {
  model: string;
  prompt: string;
  images?: string[]; // base64 (sem data:image/... prefix)
  stream?: boolean;
  format?: "json";
  options?: Record<string, any>;
};

async function startOllama() {
  const url = "http://localhost:11434/api/tags";

  // 1) Se já estiver rodando, sai
  try {
    const res = await fetch(url);
    if (res.ok) return;
  } catch {
    // ignorar, vamos tentar iniciar
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
    } catch {
      // ainda não subiu
    }
    await new Promise<void>((resolve) => setTimeout(resolve, 1_000));
  }

  throw new Error("Ollama não respondeu dentro do tempo limite");
}

type OllamaGenerateResponse = {
  response: string;   // texto retornado
  done: boolean;
  // outros campos podem existir (eval_count, context etc.)
};

const OLLAMA_URL = process.env.OLLAMA_URL ?? "http://localhost:11434";
const MODEL = process.env.OLLAMA_MODEL ?? "gemma3:4b"; // ajuste pro seu modelo multimodal
const INPUT_DIR = path.resolve(process.cwd(), "imagens");
const OUTPUT_DIR = path.resolve(process.cwd(), "saida_txt");

// extensões aceitas
const IMAGE_EXTS = new Set([".png", ".jpg", ".jpeg", ".webp", ".bmp"]);

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

startOllama();

function buildPrompt(filename: string) {
  // Prompt focado em estabilidade: JSON estruturado + evidência + INCONCLUSIVO permitido
  return `
Analyze the RAM module image and output JSON: {\"TIPO\": \"DIM\", \"Riscada\": \"\", \"Oxidada\": \"\", \"Batida\": \"\"}
`.trim();
}

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

  // stream=false => retorna um JSON único
  const data = (await res.json()) as OllamaGenerateResponse;
  return data;
}

function safeBasenameNoExt(filePath: string): string {
  const base = path.basename(filePath);
  const ext = path.extname(base);
  return base.slice(0, -ext.length);
}

function tryParseJsonOrKeep(raw: string): { parsed?: any; raw: string } {
  // Alguns modelos devolvem espaços/linhas extras; tentamos extrair o primeiro JSON
  const trimmed = raw.trim();

  // tentativa direta
  try {
    return { parsed: JSON.parse(trimmed), raw: trimmed };
  } catch {}

  // fallback: extrair entre primeiro { e último }
  const first = trimmed.indexOf("{");
  const last = trimmed.lastIndexOf("}");
  if (first >= 0 && last > first) {
    const slice = trimmed.slice(first, last + 1);
    try {
      return { parsed: JSON.parse(slice), raw: slice };
    } catch {}
  }

  return { raw: trimmed };
}

async function main() {
  ensureDir(OUTPUT_DIR);

  const images = listImages(INPUT_DIR);
  if (images.length === 0) {
    console.log(`Nenhuma imagem encontrada em: ${INPUT_DIR}`);
    console.log(`Coloque arquivos .png/.jpg/.jpeg/.webp em ./imagens`);
    return;
  }

  console.log(`Encontradas ${images.length} imagens em ${INPUT_DIR}`);
  console.log(`Usando Ollama em ${OLLAMA_URL} com modelo ${MODEL}`);

  for (const imgPath of images) {
    const filename = path.basename(imgPath);
    const outName = safeBasenameNoExt(imgPath) + ".txt";
    const outPath = path.join(OUTPUT_DIR, outName);

    console.log(`\n➡️  Processando: ${filename}`);

    const b64 = toBase64(imgPath);

    const prompt = buildPrompt(filename);

    const req: OllamaGenerateRequest = {
      model: MODEL,
      prompt,
      images: [b64],
      stream: false,
      format: "json",
      options: {
      temperature: 0.3,
      top_k: 40,
      top_p: 0.95,
      min_p: 0,
      num_ctx: 2048,
      num_predict: 4096,
      repeat_penalty: 1,
      seed: 42     
      },
    };

      try {
        const stamp = new Date().toISOString();

        const t0 = Date.now();
        const resp = await ollamaGenerate(req);
        const duracaoMs = Date.now() - t0;

        const parsedAttempt = tryParseJsonOrKeep(resp.response);

        let content =
          `# arquivo: ${filename}\n` +
          `# data: ${stamp}\n` +
          `# modelo: ${MODEL}\n` +
          `# duracao_ms: ${duracaoMs}\n\n`;

        if (parsedAttempt.parsed) {
          content += JSON.stringify(parsedAttempt.parsed, null, 2) + "\n";
        } else {
          content += `__RAW_OUTPUT__\n${parsedAttempt.raw}\n`;
        }

        fs.writeFileSync(outPath, content, "utf-8");
        console.log(`✅ Salvo: ${outPath}`);
      }catch (err: any) {
      const msg = err?.message ?? String(err);
      const stamp = new Date().toISOString();
      const fail = `# arquivo: ${filename}\n# data: ${stamp}\n# modelo: ${MODEL}\n\nERRO:\n${msg}\n`;
      fs.writeFileSync(outPath, fail, "utf-8");
      console.log(`❌ Erro em ${filename}. Log salvo em: ${outPath}`);
    }
  }

  console.log(`\n🏁 Finalizado. Saídas em: ${OUTPUT_DIR}`);
}

main().catch((e) => {
  console.error("Erro fatal:", e);
  process.exit(1);
});
