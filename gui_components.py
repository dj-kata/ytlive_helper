# -*- coding: utf-8 -*-
"""
GUI Components Module
配信管理アプリケーションのGUI構築とUI更新を担当
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog


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
            self.strings["columns"]["datetime"], 
            self.strings["columns"]["user"], 
            self.strings["columns"]["comment"], 
            self.strings["columns"]["stream_id"], 
            self.strings["columns"]["platform"]
        )
        self.comment_tree = ttk.Treeview(comment_frame, columns=comment_columns, show='headings', height=12)
        
        # カラム幅を固定（stretch=Falseで自動リサイズを無効化）
        column_widths = {
            self.strings["columns"]["datetime"]: 140, 
            self.strings["columns"]["user"]: 120, 
            self.strings["columns"]["comment"]: 400, 
            self.strings["columns"]["stream_id"]: 120, 
            self.strings["columns"]["platform"]: 100
        }
        for col in comment_columns:
            self.comment_tree.heading(col, text=col, anchor='w')  # 列名を左揃えに
            self.comment_tree.column(col, width=column_widths[col], stretch=False)
        
        # 縦スクロールバー
        comment_scrollbar_y = ttk.Scrollbar(comment_frame, orient=tk.VERTICAL, command=self.comment_tree.yview)
        # 横スクロールバー
        comment_scrollbar_x = ttk.Scrollbar(comment_frame, orient=tk.HORIZONTAL, command=self.comment_tree.xview)
        
        self.comment_tree.configure(yscrollcommand=comment_scrollbar_y.set, xscrollcommand=comment_scrollbar_x.set)
        
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
        
        # タブ管理（配信情報タブ）
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
    
    def update_stream_list(self):
        """配信リストを更新"""
        # 既存の項目を削除
        for item in self.stream_tree.get_children():
            self.stream_tree.delete(item)
            
        # 新しい項目を追加
        for stream_id, settings in self.stream_manager.streams.items():
            status = self.strings["stream"]["status_receiving"] if settings.is_active else self.strings["stream"]["status_stopped"]
            # タイトルが長い場合は省略表示
            display_title = settings.title[:40] + "..." if len(settings.title) > 40 else settings.title
            self.stream_tree.insert('', tk.END, values=(
                stream_id, settings.platform, display_title, settings.url[:50], status
            ))
    
    def add_stream_tab(self, stream_settings):
        """配信用の情報表示タブを追加"""
        # タブフレーム作成
        tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(tab_frame, text=f"{stream_settings.platform}: {stream_settings.stream_id}")
        
        # 配信情報表示
        info_frame = ttk.LabelFrame(tab_frame, text=self.strings["stream_info"]["title"])
        info_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # タイトル表示
        title_info_frame = ttk.Frame(info_frame)
        title_info_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(title_info_frame, text=self.strings["stream_info"]["stream_title"]).pack(side=tk.LEFT)
        title_text = stream_settings.title if stream_settings.title else self.strings["stream_info"]["title_loading"]
        title_label = ttk.Label(title_info_frame, text=title_text, 
                               foreground="blue", wraplength=500)
        title_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # URL表示
        url_info_frame = ttk.Frame(info_frame)
        url_info_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(url_info_frame, text=self.strings["stream_info"]["url"]).pack(side=tk.LEFT)
        url_label = ttk.Label(url_info_frame, text=stream_settings.url, foreground="blue")
        url_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # プラットフォーム表示
        platform_info_frame = ttk.Frame(info_frame)
        platform_info_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(platform_info_frame, text=self.strings["stream_info"]["platform"]).pack(side=tk.LEFT)
        ttk.Label(platform_info_frame, text=stream_settings.platform.title()).pack(side=tk.LEFT, padx=(5, 0))
        
        # ステータス表示
        status_info_frame = ttk.Frame(info_frame)
        status_info_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(status_info_frame, text=self.strings["stream_info"]["status"]).pack(side=tk.LEFT)
        status_label = ttk.Label(status_info_frame, text=self.strings["stream_info"]["status_stopped"], foreground="red")
        status_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # 統計情報表示
        stats_frame = ttk.LabelFrame(tab_frame, text=self.strings["stats"]["title"])
        stats_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        # コメント数表示
        comment_count_frame = ttk.Frame(stats_frame)
        comment_count_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(comment_count_frame, text=self.strings["stats"]["comment_count"]).pack(side=tk.LEFT)
        comment_count_label = ttk.Label(comment_count_frame, text="0")
        comment_count_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # リクエスト処理数表示
        request_count_frame = ttk.Frame(stats_frame)
        request_count_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(request_count_frame, text=self.strings["stats"]["request_count"]).pack(side=tk.LEFT)
        request_count_label = ttk.Label(request_count_frame, text="0")
        request_count_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # 各要素をstream_settingsに関連付け
        stream_settings.title_label = title_label
        stream_settings.status_label = status_label
        stream_settings.comment_count_label = comment_count_label
        stream_settings.request_count_label = request_count_label
        stream_settings.processed_requests = 0
    
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
            
            # URLとプラットフォームを更新
            settings.url = new_url
            settings.platform = new_platform
            
            # タイトルも再取得
            new_title = self.get_stream_title(new_platform, new_url)
            settings.title = new_title
            
            # タイトルラベルが存在すれば更新
            if hasattr(settings, 'title_label'):
                title_text = new_title if new_title else self.strings["stream_info"]["title_loading"]
                settings.title_label.config(text=title_text)
            
            # リストを更新
            self.update_stream_list()
            
            # 配信が実行中の場合は警告
            if settings.is_active:
                messagebox.showinfo(
                    self.strings["messages"]["info"], 
                    self.strings["messages"]["url_updated_running"]
                )
            else:
                messagebox.showinfo(
                    self.strings["messages"]["info"], 
                    self.strings["messages"]["url_updated"]
                )
    
    def show_settings(self):
        """設定ダイアログを表示"""
        settings_window = tk.Toplevel(self.root)
        settings_window.title(self.strings["settings"]["title"])
        settings_window.geometry("600x600")
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
                            foreground="green"
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
