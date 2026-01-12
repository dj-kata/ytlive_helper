# -*- coding: utf-8 -*-
"""
GUI Components Module
配信管理アプリケーションのGUI構築とUI更新を担当
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading
import logging

# ロガー設定
logger = logging.getLogger(__name__)

# debug_print関数（ytlive_helper.pywから呼ばれる場合もあるため定義）
def debug_print(*args, **kwargs):
    """デバッグ出力（GUI Components用）"""
    try:
        # ytlive_helper.pywのdebug_printが存在する場合はそちらを使う
        import __main__
        if hasattr(__main__, 'debug_print'):
            __main__.debug_print(*args, **kwargs)
        else:
            # なければ標準出力
            print(*args, **kwargs)
    except:
        # エラーが起きても無視
        pass

def extract_title_info(title, pattern_series, pattern_base_title_list):
    """タイトル抽出関数（メインモジュールから取得）"""
    try:
        import __main__
        if hasattr(__main__, 'extract_title_info'):
            return __main__.extract_title_info(title, pattern_series, pattern_base_title_list)
        else:
            # フォールバック: 何もしない
            return title, None
    except:
        return title, None


class GUIComponents:
    """GUI構築とUI更新を担当するMixinクラス"""
    
    def add_entry_context_menu(self, entry_widget):
        """Entry/Entryウィジェットに右クリックメニューを追加
        
        Args:
            entry_widget: Entry/Entryウィジェット
        """
        # 右クリックメニューを作成
        context_menu = tk.Menu(entry_widget, tearoff=0)
        
        def cut_text():
            entry_widget.event_generate('<<Cut>>')
        
        def copy_text():
            entry_widget.event_generate('<<Copy>>')
        
        def paste_text():
            entry_widget.event_generate('<<Paste>>')
        
        def select_all():
            entry_widget.select_range(0, tk.END)
            entry_widget.icursor(tk.END)
        
        context_menu.add_command(label=self.strings["context_menu"]["cut"], command=cut_text)
        context_menu.add_command(label=self.strings["context_menu"]["copy"], command=copy_text)
        context_menu.add_command(label=self.strings["context_menu"]["paste"], command=paste_text)
        context_menu.add_separator()
        context_menu.add_command(label=self.strings["context_menu"]["select_all"], command=select_all)
        
        def show_context_menu(event):
            try:
                context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                context_menu.grab_release()
        
        entry_widget.bind("<Button-3>", show_context_menu)
    
    def setup_gui(self):
        """GUIセットアップ"""
        # メニューバー
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # ファイルメニュー
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label=self.strings["menu"]["file"], menu=file_menu)
        file_menu.add_command(label=self.strings["menu"]["settings"], command=self.show_settings)
        file_menu.add_separator()
        file_menu.add_command(label=self.strings["menu"]["exit"], command=self.on_closing)
        
        # 言語メニュー
        language_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label=self.strings["menu"]["language"], menu=language_menu)
        language_menu.add_command(label="日本語", command=lambda: self.change_language('ja'))
        language_menu.add_command(label="English", command=lambda: self.change_language('en'))
        
        # メインフレーム
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Treeviewのスタイル設定（背景色が確実に反映されるように）
        style = ttk.Style()
        style.map('Treeview', 
                  background=[('selected', '#0078d7')],  # 選択時の色
                  foreground=[('selected', 'white')])
        
        # 配信管理フレーム
        stream_frame = ttk.LabelFrame(main_frame, text=self.strings["stream"]["title"])
        stream_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 配信追加
        add_frame = ttk.Frame(stream_frame)
        add_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(add_frame, text=self.strings["stream"]["url_label"]).pack(side=tk.LEFT)
        self.url_entry = ttk.Entry(add_frame, width=70)
        self.url_entry.pack(side=tk.LEFT, padx=(5, 0))
        self.add_entry_context_menu(self.url_entry)  # 右クリックメニュー追加
        
        # Enterキーで追加
        self.url_entry.bind("<Return>", lambda e: self.add_stream())
        
        ttk.Button(add_frame, text=self.strings["stream"]["add_button"], command=self.add_stream).pack(side=tk.LEFT, padx=(10, 0))
        
        # プラットフォーム表示（読み取り専用）
        platform_label = ttk.Label(add_frame, text=self.strings["stream"]["platform_auto"], foreground="gray")
        platform_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # 配信リスト - Grid layoutで横スクロールバーも追加
        stream_list_frame = ttk.Frame(stream_frame)
        stream_list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # Treeview for stream list - 列名を左揃えに、カラム幅固定
        columns = (self.strings["columns"]["id"], self.strings["columns"]["platform"], 
                  self.strings["columns"]["title"], self.strings["columns"]["url"], 
                  self.strings["columns"]["status"])
        self.stream_tree = ttk.Treeview(stream_list_frame, columns=columns, show='headings', height=6)
        
        # カラム幅を固定（stretch=Falseで自動リサイズを無効化）
        column_widths = {
            self.strings["columns"]["id"]: 120, 
            self.strings["columns"]["platform"]: 80, 
            self.strings["columns"]["title"]: 250, 
            self.strings["columns"]["url"]: 300, 
            self.strings["columns"]["status"]: 100
        }
        for col in columns:
            self.stream_tree.heading(col, text=col, anchor='w')  # 列名を左揃えに
            self.stream_tree.column(col, width=column_widths[col], stretch=False)
        
        # 縦スクロールバー
        stream_scrollbar_y = ttk.Scrollbar(stream_list_frame, orient=tk.VERTICAL, command=self.stream_tree.yview)
        # 横スクロールバー
        stream_scrollbar_x = ttk.Scrollbar(stream_list_frame, orient=tk.HORIZONTAL, command=self.stream_tree.xview)
        
        self.stream_tree.configure(yscrollcommand=stream_scrollbar_y.set, xscrollcommand=stream_scrollbar_x.set)
        
        # タグの背景色を設定（foregroundも明示的に指定）
        self.stream_tree.tag_configure('running', background='#ffaaaa', foreground='black')  # 受信中: 薄い赤
        self.stream_tree.tag_configure('stopped', background='#ffffff', foreground='black')  # 停止中: 白
        
        # グリッドレイアウトで配置
        self.stream_tree.grid(row=0, column=0, sticky='nsew')
        stream_scrollbar_y.grid(row=0, column=1, sticky='ns')
        stream_scrollbar_x.grid(row=1, column=0, sticky='ew')
        
        # グリッド設定
        stream_list_frame.grid_rowconfigure(0, weight=1)
        stream_list_frame.grid_columnconfigure(0, weight=1)
        
        # 配信リスト用の右クリックメニュー
        self.stream_context_menu = tk.Menu(self.root, tearoff=0)
        self.stream_context_menu.add_command(label=self.strings["context_menu"]["start_receive"], command=self.start_selected_stream)
        self.stream_context_menu.add_command(label=self.strings["context_menu"]["stop_receive"], command=self.stop_selected_stream)
        self.stream_context_menu.add_separator()
        self.stream_context_menu.add_command(label=self.strings["stream"]["edit_url"], command=self.edit_stream_url)
        self.stream_context_menu.add_command(label=self.strings["stream"]["update_title"], command=self.update_selected_stream_title)
        self.stream_context_menu.add_separator()
        self.stream_context_menu.add_command(label=self.strings["context_menu"]["tweet_announcement"], command=self.tweet_stream_announcement)
        self.stream_context_menu.add_separator()
        self.stream_context_menu.add_command(label=self.strings["stream"]["delete"], command=self.remove_selected_stream)
        
        def on_stream_right_click(event):
            # 選択されたアイテムがあるかチェック
            item = self.stream_tree.identify_row(event.y)
            if item:
                self.stream_tree.selection_set(item)
                self.stream_context_menu.post(event.x_root, event.y_root)
        
        def on_stream_double_click(event):
            # ダブルクリックされた列を確認
            column = self.stream_tree.identify_column(event.x)
            column_index = int(column.replace('#', '')) - 1
            
            # URL列（インデックス3）の場合は編集
            if column_index == 3:
                self.edit_stream_url()
                return
            
            # それ以外の列の場合は受信のON/OFF切り替え
            item = self.stream_tree.identify_row(event.y)
            if item:
                self.stream_tree.selection_set(item)
                # 現在のステータスを確認
                values = self.stream_tree.item(item)['values']
                stream_id = values[0]
                settings = self.stream_manager.streams.get(stream_id)
                if settings:
                    if settings.is_active:
                        self.stop_selected_stream()
                    else:
                        self.start_selected_stream()
        
        self.stream_tree.bind("<Button-3>", on_stream_right_click)  # 右クリック
        self.stream_tree.bind("<Double-Button-1>", on_stream_double_click)  # ダブルクリック
        
        # 配信選択時に情報を更新
        def on_stream_select(event):
            selection = self.stream_tree.selection()
            if selection:
                item = self.stream_tree.item(selection[0])
                stream_id = item['values'][0]
                self.update_selected_stream_info(stream_id)
        
        self.stream_tree.bind("<<TreeviewSelect>>", on_stream_select)
        
        # 配信操作ボタン
        stream_button_frame = ttk.Frame(stream_frame)
        stream_button_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
        
        ttk.Button(stream_button_frame, text=self.strings["announcement"]["button"], command=self.show_announcement_dialog).pack(side=tk.LEFT, padx=(0, 5))
        
        # 操作説明
        help_label = ttk.Label(stream_frame, 
                              text=self.strings["stream"]["help_text"], 
                              foreground="gray")
        help_label.pack(padx=10, pady=(5, 10))
        
        # 共通リクエスト管理エリア
        request_frame = ttk.LabelFrame(main_frame, text=self.strings["request"]["title"])
        request_frame.pack(fill=tk.X, pady=(10, 0))
        
        # リクエストリストTreeview
        request_list_frame = ttk.Frame(request_frame)
        request_list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Treeview作成
        request_columns = (
            self.strings["columns"]["number"], 
            self.strings["columns"]["request_content"], 
            self.strings["columns"]["user"], 
            self.strings["columns"]["platform"]
        )
        self.request_tree = ttk.Treeview(request_list_frame, columns=request_columns, show='headings', height=8)
        
        # カラム幅を固定
        column_widths = {
            self.strings["columns"]["number"]: 60, 
            self.strings["columns"]["request_content"]: 350, 
            self.strings["columns"]["user"]: 120, 
            self.strings["columns"]["platform"]: 100
        }
        for col in request_columns:
            self.request_tree.heading(col, text=col, anchor='w')
            self.request_tree.column(col, width=column_widths[col], stretch=False)
        
        # 縦スクロールバー
        req_scrollbar_y = ttk.Scrollbar(request_list_frame, orient=tk.VERTICAL, command=self.request_tree.yview)
        # 横スクロールバー
        req_scrollbar_x = ttk.Scrollbar(request_list_frame, orient=tk.HORIZONTAL, command=self.request_tree.xview)
        
        self.request_tree.configure(yscrollcommand=req_scrollbar_y.set, xscrollcommand=req_scrollbar_x.set)
        
        # グリッドレイアウトで配置
        self.request_tree.grid(row=0, column=0, sticky='nsew')
        req_scrollbar_y.grid(row=0, column=1, sticky='ns')
        req_scrollbar_x.grid(row=1, column=0, sticky='ew')
        
        # グリッド設定
        request_list_frame.grid_rowconfigure(0, weight=1)
        request_list_frame.grid_columnconfigure(0, weight=1)
        
        # リクエスト操作ボタン
        req_button_frame = ttk.Frame(request_frame)
        req_button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        # 手動追加エントリ
        ttk.Label(req_button_frame, text=self.strings["request"]["manual_add_label"]).pack(side=tk.LEFT)
        self.manual_req_entry = ttk.Entry(req_button_frame, width=30)
        self.manual_req_entry.pack(side=tk.LEFT, padx=(5, 10))
        self.add_entry_context_menu(self.manual_req_entry)  # 右クリックメニュー追加
        
        # Enterキーで追加
        self.manual_req_entry.bind("<Return>", lambda e: self.add_manual_request())
        
        ttk.Button(req_button_frame, text=self.strings["request"]["add_button"], command=self.add_manual_request).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(req_button_frame, text=self.strings["request"]["delete_button"], command=self.remove_selected_request).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(req_button_frame, text=self.strings["request"]["move_up"], command=self.move_request_up).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(req_button_frame, text=self.strings["request"]["move_down"], command=self.move_request_down).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(req_button_frame, text=self.strings["request"]["clear"], command=self.clear_all_requests).pack(side=tk.LEFT, padx=(0, 5))
        
        # 共通コメント表示エリア
        comment_frame = ttk.LabelFrame(main_frame, text=self.strings["comment"]["title"])
        comment_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        # コメントTreeview - 横スクロールも追加、カラム幅固定
        comment_columns = (
            self.strings["columns"]["user"], 
            self.strings["columns"]["comment"], 
            self.strings["columns"]["stream_id"], 
            self.strings["columns"]["platform"],
            self.strings["columns"]["datetime"]
        )
        self.comment_tree = ttk.Treeview(comment_frame, columns=comment_columns, show='headings', height=12)
        
        # カラム幅を固定（stretch=Falseで自動リサイズを無効化）
        column_widths = {
            self.strings["columns"]["user"]: 120, 
            self.strings["columns"]["comment"]: 400, 
            self.strings["columns"]["stream_id"]: 120, 
            self.strings["columns"]["platform"]: 100,
            self.strings["columns"]["datetime"]: 140
        }
        for col in comment_columns:
            self.comment_tree.heading(col, text=col, anchor='w')  # 列名を左揃えに
            self.comment_tree.column(col, width=column_widths[col], stretch=False)
        
        # 縦スクロールバー
        comment_scrollbar_y = ttk.Scrollbar(comment_frame, orient=tk.VERTICAL, command=self.comment_tree.yview)
        # 横スクロールバー
        comment_scrollbar_x = ttk.Scrollbar(comment_frame, orient=tk.HORIZONTAL, command=self.comment_tree.xview)
        
        self.comment_tree.configure(yscrollcommand=comment_scrollbar_y.set, xscrollcommand=comment_scrollbar_x.set)
        
        # タグの背景色を設定
        self.comment_tree.tag_configure('request_add', background='#aaffaa', foreground='black')      # リクエスト追加: 薄い緑
        self.comment_tree.tag_configure('request_delete', background='#aaaaff', foreground='black')   # リクエスト削除: 薄い青
        self.comment_tree.tag_configure('platform_twitch', background='#ffddff', foreground='black')  # Twitch: 薄い紫
        self.comment_tree.tag_configure('platform_youtube', background='#ffdddd', foreground='black') # YouTube: 薄い赤
        
        # 右クリックメニュー
        self.comment_context_menu = tk.Menu(self.root, tearoff=0)
        self.comment_context_menu.add_command(label=self.strings["context_menu"]["add_manager"], command=self.add_manager_from_comment)
        self.comment_context_menu.add_command(label=self.strings["context_menu"]["add_ng_user"], command=self.add_ng_user_from_comment)
        
        def on_comment_right_click(event):
            # 選択されたアイテムがあるかチェック
            item = self.comment_tree.identify_row(event.y)
            if item:
                self.comment_tree.selection_set(item)
                self.comment_context_menu.post(event.x_root, event.y_root)
        
        self.comment_tree.bind("<Button-3>", on_comment_right_click)  # 右クリック
        
        # Treeviewとスクロールバーを配置
        self.comment_tree.grid(row=0, column=0, sticky='nsew', padx=(10, 0), pady=10)
        comment_scrollbar_y.grid(row=0, column=1, sticky='ns', pady=10)
        comment_scrollbar_x.grid(row=1, column=0, sticky='ew', padx=(10, 0))
        
        # グリッド設定
        comment_frame.grid_rowconfigure(0, weight=1)
        comment_frame.grid_columnconfigure(0, weight=1)
        
        # コメント操作ボタン
        comment_button_frame = ttk.Frame(comment_frame)
        comment_button_frame.grid(row=2, column=0, columnspan=2, sticky='ew', padx=10, pady=(0, 10))
        
        ttk.Button(comment_button_frame, text=self.strings["comment"]["clear_button"], command=self.clear_all_comments).pack(side=tk.LEFT)
        
        # 自動スクロール設定
        self.auto_scroll = tk.BooleanVar(value=True)
        ttk.Checkbutton(comment_button_frame, text=self.strings["comment"]["auto_scroll"], variable=self.auto_scroll).pack(side=tk.LEFT, padx=(10, 0))
        
        # 選択中の配信情報（リクエスト一覧の上に表示）
        stream_info_frame = ttk.LabelFrame(main_frame, text=self.strings["selected_stream_info"]["title"])
        stream_info_frame.pack(fill=tk.X, pady=(10, 0))
        
        # 配信情報の内側フレーム
        info_inner_frame = ttk.Frame(stream_info_frame)
        info_inner_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # 1行目：状態、コメント数、タイトル
        row1_frame = ttk.Frame(info_inner_frame)
        row1_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(row1_frame, text=self.strings["selected_stream_info"]["status"]).pack(side=tk.LEFT)
        self.selected_status_label = ttk.Label(row1_frame, text="-", foreground="gray")
        self.selected_status_label.pack(side=tk.LEFT, padx=(5, 20))
        
        ttk.Label(row1_frame, text=self.strings["selected_stream_info"]["comment_count"]).pack(side=tk.LEFT)
        self.selected_comment_count_label = ttk.Label(row1_frame, text="-")
        self.selected_comment_count_label.pack(side=tk.LEFT, padx=(5, 20))
        
        ttk.Label(row1_frame, text=self.strings["selected_stream_info"]["stream_title"]).pack(side=tk.LEFT)
        self.selected_title_label = ttk.Label(row1_frame, text="-", foreground="blue", cursor="hand2")
        self.selected_title_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # タイトルクリックでブラウザを開く
        def open_selected_stream_in_browser(event):
            if hasattr(self, 'selected_stream_id') and self.selected_stream_id:
                settings = self.stream_manager.streams.get(self.selected_stream_id)
                if settings:
                    import webbrowser
                    webbrowser.open(settings.url)
        
        self.selected_title_label.bind("<Button-1>", open_selected_stream_in_browser)
        
        # タイトルホバー時のアンダーライン
        def on_title_enter(event):
            self.selected_title_label.configure(font=('TkDefaultFont', 9, 'underline'))
        
        def on_title_leave(event):
            self.selected_title_label.configure(font=('TkDefaultFont', 9))
        
        self.selected_title_label.bind("<Enter>", on_title_enter)
        self.selected_title_label.bind("<Leave>", on_title_leave)
        
        # 2行目：プラットフォーム、URL
        row2_frame = ttk.Frame(info_inner_frame)
        row2_frame.pack(fill=tk.X)
        
        ttk.Label(row2_frame, text=self.strings["selected_stream_info"]["platform"]).pack(side=tk.LEFT)
        self.selected_platform_label = ttk.Label(row2_frame, text="-")
        self.selected_platform_label.pack(side=tk.LEFT, padx=(5, 20))
        
        ttk.Label(row2_frame, text=self.strings["selected_stream_info"]["url"]).pack(side=tk.LEFT)
        self.selected_url_label = ttk.Label(row2_frame, text="-", foreground="blue", cursor="hand2")
        self.selected_url_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # URLクリックでブラウザを開く
        def open_selected_url_in_browser(event):
            if hasattr(self, 'selected_stream_id') and self.selected_stream_id:
                settings = self.stream_manager.streams.get(self.selected_stream_id)
                if settings:
                    import webbrowser
                    webbrowser.open(settings.url)
        
        self.selected_url_label.bind("<Button-1>", open_selected_url_in_browser)
        
        # URLホバー時のアンダーライン
        def on_url_enter(event):
            self.selected_url_label.configure(font=('TkDefaultFont', 9, 'underline'))
        
        def on_url_leave(event):
            self.selected_url_label.configure(font=('TkDefaultFont', 9))
        
        self.selected_url_label.bind("<Enter>", on_url_enter)
        self.selected_url_label.bind("<Leave>", on_url_leave)
        
        # 選択中の配信IDを保持
        self.selected_stream_id = None
        
        # ウィンドウ位置を復元
        try:
            if hasattr(self.global_settings, 'window_x') and hasattr(self.global_settings, 'window_y'):
                x = self.global_settings.window_x
                y = self.global_settings.window_y
                # 画面の範囲内に収まるかチェック
                screen_width = self.root.winfo_screenwidth()
                screen_height = self.root.winfo_screenheight()
                if 0 <= x < screen_width and 0 <= y < screen_height:
                    self.root.geometry(f"+{x}+{y}")
                    logger.info(f"Window position restored: x={x}, y={y}")
        except Exception as e:
            logger.error(f"Failed to restore window position: {e}")
    
    def update_stream_list(self):
        """配信リストを更新"""
        debug_print(f"DEBUG: update_stream_list() called")
        # 既存の項目を削除
        for item in self.stream_tree.get_children():
            self.stream_tree.delete(item)
            
        # 新しい項目を追加
        for stream_id, settings in self.stream_manager.streams.items():
            status = self.strings["stream"]["status_receiving"] if settings.is_active else self.strings["stream"]["status_stopped"]
            # タイトルが長い場合は省略表示
            display_title = settings.title[:40] + "..." if len(settings.title) > 40 else settings.title
            
            # タグを設定（受信中なら'running'、停止中なら'stopped'）
            tag = 'running' if settings.is_active else 'stopped'
            
            debug_print(f"DEBUG: Adding stream to list: {stream_id}, URL: {settings.url[:30]}..., Status: {status}")
            
            self.stream_tree.insert('', tk.END, values=(
                stream_id, settings.platform, display_title, settings.url[:50], status
            ), tags=(tag,))
    
    def add_stream_tab(self, stream_settings):
        """配信の情報を初期化（タブは廃止）"""
        # 必要な属性を初期化
        stream_settings.processed_requests = 0
        
        # 最初の配信を自動選択
        if not self.selected_stream_id:
            self.selected_stream_id = stream_settings.stream_id
            self.update_selected_stream_info(stream_settings.stream_id)
    
    def update_selected_stream_info(self, stream_id):
        """選択中の配信情報を更新"""
        self.selected_stream_id = stream_id
        settings = self.stream_manager.streams.get(stream_id)
        
        if settings:
            # 状態を更新
            status_text = self.strings["stream"]["status_receiving"] if settings.is_active else self.strings["stream"]["status_stopped"]
            status_color = "red" if settings.is_active else "gray"
            self.selected_status_label.config(text=status_text, foreground=status_color)
            
            # コメント数を更新
            comment_count = len(settings.comments) if hasattr(settings, 'comments') else 0
            self.selected_comment_count_label.config(text=str(comment_count))
            
            # タイトルを更新
            self.selected_title_label.config(text=settings.title)
            
            # プラットフォームを更新
            self.selected_platform_label.config(text=settings.platform.title())
            
            # URLを更新（長い場合は省略）
            url_display = settings.url if len(settings.url) <= 80 else settings.url[:77] + "..."
            self.selected_url_label.config(text=url_display)
        else:
            # 配信が存在しない場合はリセット
            self.selected_status_label.config(text="-", foreground="gray")
            self.selected_comment_count_label.config(text="-")
            self.selected_title_label.config(text="-")
            self.selected_platform_label.config(text="-")
            self.selected_url_label.config(text="-")
            self.selected_stream_id = None
    
    def update_request_display(self):
        """リクエスト表示を更新"""
        # Treeviewをクリア
        for item in self.request_tree.get_children():
            self.request_tree.delete(item)
        
        # リクエストを番号付きで表示
        for index, req in enumerate(self.common_requests, start=1):
            self.request_tree.insert('', tk.END, values=(
                index,
                req['content'],
                req['author'],
                req['platform']
            ))
        
        # Ajax用のXMLファイルを生成
        self.generate_todo_xml()
    
    def edit_stream_url(self):
        """選択された配信のURLを編集"""
        selection = self.stream_tree.selection()
        if not selection:
            messagebox.showwarning(self.strings["messages"]["warning"], self.strings["messages"]["select_stream"])
            return
            
        item = self.stream_tree.item(selection[0])
        stream_id = item['values'][0]
        settings = self.stream_manager.streams.get(stream_id)
        
        if not settings:
            return
        
        current_url = settings.url
        
        # カスタムURL編集ダイアログ
        dialog = tk.Toplevel(self.root)
        dialog.title(self.strings["dialog"]["url_edit_title"])
        dialog.geometry("650x150")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 配信ID表示
        info_frame = ttk.Frame(dialog)
        info_frame.pack(fill=tk.X, padx=20, pady=(20, 10))
        ttk.Label(info_frame, text=f"配信ID: {stream_id}", font=('', 10, 'bold')).pack(anchor=tk.W)
        
        # URL入力
        url_frame = ttk.Frame(dialog)
        url_frame.pack(fill=tk.X, padx=20, pady=10)
        ttk.Label(url_frame, text=self.strings["dialog"]["new_url_label"]).pack(side=tk.LEFT)
        url_entry = ttk.Entry(url_frame, width=50)
        url_entry.pack(side=tk.LEFT, padx=(5, 0), fill=tk.X, expand=True)
        url_entry.insert(0, current_url)
        url_entry.select_range(0, tk.END)
        url_entry.focus()
        
        # 右クリックメニュー追加
        self.add_entry_context_menu(url_entry)
        
        # ボタン
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=20, pady=(10, 20))
        
        result = {'url': None}
        
        def on_ok():
            result['url'] = url_entry.get().strip()
            dialog.destroy()
        
        def on_cancel():
            dialog.destroy()
        
        ttk.Button(button_frame, text=self.strings["dialog"]["ok_button"], command=on_ok).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text=self.strings["dialog"]["cancel_button"], command=on_cancel).pack(side=tk.RIGHT)
        
        # Enterキーで確定
        url_entry.bind("<Return>", lambda e: on_ok())
        url_entry.bind("<Escape>", lambda e: on_cancel())
        
        # ダイアログを中央に配置
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - dialog.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")
        
        # ダイアログが閉じるまで待機
        self.root.wait_window(dialog)
        
        new_url = result['url']
        
        if new_url and new_url != current_url:
            # プラットフォームを再判定
            new_platform = self.detect_platform(new_url)
            if not new_platform:
                messagebox.showerror(
                    self.strings["messages"]["error"], 
                    self.strings["messages"]["unsupported_url"]
                )
                return
            
            # 受信中の場合は自動的に停止
            was_active = settings.is_active
            if was_active:
                logger.info(f"Stopping stream {stream_id} before URL change")
                debug_print(f"DEBUG: Stopping stream {stream_id} before URL change")
                self.stream_manager.stop_stream(stream_id)
                # タブのステータス更新
                if hasattr(settings, 'status_label'):
                    settings.status_label.config(
                        text=self.strings["stream_info"]["status_stopped"], 
                        foreground="black"
                    )
                debug_print(f"DEBUG: Stream {stream_id} stopped successfully")
                # リストを更新（停止状態を反映）
                self.update_stream_list()
            
            # YouTube URLの場合は正規化
            if new_platform == 'youtube':
                new_url = self.normalize_youtube_url(new_url)
                logger.info(f"YouTube URL normalized: {new_url}")
                debug_print(f"DEBUG: YouTube URL normalized: {new_url}")
            
            # URLとプラットフォームを更新
            old_url = settings.url
            logger.info(f"Changing URL from {old_url} to {new_url}")
            debug_print(f"DEBUG: Changing URL from {old_url} to {new_url}")
            settings.url = new_url
            settings.platform = new_platform
            debug_print(f"DEBUG: URL changed - settings.url is now: {settings.url}")
            debug_print(f"DEBUG: Platform changed - settings.platform is now: {settings.platform}")
            
            # タイトルを「読み込み中」に設定
            settings.title = self.strings["stream_info"]["title_loading"]
            
            # リストを更新（新しいURLを反映）
            debug_print(f"DEBUG: Calling update_stream_list() to reflect new URL")
            self.update_stream_list()
            debug_print(f"DEBUG: update_stream_list() completed")
            
            # 選択中の配信情報を更新
            if self.selected_stream_id == stream_id:
                self.update_selected_stream_info(stream_id)
            
            # 強制的にGUI更新を反映
            self.root.update_idletasks()
            debug_print(f"DEBUG: GUI update_idletasks() completed")
            
            # バックグラウンドでタイトルを取得（既存のfetch_title_asyncメソッドを使用）
            self.fetch_title_async(stream_id)
            
            # メッセージ表示
            if was_active:
                messagebox.showinfo(
                    self.strings["messages"]["info"], 
                    f"URLを変更しました。\n受信を停止しました。\n\n新しいURL: {new_url[:50]}..."
                )
            else:
                messagebox.showinfo(
                    self.strings["messages"]["info"], 
                    self.strings["messages"]["url_updated"]
                )
    
    def show_announcement_dialog(self):
        """告知ダイアログを表示"""
        if not self.stream_manager.streams:
            messagebox.showwarning(self.strings['messages']['warning'], self.strings['announcement']['warning_no_streams'])
            return
        
        # ダイアログ作成
        dialog = tk.Toplevel(self.root)
        dialog.title(self.strings['announcement']['dialog_title'])
        dialog.geometry("700x700")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 告知内容フレーム
        content_frame = ttk.LabelFrame(dialog, text=self.strings['announcement']['content_frame'])
        content_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # 入力エリア（編集可能）
        input_label = ttk.Label(content_frame, text=self.strings['announcement']['basic_text_label'])
        input_label.pack(anchor=tk.W, padx=10, pady=(10, 5))
        
        input_text_widget = tk.Text(content_frame, height=3, width=60, wrap=tk.WORD)
        input_text_widget.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        # 保存されている告知テンプレートを読み込む（存在しない場合はデフォルト値）
        template = getattr(self.global_settings, 'announcement_template', self.strings['default_settings']['announcement'])
        input_text_widget.insert("1.0", template)
        
        # プレビューエリア（読み取り専用）
        preview_label = ttk.Label(content_frame, text=self.strings['announcement']['preview_label'])
        preview_label.pack(anchor=tk.W, padx=10, pady=(10, 5))
        
        preview_text_widget = tk.Text(content_frame, height=8, width=60, wrap=tk.WORD, state=tk.DISABLED)
        preview_text_widget.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        # 配信選択フレーム
        stream_select_frame = ttk.LabelFrame(dialog, text=self.strings['announcement']['stream_select_frame'])
        stream_select_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # Treeview作成（チェックボックス + ラジオボタン風）
        tree_frame = ttk.Frame(stream_select_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        columns = ("include", "source", "stream_id", "platform", "title")
        tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=6)
        
        # カラム設定
        tree.heading("include",   text=self.strings['announcement']['include_column'])
        tree.heading("source",    text=self.strings['announcement']['source_column'])
        tree.heading("stream_id", text=self.strings['columns']['stream_id'])
        tree.heading("platform",  text=self.strings['columns']['platform'])
        tree.heading("title",     text=self.strings['columns']['title'])
        
        tree.column("include", width=100, anchor="center")
        tree.column("source", width=120, anchor="center")
        tree.column("stream_id", width=120)
        tree.column("platform", width=80)
        tree.column("title", width=250)
        
        # スクロールバー
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # OBS設定チェック
        obs_configured = bool(self.global_settings.obs_host and self.global_settings.obs_port)
        
        # データ構造（配信ごとの状態を保持）
        stream_states = {}
        first_stream = True
        
        for stream_id, settings in self.stream_manager.streams.items():
            # デフォルト: 全て含める、最初の配信を基本情報取得元に
            stream_states[stream_id] = {
                'include': True,
                'source': first_stream,
                'settings': settings
            }
            
            include_mark = "✓" if stream_states[stream_id]['include'] else ""
            source_mark = "●" if stream_states[stream_id]['source'] and obs_configured else ""
            if stream_states[stream_id]['source'] and not obs_configured:
                source_mark = self.strings['announcement']['obs_not_configured']
            
            title_display = settings.title[:40] + "..." if len(settings.title) > 40 else settings.title
            
            tree.insert('', tk.END, iid=stream_id, values=(
                include_mark,
                source_mark,
                stream_id,
                settings.platform,
                title_display
            ))
            
            first_stream = False
        
        # プレビュー更新関数
        def update_preview(*args):
            """プレビューテキストを更新"""
            # 告知内容を取得
            announcement_text = input_text_widget.get("1.0", tk.END).strip()
            
            # プレビュー本文を構築
            preview_text = announcement_text
            
            # 含める配信を追加
            for stream_id, state in stream_states.items():
                if state['include']:
                    preview_text += f"\n\n{state['settings'].title}\n{state['settings'].url}"
            
            # プレビューエリアを更新
            preview_text_widget.config(state=tk.NORMAL)
            preview_text_widget.delete("1.0", tk.END)
            preview_text_widget.insert("1.0", preview_text)
            preview_text_widget.config(state=tk.DISABLED)
        
        # 初期プレビューを表示
        update_preview()
        
        # 告知内容が変更されたらプレビューを更新
        input_text_widget.bind("<KeyRelease>", update_preview)
        
        # クリックイベント
        def on_tree_click(event):
            region = tree.identify("region", event.x, event.y)
            if region != "cell":
                return
            
            column = tree.identify_column(event.x)
            item = tree.identify_row(event.y)
            
            if not item:
                return
            
            stream_id = item
            
            if column == "#1":  # 「告知に含める」列
                # トグル
                stream_states[stream_id]['include'] = not stream_states[stream_id]['include']
                mark = "✓" if stream_states[stream_id]['include'] else ""
                tree.set(item, "include", mark)
                
                # プレビューを更新
                update_preview()
                
            elif column == "#2" and obs_configured:  # 「基本情報取得元」列（OBS設定済みのみ）
                # 他を全てFalseに、このアイテムだけTrue
                for sid in stream_states:
                    stream_states[sid]['source'] = (sid == stream_id)
                
                # 全アイテムを更新
                for sid in stream_states:
                    source_mark = "●" if stream_states[sid]['source'] else ""
                    tree.set(sid, "source", source_mark)
        
        tree.bind("<Button-1>", on_tree_click)
        
        # 説明ラベル
        if not obs_configured:
            help_text = self.strings['announcement']['help_text_not_configured']
        else:
            help_text = self.strings['announcement']['help_text_configured']
        
        help_label = ttk.Label(stream_select_frame, text=help_text, foreground="gray", font=('TkDefaultFont', 8))
        help_label.pack(padx=10, pady=(0, 10))
        
        # ボタンフレーム
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        result = {'ok': False}
        
        def on_ok():
            # 告知内容を取得
            announcement_text = input_text_widget.get("1.0", tk.END).strip()
            
            # 含める配信リスト
            included_streams = []
            source_stream_id = None
            
            for stream_id, state in stream_states.items():
                if state['include']:
                    included_streams.append({
                        'stream_id': stream_id,
                        'platform': state['settings'].platform,
                        'url': state['settings'].url,
                        'title': state['settings'].title
                    })
                if state['source']:
                    source_stream_id = stream_id
            
            if not included_streams:
                messagebox.showwarning(self.strings['messages']['warning'], self.strings['announcement']['warning_no_selection'])
                return
            
            # ツイート本文を構築
            tweet_text = announcement_text
            
            # 含める配信のタイトルとURLを追加
            for stream in included_streams:
                tweet_text += f"\n\n{stream['title']}\n{stream['url']}"
            
            # 結果を出力（デバッグ用）
            print(f"\n{'='*60}")
            print(f"告知情報")
            print(f"{'='*60}")
            print(f"\n【告知内容】")
            print(announcement_text)
            print(f"\n【含める配信】")
            for stream in included_streams:
                print(f"  - {stream['stream_id']} ({stream['platform']}): {stream['url']}")
            
            if source_stream_id and obs_configured:
                source_settings = stream_states[source_stream_id]['settings']
                base_title, series = extract_title_info(
                    source_settings.title,
                    self.global_settings.pattern_series,
                    self.global_settings.pattern_base_title_list
                )
                
                # 配信内容を取得
                today_content = ""
                try:
                    content_marker = getattr(self.global_settings, 'content_marker', self.strings['default_settings']['content_marker'])
                    today_content = self.get_today_content(
                        source_settings.platform,
                        source_settings.url,
                        content_marker
                    )
                except Exception as e:
                    logger.error(f"Failed to get today's content: {e}")
                
                print(f"\n【基本情報取得元】")
                print(f"  配信ID: {source_stream_id}")
                print(f"  タイトル: {source_settings.title}")
                print(f"  base_title: {base_title}")
                print(f"  series: {series}")
                print(f"  today_content: {today_content}")

                self.setup_obs()
                if self.obs:
                    self.obs.change_text('ythSeriesNum', series)
                    self.obs.change_text('ythMainTitle', base_title)
                    self.obs.change_text('ythTodayContent', today_content)
            
            print(f"\n【生成されたツイート本文】")
            print(tweet_text)
            print(f"{'='*60}\n")
            
            # 告知テンプレートを保存
            self.global_settings.announcement_template = announcement_text
            self.global_settings.save()
            
            # Twitter投稿画面を開く
            import urllib.parse
            import webbrowser
            
            encoded_text = urllib.parse.quote(tweet_text)
            twitter_url = f"https://twitter.com/intent/tweet?text={encoded_text}"
            
            print(f"Twitter投稿画面を開きます...")
            webbrowser.open(twitter_url)
            
            result['ok'] = True
            dialog.destroy()
        
        def on_cancel():
            dialog.destroy()
        
        ttk.Button(button_frame, text=self.strings['announcement']['tweet_button'], command=on_ok).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text=self.strings['announcement']['cancel_button'], command=on_cancel).pack(side=tk.RIGHT)
        
        # ダイアログを中央に配置
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - dialog.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")
    
    def show_settings(self):
        """設定ダイアログを表示"""
        settings_window = tk.Toplevel(self.root)
        settings_window.title(self.strings["settings"]["title"])
        settings_window.geometry("700x850")
        settings_window.transient(self.root)
        settings_window.grab_set()
        
        # タブ構成
        settings_notebook = ttk.Notebook(settings_window)
        settings_notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # OBS設定タブ
        obs_frame = ttk.Frame(settings_notebook)
        settings_notebook.add(obs_frame, text=self.strings["settings"]["obs_tab"])
        
        obs_settings_frame = ttk.LabelFrame(obs_frame, text=self.strings["settings"]["obs_connection"])
        obs_settings_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # OBS設定フォーム
        host_frame = ttk.Frame(obs_settings_frame)
        host_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(host_frame, text=self.strings["settings"]["host"]).pack(side=tk.LEFT)
        obs_host_var = tk.StringVar(value=self.global_settings.obs_host)
        ttk.Entry(host_frame, textvariable=obs_host_var, width=30).pack(side=tk.LEFT, padx=(5, 0))
        
        port_frame = ttk.Frame(obs_settings_frame)
        port_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(port_frame, text=self.strings["settings"]["port"]).pack(side=tk.LEFT)
        obs_port_var = tk.StringVar(value=str(self.global_settings.obs_port))
        ttk.Entry(port_frame, textvariable=obs_port_var, width=30).pack(side=tk.LEFT, padx=(5, 0))
        
        passwd_frame = ttk.Frame(obs_settings_frame)
        passwd_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(passwd_frame, text=self.strings["settings"]["password"]).pack(side=tk.LEFT)
        obs_passwd_var = tk.StringVar(value=self.global_settings.obs_passwd)
        ttk.Entry(passwd_frame, textvariable=obs_passwd_var, width=30, show="*").pack(side=tk.LEFT, padx=(5, 0))
        
        # その他の設定
        other_settings_frame = ttk.LabelFrame(obs_frame, text=self.strings["settings"]["other_settings"])
        other_settings_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        keep_top_var = tk.BooleanVar(value=self.global_settings.keep_on_top)
        ttk.Checkbutton(other_settings_frame, text=self.strings["settings"]["keep_on_top"], 
                       variable=keep_top_var).pack(anchor=tk.W, padx=10, pady=5)
        
        # デバッグ設定
        debug_settings_frame = ttk.LabelFrame(obs_frame, text=self.strings["settings"]["debug_settings"])
        debug_settings_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        debug_enabled_var = tk.BooleanVar(value=self.global_settings.debug_enabled)
        ttk.Checkbutton(debug_settings_frame, text=self.strings["settings"]["debug_mode"], 
                       variable=debug_enabled_var).pack(anchor=tk.W, padx=10, pady=5)
        
        # タイトル抽出設定
        title_extract_frame = ttk.LabelFrame(obs_frame, text=self.strings['title_extraction']['frame_title'])
        title_extract_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        # シリーズパターン設定
        series_pattern_frame = ttk.Frame(title_extract_frame)
        series_pattern_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(series_pattern_frame, text=self.strings['title_extraction']['series_help']).pack(side=tk.LEFT)
        pattern_series_var = tk.StringVar(value=self.global_settings.pattern_series)
        series_entry = ttk.Entry(series_pattern_frame, textvariable=pattern_series_var, width=30)
        series_entry.pack(side=tk.LEFT, padx=(5, 0))
        
        # ヘルプラベル
        series_help = ttk.Label(title_extract_frame, 
                               text=self.strings['title_extraction']['series_help'],
                               foreground="gray", font=('TkDefaultFont', 8))
        series_help.pack(anchor=tk.W, padx=10, pady=(0, 5))
        
        # base_title除外パターン設定
        base_pattern_label_frame = ttk.Frame(title_extract_frame)
        base_pattern_label_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
        ttk.Label(base_pattern_label_frame, text=self.strings['title_extraction']['base_pattern_label']).pack(side=tk.LEFT)
        
        # リストボックス
        base_pattern_list_frame = ttk.Frame(title_extract_frame)
        base_pattern_list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        base_pattern_listbox = tk.Listbox(base_pattern_list_frame, height=4)
        base_pattern_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        base_pattern_scroll = ttk.Scrollbar(base_pattern_list_frame, orient=tk.VERTICAL, 
                                           command=base_pattern_listbox.yview)
        base_pattern_listbox.configure(yscrollcommand=base_pattern_scroll.set)
        base_pattern_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 初期データ設定
        for pattern in self.global_settings.pattern_base_title_list:
            base_pattern_listbox.insert(tk.END, pattern)
        
        # ボタンフレーム
        base_pattern_button_frame = ttk.Frame(title_extract_frame)
        base_pattern_button_frame.pack(fill=tk.X, padx=10, pady=(0, 5))
        
        def add_base_pattern():
            pattern = simpledialog.askstring(self.strings['title_extraction']['pattern_dialog_title'], self.strings['title_extraction']['pattern_dialog_prompt'])
            if pattern and pattern not in self.global_settings.pattern_base_title_list:
                self.global_settings.pattern_base_title_list.append(pattern)
                base_pattern_listbox.insert(tk.END, pattern)
        
        def remove_base_pattern():
            selection = base_pattern_listbox.curselection()
            if selection:
                index = selection[0]
                self.global_settings.pattern_base_title_list.pop(index)
                base_pattern_listbox.delete(index)
        
        ttk.Button(base_pattern_button_frame, text=self.strings['title_extraction']['add_button'], command=add_base_pattern).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(base_pattern_button_frame, text=self.strings['title_extraction']['delete_button'], command=remove_base_pattern).pack(side=tk.LEFT)
        
        # ヘルプラベル
        base_help = ttk.Label(title_extract_frame, 
                             text=self.strings['title_extraction']['base_pattern_help'],
                             foreground="gray", font=('TkDefaultFont', 8))
        base_help.pack(anchor=tk.W, padx=10, pady=(0, 10))
        
        # 告知テンプレート設定
        announcement_template_frame = ttk.LabelFrame(obs_frame, text=self.strings["announcement_template"]["frame_title"])
        announcement_template_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        # テンプレート入力
        template_label_frame = ttk.Frame(announcement_template_frame)
        template_label_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
        ttk.Label(template_label_frame, text=self.strings["announcement_template"]["template_label"]).pack(side=tk.LEFT)
        
        announcement_template_text = tk.Text(announcement_template_frame, height=3, width=60, wrap=tk.WORD)
        announcement_template_text.pack(fill=tk.X, padx=10, pady=(0, 10))
        # フォールバック付きでテンプレートを読み込む
        template = getattr(self.global_settings, 'announcement_template', '配信開始しました！')
        announcement_template_text.insert("1.0", template)
        
        # ヘルプラベル
        template_help = ttk.Label(announcement_template_frame, 
                                  text=self.strings["announcement_template"]["template_help"],
                                  foreground="gray", font=('TkDefaultFont', 8))
        template_help.pack(anchor=tk.W, padx=10, pady=(0, 10))
        
        # 配信内容取得設定
        content_marker_frame = ttk.LabelFrame(obs_frame, text=self.strings["content_extraction"]["frame_title"])
        content_marker_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        # マーカー入力
        marker_input_frame = ttk.Frame(content_marker_frame)
        marker_input_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
        ttk.Label(marker_input_frame, text=self.strings["content_extraction"]["marker_label"]).pack(side=tk.LEFT)
        
        content_marker_var = tk.StringVar(value=getattr(self.global_settings, 'content_marker', '今日の内容:'))
        content_marker_entry = ttk.Entry(marker_input_frame, textvariable=content_marker_var, width=30)
        content_marker_entry.pack(side=tk.LEFT, padx=(5, 0))
        
        # ヘルプラベル
        marker_help = ttk.Label(content_marker_frame, 
                               text=self.strings["content_extraction"]["marker_help"],
                               foreground="gray", font=('TkDefaultFont', 8))
        marker_help.pack(anchor=tk.W, padx=10, pady=(0, 10))
        
        # トリガーワード設定タブ
        trigger_frame = ttk.Frame(settings_notebook)
        settings_notebook.add(trigger_frame, text=self.strings["settings"]["trigger_tab"])
        
        # プッシュワード設定
        push_frame = ttk.LabelFrame(trigger_frame, text=self.strings["settings"]["push_word"])
        push_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        push_list_frame = ttk.Frame(push_frame)
        push_list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        push_listbox = tk.Listbox(push_list_frame, height=6)
        push_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        push_scroll = ttk.Scrollbar(push_list_frame, orient=tk.VERTICAL, command=push_listbox.yview)
        push_listbox.configure(yscrollcommand=push_scroll.set)
        push_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 初期データ設定
        for word in self.global_settings.pushwords:
            push_listbox.insert(tk.END, word)
        
        push_button_frame = ttk.Frame(push_frame)
        push_button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        def add_pushword():
            word = simpledialog.askstring(
                self.strings["dialog"]["add_word_title"], 
                self.strings["dialog"]["add_push_word_prompt"]
            )
            if word and word not in self.global_settings.pushwords:
                self.global_settings.pushwords.append(word)
                push_listbox.insert(tk.END, word)
                
        def remove_pushword():
            selection = push_listbox.curselection()
            if selection:
                index = selection[0]
                self.global_settings.pushwords.pop(index)
                push_listbox.delete(index)
        
        ttk.Button(push_button_frame, text=self.strings["settings"]["add_button"], command=add_pushword).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(push_button_frame, text=self.strings["settings"]["delete_button"], command=remove_pushword).pack(side=tk.LEFT, padx=(0, 5))
        
        # プルワード設定
        pull_frame = ttk.LabelFrame(trigger_frame, text=self.strings["settings"]["pull_word"])
        pull_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        pull_list_frame = ttk.Frame(pull_frame)
        pull_list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        pull_listbox = tk.Listbox(pull_list_frame, height=6)
        pull_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        pull_scroll = ttk.Scrollbar(pull_list_frame, orient=tk.VERTICAL, command=pull_listbox.yview)
        pull_listbox.configure(yscrollcommand=pull_scroll.set)
        pull_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 初期データ設定
        for word in self.global_settings.pullwords:
            pull_listbox.insert(tk.END, word)
        
        pull_button_frame = ttk.Frame(pull_frame)
        pull_button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        def add_pullword():
            word = simpledialog.askstring(
                self.strings["dialog"]["add_word_title"], 
                self.strings["dialog"]["add_pull_word_prompt"]
            )
            if word and word not in self.global_settings.pullwords:
                self.global_settings.pullwords.append(word)
                pull_listbox.insert(tk.END, word)
                
        def remove_pullword():
            selection = pull_listbox.curselection()
            if selection:
                index = selection[0]
                self.global_settings.pullwords.pop(index)
                pull_listbox.delete(index)
        
        ttk.Button(pull_button_frame, text=self.strings["settings"]["add_button"], command=add_pullword).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(pull_button_frame, text=self.strings["settings"]["delete_button"], command=remove_pullword).pack(side=tk.LEFT, padx=(0, 5))
        
        # 権限設定タブ
        permission_frame = ttk.Frame(settings_notebook)
        settings_notebook.add(permission_frame, text=self.strings["settings"]["permission_tab"])
        
        perm_settings_frame = ttk.LabelFrame(permission_frame, text=self.strings["settings"]["permission_title"])
        perm_settings_frame.pack(fill=tk.X, padx=10, pady=10)
        
        push_manager_var = tk.BooleanVar(value=self.global_settings.push_manager_only)
        ttk.Checkbutton(perm_settings_frame, text=self.strings["settings"]["push_manager_only"], 
                       variable=push_manager_var).pack(anchor=tk.W, padx=10, pady=5)
        
        pull_manager_var = tk.BooleanVar(value=self.global_settings.pull_manager_only)
        ttk.Checkbutton(perm_settings_frame, text=self.strings["settings"]["pull_manager_only"], 
                       variable=pull_manager_var).pack(anchor=tk.W, padx=10, pady=5)
        
        # 管理者設定
        manager_frame = ttk.LabelFrame(permission_frame, text=self.strings["settings"]["manager_title"])
        manager_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        manager_list_frame = ttk.Frame(manager_frame)
        manager_list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        manager_listbox = tk.Listbox(manager_list_frame, height=6)
        manager_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        manager_scroll = ttk.Scrollbar(manager_list_frame, orient=tk.VERTICAL, command=manager_listbox.yview)
        manager_listbox.configure(yscrollcommand=manager_scroll.set)
        manager_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 初期データ設定
        for manager in self.global_settings.managers:
            display_text = f"[{manager['platform']}] {manager['name']} ({manager['id']})"
            manager_listbox.insert(tk.END, display_text)
        
        manager_button_frame = ttk.Frame(manager_frame)
        manager_button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        def remove_manager():
            selection = manager_listbox.curselection()
            if selection:
                index = selection[0]
                self.global_settings.managers.pop(index)
                manager_listbox.delete(index)
        
        ttk.Button(manager_button_frame, text=self.strings["settings"]["delete_button"], command=remove_manager).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Label(manager_frame, text=self.strings["settings"]["manager_note"], 
                 foreground="gray").pack(padx=10, pady=(0, 10))
        
        # NGユーザ設定タブ
        ng_user_frame = ttk.Frame(settings_notebook)
        settings_notebook.add(ng_user_frame, text=self.strings["settings"]["ng_user_tab"])
        
        ng_settings_frame = ttk.LabelFrame(ng_user_frame, text=self.strings["settings"]["ng_user_title"])
        ng_settings_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        ng_list_frame = ttk.Frame(ng_settings_frame)
        ng_list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        ng_listbox = tk.Listbox(ng_list_frame, height=10)
        ng_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        ng_scroll = ttk.Scrollbar(ng_list_frame, orient=tk.VERTICAL, command=ng_listbox.yview)
        ng_listbox.configure(yscrollcommand=ng_scroll.set)
        ng_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 初期データ設定
        for ng_user in self.global_settings.ng_users:
            display_text = f"[{ng_user['platform']}] {ng_user['name']} ({ng_user['id']})"
            ng_listbox.insert(tk.END, display_text)
        
        ng_button_frame = ttk.Frame(ng_settings_frame)
        ng_button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        def remove_ng_user():
            selection = ng_listbox.curselection()
            if selection:
                index = selection[0]
                self.global_settings.ng_users.pop(index)
                ng_listbox.delete(index)
        
        ttk.Button(ng_button_frame, text=self.strings["settings"]["delete_button"], command=remove_ng_user).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Label(ng_settings_frame, text=self.strings["settings"]["ng_user_note"], 
                 foreground="gray").pack(padx=10, pady=(0, 10))
        
        # ボタン
        button_frame = ttk.Frame(settings_window)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        def save_settings():
            # OBS設定を保存
            self.global_settings.obs_host = obs_host_var.get()
            try:
                self.global_settings.obs_port = int(obs_port_var.get())
            except ValueError:
                messagebox.showerror(
                    self.strings["messages"]["error"], 
                    self.strings["messages"]["invalid_port"]
                )
                return
            self.global_settings.obs_passwd = obs_passwd_var.get()
            self.global_settings.keep_on_top = keep_top_var.get()
            
            # デバッグ設定を保存
            old_debug_enabled = self.global_settings.debug_enabled
            self.global_settings.debug_enabled = debug_enabled_var.get()
            
            # タイトル抽出設定を保存
            self.global_settings.pattern_series = pattern_series_var.get()
            # pattern_base_title_listはリストボックスから既に更新されている
            
            # 告知テンプレート設定を保存
            self.global_settings.announcement_template = announcement_template_text.get("1.0", tk.END).strip()
            
            # 配信内容マーカー設定を保存
            self.global_settings.content_marker = content_marker_var.get()
            
            # 権限設定を保存
            self.global_settings.push_manager_only = push_manager_var.get()
            self.global_settings.pull_manager_only = pull_manager_var.get()
            
            self.global_settings.save()
            
            # デバッグ設定が変更された場合の警告
            if old_debug_enabled != self.global_settings.debug_enabled:
                messagebox.showinfo(
                    self.strings["messages"]["info"], 
                    self.strings["messages"]["debug_restart_required"]
                )
            
            # 最前面設定を適用
            self.root.attributes('-topmost', self.global_settings.keep_on_top)
            
            # OBS再接続
            self.setup_obs()
            
            settings_window.destroy()
            
        ttk.Button(button_frame, text=self.strings["settings"]["save_button"], command=save_settings).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text=self.strings["settings"]["cancel_button"], command=settings_window.destroy).pack(side=tk.RIGHT)
        
        # ダイアログを中央に配置
        settings_window.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - settings_window.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - settings_window.winfo_height()) // 2
        settings_window.geometry(f"+{x}+{y}")
    
    def rebuild_gui(self):
        """GUIを再構築（言語切り替え時に使用）"""
        # 現在の配信状態を保存
        stream_backups = []
        for stream_id, settings in self.stream_manager.streams.items():
            stream_backups.append({
                'stream_id': stream_id,
                'platform': settings.platform,
                'url': settings.url,
                'title': settings.title,
                'is_active': settings.is_active,
                'comments_count': len(settings.comments),
                'processed_requests': getattr(settings, 'processed_requests', 0)
            })
        
        # コメントデータを保存（全配信の最新1000件まで）
        all_comments = []
        for stream_id, settings in self.stream_manager.streams.items():
            all_comments.extend(settings.comments[-1000:])  # 最新1000件
        
        # メインフレームの全ウィジェットを削除
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # GUIを再構築
        self.setup_gui()
        
        # 配信タブを復元
        for backup in stream_backups:
            if backup['stream_id'] in self.stream_manager.streams:
                settings = self.stream_manager.streams[backup['stream_id']]
                self.add_stream_tab(settings)
                
                # ステータスラベルを更新
                if hasattr(settings, 'status_label'):
                    if backup['is_active']:
                        settings.status_label.config(
                            text=self.strings["stream_info"]["status_running"], 
                            foreground="red"
                        )
                    else:
                        settings.status_label.config(
                            text=self.strings["stream_info"]["status_stopped"], 
                            foreground="red"
                        )
                
                # カウント表示を更新
                if hasattr(settings, 'comment_count_label'):
                    settings.comment_count_label.config(text=str(backup['comments_count']))
                if hasattr(settings, 'request_count_label'):
                    settings.request_count_label.config(text=str(backup['processed_requests']))
        
        # 配信リストを更新
        self.update_stream_list()
        
        # リクエストリストを更新
        self.update_request_display()
        
        # コメント一覧を復元（時系列順でソート）
        all_comments.sort(key=lambda x: x.get('timestamp', ''))
        for comment_data in all_comments:
            self.update_comment_display(comment_data)
