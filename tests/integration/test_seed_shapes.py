import json
from pathlib import Path


def test_seed_files_exist_and_have_minimum_records():
    compounds = json.loads(Path("data/seeds/chemicals/compounds.json").read_text(encoding="utf-8"))
    papers = json.loads(Path("data/seeds/literature/papers.json").read_text(encoding="utf-8"))
    assert len(compounds) >= 3
    assert len(papers) >= 3
