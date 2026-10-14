"""Local operator workflow: initialize, find references, check, package. No PDF OCR engine."""
import argparse
from datetime import datetime, timezone
import hashlib
import html
import platform
from importlib.metadata import version as dependency_version
import json
from pathlib import Path
import re
import shutil
import sys
from zipfile import ZipFile, ZIP_DEFLATED

from .trial_validation import sha, validate_dst

RULESET = 'codex-trial-v001'
RULE_DIR = 'rules/releases/' + RULESET


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def save(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def inside(root, name):
    root = Path(root).resolve()
    path = (root / name).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f'Path outside project: {name}')
    return path


def job_paths(root, job_id):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}', job_id):
        raise ValueError('Job ID must use 1–80 letters, digits, underscores or hyphens')
    return inside(root, f'orders/local/{job_id}'), inside(root, f'build/operator/{job_id}')


def verify_rules(root):
    root = Path(root).resolve()
    manifest = read(root / RULE_DIR / 'manifest.json')
    if manifest['ruleset_id'] != RULESET:
        raise ValueError('Ruleset ID mismatch')
    for name, expected in manifest['files'].items():
        if sha(inside(root, name)) != expected:
            raise ValueError(f'Ruleset file changed: {name}; keep this baseline and record experiments separately')
    return manifest


def initialize(root, job_id, pdf=None, demo=False):
    root = Path(root).resolve()
    verify_rules(root)
    local, out = job_paths(root, job_id)
    if local.exists() or out.exists():
        raise ValueError('Job already exists; choose a new job ID')
    if not demo:
        if pdf is None:
            raise ValueError('A local PDF is required')
        pdf = Path(pdf).resolve()
        if not pdf.is_file() or not pdf.read_bytes()[:1024].lstrip().startswith(b'%PDF-'):
            raise ValueError('Input does not have a PDF signature')
    order = read(root / RULE_DIR / 'order.template.json')
    order['order_id'] = job_id
    order['ruleset_id'] = RULESET
    local.mkdir(parents=True)
    out.mkdir(parents=True)
    (out / 'implementation').mkdir()
    if not demo:
        shutil.copyfile(pdf, local / 'input.pdf')
        order['source'] = {'kind': 'local_pdf', 'path': (local / 'input.pdf').relative_to(root).as_posix(),
                           'sha256': sha(local / 'input.pdf'), 'pages': []}
    save(local / 'order.json', order)
    plan = read(root / RULE_DIR / 'plan.template.json')
    plan['job_id'] = job_id
    save(out / 'plan.json', plan)
    (out / 'README.md').write_text(
        f'# {job_id}\n\n规则版本：{RULESET}。订单：orders/local/{job_id}/order.json。\n'
        '按规则填写订单与 plan.json，生成代码保存 implementation/，输出文件命名 candidate.DST。\n'
        '执行 check 后生成回放和报告；文件通过仍待 Wilcom 与实机检查。\n', encoding='utf-8')
    return local, out


def search(root, text, font, limit):
    root = Path(root).resolve()
    verify_rules(root)
    if font not in ['Font1', 'Font2', 'Font3'] or not text.strip():
        raise ValueError('Specify nonempty text and Font1/Font2/Font3')
    catalog_path = root / 'library/catalog/v001/catalog.json'
    manifest = read(root / 'library/catalog/v001/manifest.json')
    if sha(catalog_path) != manifest['files']['library/catalog/v001/catalog.json']:
        raise ValueError('Catalog checksum changed')
    matches = []
    for sample in read(catalog_path)['samples']:
        for source in sample['sources']:
            hint = source['text_hint']
            if source['font_id_hint'] != font or text.casefold() not in hint.casefold():
                continue
            rank = 0 if hint == text else (1 if hint.casefold() == text.casefold() else 2)
            matches.append({'rank': rank, 'sample_id': sample['sample_id'], 'path': source['path'],
                            'sha256': sample['sha256'], 'filename_hint': hint,
                            'metrics': sample['inspection']['metrics'], 'flags': sample['inspection']['flags']})
    matches.sort(key=lambda item: (item['rank'], item['path']))
    return {'query': text, 'font': font, 'total_matches': len(matches), 'matches': matches[:limit],
            'notice': 'Filename hints only. Inspect actual design, case, layout, dimensions and applicability before selecting.'}


