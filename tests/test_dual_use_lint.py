from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BANNED = ("payload", "exploit", "recipe", "constructor")
SCAN = (
    ROOT / "items" / "bank.json",
    ROOT / "src" / "alleles.py",
    ROOT / "src" / "harness.py",
    ROOT / "src" / "w_hooks.py",
    ROOT / "src" / "logger.py",
    ROOT / "src" / "run.py",
)


def test_banned_keys_absent_from_items_and_runner():
    hits = []
    for path in SCAN:
        text = path.read_text(encoding="utf-8").lower()
        for key in BANNED:
            if key in text:
                hits.append(f"{path.name}:{key}")
    assert hits == [], hits
