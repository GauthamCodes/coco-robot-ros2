"""Shared post-run pipeline; structural evidence loss never creates a PASS."""
from analyzer import analyze
from manipulation import verify
from normalize import normalized, oracle_facts, payload
from oracle import score


def evaluate_recording(events,manifest,thresholds,facts=None,extra_trace=(),integrity_errors=()):
    errors=list(integrity_errors)
    if facts is None:
        try:
            boundaries={}
            if manifest.get('execution_class')=='NON_QUALIFYING' and manifest.get('profile')=='rgbd_manipulation':
                markers={}
                for e in events:
                    d=payload(e)
                    if e.get('topic')=='/diagnostics/manipulation_checkpoints' and isinstance(d,dict) and d.get('checkpoint') in ('control_started','control_finished'):
                        markers.setdefault(d['checkpoint'],[]).append(e)
                if len(markers.get('control_started',[]))==1 and len(markers.get('control_finished',[]))==1:
                    start=markers['control_started'][0];end=markers['control_finished'][0]
                    ds,de=payload(start),payload(end)
                    # Latched discovery can delay receipt: use BOTH source clocks, never mix them.
                    from oracle import finite
                    if all(finite(d.get(k)) for d in (ds,de) for k in ('stamp_ns','source_monotonic_s')) and all(finite(start.get(k)) for k in ('receive_monotonic_s','wall_s')) and de['stamp_ns']>ds['stamp_ns'] and de['source_monotonic_s']>ds['source_monotonic_s']:
                        recorder_origin=start['receive_monotonic_s']-start['wall_s']
                        boundaries=dict(start_event=dict(start,sim_s=ds['stamp_ns']/1e9,wall_s=ds['source_monotonic_s']-recorder_origin),
                                        terminal_event=dict(end,sim_s=de['stamp_ns']/1e9,wall_s=de['source_monotonic_s']-recorder_origin),mission_verdict='UNOBSERVED')
            facts=oracle_facts(events,manifest,**boundaries) if manifest.get('targets') else {}
            if boundaries:facts['boundary_provenance']='Engineering checkpoint source ROS and monotonic emission clocks; no mission verdict inferred'
        except (ValueError,TypeError,KeyError,IndexError,OverflowError,AttributeError) as exc:
            errors.append('Oracle normalization failed: '+repr(exc));facts={}
    try:oracle=score(facts)
    except (ValueError,TypeError,KeyError,IndexError,OverflowError,AttributeError) as exc:
        errors.append('Oracle evidence invalid: '+repr(exc));oracle=score({})
    try:trace=normalized(events,manifest)+list(extra_trace)
    except (ValueError,TypeError,KeyError,IndexError,OverflowError,AttributeError) as exc:
        errors.append('Invariant normalization failed: '+repr(exc));trace=list(extra_trace)
    analysis=analyze(trace,thresholds,oracle['mission_verdict'],oracle['oracle_verdict'],require_catalog_coverage=True)
    manipulation=verify(events,manifest,oracle,trace,thresholds,integrity_errors=errors)
    return dict(oracle=oracle,facts=facts,trace=trace,analysis=analysis,manipulation=manipulation,errors=errors)
