# Mia

CLI de IA multi-provider. Fala com qualquer endpoint OpenAI-compatible
(`/chat/completions`) — Groq, Hugging Face Inference Providers, OpenRouter,
um `llama.cpp --server` local, o que você configurar. Sem lock-in em
nenhum provider.

## Instalação

```bash
pip install -r requirements.txt --break-system-packages   # `rich` é opcional, só deixa mais bonito
chmod +x mia.py
sudo ln -s "$(pwd)/mia.py" /usr/local/bin/mia              # pra chamar só de `mia` em qualquer lugar
```

## Primeiro uso

```bash
mia init
```

Isso cria `~/.config/mia/config.yaml` com um exemplo. Edite pra colocar
seus providers de verdade. Cada provider tem:

- `base_url` — endpoint OpenAI-compatible
- `api_key_env` — nome da variável de ambiente onde está a chave (a chave
  em si NUNCA fica no config, só o nome da variável)
- `model` — id do modelo (no formato que o provider espera)

Exemplo:

```yaml
default_provider: groq
default_role: planejador-chefe

# Ordem de fallback: se o primeiro falhar (chave faltando, erro de
# rede, 429, timeout), a Mia tenta o próximo automaticamente — desde
# que a falha aconteça ANTES de começar a responder. Se já veio
# resposta parcial e falha no meio, ela para (pra não misturar texto
# de dois modelos diferentes).
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
    model: deepseek/deepseek-chat

roles:
  planejador-chefe:
    system: |
      Você é o planejador e analista-chefe de projetos de software do
      usuário. Responda com foco em arquitetura, riscos, trade-offs e
      próximos passos concretos.
```

Depois, exporte as chaves de API (num `.bashrc`/`.zshrc`, ou num
gerenciador de secrets):

```bash
export GROQ_API_KEY="sua-chave"
export HF_TOKEN="sua-chave"
```

## Uso

```bash
mia                          # abre o REPL usando a provider_chain do config (com fallback)
mia -p huggingface            # REPL forçando UM provider específico (ignora a chain)
mia -r default                 # REPL usando outra role
mia ask "resuma isso aqui"     # pergunta única, sem entrar no REPL (também usa a chain)
mia providers                  # lista providers configurados
mia roles                      # lista roles configuradas
mia log                        # lista sessões salvas
mia log 3                      # mostra as mensagens da sessão #3
```

Dentro do REPL, tudo que começa com `/` é comando interno (estilo Hermes):

| Comando | O que faz |
|---|---|
| `/help`, `/?` | lista todos os comandos |
| `/provider <nome>` | fixa UM provider, sai do modo chain/fallback |
| `/providers` | lista os providers configurados |
| `/model <nome>` | troca o modelo usado no provider ativo, na hora |
| `/models` | busca na API (GET `/models`) os modelos disponíveis de verdade no provider ativo |
| `/role <nome>` | troca de persona/system prompt (definida no config) |
| `/roles` | lista as roles configuradas |
| `/system <texto>` | define um system prompt manual pro resto da sessão (sem editar config) |
| `/temp <0.0-2.0>` | ajusta a temperatura das respostas |
| `/chain` | mostra a chain de providers ativa, modelo, role e temperatura atuais |
| `/new` | começa uma sessão nova (zera contexto e histórico salvo) |
| `/clear` | limpa só o contexto da conversa atual (mantém a sessão salva) |
| `/save <arquivo.md>` | salva a conversa atual em markdown |
| `/log [id]` | lista sessões salvas, ou mostra as mensagens de uma específica |
| `/sair`, `/exit`, `/quit` | encerra a Mia |

Quando você não fixa um provider (com `-p` ou `/provider`), a Mia usa
a lista em `provider_chain` do config e vai tentando em ordem. Se o
primeiro estiver fora do ar, sem chave, ou bater rate limit, ela avisa
e cai pro próximo — sem você precisar fazer nada.

## Histórico

Toda sessão e mensagem fica salva em SQLite, em
`~/.local/share/mia/history.db`. Sem depender de nenhum serviço externo.

## Adicionando mais providers/roles

É só editar `config.yaml` — não precisa mexer no código. Qualquer serviço
que exponha uma API compatível com o formato de chat completions da
OpenAI (`{model, messages, stream}` → `choices[0].delta.content`) funciona
direto.
