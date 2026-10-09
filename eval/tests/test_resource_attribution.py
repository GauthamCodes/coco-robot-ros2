import json
from unittest.mock import patch
from resource_attribution import process_memory, summarize


def test_pss_and_pid_reuse(tmp_path):
    d=tmp_path/'10';d.mkdir();(d/'smaps_rollup').write_text('Pss: 40 kB\nPrivate_Clean: 10 kB\nPrivate_Dirty: 5 kB\nSwapPss: 2 kB\n')
    with patch('resource_attribution.identity',return_value={'start_ticks':2}):
        r=process_memory(10,2,tmp_path);assert r['pss_bytes']==40960;assert r['private_bytes']==15360
    with patch('resource_attribution.identity',side_effect=[{'start_ticks':2},{'start_ticks':3}]):
        assert process_memory(10,2,tmp_path)['pss_bytes'] is None
    assert process_memory(10,2,tmp_path)['pss_bytes'] is None


def test_duplicate_identity_not_double_counted_and_old_rss_not_pss(tmp_path):
    (tmp_path/'manifest.json').write_text('{}')
    p=dict(pid=10,start_ticks=2,component='simulator',rss_bytes=100)
    (tmp_path/'host_metrics.jsonl').write_text(json.dumps(dict(owned_components=[p,p]))+'\n')
    r=summarize(tmp_path);assert r['component_peaks']['simulator']['rss_bytes']==100
    assert r['component_peaks']['simulator']['pss_bytes'] is None;assert r['errors']
