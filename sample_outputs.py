"""3プリセットの完成サンプルを生成する開発確認用スクリプト。"""
from configuration import ROOT,PRESETS,preset
from runner import generate

if __name__=='__main__':
    for name in PRESETS:
        out,report=generate(preset(name),output=ROOT/'サンプル'/name,progress=print)
        print(name,report['building_pass'],report['body_pass'],report['gauge_pass'],flush=True)
