#!/usr/bin/env python3
"""
Mia — CLI de IA multi-provider (OpenAI-compatible).

Você define os providers (Groq, Hugging Face router, OpenAI, o que for)
e as roles (personas com system prompt fixo) no config.yaml. A Mia só
fala com qualquer endpoint que exponha /chat/completions no formato
OpenAI, então funciona com Groq, HF Inference Providers, OpenRouter,
llama.cpp server local, etc. — sem lock-in.
"""
import argparse
import json
import os
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import yaml

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt
    RICH = True
    console = Console()
except ImportError:
    RICH = False
    console = None

CONFIG_DIR = Path(os.environ.get("MIA_CONFIG_DIR", Path.home() / ".config" / "mia"))
DATA_DIR = Path(os.environ.get("MIA_DATA_DIR", Path.home() / ".local" / "share" / "mia"))
CONFIG_PATH = CONFIG_DIR / "config.yaml"
DB_PATH = DATA_DIR / "history.db"

# Alguns providers ficam atrás de Cloudflare e bloqueiam o User-Agent
# padrão do urllib (Python-urllib/x.y) como se fosse bot. Um UA comum
# de navegador evita o erro 1010/403 sem mudar mais nada.
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

DEFAULT_CONFIG = {
    "default_provider": None,
    "default_role": "default",
    "providers": {},
    "roles": {
        "default": {"system": "Você é um assistente útil e direto."}
    },
}

EXAMPLE_CONFIG = """\
# Config do Mia — adicione aqui os providers que você for usar.
# Qualquer endpoint OpenAI-compatible funciona (Groq, HF router, OpenAI,
# OpenRouter, llama.cpp --server, etc). A chave de API NUNCA vai aqui:
# fica em uma variável de ambiente, referenciada por api_key_env.

default_provider: groq
default_role: planejador-chefe

# Ordem de fallback: se o primeiro falhar (erro de rede, 429, chave
# faltando etc), a Mia tenta o próximo da lista automaticamente.
# Se omitir isso, ela usa só o default_provider.
provider_chain:
  - groq
  - huggingface
  - openrouter

providers:
  groq:
    base_url: https://api.groq.com/openai/v1
    api_key_env: GROQ_API_KEY
    model: openai/gpt-oss-120b

  huggingface:
    base_url: https://router.huggingface.co/v1
    api_key_env: HF_TOKEN
    model: deepseek-ai/DeepSeek-V3-0324:together

  openrouter:
    base_url: https://openrouter.ai/api/v1
    api_key_env: OPENROUTER_API_KEY
    model: openrouter/free   # auto-router deles: escolhe um modelo free na hora
    extra_body:              # qualquer campo extra vai direto pro corpo do request
      reasoning:
        enabled: true        # ativa "pensar antes de responder" em modelos que suportam

  # local:
  #   base_url: http://localhost:8080/v1
  #   api_key_env: ""
  #   model: qwen2.5-3b-instruct

roles:
  default:
    system: "Você é um assistente útil e direto."

  planejador-chefe:
    system: |
      Você é o planejador e analista-chefe de projetos de software do
      usuário. Responda com foco em arquitetura, riscos, trade-offs e
      próximos passos concretos. Seja direto, questione decisões frágeis,
      não enrole, não elogie por elogiar.
"""

# --------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------


def ensure_dirs():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_config():
    if not CONFIG_PATH.exists():
        return dict(DEFAULT_CONFIG)
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    merged = dict(DEFAULT_CONFIG)
    merged.update(cfg)
    return merged


def cmd_init(_args):
    ensure_dirs()
    if CONFIG_PATH.exists():
        say(f"Config já existe em {CONFIG_PATH} — nada foi sobrescrito.")
        return
    CONFIG_PATH.write_text(EXAMPLE_CONFIG, encoding="utf-8")
    say(f"Config criado em {CONFIG_PATH}.")
    say("Edite o arquivo e defina as variáveis de ambiente das chaves (ex: export GROQ_API_KEY=...).")


# --------------------------------------------------------------------------
# Histórico (SQLite)
# --------------------------------------------------------------------------