def replay(out, rows, report):
    data = json.dumps(rows, separators=(',', ':'))
    status = '文件检查通过，待 Wilcom 与试绣' if report['status'].startswith('file_checks_passed') else '存在未通过项目，请先查看校验报告'
    if report.get('demonstration_only'):
        status = '演示自检：复用既有 v002，未读取 PDF · ' + status
    status = html.escape(status)
    page = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>试绣候选回放</title><style>body{font:16px/1.6 system-ui;margin:24px;color:#183a30}main{max-width:1100px;margin:auto}svg{width:100%;height:52vh;background:#f5f7f4;border:1px solid #dbe4dc}button{padding:8px 16px}input{width:65%}.notice{background:#fff2d8;padding:16px}a{color:#17634a}</style><main><h1>试绣候选回放</h1><p class="notice">__STATUS__ · 尚未完成 Wilcom / 实机验收。<br>蓝灰色为完整落针路径，绿色为已播放路径；跳转用橙色虚线显示。坐标和针距来自最终 DST。</p><p><a href="candidate.DST" download>候选 DST</a> · <a href="validation.json">校验报告</a> · <a href="job.record.json">生成记录</a> · <a href="plan.json">来源与实验假设</a></p><svg id="view"><path id="full" fill="none" stroke="#b9c9c1" stroke-width=".18"/><path id="jumps" fill="none" stroke="#d88d27" stroke-width=".25" stroke-dasharray="1 1"/><path id="current" fill="none" stroke="#187653" stroke-width=".4"/><circle id="point" r=".8" fill="#a74439"/></svg><p><button id="play">播放 / 暂停</button> <input id="seek" type="range" min="0" value="0"><span id="count"></span></p><p>计数使用 DST 命令序号，包含跳转；范围声明与 plan.json 保持相同口径。此页用于路径查看，不能证明工艺合格。</p></main><script>const rows=__ROWS__;const $=id=>document.getElementById(id);let timer=null;const points=rows.map(r=>[r[0]/10,r[1]/10]);function path(n,cmd){let d='',prev=[0,0];for(let i=0;i<n;i++){let p=points[i];if(rows[i][2]===cmd)d+='M'+prev.join(',')+'L'+p.join(',');prev=p;}return d;}if(rows.length){let xs=points.map(p=>p[0]),ys=points.map(p=>p[1]);let x=xs.reduce((a,b)=>Math.min(a,b),0),y=ys.reduce((a,b)=>Math.min(a,b),0),w=xs.reduce((a,b)=>Math.max(a,b),0)-x,h=ys.reduce((a,b)=>Math.max(a,b),0)-y;$('view').setAttribute('viewBox',[x-5,y-5,Math.max(w,1)+10,Math.max(h,1)+10].join(' '));$('full').setAttribute('d',path(rows.length,0));$('jumps').setAttribute('d',path(rows.length,1));}$('seek').max=rows.length;function draw(){let n=+$('seek').value;$('current').setAttribute('d',path(n,0));let p=points[Math.max(0,n-1)]||[0,0];$('point').setAttribute('cx',p[0]);$('point').setAttribute('cy',p[1]);$('count').textContent=n+' / '+rows.length;}$('seek').oninput=draw;$('play').onclick=()=>{if(timer){clearInterval(timer);timer=null;return;}if(+$('seek').value>=rows.length)$('seek').value=0;timer=setInterval(()=>{let n=Math.min(rows.length,+$('seek').value+8);$('seek').value=n;draw();if(n===rows.length){clearInterval(timer);timer=null;}},100);};draw();</script></html>'''
    (out / 'replay.html').write_text(page.replace('__STATUS__', status).replace('__ROWS__', data), encoding='utf-8')


def check(root, job_id):
    root = Path(root).resolve()
    verify_rules(root)
    local, out = job_paths(root, job_id)
    order = read(local / 'order.json')
    plan = read(out / 'plan.json')
    candidate = out / 'candidate.DST'
    limits = read(root / RULE_DIR / 'limits.json')
    report, rows = validate_dst(candidate, order, plan, limits)
    checks = report['checks']
    checks['job_and_ruleset_match'] = order.get('order_id') == job_id and plan.get('job_id') == job_id and order.get('ruleset_id') == RULESET
    source = order.get('source', {})
    report['demonstration_only'] = source.get('kind') == 'demo_fixture'
    try:
        if report['demonstration_only']:
            checks['order_input_hash'] = sha(inside(root, source['path'])) == source.get('sha256')
        else:
            checks['order_input_hash'] = (source.get('kind') == 'local_pdf'
                and source.get('path') == (local / 'input.pdf').relative_to(root).as_posix()
                and sha(local / 'input.pdf') == source.get('sha256'))
    except (KeyError, TypeError, OSError, ValueError):
        checks['order_input_hash'] = False
    binding_path = out / 'candidate.binding.json'
    if not binding_path.exists():
        save(binding_path, {'job_id': job_id, 'first_checked_dst_sha256': sha(candidate)})
    checks['candidate_unchanged_for_this_job'] = read(binding_path).get('first_checked_dst_sha256') == sha(candidate)
    selected = plan.get('selected_samples', [])
    source_errors = []
    for item in selected:
        try:
            reference_path = inside(root, item['path'])
            if reference_path == candidate or reference_path.suffix.lower() != '.dst':
                raise ValueError('Select a separate DST reference')
            if sha(reference_path) != item['sha256']:
                source_errors.append(item['path'])
            if not item.get('usage'):
                source_errors.append('Missing sample usage/segment description')
        except (KeyError, OSError, ValueError):
            source_errors.append('Missing or unsafe reference')
    checks['reference_hashes_and_usage'] = bool(selected) and not source_errors
    checks['reference_visual_review_declared'] = plan.get('reference_visual_reviewed') is True
    implementation = {}
    for name in plan.get('implementation_files', []):
        try:
            path = inside(root, name)
            if not path.is_relative_to(out / 'implementation') or path.suffix != '.py':
                raise ValueError('Implementation must be a .py file inside this job implementation directory')
            implementation[name] = sha(path)
        except (ValueError, OSError) as error:
            source_errors.append(str(error))
    checks['implementation_recorded'] = not source_errors and (plan.get('route') == 'exact_reuse' or bool(implementation))
    if plan.get('route') != 'exact_reuse':
        checks['implementation_command_and_environment_declared'] = isinstance(plan.get('implementation_notes'), str) and bool(plan['implementation_notes'].strip())
    if plan.get('route') == 'exact_reuse':
        checks['exact_reuse_bytes_identical'] = len(selected) == 1 and sha(candidate) == selected[0].get('sha256')
    if plan.get('route') in ['compose', 'experimental']:
        checks['experimental_hypotheses_recorded'] = bool(plan.get('hypotheses'))
    report['issues'].extend(source_errors)
    for key, passed in checks.items():
        if not passed and key not in report['issues']:
            report['issues'].append(key)
    report['status'] = 'file_checks_passed_pending_wilcom_and_sewout' if all(checks.values()) else 'needs_review'
    report['ruleset_id'] = RULESET
    save(out / 'validation.json', report)
    save(out / 'order.snapshot.json', order)
    manifest_path = root / RULE_DIR / 'manifest.json'
    record = {'schema_version': 1, 'job_id': job_id, 'route': plan.get('route'), 'status': report['status'],
              'checked_at_utc': datetime.now(timezone.utc).isoformat(), 'ruleset_id': RULESET,
              'ruleset_manifest_sha256': sha(manifest_path), 'order_sha256': sha(local / 'order.json'),
              'plan_sha256': sha(out / 'plan.json'), 'selected_samples': selected,
              'implementation_sha256': implementation, 'candidate_sha256': sha(candidate),
              'validation_sha256': sha(out / 'validation.json'), 'demonstration_only': report['demonstration_only'],
              'codex_model_reported': plan.get('codex_model_reported'), 'machine_tested': False,
              'validation_runtime': {'python': platform.python_version(), 'pyembroidery': dependency_version('pyembroidery'), 'platform': platform.system()},
              'first_checked_dst_sha256': read(binding_path)['first_checked_dst_sha256']}
    save(out / 'job.record.json', record)
    replay(out, [row for row in rows if row[2] != 4], report)
    feedback = local / 'feedback'
    feedback.mkdir(exist_ok=True)
    if not (feedback / 'trial-report.md').exists():
        (feedback / 'trial-report.md').write_text(
            f'# {job_id} 试绣反馈\n\n规则：{RULESET}\n候选 SHA256：{sha(candidate)}\n'
            '状态：尚未试绣。请复制本表为每次重复的独立记录。\n\n'
            '- 日期 / 操作员：\n- 机器、装置/模式：\n- 面料、衬料、毛线、针具、装框：\n'
            '- 转速、张力：\n- Wilcom 显示尺寸、针数、方向：\n'
            '- 是否另存、缩放、旋转、镜像；实际使用文件：\n- 完成情况、断线、停机次数和位置：\n'
            '- 在绷 / 放松后尺寸及等待时间：\n- 起收、回走、交叉与字形问题：\n'
            '- 照片文件名（全图带尺 / 近照）：\n- 接受 / 不接受 / 需复测：\n', encoding='utf-8')
    return report


def package(root, job_id):
    root = Path(root).resolve()
    # Recheck immediately, so a modified candidate cannot reuse a stale report.
    report = check(root, job_id)
    local, out = job_paths(root, job_id)
    plan = read(out / 'plan.json')
    members = {name: out / name for name in ['README.md', 'candidate.DST', 'replay.html', 'validation.json', 'job.record.json', 'order.snapshot.json', 'plan.json', 'candidate.binding.json']}
    for name in plan.get('implementation_files', []):
        path = inside(root, name)
        if not path.is_relative_to(out / 'implementation') or path.suffix != '.py':
            raise ValueError('Unsafe implementation file')
        members[path.relative_to(out).as_posix()] = path
    for sample in plan.get('selected_samples', []):
        path = inside(root, sample['path'])
        actual = sha(path)
        if path.suffix.lower() != '.dst' or actual != sample.get('sha256'):
            raise ValueError('Invalid reference in package')
        members['reference-inputs/' + actual + '.DST'] = path
    for path in (local / 'feedback').rglob('*'):
        if path.is_file() and path.suffix.lower() in ['.md', '.txt', '.json', '.jpg', '.jpeg', '.png', '.mp4', '.webm', '.dst']:
            if not path.resolve().is_relative_to(local / 'feedback'):
                raise ValueError('Feedback symlink leaves this job')
            members['feedback/' + path.relative_to(local / 'feedback').as_posix()] = path
    rules_manifest = read(root / RULE_DIR / 'manifest.json')
    for name in rules_manifest['files']:
        members['rulepack/' + name] = inside(root, name)
    members['rulepack/' + RULE_DIR + '/manifest.json'] = root / RULE_DIR / 'manifest.json'
    dist = root / 'dist'
    dist.mkdir(exist_ok=True)
    number = 1
    while (dist / f'{job_id}-feedback-{number:03}.zip').exists():
        number += 1
    target = dist / f'{job_id}-feedback-{number:03}.zip'
    reference_map = {sample['path']: 'reference-inputs/' + sample['sha256'] + '.DST' for sample in plan.get('selected_samples', [])}
    package_manifest = {'job_id': job_id, 'reference_path_map': reference_map, 'status': report['status'], 'ruleset_id': RULESET,
                        'notice': 'Includes order text and selected references, but no original order PDF. Inspect before sharing.',
                        'files': {name: sha(path) for name, path in members.items()}}
    with ZipFile(target, 'x', ZIP_DEFLATED) as archive:
        for name, path in sorted(members.items()):
            archive.write(path, name)
        archive.writestr('package-manifest.json', json.dumps(package_manifest, ensure_ascii=False, indent=2))
    target.with_suffix('.zip.sha256').write_text(sha(target) + '  ' + target.name + '\n')
    return target, report['status']


def demo(root, job_id):
    root = Path(root).resolve()
    local, out = initialize(root, job_id, demo=True)
    case_dir = root / 'releases/reference-guided/v002/01-F2-Bulldogs'
    case = read(case_dir / 'validation.json')
    source = case_dir / case['dst_file']
    order = read(local / 'order.json')
    order.update(status='confirmed_demo_fixture', source={'kind': 'demo_fixture', 'path': source.relative_to(root).as_posix(), 'sha256': sha(source), 'pages': []})
    order['design'] = {'text': 'Bulldogs', 'font_id': 'Font2', 'width_mm': 328.9, 'lines': ['Bulldogs'], 'alignment': 'single_line'}
    order['field_review'] = {key: True for key in ['text', 'font', 'dimensions', 'layout']}
    order['notes'] = 'Workflow smoke test using frozen v002; not PDF parsing or a new design.'
    save(local / 'order.json', order)
    shutil.copyfile(source, out / 'candidate.DST')
    plan = read(out / 'plan.json')
    plan.update(route='exact_reuse', reference_visual_reviewed=True,
                selected_samples=[{'path': source.relative_to(root).as_posix(), 'sha256': sha(source), 'usage': 'Copy frozen v002 candidate for workflow smoke test; design metadata from its validation report.'}],
                returns=[{'start_commands_1based': [1, 10], 'end_commands_1based': [821, 829]}],
                limitations=['Demo only; no local PDF parsed and no machine acceptance.'])
    save(out / 'plan.json', plan)
    return check(root, job_id)


def main(root=None):
    root = Path(root or Path(__file__).resolve().parents[2]).resolve()
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('verify-rules')
    init = sub.add_parser('init'); init.add_argument('--job', required=True); init.add_argument('--pdf', required=True)
    find = sub.add_parser('search'); find.add_argument('--text', required=True); find.add_argument('--font', required=True); find.add_argument('--limit', type=int, default=12)
    for name in ['check', 'package', 'demo']:
        p = sub.add_parser(name); p.add_argument('--job', required=True)
    args = parser.parse_args()
    try:
        if args.command == 'verify-rules':
            m = verify_rules(root); print(f"PASS: {m['ruleset_id']} / {len(m['files'])} files")
        elif args.command == 'init':
            local, out = initialize(root, args.job, args.pdf); print(f'Order: {local / "order.json"}\nCandidate workspace: {out}')
        elif args.command == 'search':
            if not 1 <= args.limit <= 100:
                raise ValueError('Limit must be 1–100')
            print(json.dumps(search(root, args.text, args.font, args.limit), ensure_ascii=False, indent=2))
        elif args.command in ['demo', 'check']:
            result = demo(root, args.job) if args.command == 'demo' else check(root, args.job)
            print(json.dumps({'status': result['status'], 'issues': result['issues'], 'metrics': result.get('metrics')}, ensure_ascii=False, indent=2))
            if result['status'] == 'needs_review':
                return 2
        else:
            target, status = package(root, args.job); print(f'Package: {target}\nStatus: {status}\nOriginal order PDF is excluded; order text is included.')
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.exit(1, f'FAIL: {error}\n')
    return 0
