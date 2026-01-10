#!/usr/bin/python3
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading
import time
import json
import os
import re
import webbrowser
import urllib.parse
import requests
from bs4 import BeautifulSoup
import datetime
from collections import deque
import logging
import traceback
import socket

# コメント取得ライブラリ
import pytchat  # YouTube用
# Twitch用 - シンプルなIRC接続を使用
import socket

from obssocket import OBSSocket

# グローバル設定を先に読み込んでログレベルを決定
def setup_logging():
    """ログ設定を初期化"""
    # 設定ファイルから先読み
    debug_enabled = False
    if os.path.exists('global_settings.json'):
        try:
            with open('global_settings.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                debug_enabled = data.get('debug_enabled', False)
        except:
            pass
    
    # ログレベル設定
    if debug_enabled:
        log_level = logging.DEBUG
        console_handler = logging.StreamHandler()
    else:
        log_level = logging.INFO
        console_handler = None  # コンソール出力なし
    
    # ファイルハンドラー
    file_handler = logging.FileHandler('./dbg.log', encoding='utf-8')
    file_handler.setLevel(log_level)
    
    # フォーマッター
    formatter = logging.Formatter('%(asctime)s %(filename)s:%(lineno)d %(funcName)s() [%(levelname)s] %(message)s')
    file_handler.setFormatter(formatter)
    
    # ルートロガー設定
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # 既存のハンドラーをクリア
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    root_logger.addHandler(file_handler)
    
    if console_handler:
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # 外部ライブラリのログレベルを制限
    external_loggers = [
        'hpack',
        'urllib3',
        'requests',
        'httpx',
        'httpcore',
        'pytchat',
        'websockets',
        'asyncio',
        'obsws_python'
    ]
    
    for logger_name in external_loggers:
        external_logger = logging.getLogger(logger_name)
        external_logger.setLevel(logging.WARNING)
    
    return debug_enabled

# ログ設定を初期化
DEBUG_ENABLED = setup_logging()
logger = logging.getLogger(__name__)

def debug_print(*args, **kwargs):
    """デバッグ設定が有効な時のみprint出力"""
    if DEBUG_ENABLED:
        print(*args, **kwargs)

class StreamSettings:
    """各配信の設定を管理するクラス"""
    def __init__(self, stream_id="", platform="youtube", url="", title=""):
        self.stream_id = stream_id
        self.platform = platform  # "youtube" or "twitch"
        self.url = url
        self.title = title  # 配信タイトル
        self.comments = []
        self.is_active = False

class GlobalSettings:
    """グローバル設定を管理するクラス"""
    def __init__(self):
        self.obs_host = 'localhost'
        self.obs_port = 4444
        self.obs_passwd = ''
        self.keep_on_top = False
        self.series_query = '#[number]'
        self.content_header = '◆今回の予定'
        self.window_x = 100
        self.window_y = 100
        self.last_streams = []  # 最後に開いていた配信URLのリスト
        
        # デバッグ設定
        self.debug_enabled = False
        
        # 共通トリガーワード設定
        self.pushwords = ['お題 ', 'お題　', 'リク ', 'リク　']
        self.pullwords = ['リクあり', '消化済']
        
        # 共通権限設定
        self.push_manager_only = False
        self.pull_manager_only = False
        
        # 共通管理者リスト（新形式：辞書のリスト）
        self.managers = []

        # 共通NGリスト（新形式：辞書のリスト）
        self.ng_users = []
        
    def save(self, filename='global_settings.json'):
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.__dict__, f, indent=2, ensure_ascii=False)
    
    def load(self, filename='global_settings.json'):
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for key, value in data.items():
                    setattr(self, key, value)

                # 旧形式のリストを新形式に変換
                self._convert_old_format()

    def _convert_old_format(self):
        """旧形式のリストを新形式に変換"""
        # 管理者リストの変換
        if self.managers and len(self.managers) > 0:
            if isinstance(self.managers[0], str):
                new_managers = []
                for manager in self.managers:
                    if '(' in manager and ')' in manager:
                        name = manager.split('(')[0]
                        user_id = manager.split('(')[1][:-1]
                        if user_id.startswith('UC'):
                            new_managers.append({
                                "platform": "youtube",
                                "id": user_id,
                                "name": name
                            })
                        else:
                            new_managers.append({
                                "platform": "twitch",
                                "id": manager,
                                "name": name
                            })
                    else:
                        new_managers.append({
                            "platform": "twitch",
                            "id": manager,
                            "name": manager
                        })
                self.managers = new_managers
        
        # NGユーザリストが初期化されていない場合
        if not hasattr(self, 'ng_users'):
            self.ng_users = []

class CommentReceiver:
    """コメント受信の基底クラス"""
    def __init__(self, settings):
        self.settings = settings
        self.stop_event = threading.Event()
        
    def start(self):
        raise NotImplementedError
        
    def stop(self):
        self.stop_event.set()

