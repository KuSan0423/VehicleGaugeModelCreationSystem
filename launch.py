"""外部Python用の起動入口。リポジトリ直下から従来どおり実行できる。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / 'src'))
from rail_clearance.cli import main

if __name__ == '__main__':
    main()
