#!/usr/bin/env python3
"""Verified same-word pilot. Rebuild curves from manual needle order, not a bitmap skeleton.
All distances are mm; DST record coordinates are integer 0.1 mm, y down in Python.
"""
from pathlib import Path
import argparse, csv, json, math, os, tempfile, hashlib
os.environ.setdefault('MPLCONFIGDIR', str(Path(tempfile.gettempdir()) / 'chenille-mpl'))
import numpy as np
from scipy.interpolate import CubicSpline
from scipy.spatial import cKDTree
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pyembroidery as pe
from pyembroidery.DstWriter import encode_record

from project import ROOT, DEFAULT_OUTPUT, SOURCE, SOURCE_SHA256, output_path


def cumulative(p):
    return np.r_[0., np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]


def at(p,s):
    a=cumulative(p)
    return np.column_stack([np.interp(np.atleast_1d(s),a,p[:,i]) for i in range(2)])


def smooth(p):
    """Split at verified sharp reversals; interpolate each smooth portion separately."""
    p=p[np.r_[True,np.linalg.norm(np.diff(p,axis=0),axis=1)>1e-8]]
    v=np.diff(p,axis=0);n=np.linalg.norm(v,axis=1)
    cos=(v[:-1]*v[1:]).sum(1)/(n[:-1]*n[1:])
    cuts=[0,*list(np.where(cos<-.4)[0]+1),len(p)-1]
    result=[];anchors=[]
    for a,b in zip(cuts[:-1],cuts[1:]):
        q=p[a:b+1];s=cumulative(q)
        t=np.linspace(0,s[-1],max(2,math.ceil(s[-1]/.06)))
        z=CubicSpline(s,q,bc_type='natural')(t) if len(q)>2 else at(q,t)
        if result:z=z[1:]
        result.extend(z);anchors.append(len(result)-1)
    return np.array(result),anchors,cuts


def needle_sample(p,max_step=2.45,error=.045,min_step=.35):
    """Bound chord deviation and length, while preserving all deliberate cusp endpoints."""
    s=cumulative(p);out=[p[0]];i=0
    while i<len(p)-1:
        j=min(np.searchsorted(s,s[i]+max_step),len(p)-1)
        while j>i+1:
            a=p[j]-p[i];n=np.linalg.norm(a)
            if n<1e-8: deviation=np.linalg.norm(p[i:j+1]-p[i],axis=1).max()
            else:
                proj=np.clip(((p[i:j+1]-p[i])@a)/(n*n),0,1)
                deviation=np.linalg.norm(p[i:j+1]-p[i]-proj[:,None]*a,axis=1).max()
            if deviation<=error or s[j]-s[i]<=min_step:break
            j-=1
        out.append(p[j]);i=j
    return np.array(out)


def turnback(p,r,leg):
    """Approach on a parallel return leg, semicircle into main path at arc-length r.
    Total return line includes approach plus semicircle; terminal uses reversed path.
    """
    q=at(p,r)[0];t=at(p,r+.02)[0]-at(p,max(0,r-.02))[0];t/=np.linalg.norm(t)
    normal=np.array([-t[1],t[0]])
    ss=np.linspace(r+leg,r,max(20,int(leg/.04)))
    pts=at(p,ss)
    tang=at(p,ss+.015)-at(p,np.maximum(0,ss-.015));tang/=np.linalg.norm(tang,axis=1)[:,None]
    ns=np.column_stack([-tang[:,1],tang[:,0]])
    offset=pts+2*r*ns
    theta=np.linspace(0,np.pi,5 if r>=.3 else 4)
    arc=q+r*normal+r*(np.cos(theta)[:,None]*normal-np.sin(theta)[:,None]*t)
    # Tangent at the attachment follows -t then +t; offset curve remains local.
    approach=needle_sample(offset,max_step=1.8,error=.028,min_step=.24)
    if len(approach)>2 and np.linalg.norm(approach[-1]-approach[-2])<.35:
        approach=np.delete(approach,-2,axis=0)
    return np.vstack([approach,arc[1:]])


