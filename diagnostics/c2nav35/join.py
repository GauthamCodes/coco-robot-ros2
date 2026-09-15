#!/usr/bin/env python3
"""Offline exact-input/GT join. No ROS imports, runtime, or forward filling."""
import argparse
import bisect
import json
import hashlib
import math
import subprocess
from pathlib import Path


def unit(q):
    norm = math.sqrt(sum(x*x for x in q))
    if not math.isfinite(norm) or abs(norm - 1) > 1e-3:
        raise ValueError('invalid quaternion')
    return [x/norm for x in q]


def product(a, b):
    x, y, z, w = a
    X, Y, Z, W = b
    return [w*X+x*W+y*Z-z*Y, w*Y-x*Z+y*W+z*X,
            w*Z+x*Y-y*X+z*W, w*W-x*X-y*Y-z*Z]


def interpolate(a, b, fraction):
    qa, qb = unit(a[3:]), unit(b[3:])
    dot = sum(x*y for x, y in zip(qa, qb))
    if dot < 0:
        qb, dot = [-x for x in qb], -dot
    if dot > .9995:
        q = [x + fraction*(y-x) for x, y in zip(qa, qb)]
        length = math.sqrt(sum(x*x for x in q))
        q = [x/length for x in q]
    else:
        angle = math.acos(min(1, dot))
        q = [(math.sin((1-fraction)*angle)*x + math.sin(fraction*angle)*y) / math.sin(angle)
             for x, y in zip(qa, qb)]
    return [x + fraction*(y-x) for x, y in zip(a[:3], b[:3])] + q


def base_pose(pose, extrinsic):
    if len(pose) != 7 or not all(math.isfinite(v) for v in pose):
        raise ValueError('malformed pose')
    q = unit(pose[3:])
    e = unit(extrinsic[3:])
    rotated = product(product(q, extrinsic[:3] + [0]), [-q[0], -q[1], -q[2], q[3]])
    p = [x+y for x, y in zip(pose[:3], rotated[:3])]
    x, y, z, w = product(q, e)
    return [p[0], p[1], math.atan2(2*(w*z+x*y), 1-2*(y*y+z*z))]


def relative(a, b):
    x, y = b[0]-a[0], b[1]-a[1]
    c, s = math.cos(a[2]), math.sin(a[2])
    angle = b[2]-a[2]
    return [c*x+s*y, -s*x+c*y, math.atan2(math.sin(angle), math.cos(angle))]


def read(path):
    with open(path) as stream:
        rows = [json.loads(line, parse_constant=lambda value: (_ for _ in ()).throw(
            ValueError('nonfinite JSON constant: ' + value))) for line in stream]
    if not rows or rows[0].get('stage') != 'manifest':
        raise ValueError('missing manifest')
    if rows[-1].get('stage') != 'footer':
        raise ValueError('missing footer: capture incomplete')
    footer = rows[-1]
    body = rows[1:-1]
    if not body or any(r.get('stage') in ('manifest', 'footer') for r in body):
        raise ValueError('empty or concatenated capture')
    if (footer.get('completion') != 'complete' or
            footer.get('successful') != len(body) or
            footer.get('attempted') != len(body) or
            footer.get('malformed') != 0):
        raise ValueError('incomplete capture or inconsistent integrity counters')
    if rows[-1]['dropped'] or rows[-1]['write_failed']:
        raise ValueError('capture reports loss/write failure')
    if any(row.get('schema') != 1 for row in rows):
        raise ValueError('unknown schema')
    scans = [r['scan_id'] for r in rows if r.get('stage') == 'scan']
    if len(set(scans)) != len(scans):
        raise ValueError('duplicate scan identity: require one AMCL instance per process')
    return rows


def validate_stream(rows, kind):
    """Reject ambiguity before constructing lookup dictionaries or sorting."""
    seen = set()
    last_stamp = last_receipt = None
    frames = set()
    for r in rows:
        stage = r.get("stage")
        if stage in ("manifest", "footer"):
            continue
        if r.get("epoch", 0) != 0:
            raise ValueError("clock discontinuity: nonzero epoch")
        if kind == "gt":
            key = r["id"]
            stamp, receipt = r["stamp_ns"], r.get("receipt_sim")
            frames.add((r["frame"], r["child"]))
        else:
            key = (stage, r.get("prediction_id") if stage in
                   ("prediction_begin", "prediction_end", "motion_decomposition")
                   else r.get("scan_id"))
            stamp, receipt = r.get("scan_ns"), r.get("receipt_ns")
            if stage == "tf_success":
                frames.add((r["source"], r["target"], r.get("scan_frame", "")))
        if key in seen:
            raise ValueError("duplicate record identity")
        seen.add(key)
        if stamp is not None:
            if last_stamp is not None and (stamp < last_stamp or
                                          (kind == "gt" and stamp == last_stamp)):
                raise ValueError("nonmonotonic acquisition time")
            last_stamp = stamp
        if receipt is not None:
            if last_receipt is not None and receipt < last_receipt:
                raise ValueError("clock discontinuity: receipt time reversed")
            last_receipt = receipt
    if len(frames) != 1 or any(not x for frame in frames for x in frame):
        raise ValueError("missing records or frame continuity failure")