class YouTubeCommentReceiver(CommentReceiver):
    """YouTubeコメント受信クラス"""
    def __init__(self, settings, callback, global_settings):
        super().__init__(settings)
        self.callback = callback
        self.global_settings = global_settings
        self.livechat = None
        
    def extract_video_id(self, url):
        """URLからビデオIDを抽出"""
        debug_print(f"DEBUG: extract_video_id called with URL: {url}")
        
        if 'youtube.com' in url and 'v=' in url:
            video_id = re.search(r'v=([a-zA-Z0-9_-]+)', url).group(1)
            debug_print(f"DEBUG: Extracted video_id from youtube.com URL: {video_id}")
            return video_id
        elif 'youtu.be/' in url:
            video_id = url.split('/')[-1]
            debug_print(f"DEBUG: Extracted video_id from youtu.be URL: {video_id}")
            return video_id
        elif 'livestreaming' in url:
            video_id = url.split('/')[-2]
            debug_print(f"DEBUG: Extracted video_id from livestreaming URL: {video_id}")
            return video_id
        else:
            debug_print(f"ERROR: Could not extract video_id from URL: {url}")
            return None
        
    def start(self):
        """コメント受信開始"""
        video_id = self.extract_video_id(self.settings.url)
        if not video_id:
            logger.error(f"Invalid YouTube URL: {self.settings.url}")
            debug_print(f"ERROR: Invalid YouTube URL: {self.settings.url}")
            return
            
        try:
            debug_print(f"DEBUG: Creating pytchat for video_id: {video_id}")
            self.livechat = pytchat.create(video_id=video_id, interruptable=False)
            logger.info(f"Started YouTube comment receiver for {video_id}")
            debug_print(f"DEBUG: pytchat created successfully, is_alive: {self.livechat.is_alive()}")
            
            while self.livechat.is_alive() and not self.stop_event.is_set():
                try:
                    debug_print(f"DEBUG: Getting chat data...")
                    chatdata = self.livechat.get()
                    debug_print(f"DEBUG: Got {len(chatdata.items)} comments")
                    
                    for comment in chatdata.items:
                        debug_print(f"DEBUG: Processing comment from {comment.author.name}: {comment.message}")
                        
                        # 管理者ID確認のためのデバッグ
                        is_moderator = False
                        for manager in self.global_settings.managers:
                            if manager['platform'] == 'youtube' and manager['id'] == comment.author.channelId:
                                is_moderator = True
                                break
                            
                        comment_data = {
                            'platform': 'youtube',
                            'author': comment.author.name,
                            'message': comment.message,
                            'timestamp': comment.datetime,
                            'author_id': comment.author.channelId,
                            'is_moderator': is_moderator
                        }
                        
                        debug_print(f"DEBUG: Calling callback with comment_data")
                        self.callback(comment_data)
                        debug_print(f"DEBUG: Callback completed")
                        
                except Exception as inner_e:
                    debug_print(f"DEBUG: Error in chat loop: {inner_e}")
                    logger.error(f"Error in chat loop: {inner_e}")
                    
                time.sleep(1)
                
        except Exception as e:
            logger.error(f"YouTube comment receiver error: {e}")
            debug_print(f"ERROR: YouTube comment receiver error: {e}")
            import traceback
            debug_print(f"ERROR: Traceback: {traceback.format_exc()}")
        finally:
            if self.livechat:
                self.livechat.terminate()
                debug_print(f"DEBUG: pytchat terminated")

class TwitchCommentReceiver(CommentReceiver):
    """Twitchコメント受信クラス（シンプルIRC接続）"""
    def __init__(self, settings, callback, global_settings):
        super().__init__(settings)
        self.callback = callback
        self.global_settings = global_settings
        
    def extract_channel_name(self, url):
        """URLからチャンネル名を抽出"""
        if 'twitch.tv/' in url:
            channel = url.split('/')[-1].lower()
            # URLパラメータを除去
            if '?' in channel:
                channel = channel.split('?')[0]
            return channel
        return None
    
    def start(self):
        """コメント受信開始（シンプルIRC接続）"""
        channel = self.extract_channel_name(self.settings.url)
        if not channel:
            logger.error(f"Invalid Twitch URL: {self.settings.url}")
            debug_print(f"ERROR: Invalid Twitch URL: {self.settings.url}")
            return
            
        self.start_with_irc(channel)
    
    def start_with_irc(self, channel):
        """シンプルなIRC接続を使った方法"""
        try:
            debug_print(f"DEBUG: Starting IRC connection for Twitch channel: {channel}")
            
            # Twitch IRCサーバーに接続
            sock = socket.socket()
            sock.settimeout(10)  # 接続時は10秒のタイムアウト
            sock.connect(('irc.chat.twitch.tv', 6667))
            
            # 匿名ログイン（justinfan + タイムスタンプ）
            anonymous_nick = f"justinfan{int(time.time())}"
            sock.send(f"PASS SCHMOOPIIE\n".encode('utf-8'))
            sock.send(f"NICK {anonymous_nick}\n".encode('utf-8'))
            
            # チャンネルに参加
            sock.send(f"JOIN #{channel}\n".encode('utf-8'))
            
            debug_print(f"DEBUG: Connected to Twitch IRC as {anonymous_nick}, joined #{channel}")
            
            buffer = ""  # メッセージのバッファ
            
            while not self.stop_event.is_set():
                try:
                    sock.settimeout(1)  # メッセージ受信時は1秒のタイムアウト
                    data = sock.recv(2048).decode('utf-8', errors='ignore')
                    
                    if not data:  # 接続が切れた場合
                        debug_print("DEBUG: IRC connection lost")
                        break
                    
                    buffer += data
                    
                    # 改行で分割してメッセージを処理
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        line = line.strip()
                        
                        if not line:
                            continue
                            
                        debug_print(f"DEBUG: Raw IRC line: {line}")
                        
                        # PINGに応答
                        if line.startswith('PING'):
                            pong_response = line.replace('PING', 'PONG')
                            sock.send(f"{pong_response}\n".encode('utf-8'))
                            debug_print(f"DEBUG: Responded to PING")
                            continue
                        
                        # PRIVMSGメッセージを解析
                        if 'PRIVMSG' in line:
                            self.parse_privmsg(line)
                            
                except socket.timeout:
                    continue
                except Exception as e:
                    debug_print(f"DEBUG: IRC loop error: {e}")
                    break
                    
            sock.close()
            debug_print(f"DEBUG: IRC connection closed")
            
        except Exception as e:
            logger.error(f"Twitch IRC receiver error: {e}")
            debug_print(f"ERROR: Twitch IRC receiver error: {e}")
            import traceback
            debug_print(f"ERROR: IRC Traceback: {traceback.format_exc()}")
    
    def parse_privmsg(self, line):
        """PRIVMSGメッセージを解析"""
        try:
            # Twitch IRCの形式: :user!user@user.tmi.twitch.tv PRIVMSG #channel :message
            parts = line.split(' ', 3)
            if len(parts) < 4:
                return
                
            user_part = parts[0][1:]  # 最初の `:` を除去
            user_name = user_part.split('!')[0]
            message_part = parts[3]
            
            if message_part.startswith(':'):
                message = message_part[1:]  # 最初の `:` を除去
            else:
                message = message_part
                
            debug_print(f"DEBUG: Parsed Twitch message from {user_name}: {message}")
            
            # 管理者判定
            is_moderator = False
            for manager in self.global_settings.managers:
                if manager['platform'] == 'twitch' and manager['id'] == user_name:
                    is_moderator = True
                    break
            
            comment_data = {
                'platform': 'twitch',
                'author': user_name,
                'message': message,
                'timestamp': datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S'),
                'author_id': user_name,
                'is_moderator': is_moderator
            }
            
            self.callback(comment_data)
            
        except Exception as e:
            debug_print(f"DEBUG: Error parsing PRIVMSG: {e}")
            debug_print(f"DEBUG: Line was: {line}")