def snap(p):
    q=np.rint(p*10).astype(int)
    return q[np.r_[True,np.any(np.diff(q,axis=0)!=0,axis=1)]]


def choose_tie(p,r,origin,terminal=False):
    # Search the short approach length against final quantized stitch arc-length.
    best=None
    for leg in np.linspace(10-np.pi*r-.35,10-np.pi*r+.35,281):
        q=turnback(p,r,float(leg))
        if terminal:q=q[::-1]
        z=snap(q-(q[0] if origin is None else origin));length=float(cumulative(z/10)[-1]);err=abs(length-10)
        if best is None or err<best[0]:best=(err,q,length,float(leg))
    return best


def raw_decode(path):
    """Independent table-driven DST decoder, without pyembroidery reader helpers."""
    data=Path(path).read_bytes();assert len(data)>=515 and (len(data)-512)%3==0
    header={x[:2]:x[3:].strip() for x in data[:512].decode('ascii').split('\r') if len(x)>3 and x[2]==':'}
    weights=[(0,0,1,1),(1,0,1,3),(0,2,3,9),(1,2,3,27),(2,2,3,81)]
    yweights=[(0,7,6,1),(1,7,6,3),(0,5,4,9),(1,5,4,27),(2,5,4,81)]
    x=y=0;rows=[];ended=False
    for off in range(512,len(data),3):
        b=data[off:off+3];assert b[2]&3==3,'invalid marker bits'
        if b[2]&0xf3==0xf3:
            assert b==b'\x00\x00\xf3' and off==len(data)-3
            rows.append([x,y,4]);ended=True;break
        assert not b[2]&0x40,'Unexpected color/sequin command'
        dx=sum((((b[k]>>plus)&1)-((b[k]>>minus)&1))*w for k,plus,minus,w in weights)
        dy=-sum((((b[k]>>plus)&1)-((b[k]>>minus)&1))*w for k,plus,minus,w in yweights)
        x+=dx;y+=dy;rows.append([x,y,1 if b[2]&128 else 0])
    assert ended,'Missing END'
    a=np.array(rows);machine=np.column_stack([a[:,0],-a[:,1]])
    assert int(header['ST'])==len(rows)
    assert int(header['CO'])==0
    for key,val in [('+X',machine[:,0].max()),('-X',-machine[:,0].min()),('+Y',machine[:,1].max()),('-Y',-machine[:,1].min())]:
        assert int(header[key])==max(0,int(val)),(key,val,header[key])
    assert int(header['AX'])==x and int(header['AY'])==-y
    return a,header


def write_dst(path,points):
    m=np.column_stack([points[:,0],-points[:,1]])
    h=f'LA:{path.stem[:16]:<16}\rST:{len(points)+1:7}\rCO:  0\r'
    for key,val in [('+X',m[:,0].max()),('-X',-m[:,0].min()),('+Y',m[:,1].max()),('-Y',-m[:,1].min())]:h+=f'{key}:{max(0,int(val)):5}\r'
    h+=f'AX:{int(m[-1,0]):+6}\rAY:{int(m[-1,1]):+6}\rMX:+    0\rMY:+    0\rPD:******\r'
    header=(h.encode('ascii')+b'\x1a').ljust(512,b' ');assert len(header)==512
    body=[];prev=np.zeros(2,dtype=int)
    for pt in points:
        delta=pt-prev;assert np.abs(delta).max()<=121
        body.append(encode_record(int(delta[0]),int(delta[1]),pe.STITCH));prev=pt
    path.write_bytes(header+b''.join(body)+encode_record(0,0,pe.END))


