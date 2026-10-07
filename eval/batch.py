"""Sequential, locked, resumable evaluator runner. Owns only registered children."""
import csv
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from analyzer import analyze
from environment import capture
from evidence import atomic_json,bag_hash,bytes_used,disk_check,file_hash,outside_git,retain_bags,runtime_fingerprint
from normalize import oracle_facts,normalized,host_measurements
from oracle import score
from qualification import identity,inventory,qualify,cpu_percent,load_policy
from tracing import availability,TraceSession,inspect as inspect_trace
from batch_statistics import aggregate,determinism,held_out_aggregates

REPO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO/'scripts'))
from process_groups import stop,group_alive


def initialize(run,job,source,root):
    run.mkdir();(run/'logs').mkdir()
    # MCAP writer creates bag itself. It must not preexist at open time.
    manifest=dict(schema_version=1,run_id=run.name,state='CREATED',qualified=False,
                  qualification_reasons=[],source_sha=source,job=job,seed=job['seed'],seed_group=job['seed_group'],
                  requested_colour='red',home_xy_m=[-2.,0.],owned_processes=[],
                  storage_root=str(root),topics_sha256=file_hash(REPO/'eval/topics.py'))
    atomic_json(run/'manifest.json',manifest)
    atomic_json(run/'env.json',capture(Path.home()/'isaac-sim/venv/bin/python'))
    (run/'host_metrics.csv').write_text('wall_epoch_ns,wall_elapsed_s,sim_s,cpu_percent,load1,ram_available_bytes,vram_free_bytes,rtf,qualified,reasons\n')
    atomic_json(run/'oracle.json',score({}))
    atomic_json(run/'analysis.json',analyze([],{},'UNOBSERVED','UNSCORABLE'))
    return manifest


def save(run,manifest):atomic_json(run/'manifest.json',manifest)


def reconcile(root):
    """Never kill saved PIDs after a crash; PID reuse and detached groups must be checked."""
    interrupted=[]
    for run in sorted(root.glob('run-*')):
        manifest=json.loads((run/'manifest.json').read_text())
        if manifest['state']=='BLOCKED':continue
        living=[]
        for saved in manifest.get('owned_processes',[]):
            try:current=identity(saved['pid'])
            except (OSError,ValueError):current=None
            if current and current['start_ticks']==saved['start_ticks'] or group_alive(saved['pgid']):living.append(saved)
        if living:
            raise RuntimeError(f'Crash recovery requires owned-process reconciliation for {run}: {living}; no automatic PID kill')
        if manifest['state'] in ('COMPLETE','INTERRUPTED'):continue
        manifest['state']='INTERRUPTED';manifest['qualified']=False
        manifest['qualification_reasons'].append('CRASH_INTERRUPTED')
        save(run,manifest);interrupted.append(run)
    return interrupted


def read_events(run):
    path=run/'logs/events.jsonl'
    if not path.exists():return []
    events=[]
    with path.open() as stream:
        for line in stream:
            # A truncated/corrupt trace is evidence loss, never a clean run.
            events.append(json.loads(line))
    return events


def simulator_failure(run,events):
    """Direct simulator exit is a failed run, distinct from host qualification."""
    failure=run/'logs/episode/runner_failure.txt';exits=run/'logs/episode/runtime_exit_observation.json'
    if not failure.exists() or not exits.exists():return None
    from normalize import payload,state_name
    mission_started=any(e['topic']=='/mission/state' and state_name(payload(e))=='LOCALIZE' for e in events)
    text=failure.read_text()
    if not any(reason in text for reason in ('A required child exited or run timed out','Isaac startup failed or timed out')):return None
    status=json.loads(exits.read_text())
    code=status.get('simulator_returncode')
    if isinstance(code,int) and code not in (-2,-9,-15):
        return {'exit_code':code,'phase':'mission' if mission_started else 'startup','runner_failure':text,'pre_teardown_observation':status,
                'evidence_label':'observed simulator exit; not a qualified completion'}
    return None


