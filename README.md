# Presented Games and Wired Predicates

SOURCE=`api`. N=5 MATH items × omit vs inject × two SYSTEM grammars (20 live calls). Wired R is the answer box. Official W is a named lemma in the `<lemma>` channel after the answer already passed. Token volume is logged and is not the official column.

Clone without a key runs `pytest` and can replay integers from committed traces. `python -m src.run` is a live twenty-call fill (empty-lemma system prompt and required-tag system prompt). Completions sit beside the jsonl. Fixtures are not Table 1.

Type rule (speech): if presented text L names G on an active locus, wire G or strip G from L. Logging W is not that reporting standard.

## Run

```bash
git clone <this-repo>
cd presented-language-trial
pip install -e .
copy .env.example .env
```

Paste an API key (`yk_live_…`) into `.env` as `OPENAI_API_KEY=`. Then:

```bash
python -m src.run
```

Gateway: `https://api.aitklabs.in/v1`. Frozen `MODEL_ID=openai/gpt-4o` (`/v1/models` catalog and [apikeys.in docs](https://apikeys.in/docs.html)). Never `model=auto`. Confirm the slug on the [Models page](https://apikeys.in/models.html) if the catalog moves.

Windows: `copy .env.example .env`. Unix: `cp .env.example .env`.

`pytest` does not call the API.

## Cell

Same item both arms. Inject writes the item-specific G string at π_tool (mock tool note). Omit pads to the same character count with filler that is not a named method. Both arms share one SYSTEM grammar per call: empty lemma allowed (`optional_v0`) or lemma tag required with `None` allowed (`mandatory_structure`). The inject arm does not get an extra instruction to emit the tag. Official W requires the frozen needle after R=1; `None` scores 0. W=0 is a legal reject.

Table 1 is the live stamp in `traces/` (`SOURCE=api`, protocol file `freeze/protocol_v0.1-tag-law.json`). Do not average verdicts.

## Layout

```text
PROTOCOL.md
freeze/protocol.json
freeze/protocol_v0.1-tag-law.json
src/run.py
items/bank.json
traces/
```

Authors: 3am Labs, With Apart Research. MIT.
