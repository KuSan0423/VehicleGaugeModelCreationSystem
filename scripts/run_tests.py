"""単体テスト。--gui を指定すると非表示ウィンドウの操作確認も実行。"""
import argparse
import runpy
import sys
import unittest
from pathlib import Path

PROJECT_ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT_ROOT/'src'))

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gui',action='store_true')
    args=parser.parse_args()
    suite=unittest.defaultTestLoader.discover(str(PROJECT_ROOT/'tests'),top_level_dir=str(PROJECT_ROOT))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():raise SystemExit(1)
    if args.gui:runpy.run_path(str(PROJECT_ROOT/'tests/gui_smoke.py'),run_name='__main__')

if __name__=='__main__':main()
