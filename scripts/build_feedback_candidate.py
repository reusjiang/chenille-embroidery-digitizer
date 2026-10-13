#!/usr/bin/env python3
"""Build hash-bound manual-reference candidates, preserving frozen releases.

This is a same-word reconstruction experiment, not the missing studio generator.
Only reviewed continuous references in configs/feedback-v002.json are accepted.
"""
import argparse
import csv
import hashlib
import html
import json
import platform
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pyembroidery as pe
from scipy.spatial import cKDTree
from generate_dst import at, cumulative, smooth, needle_sample, choose_tie, turnback, snap, write_dst, raw_decode
from generate_dst import plt
from project import ROOT, output_path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def reference_points(path, expected):
    if digest(path) != expected:
        raise ValueError(f'Input checksum changed: {path}')
    rows = np.array(pe.read_dst(str(path), {'trim_at':False, 'clipping':False}).stitches)
    if rows[-1,2] != pe.END or not np.all(rows[:-1,2] == pe.STITCH):
        raise ValueError('This candidate builder only accepts continuous, single-color references')
    return rows[:-1,:2]/10


def sampled_path(points, step):
    parts=[]
    for a,b in zip(points[:-1], points[1:]):
        n=max(1, int(np.ceil(np.linalg.norm(b-a)/step)))
        parts.append(np.linspace(a,b,n+1)[:-1])
    return np.vstack([*parts,points[-1:]])


def centered(points):
    return points-(points.min(axis=0)+points.max(axis=0))/2


def compare(reference, candidate, step=.25):
    a=sampled_path(centered(reference),step)
    b=sampled_path(centered(candidate),step)
    ba=cKDTree(a).query(b)[0]
    ab=cKDTree(b).query(a)[0]
    return {'sampling_step_mm':step,'alignment':'independent bounding-box centers; translation only',
            'candidate_to_reference_p95_mm':float(np.quantile(ba,.95)),
            'reference_to_candidate_p95_mm':float(np.quantile(ab,.95)),
            'bidirectional_p95_max_mm':float(max(np.quantile(ba,.95),np.quantile(ab,.95))),
            'mean_symmetric_mm':float((ba.mean()+ab.mean())/2),
            'scope':'Nearest sampled path distances, not stitch-order or physical quality. Reference used as reconstruction input.'}


def choose_return(path, radius, origin, terminal=False):
    best=choose_tie(path,radius,origin,terminal)
    if best[0] <= .04:
        return best
    # Curved reference entries need a wider approach-length search than v001.
    # Always optimize against quantized coordinates, with the same final origin.
    upper=min(20.,cumulative(path)[-1]-radius)
    for leg in np.linspace(.5,upper,391):
        q=turnback(path,radius,float(leg))
        if terminal:q=q[::-1]
        z=snap(q-(q[0] if origin is None else origin))
        length=float(cumulative(z/10)[-1]);error=abs(length-10)
        if error<best[0]:best=(error,q,length,float(leg))
    return best


def reconstruct(core, width, par):
    if not np.isfinite(width) or not 100<=width<=500 or abs(width*10-round(width*10))>1e-6:
        raise ValueError('Width must be 100–500 mm at DST 0.1 mm resolution')
    if cumulative(core)[-1] <= 2*par['return_length_mm']:
        raise ValueError('Reference core is too short for two reviewed return regions')
    dense, _, cuts = smooth(core)
    factor=width/np.ptp(dense[:,0])
    # choose_tie currently implements exactly 10 mm; reject unsupported config.
    if par['return_length_mm'] != 10:
        raise ValueError('Only the reviewed 10 mm return requirement is implemented')
    for _ in range(12):
        path=dense*factor
        rs,re=par['start_radius_mm'],par['end_radius_mm']
        st=choose_return(path,rs,None)
        origin=st[1][0]
        en=choose_return(path[::-1],re,origin,terminal=True)
        s=cumulative(path)
        middle=np.vstack([at(path,rs),path[(s>rs)&(s<s[-1]-re)],at(path,s[-1]-re)])
        split=[int(np.argmin(np.linalg.norm(middle-core[c]*factor,axis=1))) for c in cuts[1:-1]]
        borders=[0,*split,len(middle)-1]
        if any(b<=a for a,b in zip(borders[:-1],borders[1:])):
            raise ValueError('Reviewed cusp boundaries collapsed')
        mm=[]; segments=[]
        for a,b in zip(borders[:-1],borders[1:]):
            piece=needle_sample(middle[a:b+1],max_step=par['max_step_mm'],
                                error=par['chord_error_mm'],min_step=par['min_sampling_step_mm'])
            quantized=snap(piece-origin)
            first=max(0,len(mm)-1)
            if mm:
                if not np.array_equal(mm[-1],quantized[0]): raise ValueError('Disconnected main pieces')
                mm.extend(quantized[1:])
            else: mm.extend(quantized)
            segments.append([first,len(mm)-1])
        mm=np.array(mm)
        ss=snap(st[1]-origin); ee=snap(en[1]-origin)
        if not np.array_equal(ss[-1],mm[0]) or not np.array_equal(mm[-1],ee[0]):
            raise ValueError('Disconnected return lines')
        pts=np.vstack([ss,mm[1:],ee[1:]])
        actual=np.ptp(pts[:,0])/10
        if round(actual*10) == round(width*10): break
        factor*=width/actual
    else: raise ValueError('Final width calibration did not converge')
    return pts,len(ss)-1,len(ss)+len(mm)-2,factor,origin,cuts,segments,mm


