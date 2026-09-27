"""プロジェクトの仮想環境選択と、外部Python側の依存関係確認。"""
import importlib
import os
from pathlib import Path
import subprocess
import sys
from .paths import PROJECT_ROOT

def python_in(venv_dir):
    return Path(venv_dir)/('Scripts/python.exe' if os.name=='nt' else 'bin/python')

def venv_environment(venv_dir):
    env=os.environ.copy()
    env.pop('PYTHONHOME',None)
    env.pop('PYTHONPATH',None)
    env['VIRTUAL_ENV']=str(venv_dir)
    env['PATH']=str(python_in(venv_dir).parent)+os.pathsep+env.get('PATH','')
    env['PYTHONUTF8']='1'
    return env

def use_project_venv(entrypoint,argv=None):
    """明示的activateなしでもプロジェクト.venvへ一度だけ切り替える。"""
    target=PROJECT_ROOT/'.venv'
    if not target.exists():return
    executable=python_in(target)
    if not executable.is_file() or not (target/'pyvenv.cfg').is_file():
        raise SystemExit('.venvが不完全です。内容を確認し、セットアップ.cmdで環境を準備してください。')
    if Path(sys.prefix).resolve()==target.resolve():return
    marker=str(target.resolve())
    if os.environ.get('RAIL_CLEARANCE_VENV_REEXEC')==marker:
        raise SystemExit('.venvへの切り替えに失敗しました。仮想環境を再作成してください。')
    env=venv_environment(target)
    env['RAIL_CLEARANCE_VENV_REEXEC']=marker
    command=[str(executable),'-X','utf8',str(entrypoint),*(sys.argv[1:] if argv is None else argv)]
    raise SystemExit(subprocess.call(command,env=env))

def ensure_dependencies():
    if sys.version_info < (3,10):raise SystemExit('Python 3.10以降が必要です。')
    try:
        pillow=importlib.import_module('PIL')
        importlib.import_module('tkinter')
        if int(pillow.__version__.split('.')[0])<10:raise ImportError('Pillow 10以降が必要です。')
    except (ImportError,OSError) as exc:
        raise SystemExit(f'実行環境の準備が必要です：{exc}\nセットアップ.cmd または python scripts/setup_venv.py を実行してください。') from exc
