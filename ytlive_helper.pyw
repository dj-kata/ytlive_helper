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

# 分割したモジュールをインポート
from gui_components import GUIComponents
from comment_handler import CommentHandler

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

def load_language(lang_code='ja'):
    """言語ファイルをロード
    
    Args:
        lang_code (str): 言語コード ('ja' or 'en')
        
    Returns:
        dict: UI文字列の辞書
    """
    try:
        if lang_code == 'ja':
            import lang_ja
            return lang_ja.STRINGS
        elif lang_code == 'en':
            import lang_en
            return lang_en.STRINGS
        else:
            # デフォルトは日本語
            import lang_ja
            return lang_ja.STRINGS
    except ImportError as e:
        logger.error(f"Failed to load language file: {e}")
        # フォールバック：最小限の辞書を返す
        return {
            "menu": {"file": "File", "settings": "Settings", "exit": "Exit", "language": "Language"},
            "messages": {"error": "Error"},
        }

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
        
        # 言語設定
        self.language = 'ja'  # デフォルトは日本語
        
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
        video_id = None
        
        # youtube.com/watch?v=VIDEOID 形式
        if 'youtube.com/watch' in url:
            query = urllib.parse.urlparse(url).query
            params = urllib.parse.parse_qs(query)
            video_id = params.get('v', [None])[0]
        # youtu.be/VIDEOID 形式
        elif 'youtu.be/' in url:
            video_id = url.split('/')[-1].split('?')[0]
        # youtube.com/live/VIDEOID 形式
        elif 'youtube.com/live/' in url:
            video_id = url.split('/live/')[-1].split('?')[0]
        
        return video_id
        
    def start(self):
        """pytchatを使ったコメント受信"""
        try:
            debug_print(f"DEBUG: YouTubeCommentReceiver.start() called")
            video_id = self.extract_video_id(self.settings.url)
            
            if not video_id:
                logger.error(f"Invalid YouTube URL: {self.settings.url}")
                debug_print(f"ERROR: Invalid YouTube URL: {self.settings.url}")
                return
                
            debug_print(f"DEBUG: Extracted video_id: {video_id}")
            debug_print(f"DEBUG: Creating pytchat.create with video_id: {video_id}")
            
            self.livechat = pytchat.create(video_id=video_id)
            debug_print(f"DEBUG: pytchat.create successful, livechat object created")
            debug_print(f"DEBUG: Starting comment loop")
            
            while not self.stop_event.is_set() and self.livechat.is_alive():
                try:
                    debug_print(f"DEBUG: Checking for new comments...")
                    for comment in self.livechat.get().sync_items():
                        debug_print(f"DEBUG: Received comment from {comment.author.name}: {comment.message}")
                        
                        # 管理者判定（新形式）
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