def get_db():
    ensure_dirs()
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            provider TEXT,
            model TEXT,
            role TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
        )
        """
    )
    conn.commit()
    return conn


def new_session(conn, provider, model, role):
    cur = conn.execute(
        "INSERT INTO sessions (created_at, provider, model, role) VALUES (?, ?, ?, ?)",
        (time.strftime("%Y-%m-%d %H:%M:%S"), provider, model, role),
    )
    conn.commit()
    return cur.lastrowid


def log_message(conn, session_id, role, content):
    conn.execute(
        "INSERT INTO messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
        (session_id, role, content, time.strftime("%Y-%m-%d %H:%M:%S")),
    )
    conn.commit()


def list_sessions(conn, limit=20):
    return conn.execute(
        "SELECT id, created_at, provider, model, role FROM sessions ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()


def load_session_messages(conn, session_id):
    return conn.execute(
        "SELECT role, content FROM messages WHERE session_id = ? ORDER BY id ASC",
        (session_id,),
    ).fetchall()


# --------------------------------------------------------------------------
# Provider (qualquer endpoint OpenAI-compatible)
# --------------------------------------------------------------------------


class ProviderError(Exception):
    pass


def resolve_provider(cfg, name):
    providers = cfg.get("providers") or {}
    if not providers:
        raise ProviderError(
            f"Nenhum provider configurado ainda. Rode `mia init` e edite {CONFIG_PATH}."
        )
    if name not in providers:
        raise ProviderError(f"Provider '{name}' não existe. Disponíveis: {', '.join(providers)}")
    p = dict(providers[name])
    p["name"] = name
    key_env = p.get("api_key_env")
    p["api_key"] = os.environ.get(key_env, "") if key_env else ""
    if key_env and not p["api_key"]:
        raise ProviderError(
            f"Variável de ambiente {key_env} não definida (necessária pro provider '{name}')."
        )
    return p


def build_provider_chain(cfg, explicit_name):
    """Monta a lista de providers a tentar, em ordem.

    Se `explicit_name` for passado (via -p ou /provider), usa só ele.
    Senão, usa `provider_chain` do config; se não existir, usa só o
    `default_provider` (ou o primeiro configurado).
    """
    providers_cfg = cfg.get("providers") or {}
    if not providers_cfg:
        raise ProviderError(
            f"Nenhum provider configurado ainda. Rode `mia init` e edite {CONFIG_PATH}."
        )

    if explicit_name:
        names = [explicit_name]
    else:
        names = cfg.get("provider_chain") or [cfg.get("default_provider") or next(iter(providers_cfg))]

    chain = []
    errors = []
    for name in names:
        if name not in providers_cfg:
            errors.append(f"'{name}' não está em providers")
            continue
        try:
            chain.append(resolve_provider(cfg, name))
        except ProviderError as e:
            errors.append(str(e))

    if not chain:
        raise ProviderError(
            "Nenhum provider da chain está utilizável agora:\n  - " + "\n  - ".join(errors)
        )
    return chain


def resolve_role(cfg, name):
    roles = cfg.get("roles") or {}
    name = name or cfg.get("default_role") or "default"
    if name not in roles:
        raise ProviderError(f"Role '{name}' não existe. Disponíveis: {', '.join(roles) or '(nenhuma)'}")
    return name, roles[name].get("system", "")


def chat_completion_stream(provider, messages, temperature=0.7):
    """Faz o POST /chat/completions com stream=True.

    Yielda tuplas (tipo, texto), onde tipo é "content" (resposta normal)
    ou "reasoning" (texto de raciocínio, quando o provider suporta e
    `extra_body` habilita isso — ex: OpenRouter com reasoning.enabled).
    """
    url = provider["base_url"].rstrip("/") + "/chat/completions"
    payload = {
        "model": provider["model"],
        "messages": messages,
        "temperature": temperature,
        "stream": True,
    }
    # extra_body: qualquer campo extra que o provider aceitar, ex:
    #   extra_body: {reasoning: {enabled: true}}
    # é só um merge direto no corpo do request — mesma ideia do
    # extra_body do SDK oficial da OpenAI/OpenRouter.
    payload.update(provider.get("extra_body") or {})

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "text/event-stream")
    req.add_header("User-Agent", USER_AGENT)
    if provider.get("api_key"):
        req.add_header("Authorization", f"Bearer {provider['api_key']}")

    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            content_type = resp.headers.get("Content-Type", "")

            # Alguns providers devolvem status 200 mas o corpo NÃO é um
            # stream SSE de verdade (é um JSON de erro comum, ex: sem
            # crédito, chave inválida). Se não for text/event-stream,
            # trata como resposta única em vez de tentar ler linha a
            # linha (senão ela é ignorada em silêncio e a Mia acha que
            # deu tudo certo com resposta vazia).
            if "text/event-stream" not in content_type:
                raw = resp.read().decode("utf-8", errors="ignore")
                try:
                    obj = json.loads(raw)
                except json.JSONDecodeError:
                    raise ProviderError(f"Resposta inesperada de '{provider['name']}': {raw[:400]}")
                _raise_if_error_payload(provider, obj)
                choices = obj.get("choices") or [{}]
                msg = choices[0].get("message", {}) or {}
                reasoning = msg.get("reasoning")
                if reasoning:
                    yield "reasoning", reasoning
                content = msg.get("content") or choices[0].get("text")
                if content:
                    yield "content", content
                return

            for raw_line in resp:
                line = raw_line.decode("utf-8", errors="ignore").strip()
                if not line or not line.startswith("data:"):
                    continue
                chunk = line[len("data:"):].strip()
                if chunk == "[DONE]":
                    break
                try:
                    obj = json.loads(chunk)
                except json.JSONDecodeError:
                    continue
                _raise_if_error_payload(provider, obj)
                choices = obj.get("choices") or [{}]
                delta = choices[0].get("delta", {}) or {}
                reasoning_piece = delta.get("reasoning")
                if reasoning_piece:
                    yield "reasoning", reasoning_piece
                content_piece = delta.get("content")
                if content_piece:
                    yield "content", content_piece
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        raise ProviderError(f"HTTP {e.code} de '{provider['name']}': {body[:500]}")
    except urllib.error.URLError as e:
        raise ProviderError(f"Falha de conexão com '{provider['name']}': {e.reason}")


def _raise_if_error_payload(provider, obj):
    """Alguns providers embutem erro de quota/token DENTRO do corpo/stream
    com status 200, em vez de devolver 4xx. Detecta isso pra forçar o
    fallback pro próximo provider em vez de terminar em silêncio."""
    if isinstance(obj, dict) and "error" in obj:
        err = obj["error"]
        msg = err.get("message") if isinstance(err, dict) else str(err)
        raise ProviderError(f"'{provider['name']}' retornou erro: {msg}")


def fetch_models(provider):
    """GET /models — todo endpoint OpenAI-compatible expõe isso.
    Usado pelo /models do REPL pra listar modelos de verdade da API,
    em vez de depender do que tá hardcoded no config.
    """
    url = provider["base_url"].rstrip("/") + "/models"
    req = urllib.request.Request(url, method="GET")
    req.add_header("User-Agent", USER_AGENT)
    if provider.get("api_key"):
        req.add_header("Authorization", f"Bearer {provider['api_key']}")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return sorted(m.get("id", "?") for m in data.get("data", []))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        raise ProviderError(f"HTTP {e.code} ao listar modelos de '{provider['name']}': {body[:300]}")
    except urllib.error.URLError as e:
        raise ProviderError(f"Falha de conexão com '{provider['name']}': {e.reason}")


def stream_with_fallback(providers, messages, temperature=0.7):
    """Tenta cada provider da chain em ordem.

    Se um falhar ANTES de mandar qualquer texto (chave inválida, 429,
    timeout de conexão etc), passa pro próximo silenciosamente (com um
    aviso). Se já começou a responder e falhar no meio, não tenta de
    novo — evita duplicar/misturar texto de dois providers na mesma
    resposta. Yielda tuplas (provider, tipo, texto), tipo em
    {"content", "reasoning"}.
    """
    last_err = None
    for i, provider in enumerate(providers):
        got_any = False
        try:
            for kind, piece in chat_completion_stream(provider, messages, temperature):
                got_any = True
                yield provider, kind, piece
            return
        except ProviderError as e:
            last_err = e
            if got_any:
                raise ProviderError(f"'{provider['name']}' falhou no meio da resposta: {e}")
            if i + 1 < len(providers):
                say(
                    f"[aviso] '{provider['name']}' falhou ({e}) — tentando '{providers[i + 1]['name']}'...",
                    style="yellow",
                )
            continue
    raise ProviderError(f"Todos os providers da chain falharam. Último erro: {last_err}")


# --------------------------------------------------------------------------
# Saída
# --------------------------------------------------------------------------


def say(text, style=None):
    if RICH and console:
        console.print(text, style=style)
    else:
        print(text)


# --------------------------------------------------------------------------
# Comandos utilitários
# --------------------------------------------------------------------------


def cmd_providers(cfg):
    providers = cfg.get("providers") or {}
    if not providers:
        say("Nenhum provider configurado ainda. Rode `mia init`.")
        return
    for name, p in providers.items():
        flag = " (padrão)" if name == cfg.get("default_provider") else ""
        say(f"- {name}{flag}: {p.get('model')} @ {p.get('base_url')}")


def cmd_roles(cfg):
    roles = cfg.get("roles") or {}
    for name, r in roles.items():
        flag = " (padrão)" if name == cfg.get("default_role") else ""
        preview = (r.get("system", "").strip().splitlines() or [""])[0][:80]
        say(f"- {name}{flag}: {preview}")


def cmd_log(args):
    conn = get_db()
    if args.session_id:
        msgs = load_session_messages(conn, args.session_id)
        if not msgs:
            say(f"Sessão {args.session_id} não encontrada ou vazia.")
            return
        for role, content in msgs:
            label = "Você" if role == "user" else "Mia"
            say(f"\n[{label}]")
            say(content)
    else:
        rows = list_sessions(conn)
        if not rows:
            say("Sem histórico ainda.")
            return
        for sid, created_at, provider, model, role in rows:
            say(f"#{sid}  {created_at}  provider={provider} role={role} model={model}")


# --------------------------------------------------------------------------
# Chat
# --------------------------------------------------------------------------


def build_messages(system_prompt, history, user_input):
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.extend(history)
    messages.append({"role": "user", "content": user_input})
    return messages


def run_one_shot(cfg, provider_name, role_name, prompt):
    chain = build_provider_chain(cfg, provider_name)
    role_name, system_prompt = resolve_role(cfg, role_name)
    messages = build_messages(system_prompt, [], prompt)

    conn = get_db()
    session_id = new_session(conn, chain[0]["name"], chain[0]["model"], role_name)
    log_message(conn, session_id, "user", prompt)

    full = []
    used_provider = chain[0]["name"]
    reasoning_started = False
    try:
        for provider, kind, piece in stream_with_fallback(chain, messages):
            used_provider = provider["name"]
            if kind == "reasoning":
                if not reasoning_started:
                    print("\n[raciocínio]\n", end="", flush=True)
                    reasoning_started = True
                print(piece, end="", flush=True)
            else:
                if reasoning_started:
                    print("\n\n[resposta]\n", end="", flush=True)
                    reasoning_started = False
                print(piece, end="", flush=True)
                full.append(piece)
    except ProviderError as e:
        print()
        say(f"[erro] {e}", style="bold red")
        sys.exit(1)
    print()
    if full:
        log_message(conn, session_id, "assistant", "".join(full))
        if used_provider != chain[0]["name"]:
            say(f"(respondido por: {used_provider})", style="dim")


def run_repl(cfg, provider_name, role_name):
    """REPL estilo Hermes: tudo que começa com / é comando interno."""
    state = {
        "chain": build_provider_chain(cfg, provider_name),
        "role_name": None,
        "system_prompt": "",
        "temperature": 0.7,
        "history": [],
        "conn": get_db(),
        "session_id": None,
    }
    state["role_name"], state["system_prompt"] = resolve_role(cfg, role_name)
    state["session_id"] = new_session(
        state["conn"], state["chain"][0]["name"], state["chain"][0]["model"], state["role_name"]
    )

    print_banner(state)
    say("Digite /help pra ver todos os comandos.\n")

    while True:
        try:
            if RICH and console:
                user_input = Prompt.ask("[bold green]você[/bold green]")
            else:
                user_input = input("você> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not user_input.strip():
            continue

        if user_input.startswith("/"):
            parts = user_input.strip().split(maxsplit=1)
            cmd = parts[0][1:].lower()
            arg = parts[1].strip() if len(parts) > 1 else None
            if not handle_command(cmd, arg, cfg, state):
                break
            continue

        ask_and_stream(state, user_input)


COMMAND_HELP = [
    ("/help, /?", "mostra esta lista de comandos"),
    ("/provider <nome>", "fixa UM provider (sai do modo chain/fallback)"),
    ("/providers", "lista os providers configurados"),
    ("/model <nome>", "troca o modelo usado no provider ativo"),
    ("/models", "busca na API os modelos disponíveis no provider ativo"),
    ("/role <nome>", "troca de persona/system prompt (definida no config)"),
    ("/roles", "lista as roles configuradas"),
    ("/system <texto>", "define um system prompt manual pro resto da sessão"),
    ("/temp <0.0-2.0>", "ajusta a temperatura"),
    ("/chain", "mostra a chain de providers ativa e a config atual"),
    ("/new", "começa uma sessão nova (zera o contexto e o histórico salvo)"),
    ("/clear", "limpa só o contexto da conversa (mantém a sessão)"),
    ("/save <arquivo>", "salva a conversa atual em um arquivo markdown"),
    ("/log [id]", "lista sessões salvas, ou mostra as mensagens de uma"),
    ("/sair, /exit, /quit", "encerra a Mia"),
]


def handle_command(cmd, arg, cfg, state):
    """Processa um comando /. Retorna False se deve encerrar o REPL."""

    if cmd in ("sair", "exit", "quit"):
        return False

    if cmd in ("help", "?"):
        for name, desc in COMMAND_HELP:
            say(f"  {name:<20} {desc}")
        return True

    if cmd == "clear":
        state["history"].clear()
        say("Contexto da conversa limpo (a sessão salva continua a mesma).")
        return True

    if cmd == "new":
        state["history"].clear()
        state["session_id"] = new_session(
            state["conn"], state["chain"][0]["name"], state["chain"][0]["model"], state["role_name"]
        )
        say(f"Nova sessão iniciada (#{state['session_id']}).")
        return True

    if cmd == "provider":
        if not arg:
            say("Uso: /provider <nome>")
            return True
        try:
            state["chain"] = [resolve_provider(cfg, arg)]
            say(f"Provider fixado em: {state['chain'][0]['name']} ({state['chain'][0]['model']})")
        except ProviderError as e:
            say(f"[erro] {e}", style="bold red")
        return True

    if cmd == "providers":
        cmd_providers(cfg)
        return True

    if cmd == "model":
        if not arg:
            say("Uso: /model <nome-do-modelo>")
            return True
        state["chain"][0]["model"] = arg
        if len(state["chain"]) > 1:
            say(f"Modelo trocado para '{arg}' em '{state['chain'][0]['name']}' (só o 1º da chain).")
        else:
            say(f"Modelo trocado para: {arg}")
        return True

    if cmd == "models":
        provider = state["chain"][0]
        say(f"Buscando modelos disponíveis em '{provider['name']}'...")
        try:
            models = fetch_models(provider)
        except ProviderError as e:
            say(f"[erro] {e}", style="bold red")
            return True
        if not models:
            say("Nenhum modelo retornado pela API.")
        for m in models:
            marker = " ←" if m == provider["model"] else ""
            say(f"  {m}{marker}")
        return True

    if cmd == "role":
        if not arg:
            say("Uso: /role <nome>")
            return True
        try:
            state["role_name"], state["system_prompt"] = resolve_role(cfg, arg)
            say(f"Role trocada para: {state['role_name']}")
        except ProviderError as e:
            say(f"[erro] {e}", style="bold red")
        return True

    if cmd == "roles":
        cmd_roles(cfg)
        return True

    if cmd == "system":
        if not arg:
            say(f"System prompt atual:\n{state['system_prompt']}")
            return True
        state["system_prompt"] = arg
        state["role_name"] = "(manual)"
        say("System prompt atualizado pro resto da sessão.")
        return True

    if cmd == "temp":
        if not arg:
            say(f"Temperatura atual: {state['temperature']}")
            return True
        try:
            value = float(arg)
        except ValueError:
            say("Uso: /temp <número entre 0.0 e 2.0>")
            return True
        state["temperature"] = value
        say(f"Temperatura ajustada para {value}.")
        return True

    if cmd == "chain":
        for i, p in enumerate(state["chain"]):
            marker = " (ativo)" if i == 0 else ""
            say(f"  {i + 1}. {p['name']} → {p['model']}{marker}")
        say(f"role={state['role_name']}  temp={state['temperature']}")
        return True

    if cmd == "save":
        if not arg:
            say("Uso: /save <caminho-do-arquivo.md>")
            return True
        save_conversation(state, arg)
        return True

    if cmd == "log":
        if arg:
            try:
                session_id = int(arg)
            except ValueError:
                say("Uso: /log [id-numérico]")
                return True
            msgs = load_session_messages(state["conn"], session_id)
            if not msgs:
                say(f"Sessão {session_id} não encontrada ou vazia.")
                return True
            for role, content in msgs:
                label = "Você" if role == "user" else "Mia"
                say(f"\n[{label}]")
                say(content)
        else:
            for sid, created_at, p, m, r in list_sessions(state["conn"], limit=10):
                say(f"#{sid}  {created_at}  {p}/{r}")
        return True

    say(f"Comando desconhecido: /{cmd}. Use /help pra ver a lista.")
    return True


def ask_and_stream(state, user_input):
    log_message(state["conn"], state["session_id"], "user", user_input)
    messages = build_messages(state["system_prompt"], state["history"], user_input)

    full = []
    reasoning_started = False
    answer_started = False
    try:
        for _provider, kind, piece in stream_with_fallback(state["chain"], messages, state["temperature"]):
            if kind == "reasoning":
                if not reasoning_started:
                    say("\nraciocínio>", style="dim italic")
                    reasoning_started = True
                if RICH and console:
                    console.print(piece, end="", style="dim italic")
                else:
                    print(piece, end="", flush=True)
            else:
                if not answer_started:
                    say("\nmia>", style="bold magenta")
                    answer_started = True
                print(piece, end="", flush=True)
                full.append(piece)
    except ProviderError as e:
        print()
        say(f"[erro] {e}", style="bold red")
        return
    print("\n")

    answer = "".join(full)
    state["history"].append({"role": "user", "content": user_input})
    state["history"].append({"role": "assistant", "content": answer})
    log_message(state["conn"], state["session_id"], "assistant", answer)


def save_conversation(state, path):
    lines = [f"# Conversa com a Mia — role: {state['role_name']}\n"]
    for msg in state["history"]:
        label = "Você" if msg["role"] == "user" else "Mia"
        lines.append(f"**{label}:** {msg['content']}\n")
    try:
        Path(path).write_text("\n".join(lines), encoding="utf-8")
        say(f"Conversa salva em {path}")
    except OSError as e:
        say(f"[erro] Não deu pra salvar em '{path}': {e}", style="bold red")


def print_banner(state):
    chain_desc = " → ".join(f"{p['name']} ({p['model']})" for p in state["chain"])
    txt = f"Mia · providers={chain_desc} · role={state['role_name']}"
    if RICH and console:
        console.print(Panel(txt, style="bold cyan"))
    else:
        print("=" * len(txt))
        print(txt)
        print("=" * len(txt))


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(prog="mia", description="Mia — CLI de IA multi-provider.")
    parser.add_argument("-p", "--provider", help="Nome do provider (do config.yaml)")
    parser.add_argument("-r", "--role", help="Nome da role/persona (do config.yaml)")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("init", help="Cria um config.yaml de exemplo")
    sub.add_parser("providers", help="Lista providers configurados")
    sub.add_parser("roles", help="Lista roles configuradas")

    p_log = sub.add_parser("log", help="Mostra histórico de sessões")
    p_log.add_argument("session_id", nargs="?", type=int, help="ID da sessão pra ver mensagens")

    p_ask = sub.add_parser("ask", help="Pergunta única, sem entrar no REPL")
    p_ask.add_argument("prompt", nargs="+", help="Sua pergunta")

    args = parser.parse_args()
    cfg = load_config()

    try:
        if args.command == "init":
            cmd_init(args)
        elif args.command == "providers":
            cmd_providers(cfg)
        elif args.command == "roles":
            cmd_roles(cfg)
        elif args.command == "log":
            cmd_log(args)
        elif args.command == "ask":
            run_one_shot(cfg, args.provider, args.role, " ".join(args.prompt))
        else:
            run_repl(cfg, args.provider, args.role)
    except ProviderError as e:
        say(f"[erro] {e}", style="bold red")
        sys.exit(1)


if __name__ == "__main__":
    main()
