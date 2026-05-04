from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    print("This project uses lexical+dense-overlap retrieval for the seed dataset. Replace this script with external embedding generation when production embeddings are enabled.")


if __name__ == "__main__":
    main()
