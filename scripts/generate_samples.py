"""3プリセットの完成サンプルを生成する開発確認用スクリプト。"""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from rail_clearance.configuration import PRESETS,preset
from rail_clearance.paths import EXAMPLES_DIR
from rail_clearance.runtime import use_project_venv,ensure_dependencies

if __name__=='__main__':
    use_project_venv(Path(__file__).resolve())
    ensure_dependencies()
    from rail_clearance.runner import generate
    for name in PRESETS:
        out,report=generate(preset(name),output=EXAMPLES_DIR/name,progress=print)
        print(name,report['building_pass'],report['body_pass'],report['gauge_pass'],flush=True)
