# Figures

Hero figure for the public draft. Regenerated from stamp 20260914T083741Z only.

| File | What it shows |
|---|---|
| `paper/figure1_taglaw.png` | Figure 1. Panel A: empty lemma permitted; omit vs inject answer and official \(W\) (0/1) for five items; telescoping item marked **answer rose**. Panel B: lemma tag required, None permitted; same axes. Missing bars are zeros. SOURCE=`api`, `model_id=openai/gpt-4o`, stamp `20260914T083741Z`. |
| `paper/make_figure1.py` | Reproducible matplotlib script. Reads `traces/api_taglaw_20260914T083741Z.jsonl`. |

Caption in `REPORT.md` is meant to stand alone. Raw 0/1 counts. No percentage hero.

```bash
python paper/make_figure1.py
```
