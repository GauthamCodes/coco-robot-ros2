"""Aggregate reporting only; no held-out trace inspection."""
import math
from collections import Counter,defaultdict


def wilson(k,n):
    if n==0:return None
    if not 0<=k<=n:raise ValueError('invalid k/n')
    z=1.96;p=k/n;den=1+z*z/n
    center=(p+z*z/(2*n))/den
    half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return [max(0.,center-half),min(1.,center+half)]


def aggregate(rows):
    result={}
    for backend in ('gazebo','isaac'):
        selected=[r for r in rows if r['backend']==backend and r['qualified']]
        # UNSCORABLE runs remain visible and do not masquerade as counted failures.
        scored=[r for r in selected if r['oracle_verdict'] in ('PASS','FAIL')]
        k=sum(r['oracle_verdict']=='PASS' for r in scored);fail=[r for r in scored if r['oracle_verdict']=='FAIL']
        result[backend]={'k':k,'n':len(scored),'wilson95':wilson(k,len(selected)) if len(scored)==len(selected) else None,
                         'qualified_total':len(selected),'completion_rate':k/len(selected) if selected and len(scored)==len(selected) else None,
                         'unscorable_qualified':len(selected)-len(scored),
                         'failure_pareto':Counter(r['invariant_label'] for r in fail).most_common(),
                         'unclassified_count':sum(r['invariant_label']=='UNCLASSIFIED' for r in fail)}
    result['unqualified']=[r for r in rows if not r['qualified']]
    return result


def determinism(rows):
    groups=defaultdict(list)
    for r in rows:
        if r['qualified']:groups[(r['backend'],r['seed'])].append(r)
    result=[]
    for (backend,seed),runs in sorted(groups.items()):
        verdict=None
        if len(runs)>=3:
            fails=[r for r in runs if r['oracle_verdict']=='FAIL']
            if not fails and all(r['oracle_verdict']=='PASS' for r in runs):verdict='not reproduced'
            elif len(fails)==len(runs) and len({r['invariant_label'] for r in fails})==1 and fails[0]['invariant_label']!='UNCLASSIFIED':verdict='deterministic'
            elif fails and all(r['oracle_verdict'] in ('PASS','FAIL') for r in runs):verdict='intermittent'
        result.append(dict(backend=backend,seed=seed,n=len(runs),verdict=verdict,additional_reproduction_required=verdict is None))
    return result
