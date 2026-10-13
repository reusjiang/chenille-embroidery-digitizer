#!/usr/bin/env python3
"""Audit a 50-case needle-path comparison batch; never modify the source batch.

Usage: python audit_feedback.py --source PATH --output PATH
Python standard library only. P95 distances are source-reported, not recomputed.
"""
import argparse
import hashlib
import json
import math
import statistics
from collections import Counter
from pathlib import Path
import xml.etree.ElementTree as ET
from zipfile import ZipFile


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def decode(path):
    data = path.read_bytes()
    assert len(data) >= 515, path
    x = y = 0
    rows = []
    trailing = None
    for off in range(512, len(data)-2, 3):
        a, b, c = data[off:off+3]
        assert c & 3 == 3, (path, off)
        if c & 0xf3 == 0xf3:
            assert (a, b, c) == (0, 0, 0xf3), path
            rows.append([x, y, 4])
            trailing = len(data)-off-3
            break
        dx = ((a&1)>0)-((a&2)>0) + 9*(((a&4)>0)-((a&8)>0))
        dx += 3*(((b&1)>0)-((b&2)>0)) + 27*(((b&4)>0)-((b&8)>0))
        dx += 81*(((c&4)>0)-((c&8)>0))
        dy = ((a&128)>0)-((a&64)>0) + 9*(((a&32)>0)-((a&16)>0))
        dy += 3*(((b&128)>0)-((b&64)>0)) + 27*(((b&32)>0)-((b&16)>0))
        dy += 81*(((c&32)>0)-((c&16)>0))
        x += dx
        y -= dy
        cmd = 5 if c & 0xc0 == 0xc0 else 6 if c & 0x40 else 1 if c & 0x80 else 0
        rows.append([x, y, cmd])
    assert trailing is not None, ('missing END', path)
    stitches = [r for r in rows if r[2] == 0]
    lengths = []
    prev = [0, 0, 0]
    for row in rows:
        if row[2] == 0:
            lengths.append(math.hypot(row[0]-prev[0], row[1]-prev[1])/10)
        prev = row
    nonzero = [x for x in lengths if x > 0]
    stats = dict(
        width_mm=(max(r[0] for r in stitches)-min(r[0] for r in stitches))/10,
        height_mm=(max(r[1] for r in stitches)-min(r[1] for r in stitches))/10,
        stitches=len(stitches), jump_commands=sum(r[2] == 1 for r in rows),
        jump_runs=sum(r[2] == 1 and (i == 0 or rows[i-1][2] != 1) for i, r in enumerate(rows)),
        color_changes=sum(r[2] == 5 for r in rows), sequin_commands=sum(r[2] == 6 for r in rows),
        zero_stitches=lengths.count(0), needle_min_mm=round(min(nonzero), 3),
        needle_median_mm=round(statistics.median(nonzero), 3), needle_max_mm=round(max(nonzero), 3),
        nonzero_stitches_under_0_5mm=sum(0 < x < .5 for x in lengths),
        stitches_over_requested_2_5mm=sum(x > 2.5+1e-9 for x in lengths),
        final_end=True, trailing_padding_bytes=trailing)
    return rows, stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    source, out = args.source.resolve(), args.output.resolve()
    assert source != out and source not in out.parents, 'Output must be outside raw batch'
    files = sorted(source.glob('*/feedback.json'))
    records = [read(f) for f in files]
    assert len(records) == 50 and len({r['id'] for r in records}) == 50
    manifest = read(source/'manifest.json')
    mismatches = [n for n, h in manifest.items() if not (source/n).is_file() or sha(source/n) != h]
    assert not mismatches, mismatches
    checks, normalized, issues = [], [], []
    for file, r in zip(files, records):
        folder = file.parent
        paths = read(folder/'paths.json')
        generated = list((folder/'generated').glob('*.DST'))
        assert len(generated) == 1
        dst_stats = {}
        for kind, dst in [('reference', folder/'manual.DST'), ('generated', generated[0])]:
            assert sha(dst) == r[kind]['sha256'], (r['id'], kind, 'hash')
            decoded, stats = decode(dst)
            assert decoded == paths['manual' if kind == 'reference' else 'generated'], (r['id'], kind, 'coordinates')
            for key, val in stats.items():
                if key in r[kind]:
                    assert val == r[kind][key], (r['id'], kind, key, val, r[kind][key])
            dst_stats[kind] = stats
        for emb in r['emb_references']:
            assert sha(folder/emb['file']) == emb['sha256']
        assert read(folder/'metrics.json') == r['metrics']
        record = read(folder/'record.json')
        assert all(r[k] == v for k, v in record.items())
        validation = read(folder/'generated/validation.json')
        assert all(r['generated'][k] == v for k, v in validation.items())
        h = 100*(r['generated']['height_mm']/r['reference']['height_mm']-1)
        assert round(h, 1) == r['height_delta_pct']
        row = {
            'id': r['id'], 'text': r['text'], 'font': r['font'],
            'evidence_type': 'digital_path_comparison', 'machine_tested': r['machine_tested'],
            'wilcom_checked': r['wilcom_checked'], 'operator_acceptance': None,
            'actual_thread_break_count': None, 'actual_unplanned_stop_count': None,
            'source_feedback': f'../../inbox/{source.name}/{r["id"]}/feedback.json',
            'reference_sha256': r['reference']['sha256'], 'generated_sha256': r['generated']['sha256'],
            'reference': dst_stats['reference'], 'generated': dst_stats['generated'],
            'height_delta_pct_unrounded': h,
            'height_change_over_5pct': abs(h) > 5,
            'jump_run_delta': r['generated']['jump_runs']-r['reference']['jump_runs'],
            'source_reported_metrics': r['metrics'],
            'bidirectional_p95_max_mm': max(r['metrics']['p95_generated_to_reference_mm'], r['metrics']['p95_reference_to_generated_mm']),
            'source_ai_visual_severity': r['visual_severity'],
            'source_ai_stiffness_note': r['stiffness_note'], 'source_ai_suggestion': r['suggestion'],
            'tie_in_out': r['generated']['tie_in_out'], 'native_emb_generated': r['generated']['native_emb_generated'],
        }
        normalized.append(row)
        for item in r['issues']:
            issues.append({'id': r['id'], 'text': r['text'], 'font': r['font'], **item,
                           'review_status': 'source_ai_assessment_pending_operator_review'})
        checks.append({'id': r['id'], 'dst_hashes_verified': 2, 'emb_hashes_verified': len(r['emb_references']),
                       'independent_dst_decode_matches_paths_json': True, 'source_metrics_copies_match': True})
    assert read(source/'feedback-records.json') == records
    original_issues = [{k:v for k,v in x.items() if k != 'review_status'} for x in issues]
    assert read(source/'issue-rows.json') == original_issues
    assert read(source/'records.json') == [read(f.parent/'record.json') for f in files]
    def group(items):
        p95 = [r['bidirectional_p95_max_mm'] for r in items]
        h = [r['height_delta_pct_unrounded'] for r in items]
        return {'samples':len(items), 'height_change_over_5pct':sum(abs(x)>5 for x in h),
                'height_change_over_10pct':sum(abs(x)>10 for x in h),
                'height_delta_pct_median':statistics.median(h),
                'height_delta_pct_min':min(h), 'height_delta_pct_max':max(h),
                'bidirectional_p95_max_mm_median':statistics.median(p95),
                'bidirectional_p95_max_mm_max':max(p95),
                'jump_runs_changed':sum(r['jump_run_delta'] != 0 for r in items),
                'jump_runs_reduced':sum(r['jump_run_delta'] < 0 for r in items),
                'source_ai_visual_severity_3':sum(r['source_ai_visual_severity']==3 for r in items)}
    # Read original workbook without writing it, including all user-review cells.
    ns = {'x':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    with ZipFile(source/'反馈汇总.xlsx') as z:
        strings=[]
        if 'xl/sharedStrings.xml' in z.namelist():
            strings=[''.join(s.itertext()) for s in ET.fromstring(z.read('xl/sharedStrings.xml'))]
        def cell_value(c):
            if c.get('t') == 'inlineStr': return ''.join(c.find('x:is',ns).itertext())
            v=c.find('x:v',ns)
            if v is None: return None
            return strings[int(v.text)] if c.get('t') == 's' else v.text
        xml=ET.fromstring(z.read('xl/worksheets/sheet1.xml'))
        reviews={c.get('r'):cell_value(c) for c in xml.findall('.//x:c',ns)
                 if c.get('r').startswith('H') and 6<=int(c.get('r')[1:])<=55}
        assert len(reviews)==50
        xlsx_errors=[]
        for name in z.namelist():
            if name.startswith('xl/worksheets/sheet') and name.endswith('.xml'):
                tree=ET.fromstring(z.read(name))
                xlsx_errors += [(name,c.get('r'),cell_value(c)) for c in tree.findall('.//x:c',ns) if c.get('t')=='e']
    summary={'schema_version':1, 'review_date':'2026-10-13',
             'batch_generation_date':sorted({r['generated']['generated_at'][:10] for r in records}),
             'evidence_type':'digital_path_comparison', 'machine_trials':sum(r['machine_tested'] is True for r in records),
             'wilcom_checks':sum(r['wilcom_checked'] is True for r in records),
             'missing_ties':sum(r['tie_in_out']=='not_added_requires_digitizer' for r in normalized),
             'native_emb_generated':sum(r['native_emb_generated'] for r in normalized),
             'source_issue_counts':dict(Counter(x['code'] for x in issues)),
             'all':group(normalized), 'fonts':{str(f):group([r for r in normalized if r['font']==f]) for f in [1,2,3]},
             'metric_note':'P95 is source-reported nearest sampled-path distance; max of two directions, not stitch-order or physical error.',
             'source_user_review_counts':dict(Counter(reviews.values()))}
    common_words=sorted(set.intersection(*[{r['text'] for r in normalized if r['font']==f} for f in [1,2,3]]))
    summary['matched_word_comparison']={'words':common_words,
        'fonts':{str(f):group([r for r in normalized if r['font']==f and r['text'] in common_words]) for f in [1,2,3]}}
    summary['stitch_length_diagnostics']={kind:{
        'nonzero_under_0_5mm_total':sum(r[kind]['nonzero_stitches_under_0_5mm'] for r in normalized),
        'samples_with_nonzero_under_0_5mm':sum(r[kind]['nonzero_stitches_under_0_5mm']>0 for r in normalized),
        'maximum_stitch_mm':max(r[kind]['needle_max_mm'] for r in normalized),
        'samples_with_stitches_over_2_5mm':sum(r[kind]['stitches_over_requested_2_5mm']>0 for r in normalized)
    } for kind in ['reference','generated']}
    source_summary=read(source/'summary.json')
    for key in ['machine_trials','missing_ties','native_emb_generated']:
        assert summary[key]==source_summary[key]
    assert summary['all']['height_change_over_5pct']==source_summary['height_change_over_5pct']
    audit={'review_date':'2026-10-13','manifest_entries':len(manifest),'manifest_mismatches':mismatches,
           'source_manifest_sha256':sha(source/'manifest.json'), 'source_workbook_sha256':sha(source/'反馈汇总.xlsx'),
           'individual_records_match_aggregate':True, 'original_records_match_aggregate':True,
           'issue_rows_match_aggregate':True,'xlsx_user_review_cells':reviews,'xlsx_stored_error_cells':xlsx_errors,
           'xlsx_recalculated':False,'metrics_recomputed_from_geometry':False,
           'unlisted_files':sorted(str(f.relative_to(source)) for f in source.rglob('*') if f.is_file() and str(f.relative_to(source)) not in manifest),
           'source_core_code_available_in_this_repo':False,
           'checks':checks,
           'limitations':['Original Windows ZIP unavailable; hashes checked against supplied manifest and per-case provenance, not the archive itself.',
                          'Core studio source is absent in this repository; cannot confirm geometry root cause from source code.',
                          'No machine sew-out, Wilcom inspection or operator acceptance evidence in this batch.']}
    out.mkdir(parents=True,exist_ok=True)
    for name,obj in [('summary.json',summary),('records.json',normalized),('issues.json',issues),('audit.json',audit)]:
        (out/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    lines=['# 50 份针路对照明细','', '整理日期：2026-10-13。每行是一款数字针路对照，不是一轮实机试绣。',
           'P95 列为两个方向各自 P95 的较大值；高度变化按未舍入尺寸计算。视觉程度保留原 AI 意见，待操作方复核。',
           '原始图表链接仅在保留本地 inbox 目录时可用；该目录不随 Git 发布。','',
           '| 样本 | 高度变化 | 双向 P95 较大值 mm | 空移段 人工/候选 | 原视觉程度 | 优先核查部位 |',
           '|---|---:|---:|---:|---:|---|']
    for r in normalized:
        link=r['source_feedback'].replace('/feedback.json','/feedback.html')
        lines.append(f'| [{r["id"]}]({link}) | {r["height_delta_pct_unrounded"]:+.1f}% | {r["bidirectional_p95_max_mm"]:.3f} | {r["reference"]["jump_runs"]}/{r["generated"]["jump_runs"]} | {r["source_ai_visual_severity"]} | {r["source_ai_suggestion"]} |')
    (out/'cases.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'summary':summary,'audit_manifest_entries':len(manifest),'decoded_dst_files':len(checks)*2,
                      'xlsx_reviews':dict(Counter(reviews.values()))},ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
