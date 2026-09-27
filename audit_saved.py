"""Blenderでサンプル保存ファイルを開き直して基準・配置を監査。"""
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import bpy
from configuration import ROOT,PRESETS,preset
from geometry import dimensions,formation
from blender_model import signature,audit

bpy.ops.wm.open_mainfile(filepath=str(ROOT/'data/基準_Ver2.blend'))
baseline=signature(bpy.data.objects['建築限界'])
rows=[]
for name in PRESETS:
    config=preset(name);d=dimensions(config)
    path=ROOT/'サンプル'/name/'編成_指定条件.blend'
    bpy.ops.wm.open_mainfile(filepath=str(path))
    assert signature(bpy.data.objects['建築限界'])==baseline
    arr=formation(d,config['radius_m'],config['direction'])
    for i,car in enumerate(d['cars']):
        obj=bpy.data.objects[f'{i+1}号車_body']
        top=[v.co for v in obj.data.vertices if v.co.z>4.4]
        assert abs(min(v.x for v in top)+1)<1e-6
        assert abs(max(v.x for v in top)-1)<1e-6
        assert abs(max(v.z for v in top)-4.515)<1e-6
        assert abs(max(v.y for v in top)-.65)<1e-6
        expected=arr['poses'][i]
        assert abs(obj.matrix_world.translation.x-expected[0])<1e-5
        assert abs(obj.matrix_world.translation.y-expected[1])<1e-5
        rows.append(dict(preset=name,car=i+1,pantograph_centered_fixed_size=True,mesh=audit(obj)))
(ROOT/'保存モデル監査.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
print('SAVED MODEL AUDIT OK',len(rows))
