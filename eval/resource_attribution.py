"""Read-only engineering attribution and historical comparison; no qualification.

PSS apportions shared pages; RSS sums are explicitly not physical allocation.
Missing /proc permissions never become zero. PID identity is checked around reads.
"""
import argparse
import json
from pathlib import Path
from collections import defaultdict
from evidence import file_hash
from qualification import identity


def process_memory(pid, start_ticks, proc=Path('/proc')):
    result=dict(pss_bytes=None, private_bytes=None, swap_pss_bytes=None, memory_error=None)
    try:
        if identity(pid,proc)['start_ticks']!=start_ticks:raise ValueError('PID identity changed')
        fields={line.split(':',1)[0]:int(line.split()[1])*1024
                for line in (proc/str(pid)/'smaps_rollup').read_text().splitlines()
                if ':' in line and len(line.split())==3 and line.split()[-1]=='kB'}
        result.update(pss_bytes=fields.get('Pss'),swap_pss_bytes=fields.get('SwapPss'),
                      private_bytes=sum(fields[k] for k in ('Private_Clean','Private_Dirty'))
                      if all(k in fields for k in ('Private_Clean','Private_Dirty')) else None)
        if identity(pid,proc)['start_ticks']!=start_ticks:raise ValueError('PID identity changed during sample')
    except (OSError,ValueError,IndexError) as exc:
        result.update(pss_bytes=None,private_bytes=None,swap_pss_bytes=None,memory_error=str(exc))
    return result


def pressure(proc=Path('/proc')):
    try:
        return {parts[0]:{k:float(v) for k,v in (p.split('=') for p in parts[1:])}
                for parts in (line.split() for line in (proc/'pressure/memory').read_text().splitlines())}
    except (OSError,ValueError) as exc:return {'unavailable':str(exc)}


def summarize(root):
    root=Path(root);path=root/'host_metrics.jsonl';rows=[];errors=[]
    if path.exists():
        with path.open() as stream:
            for n,line in enumerate(stream):
                try:rows.append(json.loads(line))
                except ValueError:errors.append(f'truncated sample {n+1}')
    manifest=json.loads((root/'manifest.json').read_text())
    peaks=defaultdict(dict);lifetimes={}
    for row in rows:
        groups=defaultdict(list);seen=set()
        for p in row.get('owned_components',[]):
            key=(p['pid'],p['start_ticks'])
            if key in seen:errors.append(f'duplicate PID identity {key}');continue
            seen.add(key);groups[p['component']].append(p)
            life=lifetimes.setdefault(str(key),dict(pid=key[0],start_ticks=key[1],
                first_observed_wall_epoch_ns=row.get('wall_epoch_ns'),last_observed_wall_epoch_ns=None))
            life['last_observed_wall_epoch_ns']=row.get('wall_epoch_ns')
        for component,processes in groups.items():
            for field in ('rss_bytes','pss_bytes','private_bytes','cpu_percent_one_core'):
                values=[p.get(field) for p in processes]
                if all(isinstance(v,(int,float)) for v in values):
                    peaks[component][field]=max(peaks[component].get(field) or 0,sum(values))
                else:peaks[component].setdefault(field,None)
    extrema={}
    for field in ('ram_available_bytes','cpu_percent','load1','vram_used_bytes','rtf','evidence_bytes'):
        values=[r[field] for r in rows if isinstance(r.get(field),(int,float))]
        extrema[field]=dict(min=min(values),max=max(values)) if values else None
    return dict(source=str(root),profile=manifest.get('profile'),state=manifest.get('state'),
                qualified=False,sample_count=len(rows),component_peaks=dict(peaks),host_extrema=extrema,
                process_observation_intervals=list(lifetimes.values()),errors=errors,
                source_hashes={p.name:file_hash(p) for p in (root/'manifest.json',path) if p.exists()},
                caveats=['RSS double-counts shared pages; PSS apportions them when readable.',
                         'Component peaks are not simultaneous; do not sum maxima.',
                         'Host RAM/CPU/GPU include background processes; no causal cross-workload subtraction.',
                         'Process intervals are observed bounds, not exact exit times; start_ticks is kernel boot clock.',
                         'RTF is clock receipt delta, not validated settled workload RTF.',
                         'DDS queue occupancy and per-plugin/per-process GPU allocations are unavailable.'])


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('runs',nargs='+',type=Path);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    result={'execution_class':'NON_QUALIFYING','runs':[summarize(r) for r in a.runs]}
    with a.output.open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False)

if __name__=='__main__':main()
