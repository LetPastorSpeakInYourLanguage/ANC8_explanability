"""Git clean filter: commit notebooks without their outputs.

Notebook outputs can print survey records (notebook 1, for instance, lists
individual women by case ID while auditing the roster), and survey records are
not redistributable. So what git stores is code and markdown only; the copies
on disk keep their outputs.

    git config filter.nbstrip.clean "python scripts/strip_notebook_outputs.py"
    git config filter.nbstrip.smudge cat

with `*.ipynb filter=nbstrip` in .gitattributes.
"""

import json
import sys


def main():
    raw = sys.stdin.buffer.read().decode("utf-8")
    nb = json.loads(raw)
    for cell in nb.get("cells", []):
        if cell.get("cell_type") == "code":
            cell["outputs"] = []
            cell["execution_count"] = None
        cell.get("metadata", {}).pop("execution", None)
    out = json.dumps(nb, indent=1, ensure_ascii=False) + "\n"
    sys.stdout.buffer.write(out.encode("utf-8"))


if __name__ == "__main__":
    main()
