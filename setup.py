"""
cx_Freeze用ビルドスクリプト
ytlive_helper.pywをWindows実行ファイルにビルドします

使用方法:
    python setup.py build

実行ファイルは build/exe.win-amd64-3.x/ フォルダに生成されます
"""

import sys
import os
from cx_Freeze import setup, Executable

# Pythonの標準ライブラリのパスを取得
import sysconfig
python_lib_path = sysconfig.get_paths()["stdlib"]
python_lib_dynload = os.path.join(python_lib_path, "lib-dynload")

# 出力ディレクトリ名を指定（シンプルな名前に変更）
OUTPUT_DIR = "ytlive_helper"  # お好みのディレクトリ名に変更可能

# アプリケーション情報
APP_NAME = "ytlive_helper"
VERSION = "1.0.0"
DESCRIPTION = "YouTube/Twitch配信コメント管理ツール"

# ビルドに含めるファイルとモジュール
include_files = [
    # Pythonスクリプト
    ("gui_components.py", "gui_components.py"),
    ("comment_handler.py", "comment_handler.py"),
    ("update.py", "update.py"),
    ("lang_ja.py", "lang_ja.py"),
    ("lang_en.py", "lang_en.py"),
    ("obssocket.py", "obssocket.py"),
]

# アイコンファイル（存在する場合）
if os.path.exists("icon.ico"):
    include_files.append(("icon.ico", "icon.ico"))
    print("Including icon.ico")
if os.path.exists("icon.png"):
    include_files.append(("icon.png", "icon.png"))
    print("Including icon.png")

# バージョンファイル（存在する場合）
if os.path.exists("version.txt"):
    include_files.append(("version.txt", "version.txt"))
    print("Including version.txt")

# Pythonのencodingsフォルダを明示的に含める（重要！）
encodings_path = os.path.join(python_lib_path, "encodings")
if os.path.exists(encodings_path):
    include_files.append((encodings_path, "lib/encodings"))
    print(f"Including encodings from: {encodings_path}")

# 自動的に含めるパッケージ
packages = [
    # GUI関連
    "tkinter",
    "tkinter.ttk",
    "tkinter.messagebox",
    "tkinter.simpledialog",
    
    # 標準ライブラリ（必須）
    "encodings",           # ★重要: これがないとエラーになる
    "encodings.utf_8",
    "encodings.cp1252",
    "encodings.latin_1",
    "encodings.ascii",
    "encodings.idna",
    "encodings.mbcs",      # Windowsで必要
    
    # importlib関連（必須）
    "importlib",
    "importlib.abc",
    "importlib.machinery",
    
    # collections関連（必須）
    "collections",
    "collections.abc",
    
    # 基本モジュール
    "threading",
    "json",
    "os",
    "sys",
    "re",
    "webbrowser",
    "urllib",
    "urllib.parse",
    "urllib.request",
    "urllib3",
    "datetime",
    "logging",
    "logging.handlers",
    "traceback",
    "socket",
    "time",
    "io",
    "base64",
    "pathlib",
    
    # Web/HTTP関連
    "requests",
    "bs4",  # BeautifulSoup4
    "html",
    "html.parser",
    
    # コメント取得
    "pytchat",  # YouTube用コメント取得
    
    # OBS連携
    "obsws_python",  # OBS WebSocket
    "websocket",
    
    # 画像処理
    "PIL",  # Pillow
    "numpy",
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
    
    # 重要: 標準ライブラリをZIPに含める
    "zip_include_packages": [
        "encodings",
        "importlib", 
        "collections",
        "urllib",
        "email",
        "http",
        "xml",
        "html",
    ],
    
    # Pythonインタープリタの初期化に必要
    "replace_paths": [("*", "")],  # パスを相対パスに変更
    
    # Python環境変数を設定
    "bin_path_includes": [],
    "bin_path_excludes": [],
}

# 実行ファイルの設定
executables = []

# アイコンファイルのパスを確認
icon_file = "icon.ico" if os.path.exists("icon.ico") else None

# リリース版（コンソールなし）.pywを使用
base_release = None
if sys.platform == "win32":
    base_release = "Win32GUI"  # コンソールウィンドウを非表示

executables.append(
    Executable(
        "ytlive_helper.pyw",
        base=base_release,
        target_name=f"{APP_NAME}.exe",
        icon=icon_file,  # exeファイルのアイコン
    )
)

# デバッグ版（コンソール付き）- エラー確認用
# コンソールが表示されるため、エラーメッセージを直接確認できます
# executables.append(
    # Executable(
        # "ytlive_helper.pyw",
        # base=None,  # コンソールを表示
        # target_name=f"{APP_NAME}_debug.exe",
        # icon=icon_file,  # exeファイルのアイコン
    # )
# )

if icon_file:
    print(f"Using icon file: {icon_file}")

# セットアップ
setup(
    name=APP_NAME,
    version=VERSION,
    description=DESCRIPTION,
    options={"build_exe": build_exe_options},
    executables=executables,
)

print("\n" + "="*70)
print("ビルド設定情報")
print("="*70)
print(f"出力ディレクトリ: {OUTPUT_DIR}")
print(f"含まれるパッケージ数: {len(packages)}")
print(f"除外パッケージ数: {len(excludes)}")
print(f"追加ファイル数: {len(include_files)}")
print("="*70)
print("\n重要: encodingsモジュールが含まれていることを確認してください")
print("エラーが発生する場合は、dist/ytlive_helper/lib/ に encodings フォルダがあるか確認してください")
print("="*70)