def gt_at(rows, stamp, epoch, max_gap_ns, extrinsic):
    samples = [r for r in rows if r.get('stage') == 'gt' and r['epoch'] == epoch]
    if any(a['stamp_ns'] >= b['stamp_ns'] for a, b in zip(samples, samples[1:])):
        raise ValueError('GT acquisition ordering invalid')
    times = [r['stamp_ns'] for r in samples]
    if len(set(times)) != len(times):
        raise ValueError('duplicate GT acquisition stamp')
    index = bisect.bisect_left(times, stamp)
    if index < len(times) and times[index] == stamp:
        a = b = samples[index]
    elif index == 0 or index == len(times):
        raise ValueError('GT extrapolation required')
    else:
        a, b = samples[index-1:index+1]
    if (a['frame'], a['child']) != (b['frame'], b['child']):
        raise ValueError('GT frame change')
    gap = b['stamp_ns'] - a['stamp_ns']
    if gap > max_gap_ns:
        raise ValueError('GT bracket too wide')
    fraction = (stamp-a['stamp_ns']) / gap if gap else 0
    pose = interpolate(a['pose'], b['pose'], fraction)
    return base_pose(pose, extrinsic), [a['id'], b['id']], gap


def join(events, gt, extrinsic, max_gap_ns, motion_oracle=None):
    validate_stream(events, "amcl")
    validate_stream(gt, "gt")
    if max_gap_ns <= 0:
        raise ValueError("positive interpolation bound required")
    unit(extrinsic[3:])
    poses = {(r['epoch'], r['scan_id']): r for r in events
             if r.get('stage') == 'tf_success'}
    frames = {(r['frame'], r['child']) for r in gt if r.get('stage') == 'gt'}
    if len(frames) != 1:
        raise ValueError('GT absent or frames changed')
    decompositions = {r['prediction_id']: r for r in events
                      if r.get('stage') == 'motion_decomposition'}
    ends = {r['prediction_id']: r for r in events if r.get('stage') == 'prediction_end'}
    sensor = {r['scan_id']: r['stage'] for r in events
              if r.get('stage') in ('sensor_success', 'sensor_failure')}
    output = []
    seen = set()
    for r in events:
        if r.get('stage') != 'prediction_begin':
            continue
        row = dict(r, status='unobservable', sensor_status=sensor.get(r['scan_id']))
        try:
            identity = r['prediction_id']
            if identity in seen:
                raise ValueError('duplicate prediction ID; use one AMCL instance')
            seen.add(identity)
            if r['truncated'] or r['tf_ok'] != 1 or identity not in ends:
                raise ValueError('incomplete prediction')
            current = poses.get((r['epoch'], r['scan_id']))
            if current is None or current.get('tf_ok') != 1:
                raise ValueError('missing successful current TF')
            for field in ('scan_ns', 'tf_ns', 'pose', 'source', 'target'):
                if current[field] != r[field]:
                    raise ValueError('current TF mismatch: ' + field)
            anchor = poses.get((r['epoch'], r['anchor_id']))
            if (anchor is None or anchor.get('tf_ok') != 1 or
                    anchor['scan_ns'] != r['anchor_ns']):
                raise ValueError('anchor missing or crosses epoch')
            for tf_record in (current, anchor):
                tf_pose = base_pose(tf_record['tf'], [0, 0, 0, 0, 0, 0, 1])
                mismatch = relative(tf_pose, tf_record['pose'])
                if any(abs(value) > 1e-9 for value in mismatch):
                    raise ValueError('TF transform and consumed pose mismatch')
            if r['tf_ns'] != r['scan_ns'] or anchor['tf_ns'] != anchor['scan_ns']:
                raise ValueError('returned TF time differs from scan time; no scan-time GT pairing')
            if (r['source'], r['target']) != (anchor['source'], anchor['target']):
                raise ValueError('odometry frames changed')
            if r['anchor'] != anchor['pose']:
                raise ValueError('anchor pose does not match recorded lookup')
            if r['scan_ns'] < r['anchor_ns']:
                raise ValueError('scan precedes anchor')
            if identity not in decompositions:
                raise ValueError('no differential-model decomposition')
            for event in (decompositions[identity], ends[identity]):
                for field in ('scan_id', 'epoch', 'scan_ns', 'anchor_id', 'anchor_ns',
                              'pose', 'anchor', 'delta', 'source', 'target', 'scan_frame',
                              'tf_ok', 'tf_ns', 'tf'):
                    if event.get(field) != r.get(field):
                        raise ValueError('prediction event mismatch: ' + field)
            for vector in (r['pose'], r['anchor'], decompositions[identity]['motion']):
                if len(vector) != 3 or not all(math.isfinite(v) for v in vector):
                    raise ValueError('malformed motion vector')
            current_gt, ids, gap = gt_at(gt, r['scan_ns'], r['epoch'], max_gap_ns, extrinsic)
            anchor_gt, aids, agap = gt_at(gt, r['anchor_ns'], r['epoch'], max_gap_ns, extrinsic)
            odom_delta = relative(r['anchor'], r['pose'])
            if motion_oracle is not None:
                predicted = json.loads(subprocess.check_output(
                    [str(motion_oracle), *map(str, r['pose'] + r['delta'] + anchor_gt)],
                    text=True, timeout=5))
                odom_delta = relative(anchor_gt, predicted)
            gt_delta = relative(anchor_gt, current_gt)
            residual = [a-b for a, b in zip(odom_delta, gt_delta)]
            residual[2] = math.atan2(math.sin(residual[2]), math.cos(residual[2]))
            row.update(status='paired', motion=decompositions[identity]['motion'],
                       gt_pose=current_gt, gt_anchor=anchor_gt,
                       gt_sample_ids=ids, gt_anchor_sample_ids=aids,
                       gt_gap_ns=gap, gt_anchor_gap_ns=agap,
                       odom_body_delta=odom_delta, gt_body_delta=gt_delta,
                       residual=residual, longitudinal=residual[0],
                       lateral=residual[1], yaw=residual[2],
                       world_frame=next(iter(frames))[0],
                       world_residual=[math.cos(anchor_gt[2])*residual[0] -
                                       math.sin(anchor_gt[2])*residual[1],
                                       math.sin(anchor_gt[2])*residual[0] +
                                       math.cos(anchor_gt[2])*residual[1]])
        except (ValueError, TypeError) as error:
            row['error'] = str(error)
        output.append(row)
    if not output:
        raise ValueError('no actual predictions captured')
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('amcl', type=Path)
    parser.add_argument('gt', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--gt-to-base', type=float, nargs=7, required=True,
                        metavar=('X', 'Y', 'Z', 'QX', 'QY', 'QZ', 'QW'),
                        help='verified pose of base_footprint in GT model frame')
    parser.add_argument('--extrinsic-evidence', required=True,
                        help='reference proving the supplied rigid transform')
    parser.add_argument('--motion-oracle', type=Path, required=True,
                        help='zero-noise oracle linked against installed Nav2')
    parser.add_argument('--gt-model-frame', required=True)
    parser.add_argument('--base-frame', default='base_footprint')
    parser.add_argument('--max-gap-ms', type=float, default=50)
    args = parser.parse_args()
    if args.max_gap_ms <= 0 or not all(math.isfinite(x) for x in args.gt_to_base):
        parser.error('finite extrinsic and positive interpolation bound required')
    events, gt = read(args.amcl), read(args.gt)
    if not args.extrinsic_evidence.strip():
        parser.error('nonempty extrinsic evidence required')
    if any(r['child'] != args.gt_model_frame for r in gt if r.get('stage') == 'gt'):
        parser.error('GT model frame does not match extrinsic source')
    if any(r['source'] != args.base_frame for r in events if r.get('stage') == 'tf_success'):
        parser.error('TF base frame does not match extrinsic target')
    rows = join(events, gt, args.gt_to_base,
                int(args.max_gap_ms*1e6), args.motion_oracle.resolve())
    with args.output.open('x') as stream:
        json.dump({'schema': 1, 'motion_oracle': str(args.motion_oracle.resolve()),
                   'motion_oracle_sha256': hashlib.sha256(args.motion_oracle.read_bytes()).hexdigest(),
                   'extrinsic': args.gt_to_base,
                   'extrinsic_evidence': args.extrinsic_evidence,
                   'max_gap_ms': args.max_gap_ms,
                   'status': 'OK' if all(r['status'] == 'paired' for r in rows) else 'UNOBSERVABLE',
                   'gt_model_frame': args.gt_model_frame, 'base_frame': args.base_frame,
                   'predictions': rows}, stream,
                  indent=2, allow_nan=False)


if __name__ == '__main__':
    main()
