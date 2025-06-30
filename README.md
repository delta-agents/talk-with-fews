# Talk with FEWS

This template package contains core functionality for a python package, developed to showcase and speed up the process of developing a python package. This Python package template is developed by HKV and is published under the GNU GPL-3 license.

## Developing

Here are a couple quick useful things to know when using this repo.

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