def render(out, name, reference, previous, candidate, se, es):
    fig,axs=plt.subplots(3,1,figsize=(14,9),sharex=True,sharey=True)
    ref=centered(reference)
    for ax,points,title,color in [(axs[0],reference,'Manual reference','#286b84'),
            (axs[1],previous,'Previous centerline draft','#c35468'),
            (axs[2],candidate,'v002 manual-reference candidate','#28664f')]:
        q=centered(points)
        ax.plot(ref[:,0],ref[:,1],color='#bdc9cf',lw=1)
        ax.plot(q[:,0],q[:,1],color=color,lw=1,marker='.',ms=1.3)
        ax.set_title(title,loc='left');ax.set_aspect('equal');ax.grid(alpha=.12);ax.set_ylabel('mm')
    axs[0].invert_yaxis();axs[2].set_xlabel('mm')
    fig.suptitle(name+' / same width / translation only / NOT SEWN')
    fig.tight_layout();fig.savefig(out/'comparison.png',dpi=150);plt.close(fig)
    fig,axs=plt.subplots(1,2,figsize=(12,4.5))
    for ax,a,b,title in [(axs[0],0,se+12,'Start return'),(axs[1],max(0,es-12),len(candidate),'End return')]:
        q=candidate[a:b];ax.plot(q[:,0],q[:,1],'.-',lw=1.3)
        for i,p in enumerate(q):ax.annotate(str(a+i+1),p,fontsize=7,xytext=(3,3),textcoords='offset points')
        ax.set_aspect('equal');ax.invert_yaxis();ax.set_title(title);ax.grid(alpha=.15);ax.set_xlabel('mm')
    fig.tight_layout();fig.savefig(out/'returns.png',dpi=150);plt.close(fig)


