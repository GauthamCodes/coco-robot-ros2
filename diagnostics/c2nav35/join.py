#!/usr/bin/env python3
"""Offline exact-input/GT join. No ROS imports, runtime, or forward filling."""
import argparse
import bisect
import json
import math
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
        rows = [json.loads(line) for line in stream]
    if not rows or rows[0].get('stage') != 'manifest':
        raise ValueError('missing manifest')
    if rows[-1].get('stage') != 'footer':
        raise ValueError('missing footer: capture incomplete')
    if rows[-1]['dropped'] or rows[-1]['write_failed']:
        raise ValueError('capture reports loss/write failure')
    if any(row.get('schema') != 1 for row in rows):
        raise ValueError('unknown schema')
    scans = [r['scan_id'] for r in rows if r.get('stage') == 'scan']
    if len(set(scans)) != len(scans):
        raise ValueError('duplicate scan identity: require one AMCL instance per process')
    return rows


def gt_at(rows, stamp, epoch, max_gap_ns, extrinsic):
    samples = [r for r in rows if r.get('stage') == 'gt' and r['epoch'] == epoch]
    samples.sort(key=lambda r: r['stamp_ns'])
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


def join(events, gt, extrinsic, max_gap_ns):
    poses = {(r['epoch'], r['scan_id']): r for r in events
             if r.get('stage') == 'tf_success'}
    frames = {(r['frame'], r['child']) for r in gt if r.get('stage') == 'gt'}
    if len(frames) != 1:
        raise ValueError('GT absent or frames changed')
    decompositions = {r['prediction_id']: r for r in events
                      if r.get('stage') == 'motion_decomposition'}
    ends = {r['prediction_id'] for r in events if r.get('stage') == 'prediction_end'}
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
            anchor = poses.get((r['epoch'], r['anchor_id']))
            if anchor is None or anchor['scan_ns'] != r['anchor_ns']:
                raise ValueError('anchor missing or crosses epoch')
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
            current_gt, ids, gap = gt_at(gt, r['scan_ns'], r['epoch'], max_gap_ns, extrinsic)
            anchor_gt, aids, agap = gt_at(gt, r['anchor_ns'], r['epoch'], max_gap_ns, extrinsic)
            odom_delta = relative(r['anchor'], r['pose'])
            gt_delta = relative(anchor_gt, current_gt)
            residual = [a-b for a, b in zip(odom_delta, gt_delta)]
            residual[2] = math.atan2(math.sin(residual[2]), math.cos(residual[2]))
            row.update(status='paired', motion=decompositions[identity]['motion'],
                       gt_pose=current_gt, gt_anchor=anchor_gt,
                       gt_sample_ids=ids, gt_anchor_sample_ids=aids,
                       gt_gap_ns=gap, gt_anchor_gap_ns=agap,
                       odom_body_delta=odom_delta, gt_body_delta=gt_delta,
                       residual=residual)
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
    parser.add_argument('--max-gap-ms', type=float, default=50)
    args = parser.parse_args()
    if args.max_gap_ms <= 0 or not all(math.isfinite(x) for x in args.gt_to_base):
        parser.error('finite extrinsic and positive interpolation bound required')
    rows = join(read(args.amcl), read(args.gt), args.gt_to_base,
                int(args.max_gap_ms*1e6))
    with args.output.open('x') as stream:
        json.dump({'schema': 1, 'extrinsic': args.gt_to_base,
                   'extrinsic_evidence': args.extrinsic_evidence,
                   'max_gap_ms': args.max_gap_ms, 'predictions': rows}, stream,
                  indent=2, allow_nan=False)


if __name__ == '__main__':
    main()
