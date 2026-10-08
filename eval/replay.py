"""Execute the production scorers on saved Dev evidence, never qualify replay."""
import json
from collections import defaultdict, deque
from pathlib import Path

from analyzer import analyze
from backcheck import normalized as historical_facts
from evidence import atomic_json, file_hash, bag_hash, ros_json_data
from normalize import normalized, oracle_facts, host_measurements
from oracle import score
from seed_policy import expand


def check_dev(manifest):
    import yaml
    policy=yaml.safe_load(Path(__file__).with_name('seeds.yaml').read_text())
    seed=manifest.get('seed')
    if seed not in expand(policy['dev']) or seed in expand(policy['test_a']) or seed in expand(policy['reserve_m4']):
        raise ValueError('Replay requires a governed Dev seed; no held-out inspection')


def mcap_events(source):
    """Decode CDR; match receipt stamps and wall sidecars without inventing time."""
    import rosbag2_py
    from rclpy.serialization import deserialize_message
    from rosidl_runtime_py.utilities import get_message
    from rosidl_runtime_py.convert import message_to_ordereddict
    sidecars=defaultdict(deque)
    for line in (source/'logs/events.jsonl').read_text().splitlines():
        event=json.loads(line)
        sidecars[(event['topic'],round(event['sim_s']*1e9))].append(event)
    reader=rosbag2_py.SequentialReader()
    reader.open(rosbag2_py.StorageOptions(uri=str(source/'bag'),storage_id='mcap'),
                rosbag2_py.ConverterOptions('',''))
    types={t.name:get_message(t.type) for t in reader.get_all_topics_and_types()}
    events=[];uuids=set();headers=0
    while reader.has_next():
        topic,raw,stamp=reader.read_next()
        data=ros_json_data(message_to_ordereddict(deserialize_message(raw,types[topic])))
        matches=sidecars[(topic,stamp)]
        if not matches:raise ValueError(f'MCAP receipt has no matching wall sidecar: {topic} {stamp}')
        event=matches.popleft()
        if data!=event['data']:raise ValueError('MCAP/decoded sidecar payload mismatch')
        if 'header' in data:headers+=1
        for status in data.get('status_list',[]):
            uuids.add(bytes(status['goal_info']['goal_id']['uuid']).hex())
        events.append(dict(event,sim_s=stamp/1e9,data=data))
    if any(sidecars.values()):raise ValueError('Sidecar records missing from MCAP')
    return events,dict(records=len(events),source_headers=headers,goal_uuids=sorted(uuids),
                       timestamp_reconstruction='MCAP ROS receive ns; source stamps preserved in decoded payload; wall receipt from validated sidecar')


def run(source,output,kind):
    source=Path(source).resolve();output=Path(output).resolve()
    manifest=json.loads((source/'manifest.json').read_text());check_dev(manifest)
    output.mkdir(parents=True,exist_ok=False);(output/'logs').mkdir()
    hashes={str(p.relative_to(source)):file_hash(p) for p in source.iterdir() if p.is_file()}
    if kind=='historical':
        from historical_replay import historical_events
        events=historical_events(source)
        facts=historical_facts(source)
        manifest=dict(manifest,home_xy_m=facts['home_xy_m'])
        reconstruction=dict(records=len(events),goal_uuids=[],
                            timestamp_reconstruction='Saved source simulation stamps; historical observations wall stamps only',
                            limitation='Historical trace has no MCAP or action UUIDs; absent fields remain unknown')
    else:
        events,reconstruction=mcap_events(source)
        facts=oracle_facts(events,manifest)
        hashes['bag']=bag_hash(source/'bag')
        hashes['logs/events.jsonl']=file_hash(source/'logs/events.jsonl')
    manifest=dict(manifest,qualified=False,evidence_label='HISTORICAL_REPLAY' if kind=='historical' else 'SYNTHETIC_MCAP_REPLAY',
                  replay_source=str(source),replay_source_hashes=hashes)
    result=score(facts)
    trace=normalized(events,manifest)
    if kind=='mcap' and (source/'host_metrics.csv').exists():trace+=host_measurements(source/'host_metrics.csv')
    thresholds=json.loads(Path(__file__).with_name('thresholds.json').read_text())['thresholds']
    analysis=analyze(trace,thresholds,result['mission_verdict'],result['oracle_verdict'],require_catalog_coverage=True)
    atomic_json(output/'manifest.json',manifest);atomic_json(output/'oracle.json',result)
    atomic_json(output/'logs/oracle_facts.json',facts);atomic_json(output/'analysis.json',analysis)
    for name,items in [('events',events),('normalized',trace)]:
        with (output/'logs'/f'{name}.jsonl').open('x') as stream:
            for event in items:stream.write(json.dumps(event,allow_nan=False)+'\n')
    summary=dict(evidence_label=manifest['evidence_label'],qualified=False,source=str(source),
                 reconstruction=reconstruction,oracle_verdict=result['oracle_verdict'],
                 mission_verdict=result['mission_verdict'],mission_oracle_disagreement=result['mission_oracle_disagreement'],
                 first_violated_invariant=analysis['first_violated_invariant'],
                 first_supported_violation=analysis['first_supported_violation'],
                 catalog_measurements_complete=analysis['catalog_measurements_complete'],
                 analysis_sha256=file_hash(output/'analysis.json'),oracle_sha256=file_hash(output/'oracle.json'))
    atomic_json(output/'replay.json',summary)
    return summary
