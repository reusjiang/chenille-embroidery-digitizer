"""Build a case report from decoded metrics; raw PDF and font files are optional."""
import csv,json
from pathlib import Path
import numpy as np
import pyembroidery as pe
from PIL import Image,ImageDraw,ImageFont
from generate_dst import plt
from project import ROOT,SOURCE,output_args

out=output_args('Create source evidence, close-ups and a report for the pilot.')
r=json.loads((out/'validation.json').read_text(encoding='utf-8'))
p=np.array(json.loads((out/'replay_data.json').read_text(encoding='utf-8'))['points'])
se=r['return_needle_ranges_1based']['start'][1];es=r['return_needle_ranges_1based']['end'][0]
fig,axs=plt.subplots(2,2,figsize=(13,8))
for ax,q,title,color in [(axs[0,0],p[:se+3],f"Start return / {r['return_lengths_mm']['start']:.3f} mm",'#c4752b'),(axs[0,1],p[es-4:],f"End return / {r['return_lengths_mm']['end']:.3f} mm",'#ad3c6e')]:
    ax.plot(q[:,0],q[:,1],'.-',c=color,lw=1.3,ms=4);ax.set_title(title);ax.set_aspect('equal');ax.invert_yaxis();ax.grid(alpha=.2);ax.set_xlabel('mm');ax.set_ylabel('mm')
for ax,a,b,title,col in [(axs[1,0],max(0,se-5),se,'Start turn / decoded needles','#c4752b'),(axs[1,1],es-1,min(len(p),es+3),'End turn / decoded needles','#ad3c6e')]:
    q=p[a:b];ax.plot(q[:,0],q[:,1],'.-',c=col,lw=1.3,ms=8);ax.set_aspect('equal');ax.invert_yaxis();ax.grid(alpha=.2);ax.set_title(title);ax.set_xlabel('mm');ax.set_ylabel('mm');ax.margins(.6)
    for i,pt in enumerate(q):ax.annotate(str(a+i+1),pt,xytext=(6,8 if i%2 else -16),textcoords='offset points',fontsize=10)
fig.tight_layout();fig.savefig(out/'details.png',dpi=180);plt.close(fig)
a=np.array(pe.read_dst(str(SOURCE),{'trim_at':False,'clipping':False}).stitches)
with (out/'source_stitches.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.writer(f);w.writerow(['source_needle_1based','x_mm','y_mm','command']);w.writerows((i+1,x/10,y/10,int(c)) for i,(x,y,c) in enumerate(a))
fig,ax=plt.subplots(figsize=(15,5));q=a[:-1,:2]/10;ax.plot(q[:,0],q[:,1],'.-',lw=.8,ms=2,c='#234f68')
for i in r['source_sharp_turn_needles_1based']:
    ax.scatter(*q[i-1],c='#c46528',s=25);ax.annotate(str(i),q[i-1],xytext=(4,-14),textcoords='offset points',fontsize=9)
ax.set_aspect('equal');ax.invert_yaxis();ax.grid(alpha=.15);ax.set_title('Original manual DST / reversal needle indices (1-based)');ax.set_xlabel('mm');ax.set_ylabel('mm');fig.tight_layout();fig.savefig(out/'source_analysis.png',dpi=180);plt.close(fig)
font_path=ROOT/'assets/private/fonts/Font2.OTF'
font_note='原始字体未随 Git 分发；本次跳过字体参考图，DST 重建不依赖该字体文件。'
if font_path.is_file():
    font=ImageFont.truetype(str(font_path),220);box=font.getbbox('Bulldogs');im=Image.new('RGB',(box[2]-box[0]+80,box[3]-box[1]+80),'white');ImageDraw.Draw(im).text((40-box[0],40-box[1]),'Bulldogs',font=font,fill='#285063');im.save(out/'font2_reference.png')
    font_note='已使用本地 Font2 / Loverine 生成 font2_reference.png。'
report=f'''# Bulldogs / Font2 生成报告

本次为同词人工路径重建试验，仅支持经过核对的 Bulldogs 样本。尚未完成 Wilcom 导入验证或实机试绣。生成结果位于 build/，不会覆盖 releases/ 中的冻结版本。

| 项目 | 最终 DST 回读结果 |
|---|---|
| 普通落针宽高 | {r['width_mm']:.1f} × {r['height_mm']:.1f} mm |
| 普通落针命令（含起点零位移） | {r['stitch_commands']} |
| 跳针命令 / 跳转次数 | {r['jump_commands']} / {r['jump_runs']} |
| 起点 / 终点 mm | {r['start_mm']} / {r['end_mm']} |
| 落针包围盒 mm | {r['bbox_mm']} |
| 起针回线 / 针号范围 | {r['return_lengths_mm']['start']:.6f} mm / {r['return_needle_ranges_1based']['start']} |
| 收针回线 / 针号范围 | {r['return_lengths_mm']['end']:.6f} mm / {r['return_needle_ranges_1based']['end']} |
| 非零针距最小 / 中位 / 最大 | {r['needle_length_mm']['min_nonzero']:.3f} / {r['needle_length_mm']['median']:.3f} / {r['needle_length_mm']['max']:.3f} mm |
| 小于 0.5 mm 的非零针距数 | {r['short_stitches_under_0_5mm']} |

回线按解码后针迹累计弧长计算，包含圆弧；坐标 x 向右、y 向下。文件宽度不包含线材外缘。

样本：`{r['source_sample']}`。保留第 6–802 针主路径的顺序，重建曲线并重新落针。原样本起/收回走长度分别为 {r['source_return_lengths_mm']['start']:.6f} / {r['source_return_lengths_mm']['end_before_micro_lock']:.6f} mm；新版本将两端改为约 10 mm 的圆弧回线。原始折返针号为 {r['source_sharp_turn_needles_1based']}，见 source_analysis.png 和 source_stitches.csv。

B 上环、字肚、双 l、d/g 回走与交叉先后顺序沿用人工样本；不新增字母间连接。新起收半径为 {r['turn_radius_design_mm']} mm。内部尖转尚未全部改圆；短针与回走重叠的实物效果待验证。

双解码器坐标和命令一致，文件头范围/计数/终点、最终 END、可编码位移、目标宽度与回线长度检查通过。详见 validation.json；结构检查不代表设备工艺适用性已确认。

{font_note}

查看 replay.html、preview.png、details.png 和 stitches.csv。当前算法不是任意文字/字体的自动打带系统；参数与主路径边界具有样本专用性。
'''
(out/'generation-report.md').write_text(report,encoding='utf-8')
print(f'Report and evidence saved to {out}')
