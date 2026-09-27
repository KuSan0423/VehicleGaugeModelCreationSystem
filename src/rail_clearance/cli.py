"""通常実行で設定ウィンドウ。--all / --config で画面なし一括生成。"""
import argparse
import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from .configuration import PRESETS,preset,load
from .paths import PROJECT_ROOT

def ensure_runtime():
    """既存PythonにGUI/画像ライブラリがなければ利用可能な同梱Pythonで起動。インストールはしない。"""
    if importlib.util.find_spec('PIL') and importlib.util.find_spec('tkinter'):return
    if not os.environ.get('RAIL_PREVIEW_RELAUNCHED'):
        candidate=Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
        if candidate.is_file() and candidate.resolve()!=Path(sys.executable).resolve():
            env=os.environ.copy();env['RAIL_PREVIEW_RELAUNCHED']='1'
            raise SystemExit(subprocess.call([str(candidate),'-X','utf8',str(PROJECT_ROOT/'launch.py'),*sys.argv[1:]],env=env))
    raise SystemExit('PythonのtkinterとPillowが必要です。Pillowは python -m pip install -r requirements.txt で導入できます。')

def main():
    ensure_runtime()
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config');parser.add_argument('--all',action='store_true')
    parser.add_argument('--blender');parser.add_argument('--no-test',action='store_true')
    parser.add_argument('--no-render',action='store_true')
    args=parser.parse_args()
    if args.config or args.all:
        from .runner import generate
        configs=[preset(n) for n in PRESETS] if args.all else [load(args.config)]
        for c in configs:
            out,_=generate(c,args.blender,not args.no_test,not args.no_render,print)
            print(out)
    else:
        from .gui import main as gui_main
        gui_main()

if __name__=='__main__':main()
