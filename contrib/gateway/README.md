# Gateway for open models

An OpenAI-compatible gateway (LiteLLM): a local LiteLLM proxy routes `claude -p` to the open models of the endpoint in
`litellm.yaml`, so every model runs in the same harness, prompt and tool layer.

1. `cp .env.example .env` and set `GWDG_API_KEY` (the API key of the endpoint in `litellm.yaml`).
   `GWDG_AI_API_KEY` is accepted too by `smoke_tool_calling.py`, but LiteLLM reads `GWDG_API_KEY`, so
   `export GWDG_API_KEY="$GWDG_AI_API_KEY"` before starting it.
2. `python3 smoke_tool_calling.py` — keep only models that return `TOOL_CALL`.
3. `pip install 'litellm[proxy]'` and `litellm --config litellm.yaml --host 127.0.0.1 --port 4000` (the proxy
   listens on the loopback interface only).
4. `unset ANTHROPIC_API_KEY; export ANTHROPIC_BASE_URL=http://localhost:4000 ANTHROPIC_AUTH_TOKEN=$LITELLM_MASTER_KEY`
5. `tsbench run ... --gateway` with a `gwdg-*` model name from `litellm.yaml`; the run uses the flags of
   `docs/methods.md` (section 3) and records the endpoint as `gateway localhost:4000`.

Record per run: gateway version, `drop_params`, any `CLAUDE_CODE_DISABLE_*` flag,
and the model id from the stream-json init event. Classify tool-format errors
separately from wrong answers.

Steps 2 and 5 check that LiteLLM's Anthropic `/v1/messages` route translates Claude Code's tool calls for these
models without loss.