class StreamManager:
    """複数配信を管理するクラス"""
    def __init__(self, global_settings):
        self.streams = {}  # stream_id -> StreamSettings
        self.receivers = {}  # stream_id -> CommentReceiver
        self.threads = {}  # stream_id -> Thread
        self.global_settings = global_settings
        
    def add_stream(self, stream_settings):
        """配信を追加"""
        self.streams[stream_settings.stream_id] = stream_settings
        
    def remove_stream(self, stream_id):
        """配信を削除"""
        self.stop_stream(stream_id)
        if stream_id in self.streams:
            del self.streams[stream_id]
            
    def start_stream(self, stream_id, comment_callback):
        """配信のコメント受信を開始"""
        debug_print(f"DEBUG: StreamManager.start_stream called for {stream_id}")
        
        if stream_id not in self.streams:
            debug_print(f"ERROR: stream_id {stream_id} not found in self.streams")
            return False
            
        settings = self.streams[stream_id]
        debug_print(f"DEBUG: Found settings for {stream_id}, platform: {settings.platform}")
        
        if settings.platform == 'youtube':
            debug_print(f"DEBUG: Creating YouTubeCommentReceiver")
            receiver = YouTubeCommentReceiver(settings, comment_callback, self.global_settings)
        elif settings.platform == 'twitch':
            debug_print(f"DEBUG: Creating TwitchCommentReceiver")
            receiver = TwitchCommentReceiver(settings, comment_callback, self.global_settings)
        else:
            logger.error(f"Unknown platform: {settings.platform}")
            debug_print(f"ERROR: Unknown platform: {settings.platform}")
            return False
            
        debug_print(f"DEBUG: Created receiver, starting thread")
        self.receivers[stream_id] = receiver
        thread = threading.Thread(target=receiver.start, daemon=True)
        self.threads[stream_id] = thread
        thread.start()
        settings.is_active = True
        debug_print(f"DEBUG: Thread started for {stream_id}")
        return True
        
    def stop_stream(self, stream_id):
        """配信のコメント受信を停止"""
        if stream_id in self.receivers:
            self.receivers[stream_id].stop()
            del self.receivers[stream_id]
            
        if stream_id in self.threads:
            del self.threads[stream_id]
            
        if stream_id in self.streams:
            self.streams[stream_id].is_active = False

