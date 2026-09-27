"""通常実行で設定ウィンドウ。--all / --config で画面なし一括生成。"""
import argparse
from .configuration import PRESETS,preset,load
from .paths import PROJECT_ROOT
from .runtime import use_project_venv,ensure_dependencies

def main():
    use_project_venv(PROJECT_ROOT/'launch.py')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config');parser.add_argument('--all',action='store_true')
    parser.add_argument('--blender');parser.add_argument('--no-test',action='store_true')
    parser.add_argument('--no-render',action='store_true')
    args=parser.parse_args()
    ensure_dependencies()
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
