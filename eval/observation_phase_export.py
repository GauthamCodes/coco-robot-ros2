"""Export sensor observations with explicit control-phase events, never truth.

Events file: JSON list {phase, stamp_ns}; source timestamps are ROS nanoseconds.
Static fixtures may label baseline only. No absent phase is synthesized.
"""
import argparse
import json
from pathlib import Path
import sys
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"coco_config"))
from coco_config.observation_phase import PhaseValidator


def export(events_path, phases, colour):
    validator=PhaseValidator(colour)
    pending=iter(phases);event=next(pending,None);records=[]
    for line in events_path.read_text().splitlines():
        row=json.loads(line)
        if row["topic"]!="/perception/object_height":continue
        o=json.loads(row["data"]["data"])
        now_ns=round(row["sim_s"]*1e9)
        while event and event["stamp_ns"]<=now_ns:
            validator.transition(event["phase"],event["stamp_ns"])
            event=next(pending,None)
        records.append(validator.record(o,now_ns))
    summary={}
    for phase in ("baseline","approach","lift","release"):
        selected=[r for r in records if r["phase"]==phase]
        valid=[r["observation"] for r in selected if r["contract_valid"]]
        stats={}
        for key in ("center_height_above_support_m","support_height_m","uncertainty_m","depth_median_m","valid_fraction"):
            values=np.array([o[key] for o in valid],float)
            if len(values):
                q=np.quantile(values,[.25,.5,.75])
                stats[key]=dict(n=len(values),median=float(q[1]),iqr=float(q[2]-q[0]))
                if len(values)>=10:
                    rng=np.random.default_rng(0)
                    medians=np.median(rng.choice(values,(2000,len(values)),replace=True),axis=1)
                    stats[key]["bootstrap_median_95_interval"]=np.quantile(medians,[.025,.975]).tolist()
        summary[phase]=dict(samples=len(selected),valid_samples=len(valid),statistics=stats,
                            status="OBSERVED" if selected else "NOT_REACHED")
    return dict(execution_class="NON_QUALIFYING",ground_truth_input=False,
                phase_events=phases,summary=summary,records=records)

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("events",type=Path);p.add_argument("phases",type=Path)
    p.add_argument("output",type=Path);p.add_argument("--colour",default="red");a=p.parse_args()
    a.output.write_text(json.dumps(export(a.events,json.loads(a.phases.read_text()),a.colour),indent=2,allow_nan=False)+"\n")