def build_case(case, par, out, scheme):
    out.mkdir()
    source=ROOT/case['manual']; old=ROOT/case['previous_draft']
    ref=reference_points(source,case['manual_sha256'])
    previous=reference_points(old,case['previous_draft_sha256'])
    first,last=case['source_core_needles_1based']
    if not 1 <= first < last <= len(ref): raise ValueError('Invalid source core range')
    core=ref[first-1:last]
    pts,se,es,factor,origin,cuts,ranges,mm=reconstruct(core,case['width_mm'],par)
    if np.any(np.all(np.diff(pts,axis=0)==0,axis=1)): raise ValueError('Duplicate adjacent needle positions')
    dstname=f'{case["text"]}_F{case["font"]}_{case["width_mm"]:g}mm_v002.DST'
    dst=out/dstname;write_dst(dst,pts)
    decoded,header=raw_decode(dst)
    second=np.array(pe.read_dst(str(dst),{'trim_at':False,'clipping':False}).stitches)
    assert np.array_equal(decoded,second) and np.array_equal(decoded[:-1,:2],pts)
    p=decoded[:-1,:2]/10;lengths=np.linalg.norm(np.diff(p,axis=0),axis=1)
    returns={'start':float(cumulative(p[:se+1])[-1]),'end':float(cumulative(p[es:])[-1])}
    assert np.ptp(pts[:,0])==round(case['width_mm']*10)
    assert max(abs(x-par['return_length_mm']) for x in returns.values())<=par['return_tolerance_mm']
    assert lengths.max()<=par['max_final_stitch_mm']
    # Dense check of the final quantized main path in the original reference coordinates.
    main_in_source=(mm/10+origin)/factor
    dd=cKDTree(sampled_path(core,.025)).query(sampled_path(main_in_source,.025))[0]
    maxdev=float(dd.max())
    assert maxdev <= par['main_reconstruction_max_deviation_mm'],maxdev
    mapping=[]
    for i,((a,b),(ca,cb)) in enumerate(zip(ranges,zip(cuts[:-1],cuts[1:]))):
        mapping.append({'segment_id':f'{case["id"]}:manual-{first+ca}-{first+cb}',
            'source_needles_1based':[int(first+ca),int(first+cb)],
            'candidate_needles_1based':[se+a+1,se+b+1],
            'boundary_note':'First/last segment starts/ends at the return attachment, slightly inside source core.'})
    # Every internal sharp-reversal anchor is retained after quantization.
    for c,(_,b) in zip(cuts[1:-1],ranges[:-1]):
        assert np.array_equal(mm[b],np.rint((core[c]*factor-origin)*10).astype(int))
    oldmetric=compare(ref,previous,par['comparison_sampling_step_mm'])
    newmetric=compare(ref,p,par['comparison_sampling_step_mm'])
    assert newmetric['bidirectional_p95_max_mm']<oldmetric['bidirectional_p95_max_mm']
    report={'scheme_id':scheme,'case_id':case['id'],'text':case['text'],'font':case['font'],
        'status':'file_verified_pending_wilcom_and_sewout','method':'same_word_manual_reference_reconstruction',
        'dst_file':dstname,'dst_sha256':digest(dst),'source':case,
        'width_mm':float(np.ptp(p[:,0])),'height_mm':float(np.ptp(p[:,1])),
        'stitch_commands':len(p),'jump_commands':0,'source_core_needles_1based':[first,last],
        'source_internal_sharp_reversal_needles_1based':[int(first+c) for c in cuts[1:-1]],
        'return_lengths_mm':returns,'return_needle_ranges_1based':{'start':[1,se+1],'end':[es+1,len(p)]},
        'parameters':par,'uniform_main_scale_factor':float(factor),'origin_in_scaled_source_mm':origin.tolist(),
        'main_reconstruction_in_source_coordinates_mm':{'sample_step_mm':.025,'max':maxdev,'p95':float(np.quantile(dd,.95))},
        'needle_length_mm':{'min_nonzero':float(lengths.min()),'median':float(np.median(lengths)),'max':float(lengths.max())},
        'short_stitches_under_0_5mm':int(sum(lengths<.5)),'initial_zero_displacement_commands':1,
        'comparison':{'previous_draft':oldmetric,'candidate':newmetric},
        'checks':{'dual_decode_identical':True,'strict_header_and_end':True,'planned_coordinates_match':True,
                  'width_matches_reference':True,'both_returns_meet_10mm_tolerance':True,
                  'internal_reversal_anchors_preserved':True,'maximum_needle_length':True,
                  'main_deviation_bound':True,'reference_fit_improved':True},
        'wilcom_checked':False,'machine_tested':False,'native_emb_generated':False,
        'limitations':['Uses the same-word manual reference as input; comparison measures reconstruction fit, not unseen-word generalization.',
                      'Only these continuous single-color cases; no jump handling or general text generation.',
                      'Reference stitch order retained but not proven machine-accepted.',
                      'Return radii are inherited software design values, not machine-calibrated parameters.',
                      'Short stitches near returns require Wilcom review and physical sew-out.',
                      'No machine-specific chain/moss mode commands or native EMB objects.']}
    save_json(out/'validation.json',report)
    save_json(out/'segments.json',mapping)
    with (out/'stitches.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.writer(f);w.writerow(['needle','x_mm','y_mm','command','phase'])
        for i,row in enumerate(decoded):
            phase='end' if row[2]==pe.END else 'start_return' if i<=se else 'end_return' if i>=es else 'main'
            w.writerow([i+1,row[0]/10,row[1]/10,'END' if row[2]==pe.END else 'STITCH',phase])
    data={'points':p.tolist(),'reference':centered(ref).tolist(),'previous':centered(previous).tolist(),'report':report}
    save_json(out/'replay-data.json',data)
    template=(ROOT/'scripts/templates/candidate-replay.html').read_text(encoding='utf-8')
    (out/'replay.html').write_text(template.replace('__DATA__',json.dumps(data,ensure_ascii=False).replace('<','\\u003c')),encoding='utf-8')
    render(out,f'{case["text"]} / Font{case["font"]}',ref,previous,p,se,es)
    (out/'README.md').write_text(f'''# {case['text']} / Font{case['font']} / v002 候选

状态：文件验证通过；尚需 Wilcom 检查及实机试绣。\n
方案 `{scheme}`，输入样本 `{case['id']}`。采用同词人工笔顺重建。人工参考同时用于生成与对比，几何接近不代表泛化能力或实物合格。

- [下载候选 DST]({dstname})，SHA256：`{report['dst_sha256']}`。
- [逐针回放](replay.html)、[三方对照图](comparison.png)、[起收放大图](returns.png)。
- 实际针迹尺寸：{report['width_mm']:.1f} × {report['height_mm']:.1f} mm；落针 {len(p)}，跳针 0。
- 起/收回线：{returns['start']:.4f} / {returns['end']:.4f} mm；小于 0.5 mm 的非零针距 {report['short_stitches_under_0_5mm']} 个。
- 双向 P95 较大值（统一方法重算）：旧候选 {oldmetric['bidirectional_p95_max_mm']:.3f} mm，新候选 {newmetric['bidirectional_p95_max_mm']:.3f} mm。
- 人工主路保留范围：原第 {first}–{last} 针。原起收段替换为新回线；内部回走和尖转保留，主路有均匀尺寸校准及重新采样。

请在 Wilcom 中核对方向、尺寸、短针、起收牢固方式及实际设备模式，再按上级操作说明试绣。若另存或机器端变换，记录实际文件和操作。
反馈填写本目录中的 `trial-record.json`，绑定本文件 SHA256。不要把其他版本照片归入本候选。
''',encoding='utf-8')
    trial={'schema_version':1,'trial_id':None,'design_version':f'{scheme}/{case["id"]}',
           'generated_dst':dstname,'generated_dst_sha256':report['dst_sha256'],
           'actual_sewn_dst_sha256':None,'status':'not_run','date':None,'operator':None,
           'machine':{'id':None,'attachment_or_mode':None,'speed':None,'tension':None},
           'materials':{'fabric':None,'stabilizer':None,'yarn':None,'needle':None,'hooping':None},
           'wilcom_check':{'completed':None,'saved_after_import':None},
           'machine_transform':{'scale':None,'rotation_deg':None,'mirror':None},
           'result':{'completed':None,'thread_break_count':None,'unplanned_stop_count':None,'accepted_by_operator':None},
           'defects':[],'photos':[],'repeat_index':None,
           'notes':'复制后填写。未知保持 null。新回线与短针需重点观察。'}
    save_json(out/'trial-record.json',trial)
    return report


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--config',default='configs/feedback-v002.json')
    ap.add_argument('--output',default='build/feedback-v002')
    args=ap.parse_args()
    config_path=ROOT/args.config;cfg=json.loads(config_path.read_text(encoding='utf-8'))
    out=output_path(args.output)
    if any(out.iterdir()): raise ValueError('Candidate output must be empty; choose a new build directory')
    reports=[build_case(c,cfg['parameters'],out/c['id'],cfg['scheme_id']) for c in cfg['cases']]
    save_json(out/'summary.json',{'scheme_id':cfg['scheme_id'],'status':cfg['status'],'cases':reports})
    save_json(out/'build-info.json',{'python':platform.python_version(),
        'packages':{k:version(k) for k in ['numpy','scipy','matplotlib','pillow','pyembroidery']},
        'config_sha256':digest(config_path),
        'source_files_sha256':{str(p.relative_to(ROOT)):digest(p) for p in [Path(__file__),ROOT/'scripts/generate_dst.py',ROOT/'scripts/project.py',ROOT/'scripts/templates/candidate-replay.html']}})
    save_json(out/'config.json',cfg)
    print(json.dumps([{'id':r['case_id'],'size':[r['width_mm'],r['height_mm']],'stitches':r['stitch_commands'],
        'returns':r['return_lengths_mm'],'short':r['short_stitches_under_0_5mm'],'comparison':r['comparison']} for r in reports],ensure_ascii=False,indent=2))


if __name__=='__main__': main()