class MultiStreamCommentHelper(GUIComponents, CommentHandler):
    """メインアプリケーションクラス（多重継承でGUIとコメント処理機能を統合）"""
    def __init__(self):
        self.global_settings = GlobalSettings()
        self.global_settings.load()
        
        # 言語設定をロード
        self.strings = load_language(self.global_settings.language)
        
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
        
        # 終了処理の登録
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def restore_last_streams(self):
        """前回開いていた配信を復元"""
        if not self.global_settings.last_streams:
            return
        
        for url in self.global_settings.last_streams:
            platform = self.detect_platform(url)
            if platform:
                stream_id = f"{platform}_{int(time.time() * 1000)}"
                
                # タイトル取得
                title = self.get_stream_title(platform, url)
                
                stream_settings = StreamSettings(
                    stream_id=stream_id,
                    platform=platform,
                    url=url,
                    title=title
                )
                self.stream_manager.add_stream(stream_settings)
                self.add_stream_tab(stream_settings)
        
        self.update_stream_list()
    
    def detect_platform(self, url):
        """URLからプラットフォームを自動判定"""
        if 'youtube.com' in url or 'youtu.be' in url:
            return 'youtube'
        elif 'twitch.tv' in url:
            return 'twitch'
        return None
    
    def get_stream_title(self, platform, url):
        """配信タイトルを取得（スケルトン関数 - 実装が必要）
        
        TODO: Implement using YouTube Data API / Twitch API
        
        Args:
            platform (str): 'youtube' or 'twitch'
            url (str): 配信URL
            
        Returns:
            str: 配信タイトル（取得できない場合は空文字列）
        """
        # 実装例（APIキーが必要）:
        # if platform == 'youtube':
        #     video_id = extract_video_id(url)
        #     # YouTube Data API v3を使用してタイトル取得
        #     return get_youtube_title(video_id)
        # elif platform == 'twitch':
        #     channel_name = extract_channel_name(url)
        #     # Twitch APIを使用してタイトル取得
        #     return get_twitch_title(channel_name)
        
        return ""  # 現在は空文字列を返す
    
    def update_stream_title(self, stream_id):
        """指定された配信のタイトルを更新（オプション）
        
        Args:
            stream_id (str): 配信ID
        """
        if stream_id not in self.stream_manager.streams:
            return
        
        settings = self.stream_manager.streams[stream_id]
        new_title = self.get_stream_title(settings.platform, settings.url)
        
        if new_title:
            settings.title = new_title
            
            # タイトルラベルが存在すれば更新
            if hasattr(settings, 'title_label'):
                settings.title_label.config(text=new_title)
            
            # リストを更新
            self.update_stream_list()
    
    def setup_obs(self):
        """OBS接続設定"""
        try:
            if self.obs:
                try:
                    self.obs.disconnect()
                except:
                    pass
            
            self.obs = OBSSocket(
                host=self.global_settings.obs_host,
                port=self.global_settings.obs_port,
                password=self.global_settings.obs_passwd
            )
            logger.info(f"OBS connected: {self.global_settings.obs_host}:{self.global_settings.obs_port}")
        except Exception as e:
            logger.warning(f"OBS connection failed: {e}")
            self.obs = None
    
    def add_stream(self):
        """配信を追加"""
        url = self.url_entry.get().strip()
        
        if not url:
            messagebox.showerror(self.strings["messages"]["error"], self.strings["messages"]["url_required"])
            return
            
        # URLからプラットフォームを自動判定
        platform = self.detect_platform(url)
        if not platform:
            messagebox.showerror(self.strings["messages"]["error"], self.strings["messages"]["unsupported_url"])
            return
        
        # ユニークなIDを生成
        stream_id = f"{platform}_{int(time.time() * 1000)}"
        
        # タイトルを取得
        title = self.get_stream_title(platform, url)
        
        # StreamSettingsを作成
        stream_settings = StreamSettings(
            stream_id=stream_id,
            platform=platform,
            url=url,
            title=title
        )
        
        # StreamManagerに追加
        self.stream_manager.add_stream(stream_settings)
        
        # タブを追加
        self.add_stream_tab(stream_settings)
        
        # リストを更新
        self.update_stream_list()
        
        # 入力をクリア
        self.url_entry.delete(0, tk.END)
        
        logger.info(f"Stream added: {stream_id} ({platform})")
    
    def start_selected_stream(self):
        """選択された配信を開始"""
        selection = self.stream_tree.selection()
        if not selection:
            messagebox.showwarning(self.strings["messages"]["warning"], self.strings["messages"]["select_stream"])
            return
            
        item = self.stream_tree.item(selection[0])
        stream_id = item['values'][0]
        
        # コメント受信開始
        def comment_callback(comment_data):
            """コメント受信時のコールバック"""
            comment_data['stream_id'] = stream_id
            self.process_comment(stream_id, comment_data)
        
        success = self.stream_manager.start_stream(stream_id, comment_callback)
        
        if success:
            # UI更新
            self.update_stream_list()
            settings = self.stream_manager.streams[stream_id]
            if hasattr(settings, 'status_label'):
                settings.status_label.config(
                    text=self.strings["stream_info"]["status_running"], 
                    foreground="green"
                )
        else:
            messagebox.showerror(
                self.strings["messages"]["error"], 
                self.strings["messages"]["start_failed"].format(stream_id=stream_id)
            )
    
    def stop_selected_stream(self):
        """選択された配信を停止"""
        selection = self.stream_tree.selection()
        if not selection:
            messagebox.showwarning(self.strings["messages"]["warning"], self.strings["messages"]["select_stream"])
            return
            
        item = self.stream_tree.item(selection[0])
        stream_id = item['values'][0]
        
        # コメント受信停止
        self.stream_manager.stop_stream(stream_id)
        
        # UI更新
        self.update_stream_list()
        settings = self.stream_manager.streams.get(stream_id)
        if settings and hasattr(settings, 'status_label'):
            settings.status_label.config(
                text=self.strings["stream_info"]["status_stopped"], 
                foreground="red"
            )
    
    def remove_selected_stream(self):
        """選択された配信を削除"""
        selection = self.stream_tree.selection()
        if not selection:
            messagebox.showwarning(self.strings["messages"]["warning"], self.strings["messages"]["select_stream"])
            return
            
        item = self.stream_tree.item(selection[0])
        stream_id = item['values'][0]
        
        if messagebox.askyesno(
            self.strings["messages"]["confirm"], 
            self.strings["messages"]["delete_stream_confirm"].format(stream_id=stream_id)
        ):
            # StreamManagerから削除
            self.stream_manager.remove_stream(stream_id)
            
            # タブを削除（notebook内の対応するタブを探して削除）
            for i in range(self.notebook.index("end")):
                tab_text = self.notebook.tab(i, "text")
                if stream_id in tab_text:
                    self.notebook.forget(i)
                    break
            
            # リストを更新
            self.update_stream_list()
            
            logger.info(f"Stream removed: {stream_id}")
                    
    def configure_selected_stream(self):
        """選択された配信の設定"""
        selection = self.stream_tree.selection()
        if not selection:
            messagebox.showwarning(self.strings["messages"]["warning"], self.strings["messages"]["select_stream"])
            return
            
        item = self.stream_tree.item(selection[0])
        stream_id = item['values'][0]
        
        # 設定ダイアログを開く
        self.show_stream_settings(stream_id)
    
    def add_manual_request(self):
        """手動でリクエストを追加"""
        content = self.manual_req_entry.get().strip()
        if content:
            # 辞書形式でリクエストを追加
            request_data = {
                'content': content,
                'author': '手動追加',
                'platform': 'manual',
                'stream_id': ''
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
            # 番号（1ベース）からインデックス（0ベース）に変換
            index = item['values'][0] - 1
            if 0 <= index < len(self.common_requests):
                self.common_requests.pop(index)
                self.update_request_display()
                self.generate_xml()
    
    def move_request_up(self):
        """選択されたリクエストを上に移動"""
        selection = self.request_tree.selection()
        if selection:
            item = self.request_tree.item(selection[0])
            # 番号（1ベース）からインデックス（0ベース）に変換
            index = item['values'][0] - 1
            if index > 0:
                self.common_requests[index], self.common_requests[index-1] = \
                    self.common_requests[index-1], self.common_requests[index]
                self.update_request_display()
                self.generate_xml()
                # 選択を維持（移動後の位置）
                new_index = index - 1
                if new_index < len(self.request_tree.get_children()):
                    self.request_tree.selection_set(self.request_tree.get_children()[new_index])
    
    def move_request_down(self):
        """選択されたリクエストを下に移動"""
        selection = self.request_tree.selection()
        if selection:
            item = self.request_tree.item(selection[0])
            # 番号（1ベース）からインデックス（0ベース）に変換
            index = item['values'][0] - 1
            if index < len(self.common_requests) - 1:
                self.common_requests[index], self.common_requests[index+1] = \
                    self.common_requests[index+1], self.common_requests[index]
                self.update_request_display()
                self.generate_xml()
                # 選択を維持（移動後の位置）
                new_index = index + 1
                if new_index < len(self.request_tree.get_children()):
                    self.request_tree.selection_set(self.request_tree.get_children()[new_index])
    
    def clear_all_requests(self):
        """全リクエストをクリア"""
        if messagebox.askyesno(
            self.strings["messages"]["confirm"], 
            self.strings["messages"]["clear_requests_confirm"]
        ):
            self.common_requests.clear()
            self.update_request_display()
            self.generate_xml()
            
    def clear_all_comments(self):
        """全コメントをクリア"""
        if messagebox.askyesno(
            self.strings["messages"]["confirm"], 
            self.strings["messages"]["clear_comments_confirm"]
        ):
            # Treeviewをクリア
            for item in self.comment_tree.get_children():
                self.comment_tree.delete(item)
            
            # 各ストリームのコメントリストもクリア
            for stream_id, settings in self.stream_manager.streams.items():
                settings.comments.clear()
                if hasattr(settings, 'comment_count_label'):
                    settings.comment_count_label.config(text="0")
    
    def generate_xml(self):
        """リクエストリストからXMLを生成してOBSに送信"""
        if not self.obs:
            return
        
        # XMLテキストを生成
        xml_content = self.global_settings.content_header + "\n"
        for i, req in enumerate(self.common_requests, start=1):
            # 辞書形式からテキストを生成
            content = req['content']
            author = req.get('author', '')
            platform = req.get('platform', '')
            
            # 表示形式: "内容 (ユーザーさん) [platform]"
            if author and platform and platform != 'manual':
                formatted_text = f"{content} ({author}さん) [{platform}]"
            else:
                formatted_text = content
            
            line = self.global_settings.series_query.replace('[number]', str(i))
            line += f" {self.escape_for_xml(formatted_text)}"
            xml_content += line + "\n"
        
        # OBSに送信
        try:
            self.obs.set_text_gdi_plus_properties('リクエストリスト', text=xml_content)
        except Exception as e:
            logger.error(f"Failed to update OBS: {e}")
    
    def escape_for_xml(self, text):
        """XMLエスケープ処理"""
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        text = text.replace('"', '&quot;')
        text = text.replace("'", '&apos;')
        return text
    
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
    
    def change_language(self, lang_code):
        """言語を変更
        
        Args:
            lang_code (str): 言語コード ('ja' or 'en')
        """
        if lang_code != self.global_settings.language:
            self.global_settings.language = lang_code
            self.global_settings.save()
            
            # 言語ファイルを再ロード
            self.strings = load_language(lang_code)
            
            # GUIを再構築
            self.rebuild_gui()
    
    def run(self):
        """アプリケーションを実行"""
        self.root.mainloop()

if __name__ == '__main__':
    app = MultiStreamCommentHelper()
    app.run()
