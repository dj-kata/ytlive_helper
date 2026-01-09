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
    def __init__(self, stream_id="", platform="youtube", url=""):
        self.stream_id = stream_id
        self.platform = platform  # "youtube" or "twitch"
        self.url = url
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
        
        # 共通管理者リスト
        self.managers = []
        
    def save(self, filename='global_settings.json'):
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.__dict__, f, indent=2, ensure_ascii=False)
    
    def load(self, filename='global_settings.json'):
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for key, value in data.items():
                    setattr(self, key, value)

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
                        manager_ids = []
                        for m in self.global_settings.managers:
                            if '(' in m and ')' in m:
                                manager_ids.append(m.split('(')[1][:-1])
                            else:
                                manager_ids.append(m)
                        
                        comment_data = {
                            'platform': 'youtube',
                            'author': comment.author.name,
                            'message': comment.message,
                            'timestamp': comment.datetime,
                            'author_id': comment.author.channelId,
                            'is_moderator': comment.author.channelId in manager_ids or comment.author.name in manager_ids
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
            is_moderator = user_name in self.global_settings.managers
            
            comment_data = {
                'platform': 'twitch',
                'author': user_name,
                'message': message,
                'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
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
                stream_settings = StreamSettings(
                    stream_id=stream_id,
                    platform=platform,
                    url=url
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
        
        ttk.Button(add_frame, text="追加", command=self.add_stream).pack(side=tk.LEFT, padx=(10, 0))
        
        # プラットフォーム表示（読み取り専用）
        platform_label = ttk.Label(add_frame, text="プラットフォーム: 自動判定", foreground="gray")
        platform_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # 配信リスト
        list_frame = ttk.Frame(stream_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # Treeview for stream list
        columns = ('ID', 'Platform', 'URL', 'Status')
        self.stream_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=6)
        
        for col in columns:
            self.stream_tree.heading(col, text=col)
            self.stream_tree.column(col, width=150)
            
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.stream_tree.yview)
        self.stream_tree.configure(yscrollcommand=scrollbar.set)
        
        self.stream_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 配信操作ボタン
        button_frame = ttk.Frame(stream_frame)
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        ttk.Button(button_frame, text="開始", command=self.start_selected_stream).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="停止", command=self.stop_selected_stream).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="削除", command=self.remove_selected_stream).pack(side=tk.LEFT, padx=(0, 5))
        
        # 共通リクエスト管理エリア
        request_frame = ttk.LabelFrame(main_frame, text="リクエスト一覧（全配信）")
        request_frame.pack(fill=tk.X, pady=(10, 0))
        
        # リクエストリストボックス
        list_frame = ttk.Frame(request_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.request_listbox = tk.Listbox(list_frame, height=8)
        self.request_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        req_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.request_listbox.yview)
        self.request_listbox.configure(yscrollcommand=req_scrollbar.set)
        req_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # リクエスト操作ボタン
        req_button_frame = ttk.Frame(request_frame)
        req_button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        # 手動追加エントリ
        ttk.Label(req_button_frame, text="手動追加:").pack(side=tk.LEFT)
        self.manual_req_entry = ttk.Entry(req_button_frame, width=30)
        self.manual_req_entry.pack(side=tk.LEFT, padx=(5, 10))
        
        ttk.Button(req_button_frame, text="追加", command=self.add_manual_request).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(req_button_frame, text="削除", command=self.remove_selected_request).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(req_button_frame, text="上に移動", command=self.move_request_up).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(req_button_frame, text="下に移動", command=self.move_request_down).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(req_button_frame, text="クリア", command=self.clear_all_requests).pack(side=tk.LEFT, padx=(0, 5))
        
        # 共通コメント表示エリア
        comment_frame = ttk.LabelFrame(main_frame, text="コメント一覧（全配信）")
        comment_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        # コメントTreeview
        comment_columns = ('時刻', 'ユーザー', 'コメント', '配信ID', 'プラットフォーム')
        self.comment_tree = ttk.Treeview(comment_frame, columns=comment_columns, show='headings', height=12)
        
        for col in comment_columns:
            self.comment_tree.heading(col, text=col)
            if col == 'コメント':
                self.comment_tree.column(col, width=300)
            elif col == '配信ID':
                self.comment_tree.column(col, width=120)
            else:
                self.comment_tree.column(col, width=100)
                
        comment_scrollbar = ttk.Scrollbar(comment_frame, orient=tk.VERTICAL, command=self.comment_tree.yview)
        self.comment_tree.configure(yscrollcommand=comment_scrollbar.set)
        
        # 右クリックメニュー
        self.comment_context_menu = tk.Menu(self.root, tearoff=0)
        self.comment_context_menu.add_command(label="管理者IDに追加", command=self.add_manager_from_comment)
        
        def on_comment_right_click(event):
            # 選択されたアイテムがあるかチェック
            item = self.comment_tree.identify_row(event.y)
            if item:
                self.comment_tree.selection_set(item)
                self.comment_context_menu.post(event.x_root, event.y_root)
        
        self.comment_tree.bind("<Button-3>", on_comment_right_click)  # 右クリック
        
        self.comment_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        comment_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=10)
        
        # コメント操作ボタン
        comment_button_frame = ttk.Frame(comment_frame)
        comment_button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
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
        
        # 新しい配信設定を作成
        stream_settings = StreamSettings(
            stream_id=stream_id,
            platform=platform,
            url=url
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
            status = "実行中" if settings.is_active else "停止中"
            self.stream_tree.insert('', tk.END, values=(
                stream_id, settings.platform, settings.url[:50], status
            ))
            
    def add_stream_tab(self, stream_settings):
        """配信用の情報表示タブを追加"""
        # タブフレーム作成
        tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(tab_frame, text=f"{stream_settings.platform}: {stream_settings.stream_id}")
        
        # 配信情報表示
        info_frame = ttk.LabelFrame(tab_frame, text="配信情報")
        info_frame.pack(fill=tk.X, padx=10, pady=10)
        
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
            messagebox.showinfo("成功", f"配信 {stream_id} を開始しました")
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
        messagebox.showinfo("成功", f"配信 {stream_id} を停止しました")
        
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
        print(f"DEBUG: process_comment called for stream_id: {stream_id}")
        print(f"DEBUG: comment_data: {comment_data}")
        
        if stream_id not in self.stream_manager.streams:
            print(f"ERROR: stream_id {stream_id} not found in streams")
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
                # 既に文字列の場合、時刻部分のみを抽出
                if ' ' in timestamp_value:
                    timestamp = timestamp_value.split(' ')[1]  # '2025-07-17 23:48:06' -> '23:48:06'
                else:
                    timestamp = timestamp_value
            else:
                # datetimeオブジェクトの場合
                timestamp = timestamp_value.strftime('%H:%M:%S')
            
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
            item_id = self.comment_tree.insert('', tk.END, values=values, tags=(comment_data['author_id'],))
            
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
        
        if len(values) >= 2:
            author = values[1]  # ユーザー名
            platform = values[4]  # プラットフォーム
            
            # プラットフォームに応じた管理者ID形式を作成
            if platform == 'youtube' and tags:
                # YouTubeの場合、タグからauthor_idを取得
                author_id = tags[0]
                manager_entry = f"{author}({author_id})"
            else:
                # Twitchの場合
                manager_entry = author
            
            if manager_entry not in self.global_settings.managers:
                self.global_settings.managers.append(manager_entry)
                self.global_settings.save()
                messagebox.showinfo("管理者追加", f"{author}を管理者に追加しました。")
            else:
                messagebox.showinfo("管理者追加", f"{author}は既に管理者に登録されています。")
            
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
                    request_text = f"{req} ({author}さん) [{settings.platform}:{stream_id}]"
                    self.common_requests.append(request_text)
                    
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
        self.request_listbox.delete(0, tk.END)
        for req in self.common_requests:
            self.request_listbox.insert(tk.END, req)
            
    def generate_xml(self):
        """XMLファイルを生成"""
        with open('todo.xml', 'w', encoding='utf-8') as f:
            f.write('<?xml version="1.0" encoding="utf-8"?>\n')
            f.write('<TODOs>\n')
            
            # 共通リクエストリストを使用
            for req in self.common_requests:
                f.write(f'<item>{self.escape_for_xml(req)}</item>\n')
                    
            f.write('</TODOs>\n')
            
    def escape_for_xml(self, text):
        """XML用エスケープ"""
        return (text.replace('&', '&amp;')
                   .replace('<', '&lt;')
                   .replace('>', '&gt;')
                   .replace('"', '&quot;')
                   .replace("'", '&apos;'))
                   
    def add_manual_request(self):
        """手動でリクエストを追加"""
        request = self.manual_req_entry.get().strip()
        if request:
            request_text = f"{request} (手動追加)"
            self.common_requests.append(request_text)
            self.update_request_display()
            self.generate_xml()
            self.manual_req_entry.delete(0, tk.END)
            
    def remove_selected_request(self):
        """選択されたリクエストを削除"""
        selection = self.request_listbox.curselection()
        if selection:
            index = selection[0]
            self.common_requests.pop(index)
            self.update_request_display()
            self.generate_xml()
            
    def move_request_up(self):
        """選択されたリクエストを上に移動"""
        selection = self.request_listbox.curselection()
        if selection and selection[0] > 0:
            index = selection[0]
            # リストの要素を入れ替え
            self.common_requests[index], self.common_requests[index-1] = \
                self.common_requests[index-1], self.common_requests[index]
            self.update_request_display()
            # 選択状態を維持
            self.request_listbox.selection_set(index-1)
            self.generate_xml()
            
    def move_request_down(self):
        """選択されたリクエストを下に移動"""
        selection = self.request_listbox.curselection()
        if selection and selection[0] < len(self.common_requests) - 1:
            index = selection[0]
            # リストの要素を入れ替え
            self.common_requests[index], self.common_requests[index+1] = \
                self.common_requests[index+1], self.common_requests[index]
            self.update_request_display()
            # 選択状態を維持
            self.request_listbox.selection_set(index+1)
            self.generate_xml()
            
    def clear_all_requests(self):
        """全リクエストをクリア"""
        if messagebox.askyesno("確認", "全てのリクエストをクリアしますか？"):
            self.common_requests.clear()
            self.update_request_display()
            self.generate_xml()
            
    def clear_all_comments(self):
        """全配信の共通コメント表示をクリア"""
        for item in self.comment_tree.get_children():
            self.comment_tree.delete(item)
        
        # 各配信のコメント履歴もクリア
        for settings in self.stream_manager.streams.values():
            settings.comments.clear()
            
    def add_pushword(self, stream_id, listbox):
        """プッシュワードを追加"""
        word = simpledialog.askstring("追加", "リクエスト追加ワードを入力:")
        if word and word not in self.stream_manager.streams[stream_id].pushwords:
            self.stream_manager.streams[stream_id].pushwords.append(word)
            listbox.insert(tk.END, word)
            
    def remove_pushword(self, stream_id, listbox):
        """プッシュワードを削除"""
        selection = listbox.curselection()
        if selection:
            index = selection[0]
            self.stream_manager.streams[stream_id].pushwords.pop(index)
            listbox.delete(index)
            
    def add_pullword(self, stream_id, listbox):
        """プルワードを追加"""
        word = simpledialog.askstring("追加", "リクエスト削除ワードを入力:")
        if word and word not in self.stream_manager.streams[stream_id].pullwords:
            self.stream_manager.streams[stream_id].pullwords.append(word)
            listbox.insert(tk.END, word)
            
    def remove_pullword(self, stream_id, listbox):
        """プルワードを削除"""
        selection = listbox.curselection()
        if selection:
            index = selection[0]
            self.stream_manager.streams[stream_id].pullwords.pop(index)
            listbox.delete(index)
        
    def show_settings(self):
        """グローバル設定ダイアログ"""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("設定")
        settings_window.geometry("600x700")
        settings_window.transient(self.root)
        settings_window.grab_set()
        
        # ノートブック（タブ）
        settings_notebook = ttk.Notebook(settings_window)
        settings_notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # OBS設定タブ
        obs_frame = ttk.Frame(settings_notebook)
        settings_notebook.add(obs_frame, text="OBS設定")
        
        obs_settings_frame = ttk.LabelFrame(obs_frame, text="OBS WebSocket設定")
        obs_settings_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(obs_settings_frame, text="Host:").grid(row=0, column=0, sticky=tk.W, padx=10, pady=5)
        obs_host_var = tk.StringVar(value=self.global_settings.obs_host)
        ttk.Entry(obs_settings_frame, textvariable=obs_host_var).grid(row=0, column=1, padx=10, pady=5)
        
        ttk.Label(obs_settings_frame, text="Port:").grid(row=1, column=0, sticky=tk.W, padx=10, pady=5)
        obs_port_var = tk.StringVar(value=str(self.global_settings.obs_port))
        ttk.Entry(obs_settings_frame, textvariable=obs_port_var).grid(row=1, column=1, padx=10, pady=5)
        
        ttk.Label(obs_settings_frame, text="Password:").grid(row=2, column=0, sticky=tk.W, padx=10, pady=5)
        obs_passwd_var = tk.StringVar(value=self.global_settings.obs_passwd)
        ttk.Entry(obs_settings_frame, textvariable=obs_passwd_var, show="*").grid(row=2, column=1, padx=10, pady=5)
        
        # その他設定
        other_frame = ttk.LabelFrame(obs_frame, text="その他")
        other_frame.pack(fill=tk.X, padx=10, pady=10)
        
        keep_top_var = tk.BooleanVar(value=self.global_settings.keep_on_top)
        ttk.Checkbutton(other_frame, text="常に最前面に表示", variable=keep_top_var).pack(anchor=tk.W, padx=10, pady=5)
        
        debug_enabled_var = tk.BooleanVar(value=self.global_settings.debug_enabled)
        ttk.Checkbutton(other_frame, text="デバッグ出力を有効にする（要再起動）", variable=debug_enabled_var).pack(anchor=tk.W, padx=10, pady=5)
        
        # トリガーワード設定タブ
        trigger_frame = ttk.Frame(settings_notebook)
        settings_notebook.add(trigger_frame, text="トリガーワード設定")
        
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
            manager_listbox.insert(tk.END, manager)
        
        manager_button_frame = ttk.Frame(manager_frame)
        manager_button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        def add_manager():
            manager = simpledialog.askstring("追加", "管理者名またはIDを入力:")
            if manager and manager not in self.global_settings.managers:
                self.global_settings.managers.append(manager)
                manager_listbox.insert(tk.END, manager)
                
        def remove_manager():
            selection = manager_listbox.curselection()
            if selection:
                index = selection[0]
                self.global_settings.managers.pop(index)
                manager_listbox.delete(index)
        
        ttk.Button(manager_button_frame, text="追加", command=add_manager).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(manager_button_frame, text="削除", command=remove_manager).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Label(manager_frame, text="※コメントから右クリックで管理者IDに追加することもできます", 
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
