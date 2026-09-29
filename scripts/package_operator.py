"""Create a minimal offline handoff package. Never include private assets or runtimes."""
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
import hashlib
from project import ROOT,BASELINE
from verify_release import verify_release


def main():
    m=verify_release(BASELINE)
    dist=ROOT/'dist';dist.mkdir(exist_ok=True)
    target=dist/f"{m['release_id']}-operator-kit.zip"
    members=[BASELINE/'manifest.json',*[BASELINE/name for name in m['files']]]
    members += [ROOT/p for p in ['docs/operator-guide.md','docs/iteration-plan.md','feedback/templates/trial-report.md','feedback/templates/trial-record.json']]
    if any(not p.is_file() for p in members):raise FileNotFoundError('Required operator document is missing')
    intro='''# Bulldogs Font2 / v001 设备试绣包

版本：BULL-F2-330-v001。状态：文件检查通过，尚未完成 Wilcom 或实机验收。

1. 阅读 [操作指南](docs/operator-guide.md)。
2. 打开 [版本说明](releases/bulldogs-font2-330/v001/README.md) 和同目录 replay.html。
3. 使用同目录 Bulldogs_F2_330mm.DST；无需安装 Python。
4. 复制 [试绣记录](feedback/templates/trial-report.md) 填写，附整体/局部照片后回传。

本包仅用于试绣与反馈，不代表已批准生产。客户订单、完整样本库、字体及开发环境未包含在内。
'''
    with ZipFile(target,'w',ZIP_DEFLATED) as z:
        z.writestr('README.md',intro)
        for p in sorted(members):z.write(p,p.relative_to(ROOT).as_posix())
    checksum=hashlib.sha256(target.read_bytes()).hexdigest()
    target.with_suffix('.zip.sha256').write_text(f'{checksum}  {target.name}\n',encoding='ascii')
    print(f'Operator kit: {target}\nSHA256: {checksum}')

if __name__=='__main__':main()