def timing_qualification(stage,rtf,stall_wall_s,thresholds):
    """Use calibrated limits only during the episode, not bootstrap/teardown."""
    if stage in ('UNKNOWN','IDLE','COMPLETE','ABORT'):return []
    reasons=[];floor=thresholds.get('rtf_floor');stall=thresholds.get('clock_stall_wall_s')
    if floor is not None and rtf is not None and rtf<floor:reasons.append('RTF_BELOW_CALIBRATED_FLOOR')
    if stall is not None and stall_wall_s is not None and stall_wall_s>stall:reasons.append('SIM_CLOCK_STALLED')
    return reasons


def summarize(root):
    records=[]
    for run in sorted(root.glob('run-*')):
        m=json.loads((run/'manifest.json').read_text());o=json.loads((run/'oracle.json').read_text());a=json.loads((run/'analysis.json').read_text())
        records.append(dict(run_id=run.name,backend=m['job']['backend'],seed=m['seed'],seed_group=m['seed_group'],repeat=m['job']['repeat'],
                            state=m['state'],qualified=m['qualified'],qualification_reasons=m['qualification_reasons'],
                            oracle_verdict=o['oracle_verdict'],mission_verdict=o['mission_verdict'],
                            mission_oracle_disagreement=o.get('mission_oracle_disagreement'),
                            invariant_label=a['first_violated_invariant'],sim_time_s=m.get('sim_time_s'),
                            wall_time_s=m.get('wall_time_s'),mean_rtf=m.get('mean_rtf')))
    atomic_json(root/'summary.json',{'runs':[r for r in records if r['seed_group']!='test_a'],
                                    'held_out_results_aggregate_only':True,
                                    'held_out_attempts':sum(r['seed_group']=='test_a' for r in records),
                                    'dev':aggregate([r for r in records if r['seed_group']=='dev']),
                                    'test_a':held_out_aggregates([r for r in records if r['seed_group']=='test_a']),
                                    'dev_determinism':determinism([r for r in records if r['seed_group']=='dev']),
                                    'qualified_count':sum(r['qualified'] for r in records),
                                    'unqualified_count':sum(not r['qualified'] and r['state']!='BLOCKED' for r in records),
                                    'blocked_count':sum(r['state']=='BLOCKED' for r in records)})
    return records


