"""入力値（mm）とプリセット。BlenderにもGUIにも依存しない。"""
import copy
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_RADII = [100, 125, 150, 200, 300, 500, 1000, 2000]

def preset(name):
    lengths = {'連接車_15m': [14000, 14000],
               '連接車_15m_11m_15m': [14000, 10000, 14000],
               '連接車_41m_通常台車': [14250, 10000, 14250]}[name]
    return dict(name=name, lengths_mm=lengths, gaps_mm=[1000]*(len(lengths)-1),
                joint_fractions=[0.5]*(len(lengths)-1), normal_ends='41m' in name,
                outer_insets_mm=[3000, 3000], coupler_mm=[250, 250],
                radius_m=100, direction=1, test_radii_m=DEFAULT_RADII[:],
                equipment_reserve_mm=10, reference_spacing_m=[14, 15, 0.01])

PRESETS = ['連接車_15m', '連接車_15m_11m_15m', '連接車_41m_通常台車']

def validate(c):
    if not isinstance(c['normal_ends'],bool):raise ValueError('normal_ends はtrueまたはfalseです。')
    if not isinstance(c['name'],str) or not c['name'].strip() or len(c['name'])>60:
        raise ValueError('編成名は1～60文字で指定してください。')
    n = len(c['lengths_mm'])
    if n < 2 or n > 20:
        raise ValueError('車体数は2～20両にしてください。')
    for key in ('gaps_mm', 'joint_fractions'):
        if len(c[key]) != n-1:
            raise ValueError(f'{key} は車体数−1個必要です。')
    for key in ('outer_insets_mm', 'coupler_mm'):
        if len(c[key]) != 2:
            raise ValueError(f'{key} は左右の2個が必要です。')
    values = sum([list(c[k]) for k in ('lengths_mm', 'gaps_mm', 'joint_fractions',
                  'outer_insets_mm', 'coupler_mm', 'test_radii_m', 'reference_spacing_m')], [])
    values += [c['radius_m'], c['equipment_reserve_mm']]
    if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in values):
        raise ValueError('すべて有限の数値を入力してください。')
    if min(c['lengths_mm']) < 2000:
        raise ValueError('車体長は固定長2mのパンタグラフを収容するため2,000mm以上です。')
    if min(c['gaps_mm']) <= 0 or not all(0 < x < 1 for x in c['joint_fractions']):
        raise ValueError('車体間隔は正数、共有台車位置の比率は0より大きく1未満です。')
    if min(c['outer_insets_mm']+c['coupler_mm']) < 0:
        raise ValueError('台車の内側距離と連結器突出は0以上です。')
    if c['equipment_reserve_mm'] <= 0:
        raise ValueError('機器の端面余裕は正数です。')
    if not c['test_radii_m'] or min(c['test_radii_m']) < 100:
        raise ValueError('試験半径は100m以上を指定してください（Ver2.0補間範囲）。')
    if c['radius_m'] != 0 and c['radius_m'] < 100:
        raise ValueError('表示半径は0（直線）または100m以上です。')
    if c['direction'] not in (-1, 1):
        raise ValueError('曲線方向は1または-1です。')
    lo, hi, step = c['reference_spacing_m']
    if not (0 < lo <= hi and step > 0 and (hi-lo)/step <= 1000):
        raise ValueError('20m級の台車間走査は正の範囲・刻み、1,001点以内です。')
    return copy.deepcopy(c)

def load(path):
    return validate(json.loads(Path(path).read_text(encoding='utf-8-sig')))

def save(c, path):
    Path(path).write_text(json.dumps(validate(c), ensure_ascii=False, indent=2), encoding='utf-8')
