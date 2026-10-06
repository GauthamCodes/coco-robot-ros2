"""Append-only run evidence helpers and bounded bag storage."""
import hashlib
import json
import os
from pathlib import Path
import shutil

REPO=Path(__file__).resolve().parents[1]


def atomic_json(path,value):
    path=Path(path);tmp=path.with_name(path.name+'.tmp')
    with tmp.open('w') as f:
        json.dump(value,f,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
    os.replace(tmp,path)


def outside_git(root):
    root=Path(root).resolve()
    if root==REPO or REPO in root.parents:
        raise ValueError('Run/bag storage must remain outside repository')
    return root


def bytes_used(root):
    return sum(p.stat().st_size for p in Path(root).rglob('*') if p.is_file() and not p.is_symlink())


def file_hash(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(2**20),b''):
            digest.update(chunk)
    return digest.hexdigest()


def bag_hash(bag):
    files={str(p.relative_to(bag)):file_hash(p)
           for p in sorted(Path(bag).rglob('*')) if p.is_file()}
    digest=hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest()
    return {'sha256':digest,'files':files,'algorithm':'sha256(sorted relative-path:file-digest JSON)'}


def disk_check(root,policy,starting=False):
    used=bytes_used(root)
    free=shutil.disk_usage(root).free
    needed=policy['reserve_free_bytes']+(policy['max_run_bytes'] if starting else 0)
    reasons=[]
    if used>policy['max_batch_bytes']:reasons.append('BATCH_DISK_BUDGET_EXCEEDED')
    if starting and used+policy['max_run_bytes']>policy['max_batch_bytes']:reasons.append('BATCH_DISK_CAPACITY_INSUFFICIENT')
    if free<needed:reasons.append('FILESYSTEM_HEADROOM_INSUFFICIENT')
    return {'ok':not reasons,'reasons':reasons,'used_bytes':used,'free_bytes':free}


def retain_bags(runs,controls=2):
    """Only evict explicitly completed qualified PASS extras. Never failures/unknowns."""
    kept=0
    for run in sorted(map(Path,runs)):
        manifest=json.loads((run/'manifest.json').read_text())
        oracle=json.loads((run/'oracle.json').read_text())
        eligible=(manifest.get('state')=='COMPLETE' and manifest.get('qualified') is True
                  and oracle.get('oracle_verdict')=='PASS'
                  and manifest.get('mission_verdict')=='COMPLETE'
                  and manifest.get('invariant_label')=='NONE')
        if not eligible or kept<controls:
            if eligible:kept+=1
            continue
        bag=run/'bag'
        if bag.exists() and not bag.is_symlink():
            manifest['bag_hash']=bag_hash(bag)
            manifest['retention']='EVICTED_SUCCESS_EXTRA; two qualified controls retained'
            atomic_json(run/'manifest.json',manifest)
            # Explicit retention rule; no failed/aborted/unqualified data removed.
            shutil.rmtree(bag)
            bag.mkdir()
