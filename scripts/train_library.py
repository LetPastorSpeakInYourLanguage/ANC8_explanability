"""Train the model library (src/anc8/library.py), resumably, on CPU or GPU.

    python scripts/train_library.py --root "G:/My Drive/ANC8_training" --device cpu --workers 4
    python scripts/train_library.py --root /content/drive/MyDrive/ANC8_training --device gpu
    python scripts/train_library.py --root <dir> --status
    python scripts/train_library.py --root <dir> --only "pool95/anc8plus/Logistic regression"

Each machine runs the jobs for its own device: CatBoost and the networks on the
GPU, everything else on the CPU. Both write to the same results folder, so the
split needs no coordination. Calibration and the ensembles wait for the tuned
models they are built on; with --wait, a runner whose remaining jobs wait on
the other machine keeps polling instead of stopping.

Every job runs in its own process, with its log in <root>/logs/.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import shutil
import subprocess
import sys
import time
import traceback
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from anc8 import library as lib  # noqa: E402

KIND_ORDER = {"tune": 0, "net": 1, "calib": 2, "stack": 3, "cumlink": 4}
# Slowest tuning first, so the long jobs are not left for the end.
SLOW = {"Elastic net logistic": 0, "Extra Trees": 1, "LightGBM": 2, "Random Forest": 3,
        "HistGradientBoosting": 4, "MLP": 5, "Explainable Boosting": 6, "XGBoost": 7}
SET_ORDER = {s: i for i, s in enumerate(lib.SETS)}


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def safe(job_id: str) -> str:
    return job_id.replace("/", "__").replace(" ", "_")


def selected(args):
    sets = tuple(args.sets) if args.sets else lib.SETS
    js = lib.jobs(sets)
    if args.only:
        js = [j for j in lib.jobs(sets + ("pool95",)) if any(fnmatch.fnmatch(j.id, p) for p in args.only)]
    return js


def status(root, js):
    c = Counter()
    for j in js:
        if lib.is_done(root, j):
            s = "done"
        elif lib.failed_path(root, j).exists():
            s = "failed"
        elif lib.deps_done(root, j):
            s = "ready"
        else:
            s = "blocked"
        c[(j.device, j.kind, s)] += 1
    print(f"\n{'device':6s} {'kind':8s} {'done':>6s} {'ready':>6s} {'blocked':>8s} {'failed':>7s} {'total':>6s}")
    tot = Counter()
    for dev in ("gpu", "cpu"):
        for kind in KIND_ORDER:
            row = {s: c[(dev, kind, s)] for s in ("done", "ready", "blocked", "failed")}
            n = sum(row.values())
            if not n:
                continue
            tot.update(row)
            print(f"{dev:6s} {kind:8s} {row['done']:6d} {row['ready']:6d} {row['blocked']:8d} {row['failed']:7d} {n:6d}")
    print(f"{'all':15s} {tot['done']:6d} {tot['ready']:6d} {tot['blocked']:8d} {tot['failed']:7d} {sum(tot.values()):6d}")
    for j in js:
        f = lib.failed_path(root, j)
        if f.exists() and not lib.is_done(root, j):
            last = f.read_text(encoding="utf-8").strip().splitlines()[-1:]
            print(f"  FAILED {j.id}: {last[0] if last else ''}")
    return tot


def schedule(args):
    root = Path(args.root)
    drive_logs = root / "logs"
    drive_logs.mkdir(parents=True, exist_ok=True)
    # On Colab the Drive mount uploads a file only when it is closed, so a log held
    # open by a running job never shows up. Jobs there write to local disk, and the
    # runner copies each log to Drive every --sync seconds.
    job_logs = Path(args.local_logs) if args.local_logs else drive_logs
    job_logs.mkdir(parents=True, exist_ok=True)
    runner_log = drive_logs / f"runner_{args.device}.log"
    status_file = drive_logs / f"runner_{args.device}.json"

    def note(msg):
        line = f"[{time.strftime('%H:%M:%S')}] {msg}"
        print(line, flush=True)
        with open(runner_log, "a", encoding="utf-8") as fh:  # opened and closed per line, so Drive sees it
            fh.write(line + "\n")

    def last_line(job_id):
        f = job_logs / f"{safe(job_id)}.log"
        if not f.exists():
            return "(no output yet)"
        lines = f.read_text(encoding="utf-8", errors="replace").strip().splitlines()
        return lines[-1].strip() if lines else "(no output yet)"

    def sync(final=()):
        if job_logs != drive_logs:
            for jid in list(running) + list(final):
                src = job_logs / f"{safe(jid)}.log"
                if src.exists():
                    shutil.copyfile(src, drive_logs / src.name)
        done_n = sum(lib.is_done(root, j) for j in js)
        state = {"time": time.strftime("%Y-%m-%d %H:%M:%S"), "device": args.device,
                 "done": done_n, "total": len(js), "failed": sorted(failed),
                 "running": [{"job": jid, "minutes": round((time.time() - t0) / 60, 1), "last": last_line(jid)}
                             for jid, (_, _, t0) in running.items()]}
        tmp = status_file.with_name(status_file.name + ".tmp")
        tmp.write_text(json.dumps(state, indent=1), encoding="utf-8")
        os.replace(tmp, status_file)

    # --only runs exactly what was named, on the device given
    js = [j for j in selected(args) if args.only or j.device == args.device]
    # On the GPU the networks go first: they are quick there, while CatBoost is the slow one.
    order = dict(KIND_ORDER, net=-1) if args.device == "gpu" else KIND_ORDER
    js.sort(key=lambda j: (order[j.kind], SLOW.get(j.base, 9), SET_ORDER.get(j.set, 9), j.rung))
    # a new run retries what failed last time
    for j in js:
        lib.failed_path(root, j).unlink(missing_ok=True)

    threads = max(1, (os.cpu_count() or 2) // max(1, args.workers))
    running: dict[str, tuple] = {}
    failed: set[str] = set()
    beat = synced = time.time()
    note(f"{len(js)} {args.device} jobs, {sum(lib.is_done(root, j) for j in js)} already done; "
         f"{args.workers} at a time, {threads} threads each")
    while True:
        ended = []
        for jid, (proc, job, t0) in list(running.items()):
            if proc.poll() is None:
                continue
            del running[jid]
            ended.append(jid)
            mins = (time.time() - t0) / 60
            if proc.returncode == 0 and lib.is_done(root, job):
                note(f"done    {jid} ({mins:.1f} min)")
            else:
                failed.add(jid)
                note(f"FAILED  {jid} (exit {proc.returncode}): {last_line(jid)}")

        pending = [j for j in js if j.id not in running and j.id not in failed and not lib.is_done(root, j)]
        ready = [j for j in pending if lib.deps_done(root, j)]
        for job in ready[: max(0, args.workers - len(running))]:
            out = open(job_logs / f"{safe(job.id)}.log", "a", encoding="utf-8")
            cmd = [sys.executable, "-u", __file__, "--run-job", job.id, "--root", str(root),
                   "--device", args.device,
                   "--threads", str(threads), "--fold-jobs", str(args.fold_jobs)]
            running[job.id] = (subprocess.Popen(cmd, stdout=out, stderr=subprocess.STDOUT, cwd=ROOT), job, time.time())
            note(f"start   {job.id}")

        if ended or time.time() - synced > args.sync:
            synced = time.time()
            sync(ended)
        if not running and not ready:
            if pending and args.wait:
                time.sleep(60)
                continue
            break
        if time.time() - beat > args.heartbeat and running:
            beat = time.time()
            for jid, (_, job, t0) in running.items():
                note(f"running {jid} ({(time.time() - t0) / 60:.0f} min): {last_line(jid)}")
        time.sleep(3)

    sync()
    note(f"finished: {len(failed)} failed, {len(pending)} waiting on other jobs")
    status(root, js)


def run_one(args):
    from anc8 import models as zoo

    job = lib.find(args.run_job)
    zoo.DEVICE = args.device
    zoo.THREADS = args.threads
    if args.device == "gpu" and job.kind == "net":
        import torch

        from anc8 import deep
        assert torch.cuda.is_available(), "no CUDA device; set the Colab runtime to T4 GPU"
        deep.DEVICE = torch.device("cuda")
    # A GPU runs one fit at a time; the CPU spreads the tuning folds over processes.
    fold_jobs = 1 if args.device == "gpu" else args.fold_jobs
    try:
        from threadpoolctl import threadpool_limits
        with threadpool_limits(limits=args.threads):
            lib.run(job, args.root, fold_jobs=fold_jobs)
    except Exception:
        f = lib.failed_path(args.root, job)
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(traceback.format_exc(), encoding="utf-8")
        traceback.print_exc()
        sys.exit(1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="folder holding results/ and logs/")
    ap.add_argument("--device", choices=["cpu", "gpu"], default="cpu")
    ap.add_argument("--workers", type=int, default=1, help="jobs run at once")
    ap.add_argument("--fold-jobs", type=int, default=5, help="tuning folds fitted in parallel (CPU)")
    ap.add_argument("--sets", nargs="*", choices=lib.SETS)
    ap.add_argument("--only", nargs="*", help="job ids or patterns, e.g. 's21/anc4plus/*'")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--heartbeat", type=int, default=600, help="seconds between progress lines for running jobs")
    ap.add_argument("--sync", type=int, default=60, help="seconds between copies of the logs and status to --root")
    ap.add_argument("--local-logs", help="write job logs here and copy them to <root>/logs (for a Drive mount)")
    ap.add_argument("--wait", action="store_true", help="keep polling for jobs that wait on the other machine")
    ap.add_argument("--run-job", help=argparse.SUPPRESS)
    ap.add_argument("--threads", type=int, default=os.cpu_count() or 1, help=argparse.SUPPRESS)
    args = ap.parse_args()

    if args.run_job:
        run_one(args)
    elif args.status:
        status(Path(args.root), selected(args))
    else:
        schedule(args)


if __name__ == "__main__":
    main()