class MultiStreamCommentHelper:
    """メインアプリケーションクラス"""
    def __init__(self):
        self.global_settings = GlobalSettings()
        self.global_settings.load()
        self.stream_manager = StreamManager(self.global_settings)
        self.obs = None
        self.auto_scroll = None  # setup_guiで初期化される
        self.common_requests = []  # 共通リクエストリスト
        
        # GUI初期化
        self.root = tk.Tk()
        self.root.title("Multi-Stream Comment Helper")
        self.root.geometry("1000x700")
        if self.global_settings.keep_on_top:
            self.root.attributes('-topmost', True)
            
        self.setup_gui()
        self.setup_obs()
        self.restore_last_streams()
        
    def restore_last_streams(self):
        """最後に開いていた配信を復元"""
        for url in self.global_settings.last_streams:
            platform = self.detect_platform(url)
            if platform:
                stream_id = f"{platform}_{len(self.stream_manager.streams) + 1}"
                
                # タイトルを取得
                title = self.get_stream_title(platform, url)
                
                stream_settings = StreamSettings(
                    stream_id=stream_id,
                    platform=platform,
                    url=url,
                    title=title
                )
                self.stream_manager.add_stream(stream_settings)
                self.add_stream_tab(stream_settings)
                
        # 配信リストを更新
        self.update_stream_list()
        
    def detect_platform(self, url):
        """URLからプラットフォームを自動判定"""
        url_lower = url.lower()
        if 'youtube.com' in url_lower or 'youtu.be' in url_lower:
            return 'youtube'
        elif 'twitch.tv' in url_lower:
            return 'twitch'
        else:
            return None
    
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
        
        context_menu.add_command(label="カット", command=cut_text)
        context_menu.add_command(label="コピー", command=copy_text)
        context_menu.add_command(label="ペースト", command=paste_text)
        context_menu.add_separator()
        context_menu.add_command(label="全て選択", command=select_all)
        
        def show_context_menu(event):
            try:
                context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                context_menu.grab_release()
        
        entry_widget.bind("<Button-3>", show_context_menu)
    
    def get_stream_title(self, platform, url):
        """配信タイトルを取得（スケルトン関数 - 実装が必要）
        
        Args:
            platform (str): プラットフォーム名 ('youtube' or 'twitch')
            url (str): 配信URL
            
        Returns:
            str: 配信タイトル。取得できない場合は空文字列
        """
        # TODO: ここに実装を追加
        # YouTubeの場合の実装例:
        # if platform == 'youtube':
        #     video_id = extract_video_id(url)
        #     # YouTube Data API等を使ってタイトルを取得
        #     return title
        # 
        # Twitchの場合の実装例:
        # elif platform == 'twitch':
        #     channel = extract_channel_name(url)
        #     # Twitch API等を使ってタイトルを取得
        #     return title
        
        return ""  # 実装するまでは空文字列を返す
    
    def update_stream_title(self, stream_id):
        """指定された配信のタイトルを更新（オプション）
        
        タイトル取得関数を実装後、必要に応じてこのメソッドを呼び出して
        タイトルを再取得・更新できます。
        
        Args:
            stream_id (str): 配信ID
        """
        if stream_id in self.stream_manager.streams:
            settings = self.stream_manager.streams[stream_id]
            new_title = self.get_stream_title(settings.platform, settings.url)
            
            if new_title:
                settings.title = new_title
                
                # タイトルラベルが存在すれば更新
                if hasattr(settings, 'title_label'):
                    settings.title_label.config(text=new_title)
                
                # リストも更新
                self.update_stream_list()
        
    def setup_gui(self):
        """GUI構築"""
        # メインフレーム
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # メニューバー
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="ファイル", menu=file_menu)
        file_menu.add_command(label="設定", command=self.show_settings)
        file_menu.add_separator()
        file_menu.add_command(label="終了", command=self.on_closing)
        
        # 配信管理フレーム
        stream_frame = ttk.LabelFrame(main_frame, text="配信管理")
        stream_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 配信追加
        add_frame = ttk.Frame(stream_frame)
        add_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(add_frame, text="配信URL:").pack(side=tk.LEFT)
        self.url_entry = ttk.Entry(add_frame, width=70)
        self.url_entry.pack(side=tk.LEFT, padx=(5, 0))
        self.add_entry_context_menu(self.url_entry)  # 右クリックメニュー追加
        
        ttk.Button(add_frame, text="追加", command=self.add_stream).pack(side=tk.LEFT, padx=(10, 0))
        
        # プラットフォーム表示（読み取り専用）
        platform_label = ttk.Label(add_frame, text="プラットフォーム: 自動判定", foreground="gray")
        platform_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # 配信リスト
        stream_list_frame = ttk.Frame(stream_frame)
        stream_list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # Treeview for stream list - 列名を左揃えに、カラム幅固定
        columns = ('ID', 'Platform', 'タイトル', 'URL', 'Status')
        self.stream_tree = ttk.Treeview(stream_list_frame, columns=columns, show='headings', height=6)
        
        # カラム幅を固定（stretch=Falseで自動リサイズを無効化）
        column_widths = {'ID': 120, 'Platform': 80, 'タイトル': 250, 'URL': 300, 'Status': 100}
        for col in columns:
            self.stream_tree.heading(col, text=col, anchor='w')  # 列名を左揃えに
            self.stream_tree.column(col, width=column_widths[col], stretch=False)
        
        # 縦スクロールバー
        scrollbar_y = ttk.Scrollbar(stream_list_frame, orient=tk.VERTICAL, command=self.stream_tree.yview)
        # 横スクロールバー
        scrollbar_x = ttk.Scrollbar(stream_list_frame, orient=tk.HORIZONTAL, command=self.stream_tree.xview)
        
        self.stream_tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        
        # グリッドレイアウトで配置
        self.stream_tree.grid(row=0, column=0, sticky='nsew')
        scrollbar_y.grid(row=0, column=1, sticky='ns')
        scrollbar_x.grid(row=1, column=0, sticky='ew')
        
        # グリッド設定
        stream_list_frame.grid_rowconfigure(0, weight=1)
        stream_list_frame.grid_columnconfigure(0, weight=1)
        
        # 配信リスト用の右クリックメニュー
        self.stream_context_menu = tk.Menu(self.root, tearoff=0)
        self.stream_context_menu.add_command(label="受信開始", command=self.start_selected_stream)
        self.stream_context_menu.add_command(label="受信停止", command=self.stop_selected_stream)
        self.stream_context_menu.add_separator()
        self.stream_context_menu.add_command(label="URLを編集", command=self.edit_stream_url)
        self.stream_context_menu.add_separator()
        self.stream_context_menu.add_command(label="削除", command=self.remove_selected_stream)
        
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
                              text="※ダブルクリックで受信ON/OFF切り替え、URL列ダブルクリックでURL編集、右クリックでメニュー表示", 
                              foreground="gray")
        help_label.pack(padx=10, pady=(5, 10))
        
        # 共通リクエスト管理エリア
        request_frame = ttk.LabelFrame(main_frame, text="リクエスト一覧（全配信）")
        request_frame.pack(fill=tk.X, pady=(10, 0))
        
        # リクエストリストTreeview
        request_list_frame = ttk.Frame(request_frame)
        request_list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Treeview作成
        request_columns = ('番号', 'リクエスト内容', 'ユーザー', 'プラットフォーム')
        self.request_tree = ttk.Treeview(request_list_frame, columns=request_columns, show='headings', height=8)
        
        # カラム幅を固定
        column_widths = {'番号': 60, 'リクエスト内容': 350, 'ユーザー': 120, 'プラットフォーム': 100}
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
        ttk.Label(req_button_frame, text="手動追加:").pack(side=tk.LEFT)
        self.manual_req_entry = ttk.Entry(req_button_frame, width=30)
        self.manual_req_entry.pack(side=tk.LEFT, padx=(5, 10))
        self.add_entry_context_menu(self.manual_req_entry)  # 右クリックメニュー追加
        
        ttk.Button(req_button_frame, text="追加", command=self.add_manual_request).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(req_button_frame, text="削除", command=self.remove_selected_request).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(req_button_frame, text="上に移動", command=self.move_request_up).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(req_button_frame, text="下に移動", command=self.move_request_down).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(req_button_frame, text="クリア", command=self.clear_all_requests).pack(side=tk.LEFT, padx=(0, 5))
        
        # 共通コメント表示エリア
        comment_frame = ttk.LabelFrame(main_frame, text="コメント一覧（全配信）")
        comment_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        # コメントTreeview - 横スクロールも追加、カラム幅固定
        comment_columns = ('日時', 'ユーザー', 'コメント', '配信ID', 'プラットフォーム')
        self.comment_tree = ttk.Treeview(comment_frame, columns=comment_columns, show='headings', height=12)
        
        # カラム幅を固定（stretch=Falseで自動リサイズを無効化）
        column_widths = {'日時': 140, 'ユーザー': 120, 'コメント': 400, '配信ID': 120, 'プラットフォーム': 100}
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
        self.comment_context_menu.add_command(label="管理者IDに追加", command=self.add_manager_from_comment)
        self.comment_context_menu.add_command(label="NGユーザに追加", command=self.add_ng_user_from_comment)
        
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
        
        ttk.Button(comment_button_frame, text="クリア", command=self.clear_all_comments).pack(side=tk.LEFT)
        
        # 自動スクロール設定
        self.auto_scroll = tk.BooleanVar(value=True)
        ttk.Checkbutton(comment_button_frame, text="自動スクロール", variable=self.auto_scroll).pack(side=tk.LEFT, padx=(10, 0))
        
        # ノートブック（配信個別設定用タブ）
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.X, pady=(10, 0))
        
        # 各配信用の設定タブは動的に追加
        
    def setup_obs(self):
        """OBS接続設定"""
        try:
            self.obs = OBSSocket(
                self.global_settings.obs_host,
                self.global_settings.obs_port,
                self.global_settings.obs_passwd
            )
            logger.info("OBS connection established")
            debug_print("DEBUG: OBS connection established")
        except Exception as e:
            logger.error(f"OBS connection failed: {e}")
            debug_print(f"ERROR: OBS connection failed: {e}")
            self.obs = None
            
    def add_stream(self):
        """配信を追加"""
        url = self.url_entry.get().strip()
        
        debug_print(f"DEBUG: add_stream called with URL: {url}")
        
        if not url:
            messagebox.showerror("エラー", "URLを入力してください")
            return
            
        # URLからプラットフォームを自動判定
        platform = self.detect_platform(url)
        if not platform:
            messagebox.showerror("エラー", "対応していないURLです。\nYouTubeまたはTwitchのURLを入力してください。")
            return
            
        debug_print(f"DEBUG: Detected platform: {platform}")
        
        # ストリームIDを生成
        stream_id = f"{platform}_{len(self.stream_manager.streams) + 1}"
        debug_print(f"DEBUG: Generated stream_id: {stream_id}")
        
        # タイトルを取得
        title = self.get_stream_title(platform, url)
        debug_print(f"DEBUG: Retrieved title: {title}")
        
        # 新しい配信設定を作成
        stream_settings = StreamSettings(
            stream_id=stream_id,
            platform=platform,
            url=url,
            title=title
        )
        debug_print(f"DEBUG: Created StreamSettings")
        
        # ストリームマネージャーに追加
        self.stream_manager.add_stream(stream_settings)
        debug_print(f"DEBUG: Added to StreamManager, total streams: {len(self.stream_manager.streams)}")
        
        # リストを更新
        self.update_stream_list()
        debug_print(f"DEBUG: Updated stream list")
        
        # タブを追加
        self.add_stream_tab(stream_settings)
        debug_print(f"DEBUG: Added stream tab")
        
        # エントリをクリア
        self.url_entry.delete(0, tk.END)
        debug_print(f"DEBUG: Cleared URL entry")
        
    def update_stream_list(self):
        """配信リストを更新"""
        # 既存の項目を削除
        for item in self.stream_tree.get_children():
            self.stream_tree.delete(item)
            
        # 新しい項目を追加
        for stream_id, settings in self.stream_manager.streams.items():
            status = "● 受信中" if settings.is_active else "○ 停止中"
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
        info_frame = ttk.LabelFrame(tab_frame, text="配信情報")
        info_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # タイトル表示
        title_info_frame = ttk.Frame(info_frame)
        title_info_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(title_info_frame, text="タイトル:").pack(side=tk.LEFT)
        title_label = ttk.Label(title_info_frame, text=stream_settings.title if stream_settings.title else "(取得中...)", 
                               foreground="blue", wraplength=500)
        title_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # URL表示
        url_info_frame = ttk.Frame(info_frame)
        url_info_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(url_info_frame, text="URL:").pack(side=tk.LEFT)
        url_label = ttk.Label(url_info_frame, text=stream_settings.url, foreground="blue")
        url_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # プラットフォーム表示
        platform_info_frame = ttk.Frame(info_frame)
        platform_info_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(platform_info_frame, text="プラットフォーム:").pack(side=tk.LEFT)
        ttk.Label(platform_info_frame, text=stream_settings.platform.title()).pack(side=tk.LEFT, padx=(5, 0))
        
        # ステータス表示
        status_info_frame = ttk.Frame(info_frame)
        status_info_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(status_info_frame, text="ステータス:").pack(side=tk.LEFT)
        status_label = ttk.Label(status_info_frame, text="停止中", foreground="red")
        status_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # 統計情報表示
        stats_frame = ttk.LabelFrame(tab_frame, text="統計情報")
        stats_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        # コメント数表示
        comment_count_frame = ttk.Frame(stats_frame)
        comment_count_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(comment_count_frame, text="受信コメント数:").pack(side=tk.LEFT)
        comment_count_label = ttk.Label(comment_count_frame, text="0")
        comment_count_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # リクエスト処理数表示
        request_count_frame = ttk.Frame(stats_frame)
        request_count_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(request_count_frame, text="処理したリクエスト数:").pack(side=tk.LEFT)
        request_count_label = ttk.Label(request_count_frame, text="0")
        request_count_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # 各要素をstream_settingsに関連付け
        stream_settings.title_label = title_label
        stream_settings.status_label = status_label
        stream_settings.comment_count_label = comment_count_label
        stream_settings.request_count_label = request_count_label
        stream_settings.processed_requests = 0
        
    def start_selected_stream(self):
        """選択された配信を開始"""
        selection = self.stream_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "配信を選択してください")
            return
            
        item = self.stream_tree.item(selection[0])
        stream_id = item['values'][0]
        
        print(f"DEBUG: Starting stream {stream_id}")
        
        def comment_callback(comment_data):
            """コメント受信時のコールバック"""
            print(f"DEBUG: comment_callback called with data: {comment_data}")
            self.process_comment(stream_id, comment_data)
            
        print(f"DEBUG: Created callback function")
        
        if self.stream_manager.start_stream(stream_id, comment_callback):
            print(f"DEBUG: start_stream returned True")
            self.update_stream_list()
            # ステータスラベル更新
            settings = self.stream_manager.streams[stream_id]
            if hasattr(settings, 'status_label'):
                settings.status_label.config(text="実行中", foreground="green")
            # 受信開始時のダイアログを削除（メッセージを表示しない）
        else:
            print(f"DEBUG: start_stream returned False")
            messagebox.showerror("エラー", f"配信 {stream_id} の開始に失敗しました")
            
    def stop_selected_stream(self):
        """選択された配信を停止"""
        selection = self.stream_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "配信を選択してください")
            return
            
        item = self.stream_tree.item(selection[0])
        stream_id = item['values'][0]
        
        self.stream_manager.stop_stream(stream_id)
        self.update_stream_list()
        # ステータスラベル更新
        settings = self.stream_manager.streams[stream_id]
        if hasattr(settings, 'status_label'):
            settings.status_label.config(text="停止中", foreground="red")
        
    def remove_selected_stream(self):
        """選択された配信を削除"""
        selection = self.stream_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "配信を選択してください")
            return
            
        item = self.stream_tree.item(selection[0])
        stream_id = item['values'][0]
        
        if messagebox.askyesno("確認", f"配信 {stream_id} を削除しますか？"):
            self.stream_manager.remove_stream(stream_id)
            self.update_stream_list()
            # タブも削除
            for i, tab_id in enumerate(self.notebook.tabs()):
                tab_text = self.notebook.tab(tab_id, "text")
                if stream_id in tab_text:
                    self.notebook.forget(i)
                    break
    
    def edit_stream_url(self):
        """選択された配信のURLを編集"""
        selection = self.stream_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "配信を選択してください")
            return
        
        item = self.stream_tree.item(selection[0])
        stream_id = item['values'][0]
        
        if stream_id not in self.stream_manager.streams:
            return
        
        settings = self.stream_manager.streams[stream_id]
        current_url = settings.url
        
        # カスタムURL編集ダイアログ
        dialog = tk.Toplevel(self.root)
        dialog.title("URL編集")
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
        ttk.Label(url_frame, text="新しいURL:").pack(side=tk.LEFT)
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
        
        ttk.Button(button_frame, text="OK", command=on_ok).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="キャンセル", command=on_cancel).pack(side=tk.RIGHT)
        
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
                messagebox.showerror("エラー", "対応していないURLです。\nYouTubeまたはTwitchのURLを入力してください。")
                return
            
            # URLとプラットフォームを更新
            settings.url = new_url
            settings.platform = new_platform
            
            # タイトルも再取得
            new_title = self.get_stream_title(new_platform, new_url)
            settings.title = new_title
            
            # タイトルラベルが存在すれば更新
            if hasattr(settings, 'title_label'):
                settings.title_label.config(text=new_title if new_title else "(取得中...)")
            
            # リストを更新
            self.update_stream_list()
            
            # 配信が実行中の場合は警告
            if settings.is_active:
                messagebox.showinfo("URL更新", 
                    "URLを更新しました。\n\n配信が実行中です。変更を反映するには、一度停止して再度開始してください。")
            else:
                messagebox.showinfo("URL更新", "URLを更新しました。")
                    
    def configure_selected_stream(self):
        """選択された配信の設定"""
        selection = self.stream_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "配信を選択してください")
            return
            
        item = self.stream_tree.item(selection[0])
        stream_id = item['values'][0]
        
        # 設定ダイアログを開く
        self.show_stream_settings(stream_id)
        
    def process_comment(self, stream_id, comment_data):
        """コメントを処理"""
        debug_print(f"DEBUG: process_comment called for stream_id: {stream_id}")
        debug_print(f"DEBUG: comment_data: {comment_data}")
        
        # NGユーザチェック
        for ng_user in self.global_settings.ng_users:
            if (ng_user['platform'] == comment_data['platform'] and 
                ng_user['id'] == comment_data['author_id']):
                debug_print(f"DEBUG: Filtered NG user comment from {comment_data['author']}")
                return

        if stream_id not in self.stream_manager.streams:
            debug_print(f"ERROR: stream_id {stream_id} not found in streams")
            return
            
        settings = self.stream_manager.streams[stream_id]
        
        # コメントにstream_idを追加
        comment_data['stream_id'] = stream_id
        
        # コメントをリストに追加
        settings.comments.append(comment_data)
        print(f"DEBUG: Added comment to settings.comments, total: {len(settings.comments)}")
        
        # 統計更新
        if hasattr(settings, 'comment_count_label'):
            self.root.after(0, lambda: settings.comment_count_label.config(text=str(len(settings.comments))))
        
        # GUIスレッドで更新（共通コメント表示エリアに表示）
        print(f"DEBUG: Scheduling GUI update via root.after")
        self.root.after(0, lambda: self.update_comment_display(comment_data))
        
        # リクエスト処理
        self.process_request_commands(stream_id, comment_data)
        
    def update_comment_display(self, comment_data):
        """共通コメント表示エリアを更新"""
        debug_print(f"DEBUG: update_comment_display called")
        debug_print(f"DEBUG: comment_data in update: {comment_data}")
        
        try:
            # timestampが文字列かdatetimeオブジェクトかを判定
            timestamp_value = comment_data['timestamp']
            if isinstance(timestamp_value, str):
                # 既に文字列の場合、そのまま使用（YYYY/MM/DD HH:MM:SS形式を想定）
                timestamp = timestamp_value
            else:
                # datetimeオブジェクトの場合、日付と時刻を含む形式に変換
                timestamp = timestamp_value.strftime('%Y/%m/%d %H:%M:%S')
            
            debug_print(f"DEBUG: Formatted timestamp: {timestamp}")
            
            values = (
                timestamp,
                comment_data['author'],
                comment_data['message'],
                comment_data['stream_id'],
                comment_data['platform']
            )
            debug_print(f"DEBUG: Inserting values: {values}")
            
            # コメントデータをタグとして保存（右クリック用）
            item_id = self.comment_tree.insert('', tk.END, values=values, tags=(comment_data['author_id'], comment_data['platform']))
            
            debug_print(f"DEBUG: Successfully inserted into comment_tree")
            
            # 自動スクロール
            if self.auto_scroll.get():
                children = self.comment_tree.get_children()
                if children:
                    self.comment_tree.see(children[-1])
                    debug_print(f"DEBUG: Auto-scrolled to latest comment")
                    
            # コメント数制限（パフォーマンス対策）
            children = self.comment_tree.get_children()
            if len(children) > 1000:  # 1000件を超えたら古いものを削除
                self.comment_tree.delete(children[0])
                debug_print(f"DEBUG: Deleted old comment, total now: {len(children)-1}")
                
        except Exception as e:
            debug_print(f"ERROR: Exception in update_comment_display: {e}")
            import traceback
            debug_print(f"ERROR: Traceback: {traceback.format_exc()}")
            
    def add_manager_from_comment(self):
        """選択されたコメントのユーザーを管理者に追加"""
        selection = self.comment_tree.selection()
        if not selection:
            return
            
        item_id = selection[0]
        values = self.comment_tree.item(item_id)['values']
        tags = self.comment_tree.item(item_id)['tags']
        
        if len(values) >= 2 and len(tags) >= 2:
            author = values[1]  # ユーザー名
            platform = tags[1]  # プラットフォーム
            author_id = tags[0]  # ユーザーID
            
            # 新形式で管理者エントリを作成
            manager_entry = {
                "platform": platform,
                "id": author_id,
                "name": author
            }
            
            # 重複チェック
            for manager in self.global_settings.managers:
                if manager['platform'] == platform and manager['id'] == author_id:
                    messagebox.showinfo("管理者追加", f"{author}は既に管理者に登録されています。")
                    return
            
            self.global_settings.managers.append(manager_entry)
            self.global_settings.save()
            messagebox.showinfo("管理者追加", f"{author}を管理者に追加しました。")

    def add_ng_user_from_comment(self):
        """選択されたコメントのユーザーをNGユーザに追加"""
        selection = self.comment_tree.selection()
        if not selection:
            return

        item_id = selection[0]
        values = self.comment_tree.item(item_id)['values']
        tags = self.comment_tree.item(item_id)['tags']

        if len(values) >= 2 and len(tags) >= 2:
            author = values[1]
            platform = tags[1]
            author_id = tags[0]

            ng_entry = {
                "platform": platform,
                "id": author_id,
                "name": author
            }

            # 重複チェック
            for ng in self.global_settings.ng_users:
                if ng['platform'] == platform and ng['id'] == author_id:
                    messagebox.showinfo("NGユーザ追加", f"{author}は既にNGユーザに登録されています。")
                    return

            self.global_settings.ng_users.append(ng_entry)
            self.global_settings.save()
            messagebox.showinfo("NGユーザ追加", f"{author}をNGユーザに追加しました。")

    def process_request_commands(self, stream_id, comment_data):
        """リクエストコマンドを処理"""
        settings = self.stream_manager.streams[stream_id]
        message = comment_data['message']
        author = comment_data['author']
        is_moderator = comment_data.get('is_moderator', False)
        
        # 共通設定を使用
        global_settings = self.global_settings
        
        # プッシュワード処理
        if not global_settings.push_manager_only or is_moderator:
            for pushword in global_settings.pushwords:
                if message.startswith(pushword):
                    req = message[len(pushword):].strip()
                    # 辞書形式でリクエストを保存
                    request_data = {
                        'content': req,
                        'author': author,
                        'platform': settings.platform,
                        'stream_id': stream_id
                    }
                    self.common_requests.append(request_data)
                    
                    # リクエスト処理数更新
                    settings.processed_requests += 1
                    if hasattr(settings, 'request_count_label'):
                        self.root.after(0, lambda: settings.request_count_label.config(text=str(settings.processed_requests)))
                    
                    self.root.after(0, lambda: self.update_request_display())
                    self.generate_xml()
                    break
                    
        # プルワード処理
        if not global_settings.pull_manager_only or is_moderator:
            for pullword in global_settings.pullwords:
                if pullword in message:
                    if len(self.common_requests) > 0:
                        self.common_requests.pop(0)
                        
                        # リクエスト処理数更新
                        settings.processed_requests += 1
                        if hasattr(settings, 'request_count_label'):
                            self.root.after(0, lambda: settings.request_count_label.config(text=str(settings.processed_requests)))
                        
                        self.root.after(0, lambda: self.update_request_display())
                        self.generate_xml()
                    break
                    
    def update_request_display(self):
        """共通リクエスト表示を更新"""
        # 既存の項目を削除
        for item in self.request_tree.get_children():
            self.request_tree.delete(item)
        
        # 新しい項目を追加（番号付き）
        for idx, req in enumerate(self.common_requests, start=1):
            self.request_tree.insert('', tk.END, values=(
                idx,
                req['content'],
                req['author'],
                req['platform']
            ))
            
    def generate_xml(self):
        """XMLファイルを生成"""
        with open('todo.xml', 'w', encoding='utf-8') as f:
            f.write('<?xml version="1.0" encoding="utf-8"?>\n')
            f.write('<TODOs>\n')
            
            # 共通リクエストリストを使用
            for req in self.common_requests:
                # 辞書形式のリクエストを文字列に整形
                request_text = f"{req['content']} ({req['author']}さん) [{req['platform']}]"
                f.write(f'<item>{self.escape_for_xml(request_text)}</item>\n')
                    
            f.write('</TODOs>\n')
            
    def escape_for_xml(self, text):
        """XML用エスケープ"""
        return (text.replace('&', '&amp;')
                   .replace('<', '&lt;')
                   .replace('>', '&gt;')
                   .replace('"', '&quot;')
                   .replace("'", '&apos;'))
                   
    def add_manual_request(self):
        """手動リクエストを追加"""
        req = self.manual_req_entry.get().strip()
        if req:
            # 手動追加の場合は辞書形式で保存
            request_data = {
                'content': req,
                'author': '手動追加',
                'platform': 'manual',
                'stream_id': 'manual'
            }
            self.common_requests.append(request_data)
            self.update_request_display()
            self.generate_xml()
            self.manual_req_entry.delete(0, tk.END)
            
    def remove_selected_request(self):
        """選択されたリクエストを削除"""
        selection = self.request_tree.selection()
        if selection:
            item = self.request_tree.item(selection[0])
            # 番号から実際のインデックスを取得（番号は1から始まる）
            index = item['values'][0] - 1
            self.common_requests.pop(index)
            self.update_request_display()
            self.generate_xml()
            
    def move_request_up(self):
        """選択されたリクエストを上に移動"""
        selection = self.request_tree.selection()
        if selection:
            item = self.request_tree.item(selection[0])
            # 番号から実際のインデックスを取得（番号は1から始まる）
            index = item['values'][0] - 1
            if index > 0:
                # リストの順序を入れ替え
                self.common_requests[index], self.common_requests[index-1] = \
                    self.common_requests[index-1], self.common_requests[index]
                self.update_request_display()
                self.generate_xml()
                # 選択を移動後の位置に（番号で選択）
                for item_id in self.request_tree.get_children():
                    if self.request_tree.item(item_id)['values'][0] == index:
                        self.request_tree.selection_set(item_id)
                        self.request_tree.see(item_id)
                        break
            
    def move_request_down(self):
        """選択されたリクエストを下に移動"""
        selection = self.request_tree.selection()
        if selection:
            item = self.request_tree.item(selection[0])
            # 番号から実際のインデックスを取得（番号は1から始まる）
            index = item['values'][0] - 1
            if index < len(self.common_requests) - 1:
                # リストの順序を入れ替え
                self.common_requests[index], self.common_requests[index+1] = \
                    self.common_requests[index+1], self.common_requests[index]
                self.update_request_display()
                self.generate_xml()
                # 選択を移動後の位置に（番号で選択）
                for item_id in self.request_tree.get_children():
                    if self.request_tree.item(item_id)['values'][0] == index + 2:
                        self.request_tree.selection_set(item_id)
                        self.request_tree.see(item_id)
                        break
            
    def clear_all_requests(self):
        """全リクエストをクリア"""
        if messagebox.askyesno("確認", "全てのリクエストをクリアしますか？"):
            self.common_requests.clear()
            self.update_request_display()
            self.generate_xml()
            
    def clear_all_comments(self):
        """全コメントをクリア"""
        if messagebox.askyesno("確認", "全てのコメントをクリアしますか？"):
            # Treeviewをクリア
            for item in self.comment_tree.get_children():
                self.comment_tree.delete(item)
            
            # 各ストリームのコメントリストもクリア
            for stream_id, settings in self.stream_manager.streams.items():
                settings.comments.clear()
                if hasattr(settings, 'comment_count_label'):
                    settings.comment_count_label.config(text="0")
                    
    def show_settings(self):
        """設定ダイアログを表示"""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("設定")
        settings_window.geometry("600x600")
        settings_window.transient(self.root)
        settings_window.grab_set()
        
        # タブ構成
        settings_notebook = ttk.Notebook(settings_window)
        settings_notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # OBS設定タブ
        obs_frame = ttk.Frame(settings_notebook)
        settings_notebook.add(obs_frame, text="OBS設定")
        
        obs_settings_frame = ttk.LabelFrame(obs_frame, text="OBS接続設定")
        obs_settings_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # OBS設定フォーム
        host_frame = ttk.Frame(obs_settings_frame)
        host_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(host_frame, text="ホスト:").pack(side=tk.LEFT)
        obs_host_var = tk.StringVar(value=self.global_settings.obs_host)
        ttk.Entry(host_frame, textvariable=obs_host_var, width=30).pack(side=tk.LEFT, padx=(5, 0))
        
        port_frame = ttk.Frame(obs_settings_frame)
        port_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(port_frame, text="ポート:").pack(side=tk.LEFT)
        obs_port_var = tk.StringVar(value=str(self.global_settings.obs_port))
        ttk.Entry(port_frame, textvariable=obs_port_var, width=30).pack(side=tk.LEFT, padx=(5, 0))
        
        passwd_frame = ttk.Frame(obs_settings_frame)
        passwd_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(passwd_frame, text="パスワード:").pack(side=tk.LEFT)
        obs_passwd_var = tk.StringVar(value=self.global_settings.obs_passwd)
        ttk.Entry(passwd_frame, textvariable=obs_passwd_var, width=30, show="*").pack(side=tk.LEFT, padx=(5, 0))
        
        # その他の設定
        other_settings_frame = ttk.LabelFrame(obs_frame, text="その他の設定")
        other_settings_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        keep_top_var = tk.BooleanVar(value=self.global_settings.keep_on_top)
        ttk.Checkbutton(other_settings_frame, text="ウィンドウを最前面に表示", 
                       variable=keep_top_var).pack(anchor=tk.W, padx=10, pady=5)
        
        # デバッグ設定
        debug_settings_frame = ttk.LabelFrame(obs_frame, text="デバッグ設定")
        debug_settings_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        debug_enabled_var = tk.BooleanVar(value=self.global_settings.debug_enabled)
        ttk.Checkbutton(debug_settings_frame, text="デバッグモードを有効にする（再起動が必要）", 
                       variable=debug_enabled_var).pack(anchor=tk.W, padx=10, pady=5)
        
        # トリガーワード設定タブ
        trigger_frame = ttk.Frame(settings_notebook)
        settings_notebook.add(trigger_frame, text="トリガーワード")
        
        # プッシュワード設定
        push_frame = ttk.LabelFrame(trigger_frame, text="リクエスト追加ワード（全配信共通）")
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
            word = simpledialog.askstring("追加", "リクエスト追加ワードを入力:")
            if word and word not in self.global_settings.pushwords:
                self.global_settings.pushwords.append(word)
                push_listbox.insert(tk.END, word)
                
        def remove_pushword():
            selection = push_listbox.curselection()
            if selection:
                index = selection[0]
                self.global_settings.pushwords.pop(index)
                push_listbox.delete(index)
        
        ttk.Button(push_button_frame, text="追加", command=add_pushword).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(push_button_frame, text="削除", command=remove_pushword).pack(side=tk.LEFT, padx=(0, 5))
        
        # プルワード設定
        pull_frame = ttk.LabelFrame(trigger_frame, text="リクエスト削除ワード（全配信共通）")
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
            word = simpledialog.askstring("追加", "リクエスト削除ワードを入力:")
            if word and word not in self.global_settings.pullwords:
                self.global_settings.pullwords.append(word)
                pull_listbox.insert(tk.END, word)
                
        def remove_pullword():
            selection = pull_listbox.curselection()
            if selection:
                index = selection[0]
                self.global_settings.pullwords.pop(index)
                pull_listbox.delete(index)
        
        ttk.Button(pull_button_frame, text="追加", command=add_pullword).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(pull_button_frame, text="削除", command=remove_pullword).pack(side=tk.LEFT, padx=(0, 5))
        
        # 権限設定タブ
        permission_frame = ttk.Frame(settings_notebook)
        settings_notebook.add(permission_frame, text="権限設定")
        
        perm_settings_frame = ttk.LabelFrame(permission_frame, text="権限設定（全配信共通）")
        perm_settings_frame.pack(fill=tk.X, padx=10, pady=10)
        
        push_manager_var = tk.BooleanVar(value=self.global_settings.push_manager_only)
        ttk.Checkbutton(perm_settings_frame, text="リクエスト追加を管理者のみ許可", 
                       variable=push_manager_var).pack(anchor=tk.W, padx=10, pady=5)
        
        pull_manager_var = tk.BooleanVar(value=self.global_settings.pull_manager_only)
        ttk.Checkbutton(perm_settings_frame, text="リクエスト削除を管理者のみ許可", 
                       variable=pull_manager_var).pack(anchor=tk.W, padx=10, pady=5)
        
        # 管理者設定
        manager_frame = ttk.LabelFrame(permission_frame, text="管理者設定")
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
        
        ttk.Button(manager_button_frame, text="削除", command=remove_manager).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Label(manager_frame, text="※コメントから右クリックで管理者IDに追加することもできます", 
                 foreground="gray").pack(padx=10, pady=(0, 10))
        
        # NGユーザ設定タブ
        ng_user_frame = ttk.Frame(settings_notebook)
        settings_notebook.add(ng_user_frame, text="NGユーザ設定")
        
        ng_settings_frame = ttk.LabelFrame(ng_user_frame, text="NGユーザ管理")
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
        
        ttk.Button(ng_button_frame, text="削除", command=remove_ng_user).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Label(ng_settings_frame, text="※コメント一覧から右クリックでNGユーザに追加できます", 
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
                messagebox.showerror("エラー", "正しいport番号を入力してください")
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
                messagebox.showinfo("デバッグ設定変更", 
                                   "デバッグ設定の変更を反映するには、アプリケーションを再起動してください。")
            
            # 最前面設定を適用
            self.root.attributes('-topmost', self.global_settings.keep_on_top)
            
            # OBS再接続
            self.setup_obs()
            
            settings_window.destroy()
            
        ttk.Button(button_frame, text="保存", command=save_settings).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="キャンセル", command=settings_window.destroy).pack(side=tk.RIGHT)
        
    def on_closing(self):
        """アプリケーション終了時の処理"""
        # 現在開いている配信のURLを保存
        active_urls = []
        for stream_id, settings in self.stream_manager.streams.items():
            if settings.is_active:
                active_urls.append(settings.url)
        self.global_settings.last_streams = active_urls
        
        # 全配信を停止
        for stream_id in list(self.stream_manager.streams.keys()):
            self.stream_manager.stop_stream(stream_id)
            
        # 設定保存
        self.global_settings.save()
        
        # ウィンドウを閉じる
        self.root.destroy()
        
    def run(self):
        """アプリケーション実行"""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()

def main():
    app = MultiStreamCommentHelper()
    app.run()

if __name__ == "__main__":
    main()
