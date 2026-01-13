"""
cx_Freeze用ビルドスクリプト
ytlive_helper.pywをWindows実行ファイルにビルドします

使用方法:
    python setup.py build

実行ファイルは build/exe.win-amd64-3.x/ フォルダに生成されます
"""

import sys
from cx_Freeze import setup, Executable

# アプリケーション情報
APP_NAME = "ytlive_helper"
VERSION = "1.0.0"
DESCRIPTION = "YouTube/Twitch配信コメント管理ツール"

# 出力ディレクトリ名を指定（シンプルな名前に変更）
# デフォルト: build/exe.win-amd64-3.11
# カスタム: build/ytlive_helper または dist/ytlive_helper など
OUTPUT_DIR = "ytlive_helper"  # お好みのディレクトリ名に変更可能

# ビルドに含めるファイルとモジュール
include_files = [
    # Pythonスクリプト
    ("gui_components.py", "gui_components.py"),
    ("comment_handler.py", "comment_handler.py"),
    ("update.py", "update.py"),
    ("lang_ja.py", "lang_ja.py"),
    ("lang_en.py", "lang_en.py"),
    ("obssocket.py", "obssocket.py"),
    
    # バージョンファイル（存在する場合）
    ("version.txt", "version.txt"),
    
    # アイコンファイル（存在する場合）
    ("icon.ico", "icon.ico"),
]

# 自動的に含めるパッケージ
packages = [
    "tkinter",
    "tkinter.ttk",
    "tkinter.messagebox",
    "tkinter.simpledialog",
    "threading",
    "json",
    "os",
    "re",
    "webbrowser",
    "urllib",
    "requests",
    "bs4",  # BeautifulSoup4
    "datetime",
    "collections",
    "logging",
    "traceback",
    "socket",
    "time",
    "pytchat",  # YouTube用コメント取得
    "obsws_python",  # OBS WebSocket
    "PIL",  # Pillow
    "numpy",
    "base64",
    "io",
]

# 除外するパッケージ（不要な大きいライブラリを除外してサイズを削減）
excludes = [
    "matplotlib",
    "scipy",
    "pandas",
    "pytest",
    "setuptools",
]

# ビルドオプション
build_exe_options = {
    "packages": packages,
    "excludes": excludes,
    "include_files": include_files,
    "include_msvcr": True,  # Visual C++ランタイムを含める
    "optimize": 2,  # 最適化レベル
    "build_exe": OUTPUT_DIR,  # 出力ディレクトリを指定
}

# 実行ファイルの設定
base = None
if sys.platform == "win32":
    base = "Win32GUI"  # コンソールウィンドウを非表示にする（.pywファイル用）

executables = [
    Executable(
        "ytlive_helper.pyw",
        base=base,
        target_name=f"{APP_NAME}.exe",
        icon='icon.ico',  # アイコンファイルがあれば "icon.ico" を指定
        # shortcut_name=APP_NAME,
        # shortcut_dir="DesktopFolder",
    )
]

# セットアップ
setup(
    name=APP_NAME,
    version=VERSION,
    description=DESCRIPTION,
    options={"build_exe": build_exe_options},
    executables=executables,
)
