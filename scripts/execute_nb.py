import sys, nbformat
from nbclient import NotebookClient
path = sys.argv[1]
nb = nbformat.read(path, as_version=4)
client = NotebookClient(nb, timeout=3600, kernel_name="python3",
                        resources={"metadata": {"path": "."}})
client.execute()
nbformat.write(nb, path)
errs = [(i, o) for i, c in enumerate(nb.cells) for o in c.get("outputs", [])
        if o.get("output_type") == "error"]
if errs:
    for i, o in errs:
        print(f"CELL {i} ERROR: {o.get('ename')}: {o.get('evalue')}")
        print("\n".join(o.get("traceback", []))[-1500:])
    sys.exit(1)
print(f"OK: executed {len(nb.cells)} cells, no errors")
