import asyncio
import json
import sys
import urllib.request
import urllib.error
import re
import time
from typing import Any, Dict, List, Tuple, Optional

from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession


def executar_mcp_com_llm_profissional(
    user_prompt: str,
    *,
    mcp_server_file: str = "server_mcp.py",
    ollama_url: str = "http://localhost:11434/api/chat",
    ollama_model: str = "gemma3:4b",
    temperature: float = 0.0,
    request_timeout_s: int = 120,
    tool_call_timeout_s: int = 30,
    max_tool_rounds: int = 5,
    debug: bool = True,
) -> Dict[str, Any]:
    """
    Execução ponta-a-ponta (autônoma) de:
      - Descoberta MCP (list_tools)
      - Prompt derivado do schema real (fonte da verdade)
      - Loop tool-call -> executar tool -> devolver resultado ao LLM -> final
      - Tratamento profissional de erros e validação básica

    Retorna um dict com:
      - "final": resposta final do LLM (quando houver)
      - "trace": lista de eventos (tool calls, resultados, erros)
    """

    def _now_ms() -> int:
        return int(time.time() * 1000)

    def _safe_json_loads(s: str) -> Any:
        return json.loads(s)

    def _extract_first_json_object(text: str) -> Dict[str, Any]:
        # remove cercas ```...```
        t = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.IGNORECASE)
        t = re.sub(r"\s*```$", "", t.strip())

        m = re.search(r"\{[\s\S]*\}", t)
        if not m:
            raise ValueError("Resposta não contém um objeto JSON.")
        obj = _safe_json_loads(m.group(0))
        if not isinstance(obj, dict):
            raise ValueError("JSON retornado não é um objeto (dict).")
        return obj

    def _http_post_json(url: str, payload: Dict[str, Any], timeout_s: int) -> Dict[str, Any]:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout_s) as resp:
                body = resp.read().decode("utf-8", errors="replace")
                return _safe_json_loads(body)
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"HTTPError {e.code} ao chamar Ollama.\nURL: {url}\nResposta:\n{err_body}"
            )
        except urllib.error.URLError as e:
            raise RuntimeError(f"URLError ao chamar Ollama em {url}: {e}")

    def _ollama_chat(messages: List[Dict[str, str]]) -> str:
        payload = {
            "model": ollama_model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": float(temperature)},
        }
        obj = _http_post_json(ollama_url, payload, request_timeout_s)
        # formato esperado do /api/chat
        try:
            return obj["message"]["content"]
        except Exception:
            raise RuntimeError(f"Resposta inesperada do Ollama: {obj}")

    def _tool_prompt_block_from_schema(tools: Any) -> str:
        # Gera instruções a partir do schema real (fonte da verdade)
        # Mantém curto, mas suficiente para o LLM formar args corretos.
        lines = []
        for t in tools:
            schema = t.inputSchema if hasattr(t, "inputSchema") else {}
            lines.append(
                "\n".join(
                    [
                        f"- name: {t.name}",
                        f"  description: {t.description}",
                        f"  inputSchema: {json.dumps(schema, ensure_ascii=False)}",
                    ]
                )
            )
        return "\n".join(lines)

    def _coerce_numeric_strings(d: Dict[str, Any]) -> Dict[str, Any]:
        # Converte strings numéricas para int/float (quando aplicável)
        out = dict(d)
        for k, v in list(out.items()):
            if isinstance(v, str):
                vv = v.strip()
                try:
                    if re.fullmatch(r"[-+]?\d+", vv):
                        out[k] = int(vv)
                    elif re.fullmatch(r"[-+]?\d*\.\d+", vv):
                        out[k] = float(vv)
                except Exception:
                    pass
        return out

    def _validate_args_against_schema_minimal(args: Dict[str, Any], schema: Dict[str, Any]) -> Tuple[bool, str]:
        # Validação mínima: required fields presentes
        # (o servidor MCP ainda é a validação final)
        required = schema.get("required", [])
        missing = [r for r in required if r not in args]
        if missing:
            return False, f"Campos obrigatórios ausentes: {missing}"
        return True, ""

    async def _run() -> Dict[str, Any]:
        trace: List[Dict[str, Any]] = []

        server = StdioServerParameters(
            command=sys.executable,
            args=[mcp_server_file],
        )

        async with stdio_client(server) as (reader, writer):
            async with ClientSession(reader, writer) as session:
                await session.initialize()

                tools_resp = await session.list_tools()
                tools = tools_resp.tools

                # map tool_name -> schema
                tool_schema_map: Dict[str, Dict[str, Any]] = {}
                for t in tools:
                    tool_schema_map[t.name] = t.inputSchema if hasattr(t, "inputSchema") else {}

                tools_block = _tool_prompt_block_from_schema(tools)

                system = (
                    "Você é uma IA com acesso a tools via MCP.\n"
                    "Regras:\n"
                    "- Responda SOMENTE com JSON puro.\n"
                    '- Se for chamar tool: {"tool":"<nome>","args":{...}}\n'
                    '- Se for resposta final: {"final":"..."}\n'
                    "- Use exatamente os nomes de campos definidos em inputSchema.\n"
                    "\n"
                    "Tools disponíveis (fonte da verdade):\n"
                    f"{tools_block}\n"
                )

                messages: List[Dict[str, str]] = [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_prompt},
                ]

                for round_idx in range(1, max_tool_rounds + 1):
                    llm_raw = _ollama_chat(messages)
                    trace.append(
                        {
                            "t": _now_ms(),
                            "type": "llm_raw",
                            "round": round_idx,
                            "content": llm_raw,
                        }
                    )
                    if debug:
                        print(f"\n[LLM round {round_idx} ->] {llm_raw}")

                    try:
                        cmd = _extract_first_json_object(llm_raw)
                    except Exception as e:
                        trace.append(
                            {
                                "t": _now_ms(),
                                "type": "parse_error",
                                "round": round_idx,
                                "error": str(e),
                            }
                        )
                        # pede correção ao LLM
                        messages.append(
                            {
                                "role": "user",
                                "content": (
                                    'Sua resposta não foi JSON válido no formato esperado. '
                                    'Responda SOMENTE com {"tool":...} ou {"final":...}.'
                                ),
                            }
                        )
                        continue

                    if "final" in cmd:
                        final = cmd.get("final", "")
                        trace.append(
                            {
                                "t": _now_ms(),
                                "type": "final",
                                "round": round_idx,
                                "final": final,
                            }
                        )
                        return {"final": final, "trace": trace}

                    if "tool" not in cmd:
                        trace.append(
                            {
                                "t": _now_ms(),
                                "type": "protocol_error",
                                "round": round_idx,
                                "error": "JSON não contém 'tool' nem 'final'.",
                                "cmd": cmd,
                            }
                        )
                        messages.append(
                            {
                                "role": "user",
                                "content": 'Formato inválido. Responda SOMENTE com {"tool":...} ou {"final":...}.',
                            }
                        )
                        continue

                    tool_name = cmd.get("tool")
                    tool_args = cmd.get("args", {})
                    if not isinstance(tool_name, str) or not isinstance(tool_args, dict):
                        trace.append(
                            {
                                "t": _now_ms(),
                                "type": "protocol_error",
                                "round": round_idx,
                                "error": "Tipos inválidos em 'tool' ou 'args'.",
                                "cmd": cmd,
                            }
                        )
                        messages.append(
                            {
                                "role": "user",
                                "content": (
                                    "Tipos inválidos. 'tool' deve ser string e 'args' deve ser objeto JSON."
                                ),
                            }
                        )
                        continue

                    if tool_name not in tool_schema_map:
                        trace.append(
                            {
                                "t": _now_ms(),
                                "type": "unknown_tool",
                                "round": round_idx,
                                "tool": tool_name,
                            }
                        )
                        messages.append(
                            {
                                "role": "user",
                                "content": (
                                    f"Tool '{tool_name}' não existe. Escolha uma tool válida da lista e tente novamente."
                                ),
                            }
                        )
                        continue

                    tool_args = _coerce_numeric_strings(tool_args)

                    schema = tool_schema_map.get(tool_name, {})
                    ok, why = _validate_args_against_schema_minimal(tool_args, schema)
                    if not ok:
                        trace.append(
                            {
                                "t": _now_ms(),
                                "type": "args_invalid_local",
                                "round": round_idx,
                                "tool": tool_name,
                                "error": why,
                                "args": tool_args,
                            }
                        )
                        messages.append(
                            {
                                "role": "user",
                                "content": (
                                    f"Args inválidos para '{tool_name}': {why}. "
                                    "Corrija os args respeitando inputSchema e responda SOMENTE com JSON."
                                ),
                            }
                        )
                        continue

                    trace.append(
                        {
                            "t": _now_ms(),
                            "type": "tool_call",
                            "round": round_idx,
                            "tool": tool_name,
                            "args": tool_args,
                        }
                    )
                    if debug:
                        print(f"[MCP CALL ->] {tool_name} {tool_args}")

                    try:
                        # timeout na chamada da tool
                        tool_res = await asyncio.wait_for(
                            session.call_tool(tool_name, tool_args),
                            timeout=tool_call_timeout_s,
                        )
                        trace.append(
                            {
                                "t": _now_ms(),
                                "type": "tool_result",
                                "round": round_idx,
                                "tool": tool_name,
                                "result": str(tool_res),
                                "isError": getattr(tool_res, "isError", None),
                            }
                        )
                        if debug:
                            print(f"[MCP RESULT ->] {tool_res}")

                        # devolve o resultado ao LLM para ele concluir ou decidir próxima tool
                        messages.append(
                            {
                                "role": "assistant",
                                "content": json.dumps({"tool": tool_name, "args": tool_args}, ensure_ascii=False),
                            }
                        )
                        messages.append(
                            {
                                "role": "user",
                                "content": json.dumps(
                                    {
                                        "tool_result": tool_name,
                                        "result": str(tool_res),
                                        "note": "Use este resultado para produzir {'final':...} ou chamar outra tool.",
                                    },
                                    ensure_ascii=False,
                                ),
                            }
                        )

                    except asyncio.TimeoutError:
                        trace.append(
                            {
                                "t": _now_ms(),
                                "type": "tool_timeout",
                                "round": round_idx,
                                "tool": tool_name,
                                "timeout_s": tool_call_timeout_s,
                            }
                        )
                        messages.append(
                            {
                                "role": "user",
                                "content": (
                                    f"A tool '{tool_name}' excedeu o timeout de {tool_call_timeout_s}s. "
                                    "Você pode tentar novamente com args menores ou finalizar com {'final':...}."
                                ),
                            }
                        )
                        continue
                    except Exception as e:
                        trace.append(
                            {
                                "t": _now_ms(),
                                "type": "tool_error",
                                "round": round_idx,
                                "tool": tool_name,
                                "error": str(e),
                            }
                        )
                        messages.append(
                            {
                                "role": "user",
                                "content": (
                                    f"Erro ao executar a tool '{tool_name}': {e}. "
                                    "Corrija os args (conforme inputSchema) ou use outra tool."
                                ),
                            }
                        )
                        continue

                return {
                    "final": "",
                    "trace": trace,
                    "error": f"Não foi possível obter 'final' após {max_tool_rounds} rounds.",
                }

    return asyncio.run(_run())


if __name__ == "__main__":
    result = executar_mcp_com_llm_profissional(
        "Calcule dois números quaisquer usando a tool somar e me dê a resposta final.",
        mcp_server_file="server_mcp.py",
        ollama_model="gemma3:4b",
        debug=True,
    )
    print("\n[RESULT FINAL]")
    print(json.dumps(result, ensure_ascii=False, indent=2))