def execute(run,job,manifest,root,host_policy,storage,collect=inventory):
    # Preflight is completed before any Popen, even recorder/world generation.
    snap=collect();preflight=qualify(snap,host_policy,job['backend'])
    atomic_json(run/'logs/preflight.json',{'inventory':snap,'verdict':preflight})
    disk=disk_check(root,storage,starting=True)
    if not preflight['qualified'] or not disk['ok']:
        manifest['state']='BLOCKED';manifest['qualification_reasons']=preflight['reasons']+disk['reasons'];save(run,manifest)
        (run/'bag').mkdir(exist_ok=True)
        return False
    owned=[];handles=[];groups=[]
    started=time.monotonic();latest_clock=None;last_clock=None;last_clock_wall=None;clock_last_advance=None;previous=snap;rtfs=[]
    timing_limits=json.loads((REPO/'eval/thresholds.json').read_text())['thresholds']
    manifest['state']='RUNNING';manifest['qualified']=True;save(run,manifest)
    atomic_json(run/'logs/tracing_availability.json',availability())
    def spawn(name,args):
        handle=(run/'logs'/f'{name}.log').open('x');handles.append(handle)
        process=subprocess.Popen(args,cwd=REPO,stdout=handle,stderr=subprocess.STDOUT,start_new_session=True)
        ident=identity(process.pid);owned.append(ident);groups.append((name,process))
        manifest['owned_processes']=list(owned);save(run,manifest)
        return process
    failure=None
    executor_trace=None
    if job['seed_group']=='dev' and job['seed'] in (6,7):
        executor_trace=TraceSession(run/'logs/executor_trace')
        executor_trace.start()
    try:
        recorder=spawn('recorder',[sys.executable,str(REPO/'eval/recorder.py'),str(run)])
        deadline=time.monotonic()+30
        while not (run/'logs/recorder_ready.json').exists():
            if recorder.poll() is not None or time.monotonic()>deadline:raise RuntimeError('MCAP recorder startup failed')
            time.sleep(.1)
        legacy=run/'logs/episode'
        runner=spawn('episode',[sys.executable,str(REPO/'scripts/isaac_fetch.py'),str(legacy),
                                '--backend',job['backend'],'--level','positions','--seed',str(job['seed']),
                                '--colour','red','--domain',os.environ['ROS_DOMAIN_ID'],'--eval-logging'])
        truth=None
        with (run/'host_metrics.csv').open('a',newline='') as metrics:
            writer=csv.writer(metrics)
            while runner.poll() is None:
                tick=time.monotonic()
                if job['backend']=='gazebo' and truth is None and (legacy/'manifest.json').exists():
                    truth=spawn('truth',[sys.executable,str(REPO/'eval/gazebo_truth.py'),str(legacy/'manifest.json')])
                if recorder.poll() is not None:raise RuntimeError('Trace recorder died')
                if truth is not None and truth.poll() is not None:raise RuntimeError('Ground truth adapter died')
                snap=collect()
                # Allow only exact registered sessions and their present members.
                allowed=list(owned)
                identities={(i['pid'],i['start_ticks']) for i in owned}
                current={i['pid']:i for i in snap['processes']}
                owned_pids={i['pid'] for i in owned if i['pid'] in current
                            and current[i['pid']]['start_ticks']==i['start_ticks']}
                changed=True
                while changed:
                    changed=False
                    for process in snap['processes']:
                        if process.get('ppid') in owned_pids and process['pid'] not in owned_pids:
                            owned_pids.add(process['pid']);changed=True
                for process in snap['processes']:
                    if process['pid'] in owned_pids and (process['pid'],process['start_ticks']) not in identities:
                        owned.append(process);allowed.append(process)
                manifest['owned_processes']=list(owned)
                verdict=qualify(snap,host_policy,job['backend'],'runtime',owned=allowed)
                # Tail reads need bounded offsets; no repeated whole trace reads.
                clock_path=run/'logs/clock_latest.json'
                clock_wall=None;stage='UNKNOWN'
                if clock_path.exists():
                    clock=json.loads(clock_path.read_text());latest_clock=clock.get('sim_s');clock_wall=clock.get('clock_receive_monotonic_s')
                    stage=clock.get('mission_stage','UNKNOWN')
                rtf=None
                if latest_clock is not None and last_clock is not None and clock_wall is not None and last_clock_wall is not None and clock_wall>last_clock_wall:
                    rtf=(latest_clock-last_clock)/(clock_wall-last_clock_wall);rtfs.append(rtf)
                if latest_clock is not None and (last_clock is None or latest_clock>last_clock):clock_last_advance=clock_wall
                checks=disk_check(root,storage)
                stall_duration=tick-clock_last_advance if clock_last_advance is not None else None
                ended=legacy/'runtime_exit_observation.json'
                simulator_exited=ended.exists() and json.loads(ended.read_text()).get('simulator_returncode') is not None
                # Clock cessation after a directly observed simulator exit is
                # failure evidence, not an RTF qualification violation during a
                # still-running episode. Host/process/disk checks still apply.
                timing_reasons=[] if simulator_exited else timing_qualification(stage,rtf,stall_duration,timing_limits)
                reasons=verdict['reasons']+checks['reasons']+timing_reasons
                if not simulator_exited and stage not in ('UNKNOWN','IDLE','COMPLETE','ABORT') and latest_clock is not None and last_clock is not None and latest_clock<last_clock:
                    reasons.append('SIM_CLOCK_REGRESSED')
                if bytes_used(run)>storage['max_run_bytes']:reasons.append('RUN_DISK_BUDGET_EXCEEDED')
                writer.writerow([snap['wall_epoch_ns'],tick-started,latest_clock,cpu_percent(previous,snap),snap['load1'],snap['ram_available_bytes'],(snap['gpu'] or {}).get('free_bytes'),rtf,not reasons,json.dumps(reasons)])
                metrics.flush();previous=snap;last_clock=latest_clock;last_clock_wall=clock_wall
                if reasons:
                    manifest['qualified']=False
                    for reason in reasons:
                        if reason not in manifest['qualification_reasons']:manifest['qualification_reasons'].append(reason)
                    save(run,manifest)
                    # Preserve evidence and stop immediately; never continue unqualified as a counted run.
                    raise RuntimeError('MID_RUN_UNQUALIFIED: '+repr(reasons))
                time.sleep(max(0,1-(time.monotonic()-tick)))
    except BaseException as exc:
        failure=repr(exc);manifest['qualified']=False;manifest['qualification_reasons'].append('HARNESS_ERROR: '+failure)
        atomic_json(run/'logs/harness_error.json',{'error':failure})
    finally:
        # Stop recorder last: teardown/producer exits remain captured.
        teardown_errors=[]
        for name,child in sorted(groups,key=lambda p:p[0]=='recorder'):
            try:stop(name,child)
            except Exception as exc:teardown_errors.append(str(exc))
        if executor_trace is not None:
            atomic_json(run/'logs/executor_trace_status.json',executor_trace.close())
            try:timing=inspect_trace(executor_trace.output,owned_pids=[p['pid'] for p in owned])
            except Exception as exc:timing={'executor_timing_verified':False,'error':repr(exc)}
            atomic_json(run/'logs/executor_timing.json',timing)
        for handle in handles:handle.close()
        after=collect();post=qualify(after,host_policy,job['backend'])
        survivors=[]
        for saved in owned:
            try:current=identity(saved['pid'])
            except (OSError,ValueError):continue
            if current['start_ticks']==saved['start_ticks'] and current.get('state')!='Z':survivors.append(saved)
        if survivors:teardown_errors.append('OWNED_PROCESSES_SURVIVED')
        if (root/'batch.json').exists():
            registered=json.loads((root/'batch.json').read_text())
            if registered.get('runtime_fingerprint')!=runtime_fingerprint():teardown_errors.append('RUNTIME_SOURCE_CHANGED')
            if subprocess.check_output(['git','status','--porcelain=v1'],cwd=REPO,text=True).strip():teardown_errors.append('WORKTREE_CHANGED')
            if subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()!=manifest['source_sha']:teardown_errors.append('SOURCE_COMMIT_CHANGED_DURING_RUN')
        atomic_json(run/'logs/teardown.json',{'inventory':after,'qualification':post,'errors':teardown_errors,'surviving_owned_processes':survivors})
        if teardown_errors or not post['qualified']:
            manifest['qualified']=False;manifest['qualification_reasons']+=['TEARDOWN: '+r for r in teardown_errors+post['reasons']]
        manifest['wall_time_s']=time.monotonic()-started
        manifest['mean_rtf']=sum(rtfs)/len(rtfs) if rtfs else None
        if (run/'bag').exists():manifest['bag_hash']=bag_hash(run/'bag')
        else:(run/'bag').mkdir()
        try:
            events=read_events(run)
            child_failure=run/'logs/episode/runner_failure.txt'
            if child_failure.exists():
                sim_failure=simulator_failure(run,events)
                if sim_failure:
                    manifest['robot_run_failure']=sim_failure
                    atomic_json(run/'logs/simulator_failure.json',sim_failure)
                else:
                    manifest['qualified']=False
                    manifest['qualification_reasons'].append('EPISODE_RUNNER_FAILURE: '+child_failure.read_text())
            if (run/'logs/episode/manifest.json').exists():
                episode=json.loads((run/'logs/episode/manifest.json').read_text())
                manifest['targets']=episode['targets'];manifest['backend']=job['backend']
                facts=oracle_facts(events,manifest);result=score(facts)
                atomic_json(run/'logs/oracle_facts.json',facts);atomic_json(run/'oracle.json',result)
                facts_trace=normalized(events,manifest)+host_measurements(run/'host_metrics.csv')
                with (run/'logs/normalized.jsonl').open('w') as f:
                    for event in facts_trace:f.write(json.dumps(event,allow_nan=False)+'\n')
                analysis=analyze(facts_trace,json.loads((REPO/'eval/thresholds.json').read_text())['thresholds'],result['mission_verdict'],result['oracle_verdict'],require_catalog_coverage=True)
                atomic_json(run/'analysis.json',analysis)
                manifest['mission_verdict']=result['mission_verdict'];manifest['invariant_label']=analysis['first_violated_invariant']
                sim=[e['sim_s'] for e in events if e['topic']=='/clock']
                manifest['sim_time_s']=max(sim)-min(sim) if sim else None
                if result.get('mission_oracle_disagreement') is True:
                    atomic_json(run/'logs/oracle_disagreement.json',{
                        'stop_condition':'MISSION_ORACLE_DISAGREEMENT',
                        'oracle':result,'source_sha':manifest['source_sha']})
        except Exception as exc:
            failure='EVIDENCE_PROCESSING_ERROR: '+repr(exc)
            manifest['qualified']=False
            manifest['qualification_reasons'].append(failure)
            atomic_json(run/'logs/processing_error.json',{'error':failure})
        manifest['state']='COMPLETE' if failure is None else 'INTERRUPTED';save(run,manifest)
    return manifest['qualified']


