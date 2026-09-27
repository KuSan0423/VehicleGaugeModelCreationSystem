""".venvを作成し、requirements.txtの依存関係をその中へ導入する。"""
import os
from pathlib import Path
import subprocess
import sys
import venv

PROJECT_ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT_ROOT/'src'))
from rail_clearance.runtime import python_in,venv_environment

def main():
    if sys.version_info < (3,10):raise SystemExit('Python 3.10以降でセットアップしてください。')
    try:
        import tkinter
        tkinter.Tcl()
    except (ImportError,RuntimeError) as exc:
        raise SystemExit(f'tkinterを含むPythonが必要です。PythonのTcl/Tk機能を導入してください：{exc}') from exc
    target=PROJECT_ROOT/'.venv'
    executable=python_in(target)
    if target.exists():
        if not executable.is_file() or not (target/'pyvenv.cfg').is_file():
            raise SystemExit('既存の.venvが不完全です。必要な内容を別名で保存してから再作成してください。')
        print(f'既存の仮想環境を使用：{target}',flush=True)
    else:
        print(f'仮想環境を作成：{target}',flush=True)
        venv.EnvBuilder(with_pip=True,system_site_packages=False).create(target)
    env=venv_environment(target)
    # Keep download caches in the already ignored artifact directory.
    env['PIP_CACHE_DIR']=str(PROJECT_ROOT/'artifacts/pip-cache')
    if subprocess.run([str(executable),'-c','import pip'],env=env,stdout=subprocess.DEVNULL,
                      stderr=subprocess.DEVNULL).returncode:
        subprocess.run([str(executable),'-m','ensurepip'],env=env,check=True)
    subprocess.run([str(executable),'-m','pip','install','--disable-pip-version-check',
                    '-r',str(PROJECT_ROOT/'requirements.txt')],env=env,check=True)
    subprocess.run([str(executable),'-X','utf8','-c',
                    'import sys, tkinter, PIL; tkinter.Tcl(); print("Python:",sys.executable); print("Pillow:",PIL.__version__)'],env=env,check=True)
    print('セットアップ完了。起動.cmd または python launch.py で起動できます。',flush=True)

if __name__=='__main__':
    try:main()
    except subprocess.CalledProcessError as exc:raise SystemExit(f'セットアップに失敗しました（終了コード{exc.returncode}）。上のエラーを確認して再実行してください。') from exc
