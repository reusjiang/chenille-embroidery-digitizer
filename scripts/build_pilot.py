"""Generate a candidate, offline replay and report without touching frozen releases."""
import argparse,hashlib,json,subprocess,sys
from importlib.metadata import version
from project import ROOT,SOURCE,DEFAULT_OUTPUT,output_path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',default=DEFAULT_OUTPUT)
    args=parser.parse_args();out=output_path(args.output)
    for script in ['generate_dst.py','build_replay.py','build_report.py']:
        subprocess.run([sys.executable,str(ROOT/'scripts'/script),'--output',args.output],check=True,cwd=ROOT)
    digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    info={'status':'unreleased-candidate','python':sys.version,'source_sha256':digest(SOURCE),
          'packages':{p:version(p) for p in ['numpy','scipy','matplotlib','pillow','pyembroidery']},
          'script_sha256':{p.name:digest(p) for p in sorted((ROOT/'scripts').glob('*.py'))},
          'dst_sha256':digest(out/'Bulldogs_F2_330mm.DST'),'width_mm':330,
          'scope':'Verified Bulldogs pilot; geometry settings remain case-specific in generate_dst.py.'}
    (out/'build-info.json').write_text(json.dumps(info,indent=2),encoding='utf-8')
    print(f'Candidate ready: {out}')

if __name__=='__main__':main()
