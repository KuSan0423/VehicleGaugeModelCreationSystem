# 連接車のパラメトリック生成

Blenderの外から起動するPythonアプリです。寸法を編集すると図面プレビューが更新され、ボタンで3Dモデル生成・接触試験・画像出力を実行できます。

## 起動

`起動.cmd` をダブルクリックするか、プロジェクトのルートで実行します。

```text
python launch.py
```

Python 3.10以降、tkinter、Pillow、Blenderが必要です。このPCでは既存のCodex同梱Pythonも自動利用します。詳細は [使い方](docs/usage.md) を参照してください。

## ディレクトリ構成

```text
連接車_パラメトリック生成/
├── launch.py                  # 起動入口（従来どおり）
├── 起動.cmd                   # Windows用ランチャー
├── README.md
├── requirements.txt
├── .gitignore
├── src/
│   └── rail_clearance/         # アプリ本体・共通寸法計算・Blender処理
├── tests/                     # 単体テスト・画面操作テスト
├── scripts/                   # Blender実行入口・テスト・サンプル生成・監査
├── configs/
│   └── presets/               # 設定プリセットJSON
├── data/                      # 固定のVer2.0基準モデル・断面座標
├── docs/
│   ├── usage.md               # 詳細な操作説明
│   └── images/                # 説明用の画像
├── examples/                  # 3プリセットのモデル・画像・試験結果見本
├── outputs/                   # ユーザー操作による生成物（Git除外）
└── artifacts/                 # 開発・検証の生成物（Git除外）
    └── validation/            # 動作検証の記録
```

実装は `src/rail_clearance/` 内のPythonパッケージとして管理します。各ディレクトリへの参照は `paths.py` にまとめています。インストール操作なしでルートの起動スクリプトから実行できます。

## 一括生成・テスト

次のコマンドはプロジェクトのルートで実行します。

```text
python launch.py --config configs/presets/連接車_41m_通常台車.json
python launch.py --all
python scripts/run_tests.py
python scripts/run_tests.py --gui
```

`--gui` は非表示の設定ウィンドウで入力更新・エラー表示を確認します。サンプルの再生成は `python scripts/generate_samples.py`、保存モデル監査は `blender --background --python-exit-code 1 --python scripts/audit_saved.py` です。

## 旧配置からの変更

| 旧配置 | 現在の配置 |
|---|---|
| ルート直下の実装Python | `src/rail_clearance/` |
| `test_*.py` | `tests/` |
| `blender_worker.py`、`audit_saved.py`、`sample_outputs.py` | `scripts/`（サンプル生成は `generate_samples.py`） |
| `プリセット/` | `configs/presets/` |
| `サンプル/` | `examples/` |
| `出力/` | `outputs/` |
| `動作検証/` | `artifacts/validation/` |
| `寸法プレビュー見本.png` | `docs/images/dimension_preview.png` |
| `保存モデル監査.json` | `artifacts/saved_model_audit.json` |

既存の設定JSONはそのまま読み込めます。過去の生成物に埋め込まれたパスやログは、作成当時の記録として保持しています。
