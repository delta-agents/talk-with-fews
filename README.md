# Talk with FEWS

Talk with FEWS is developed by HKV and is published under the GNU GPL-3 license.
It allows for connecting of LLM's to the Delft-FEWS system.

## Installing

`pip install talk-with-fews`

Running the MCP server happens with `uvicorn`:

`uvicorn talk_with_fews.app:app --host 0.0.0.0 --port 8000`

Ensure your .env path is correctly set `TALK_WITH_FEWS_ENV_DIR`. See `\env\.env.example` for examples.

Custom server names can be set through the environmental variable: `TALK_WITH_FEWS_SERVERS`.

## Developing

Here are a couple quick useful things to know when using this repo.

## starting MCP

`pixi run start` which calls main.py

### Pre-commit

This repo uses pre-commit, make sure you run `pixi run pre-commit` before you commit anything.

### GitHub Tests

In the folder `.github` there are four workflows which run automatically when submitting a pull request.

### Pixi

Read bellow for more information on pixi and a quick guideline you can include in your project.

## Getting started

### Using install

run `pip install talk_with_fews`

### developing with pixi

To manage the environment we use Pixi.

<details>
<summary>windows</summary>

```powershell
iwr -useb https://pixi.sh/install.ps1 | iex
```

</details>

<details>
<summary>Linux/Mac</summary>

```bash
curl -fsSL https://pixi.sh/install.sh | bash
```

</details>

#### installing

With the `Pixi` command in powershell install the python environment:

```bash
 cd ../talk_with_fews
 pixi install
```

The `pixi.lock` file loads the correct packages and downloads to the `.pixi` folder.

For questions about how to use this package contact `hoek@hkv.nl` or `haasnoot@hkv.nl`.
