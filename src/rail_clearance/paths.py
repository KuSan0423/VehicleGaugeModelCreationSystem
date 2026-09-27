"""作業ディレクトリに依存しない、プロジェクト内の参照先。"""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / 'data'
PRESETS_DIR = PROJECT_ROOT / 'configs' / 'presets'
EXAMPLES_DIR = PROJECT_ROOT / 'examples'
OUTPUT_DIR = PROJECT_ROOT / 'outputs'
ARTIFACTS_DIR = PROJECT_ROOT / 'artifacts'
VALIDATION_DIR = ARTIFACTS_DIR / 'validation'
SCRIPTS_DIR = PROJECT_ROOT / 'scripts'
