"""外部PythonからBlenderを実行。各実行を別フォルダに保存する。"""
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
from configuration import ROOT,save,validate
from geometry import dimensions
from drawing import dimension_image,verification_image

def find_blender(explicit=None):
    candidates=[explicit,os.environ.get('BLENDER_EXE'),shutil.which('blender'),
                'C:/Program Files (x86)/Steam/steamapps/common/Blender/blender.exe']
    candidates+=list(Path('C:/Program Files/Blender Foundation').glob('Blender */blender.exe'))
    for value in candidates:
        if value and Path(value).is_file():return str(Path(value).resolve())
    raise FileNotFoundError('Blenderが見つかりません。「Blender参照」でblender.exeを選択してください。')

def generate(config,blender=None,test=True,render=True,progress=lambda s:None,output=None):
    dimensions(config)
    exe=find_blender(blender)
    if output is None:
        safe=''.join(ch for ch in config['name'] if ch not in '<>:"/\\|?*').strip() or '編成'
        output=ROOT/'出力'/f'{datetime.now():%Y%m%d_%H%M%S_%f}_{safe}'
    out=Path(output).resolve();out.mkdir(parents=True,exist_ok=True)
    save(config,out/'設定.json')
    save(validate(config),out/'計算済み設定.json')
    dimension_image(config).save(out/'寸法確認図.png')
    command=[exe,'--background','--factory-startup','--python-exit-code','1','--python',str(ROOT/'blender_worker.py'),
             '--','--config',str(out/'設定.json'),'--output',str(out)]
    if test:command.append('--test')
    if not render:command.append('--no-render')
    progress(f'Blender実行中：{out.name}')
    flags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0
    with (out/'実行ログ.txt').open('w',encoding='utf-8') as log:
        result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,creationflags=flags)
    if result.returncode or not (out/'完了.json').exists():
        raise RuntimeError(f'生成に失敗しました。ログ：{out / "実行ログ.txt"}')
    report=json.loads((out/'検証結果.json').read_text(encoding='utf-8')) if test else None
    verification_image(config,report).save(out/'検証結果プレビュー.png')
    if report:
        lines=['# 接触試験結果','',f'建築限界内：{report["building_pass"]}',f'車体・機器の非接触：{report["body_pass"]}',
               f'車両限界・機器の非重複：{report["gauge_pass"]}','','負の分離余裕は平面輪郭の重なりです。3D最短距離ではありません。',
               '車両限界同士の重なりは車体接触とは別の判定です。','詳細な条件、数値、メッシュ表面交差は検証結果.jsonを参照してください。']
        lines+=['',*report['errors']]
        (out/'試験結果.md').write_text('\n'.join(lines),encoding='utf-8')
    return out,report