def render(points,start_end,end_start,out,source):
    q=points/10
    def draw(ax,p,detail=False):
        ax.plot(p[:,0],p[:,1],color='#204963',lw=1.05,marker='.',ms=2.3 if detail else 1.5)
        ax.set_aspect('equal');ax.invert_yaxis();ax.grid(alpha=.15);ax.set_xlabel('mm');ax.set_ylabel('mm')
    fig,ax=plt.subplots(figsize=(15,5));draw(ax,q)
    ax.plot(q[:start_end+1,0],q[:start_end+1,1],color='#cf7523',lw=2)
    ax.plot(q[end_start:,0],q[end_start:,1],color='#ad3c6e',lw=2)
    ax.scatter(*q[0],s=35,c='#cf7523',zorder=4);ax.scatter(*q[-1],s=35,c='#ad3c6e',zorder=4)
    ax.set_title(f'Bulldogs / Font2 / decoded DST / {np.ptp(q[:,0]):g} mm',loc='left',pad=14)
    fig.tight_layout();fig.savefig(out/'preview.png',dpi=180);plt.close(fig)
    fig,axs=plt.subplots(2,2,figsize=(13,8))
    for ax,sl,title in [(axs[0,0],slice(0,start_end+10),'Start: 10 mm return + rounded turn'),(axs[0,1],slice(end_start-10,None),'End: rounded turn + 10 mm return')]:
        p=q[sl];draw(ax,p,True);ax.set_title(title)
        base=sl.start or 0
        for i,pt in enumerate(p):ax.annotate(str(base+i+1),pt,fontsize=7,xytext=(3,3),textcoords='offset points')
    for ax,xrange,title in [(axs[1,0],(15,60),'B loops: original traversal order'),(axs[1,1],(215,280),'d / o / g: crossings and retracing')]:
        draw(ax,q,True);ax.set_xlim(*xrange)
        selected=q[(q[:,0]>xrange[0])&(q[:,0]<xrange[1])];ax.set_ylim(selected[:,1].max()+3,selected[:,1].min()-3);ax.set_title(title)
    fig.tight_layout();fig.savefig(out/'details.png',dpi=180);plt.close(fig)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--width',type=float,default=330);ap.add_argument('--output',default=DEFAULT_OUTPUT);args=ap.parse_args()
    assert 100<=args.width<=500
    out=output_path(args.output)
    source=SOURCE
    if hashlib.sha256(source.read_bytes()).hexdigest() != SOURCE_SHA256:
        raise ValueError('Source DST differs from the reviewed pilot; do not apply fixed needle ranges.')
    sample=np.array(pe.read_dst(str(source),{'trim_at':False,'clipping':False}).stitches)
    assert np.all(sample[:-1,2]==0),'Pilot accepts this verified continuous sample only'
    original=sample[:-1,:2]/10
    # Verified original needle indices, zero based: first turnaround 5; final tip 801.
    core=original[5:802]
    dense,anchors,cuts=smooth(core)
    base=dense.copy();factor=args.width/np.ptp(base[:,0]);rs,re=.35,.25
    for calibration in range(8):
        dense=base*factor;mainlength=cumulative(dense)[-1]
        st=choose_tie(dense,rs,None);origin=st[1][0]
        en=choose_tie(dense[::-1],re,origin,terminal=True)
        s=cumulative(dense)
        middle=np.vstack([at(dense,rs),dense[(s>rs)&(s<mainlength-re)],at(dense,mainlength-re)])
        split=[]
        for c in cuts[1:-1]:
            pt=core[c]*factor;split.append(int(np.argmin(np.linalg.norm(middle-pt,axis=1))))
        pieces=[]
        for a,b in zip([0,*split],[*split,len(middle)-1]):
            z=needle_sample(middle[a:b+1]);pieces.extend(z if not pieces else z[1:])
        ss=snap(st[1]-origin);mm=snap(np.array(pieces)-origin);ee=snap(en[1]-origin)
        assert np.array_equal(ss[-1],mm[0]) and np.array_equal(mm[-1],ee[0])
        pts=np.vstack([ss,mm[1:],ee[1:]])
        width=np.ptp(pts[:,0])/10
        if abs(width-args.width)<.001:break
        factor*=args.width/width
    assert np.ptp(pts[:,0])==round(args.width*10)
    assert not np.any(np.all(np.diff(pts,axis=0)==0,axis=1))
    se=len(ss)-1;es=len(ss)+len(mm)-2
    file=out/f'Bulldogs_F2_{args.width:g}mm.DST';write_dst(file,pts)
    a,header=raw_decode(file)
    b=np.array(pe.read_dst(str(file),{'trim_at':False,'clipping':False}).stitches)
    assert np.array_equal(a,b),'Independent decoders differ'
    assert np.array_equal(a[:-1,:2],pts),'Encoding changed planned coordinates'
    stitches=a[a[:,2]==0,:2];lengths=np.linalg.norm(np.diff(stitches,axis=0),axis=1)/10
    startlen=float(cumulative(stitches[:se+1]/10)[-1]);endlen=float(cumulative(stitches[es:]/10)[-1])
    assert abs(startlen-10)<.05 and abs(endlen-10)<.05,(startlen,endlen)
    assert lengths.max()<=2.7 and lengths.min()>=.1
    # Change is measured against original manual segments, excluding deliberate new tie offsets.
    main_unshifted=np.array(pieces)/factor
    srcdense=np.vstack([np.linspace(a,b,max(2,int(np.linalg.norm(b-a)/.04))) for a,b in zip(core[:-1],core[1:])])
    deviation=cKDTree(srcdense).query(main_unshifted)[0]
    report={'case':'Bulldogs','case_id':'bulldogs-font2','font':'Font2 / Loverine','source_sample':str(source.relative_to(ROOT)),
      'method':'same-word manual-path reuse with piecewise cubic reconstruction; not general automatic digitization',
      'width_mm':float(np.ptp(stitches[:,0])/10),'height_mm':float(np.ptp(stitches[:,1])/10),'stitch_commands':len(stitches),'jump_commands':int(sum(a[:,2]==1)),'jump_runs':0,
      'start_mm':(stitches[0]/10).tolist(),'end_mm':(stitches[-1]/10).tolist(),'bbox_mm':[(stitches.min(0)/10).tolist(),(stitches.max(0)/10).tolist()],
      'return_lengths_mm':{'start':startlen,'end':endlen},'return_needle_ranges_1based':{'start':[1,se+1],'end':[es+1,len(stitches)]},
      'turn_radius_design_mm':{'start':rs,'end':re},'needle_length_mm':{'min_nonzero':float(lengths.min()),'median':float(np.median(lengths)),'max':float(lengths.max())},
      'short_stitches_under_0_5mm':int(sum(lengths<.5)),
      'source_return_lengths_mm':{'start':float(cumulative(original[:6])[-1]),'end_before_micro_lock':float(cumulative(original[801:806])[-1])},
      'source_retained_needle_range_1based':[6,802],'source_sharp_turn_needles_1based':[int(c+6) for c in cuts[1:-1]],
      'reconstructed_main_deviation_mm':{'max_sampled':float(deviation.max()),'p95_sampled':float(np.quantile(deviation,.95))},
      'checks':{'dual_read_identical':True,'header_extents_counts_endpoint':True,'single_final_END':True,'all_needle_deltas_encodable':True,'width_target':True,'both_return_lengths_within_0_05mm':True},
      'wilcom_checked':False,'machine_tested':False,'limitations':['Only this verified Bulldogs pilot is supported.','Order text/font visually confirmed; no general OCR classifier implemented.','Original font used for comparison, not for new unseen glyph centerline extraction.','10 mm is total return path including semicircle, measured as decoded segment lengths.','Internal manual sharp reversals retained; new rounded turns only at start/end.']}
    (out/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    with (out/'stitches.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f);w.writerow(['needle','x_mm','y_mm','command','phase'])
        for i,row in enumerate(a):w.writerow([i+1,row[0]/10,row[1]/10,'STITCH' if row[2]==0 else 'END','start_return' if i<=se else 'end_return' if i>=es else 'main'])
    render(stitches,se,es,out,original)
    (out/'replay_data.json').write_text(json.dumps({'points':(stitches/10).tolist(),'report':report},ensure_ascii=False),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