def run_batch(root,jobs,campaign,collect=inventory,policy=None,storage=None):
    root=outside_git(root);root.mkdir(parents=True,exist_ok=True)
    with (root/'batch.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        # A resumable campaign must never skip past a previous integrity stop.
        if (root/'STOP.json').exists():return 4
        registration={'campaign':str(campaign),'campaign_sha256':file_hash(campaign),'jobs':jobs,
                      'host_policy_sha256':file_hash(REPO/'eval/host_policy.json'),
                      'storage_policy_sha256':file_hash(REPO/'eval/storage_policy.json'),
                      'runtime_fingerprint':runtime_fingerprint(),
                      'source_sha':subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()}
        path=root/'batch.json'
        if path.exists():
            saved=json.loads(path.read_text())
            # STATUS/proof commits after a partial batch must not make the
            # unchanged campaign impossible to resume. Executable/assets/config
            # content remains strictly bound; each new run records actual HEAD.
            if {k:v for k,v in saved.items() if k!='source_sha'}!={k:v for k,v in registration.items() if k!='source_sha'}:
                raise ValueError('Resume runtime/campaign/policy/jobs changed; use a new batch root')
        if not path.exists():atomic_json(path,registration)
        provenance=root/'resume_sources.json'
        sources=json.loads(provenance.read_text()) if provenance.exists() else []
        if not sources or sources[-1]['source_sha']!=registration['source_sha']:
            sources.append({'source_sha':registration['source_sha'],'wall_epoch_ns':time.time_ns()})
            atomic_json(provenance,sources)
        for previous_run in sorted(root.glob('run-*')):
            previous_oracle=json.loads((previous_run/'oracle.json').read_text())
            if previous_oracle.get('mission_oracle_disagreement') is True:
                atomic_json(root/'STOP.json',{'stop_condition':'MISSION_ORACLE_DISAGREEMENT','run_id':previous_run.name,
                                            'source_sha':registration['source_sha'],'oracle':previous_oracle})
                return 4
        reconcile(root)
        policy=policy or load_policy();storage=storage or json.loads((REPO/'eval/storage_policy.json').read_text())
        for index,job in enumerate(jobs):
            prefix=f"run-{index:04d}-{job['backend']}-{job['seed']}-r{job['repeat']}"
            attempts=sorted(root.glob(prefix+'-a*'))
            if any(json.loads((p/'manifest.json').read_text())['state']=='COMPLETE' and json.loads((p/'manifest.json').read_text())['qualified'] for p in attempts):continue
            run=root/(prefix+f'-a{len(attempts):03d}')
            manifest=initialize(run,job,registration['source_sha'],root)
            ok=execute(run,job,manifest,root,policy,storage,collect)
            summarize(root)
            oracle=json.loads((run/'oracle.json').read_text())
            if oracle.get('mission_oracle_disagreement') is True:
                atomic_json(root/'STOP.json',{'stop_condition':'MISSION_ORACLE_DISAGREEMENT','run_id':run.name,
                                            'source_sha':registration['source_sha'],'oracle':oracle})
                return 4
            if 'BATCH_DISK_BUDGET_EXCEEDED' in manifest['qualification_reasons'] or 'RUN_DISK_BUDGET_EXCEEDED' in manifest['qualification_reasons']:
                atomic_json(root/'STOP.json',{'stop_condition':'DISK_BUDGET_EXCEEDED','run_id':run.name,
                                            'reasons':manifest['qualification_reasons']})
                return 4
            if not ok:return 3
            retain_bags(sorted(root.glob('run-*')),storage['controls_per_batch'])
        summarize(root);return 0
