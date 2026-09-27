"""3プリセットの完成サンプルを生成する開発確認用スクリプト。"""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from rail_clearance.configuration import PRESETS,preset
from rail_clearance.paths import EXAMPLES_DIR
from rail_clearance.runner import generate

if __name__=='__main__':
    for name in PRESETS:
        out,report=generate(preset(name),output=EXAMPLES_DIR/name,progress=print)
        print(name,report['building_pass'],report['body_pass'],report['gauge_pass'],flush=True)
