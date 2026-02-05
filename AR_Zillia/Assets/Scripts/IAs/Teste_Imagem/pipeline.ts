import { spawn } from "child_process";

function sleep(ms: number) {
  return new Promise<void>((resolve) => setTimeout(resolve, ms));
}

function runScript(name: string): Promise<void> {
  return new Promise((resolve, reject) => {
    console.log(`\n▶️ Iniciando ${name}...`);

    const proc = spawn(
      "npx",
      ["tsx", name],
      { stdio: "inherit", shell: true }
    );

    proc.on("close", (code) => {
      if (code === 0) {
        console.log(`✅ ${name} finalizado com sucesso`);
        resolve();
      } else {
        reject(new Error(`${name} terminou com erro (code ${code})`));
      }
    });
  });
}

async function main() {
  let iter = 0;

  while (iter < 1) {
    iter++;
    console.log(`\n🔁 LOOP ${iter} iniciado`);

    try {
      await runScript("analisar.ts");
      await runScript("avaliar.ts");

      console.log(`🏁 LOOP ${iter} finalizado com sucesso`);
    } catch (err: any) {
      console.error(`❌ ERRO no LOOP ${iter}:`, err.message);
    }
  }
}

main();
