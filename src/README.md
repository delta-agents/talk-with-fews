# Talk with FEWS

Talk with FEWS is developed by HKV and is published under the GNU GPL-3 license.
It allows for connecting of LLM's to the Delft-FEWS system.

## Installing

`pip install talk-with-fews`

Running the MCP server happens with `uvicorn`:

`uvicorn talk_with_fews.app:app --host 0.0.0.0 --port 8000`

Ensure your .env path is correctly set `TALK_WITH_FEWS_ENV_DIR`. See [`\env\.env.example`](https://github.com/delta-agents/talk-with-fews/blob/main/env/.env.example) for examples.

Custom server names can be set through the environmental variable: `TALK_WITH_FEWS_SERVERS`.
