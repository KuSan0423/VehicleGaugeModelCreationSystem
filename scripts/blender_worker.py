"""Blender --background --python で呼ぶ専用エントリーポイント。"""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from rail_clearance.configuration import load,validate
from rail_clearance.verification import run
from rail_clearance.blender_model import Model
from rail_clearance.rendering import previews

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--config',required=True);parser.add_argument('--output',required=True)
    parser.add_argument('--test',action='store_true');parser.add_argument('--no-render',action='store_true')
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    config=validate(load(args.config));out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    report=run(config,lambda s:print(s,flush=True)) if args.test else None
    model=Model(config)
    if report is not None:
        model.verify_meshes(report)
        (out/'検証結果.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    model.export(out)
    if not args.no_render:previews(model,out)
    (out/'完了.json').write_text(json.dumps(dict(success=True,tested=args.test),ensure_ascii=False),encoding='utf-8')

if __name__=='__main__':main()
