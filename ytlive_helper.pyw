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

# IPv4を強制する設定
from urllib3.util import connection

def allowed_gai_family():
    return socket.AF_INET

connection.allowed_gai_family = allowed_gai_family

# コメント取得ライブラリ
import pytchat  # YouTube用

from obssocket import OBSSocket

# 分割したモジュールをインポート
from gui_components import GUIComponents
from comment_handler import CommentHandler
from update import GitHubUpdater

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
    file_handler = logging.FileHandler('./log/dbg.log', encoding='utf-8')
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
os.makedirs('log', exist_ok=True)
DEBUG_ENABLED = setup_logging()
logger = logging.getLogger(__name__)

try:
    with open('version.txt', 'r') as f:
        tmp = f.readline()
        print(tmp)
        SWVER = tmp.strip()[2:] if tmp.startswith('v') else tmp.strip()
except Exception:
    logger.debug(traceback.format_exc())
    SWVER = "0.0.0"

def debug_print(*args, **kwargs):
    """デバッグ設定が有効な時のみprint出力"""
    if DEBUG_ENABLED:
        print(*args, **kwargs)

def extract_title_info(title, pattern_series, pattern_base_title_list):
    """タイトルからbase_titleとseriesを抽出
    
    Args:
        title (str): 元のタイトル
        pattern_series (str): シリーズ番号のパターン（例: '#[number]', '第[number]回'）
        pattern_base_title_list (list): 削除するパターンのリスト（例: ['【】', '[]']）
        
    Returns:
        tuple: (base_title, series)
        
    Examples:
        >>> extract_title_info('【あけおめ】皆伝たぬきのINFINITAS配信 #290', '#[number]', ['【】'])
        ('皆伝たぬきのINFINITAS配信', '#290')
        
        >>> extract_title_info('第10回 SOUND VOLTEX 配信', '第[number]回', [])
        ('SOUND VOLTEX 配信', '第10回')
    """
    import re
    
    base_title = title
    series = None
    
    # 1. シリーズ番号を抽出
    if pattern_series:
        # [number]を(\d+)に変換して正規表現パターンを作成
        regex_pattern = pattern_series.replace('[number]', r'(\d+)')
        match = re.search(regex_pattern, title)
        if match:
            series = match.group(0)  # マッチした全体（例: '#290', '第10回'）
            # base_titleからシリーズ番号を削除
            base_title = title.replace(series, '').strip()
    
    # 2. base_titleから指定パターンを削除
    if pattern_base_title_list:
        for pattern in pattern_base_title_list:
            if pattern == '【】':
                # 【...】形式を削除
                base_title = re.sub(r'【[^】]*】', '', base_title)
            elif pattern == '[]':
                # [...] 形式を削除
                base_title = re.sub(r'\[[^\]]*\]', '', base_title)
            elif pattern == '()':
                # (...) 形式を削除
                base_title = re.sub(r'\([^)]*\)', '', base_title)
            elif pattern == '「」':
                # 「...」形式を削除
                base_title = re.sub(r'「[^」]*」', '', base_title)
            else:
                # その他のパターンはそのまま削除
                base_title = base_title.replace(pattern, '')
    
    # 3. 余分な空白を削除
    base_title = ' '.join(base_title.split())
    
    return base_title, series

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
        
        # タイトル抽出設定
        self.pattern_series = '#[number]'  # シリーズ番号抽出パターン
        self.pattern_base_title_list = ['【】', '[]']  # base_titleから削除するパターンのリスト
        
        # 告知テンプレート設定
        self.announcement_template = '配信開始しました！'  # 基本の告知文のテンプレート
        
        # 配信内容取得設定
        self.content_marker = '今日の内容:'  # 概要欄から配信内容を取得する際のマーカー文字列
        
        # 告知設定
        self.announcement_template = '配信開始しました！'  # 基本の告知文テンプレート
        
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

class TwitchAPI:
    """Twitch API クライアント（タイトル取得用）"""
    
    def __init__(self):
        """初期化"""
        self.access_token = None
        self.client_id = None
        self.client_secret = None
        
        # config_secret.py から認証情報を読み込む
        try:
            import config_secret
            self.client_id, self.client_secret = config_secret.get_twitch_credentials()
            logger.info("Twitch API credentials loaded from config_secret.py")
        except ImportError:
            logger.warning("config_secret.py not found - Twitch API title fetching disabled")
        except Exception as e:
            logger.warning(f"Failed to load Twitch API credentials: {e}")
    
    def get_access_token(self):
        """OAuth 2.0 Client Credentials Flow でアクセストークンを取得"""
        if not self.client_id or not self.client_secret:
            return None
        
        url = "https://id.twitch.tv/oauth2/token"
        
        params = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials"
        }
        
        try:
            response = requests.post(url, params=params, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            self.access_token = data["access_token"]
            
            logger.info("Twitch API access token obtained")
            return self.access_token
            
        except Exception as e:
            logger.warning(f"Failed to get Twitch access token: {e}")
            return None
    
    def get_user_id(self, username):
        """ユーザー名からユーザーIDを取得"""
        if not self.access_token:
            if not self.get_access_token():
                return None
        
        url = "https://api.twitch.tv/helix/users"
        
        headers = {
            "Client-ID": self.client_id,
            "Authorization": f"Bearer {self.access_token}"
        }
        
        params = {
            "login": username
        }
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            
            if data["data"]:
                user_id = data["data"][0]["id"]
                logger.debug(f"Twitch user ID obtained: {username} -> {user_id}")
                return user_id
            else:
                logger.warning(f"Twitch user not found: {username}")
                return None
                
        except Exception as e:
            logger.warning(f"Failed to get Twitch user ID: {e}")
            return None
    
    def get_stream_title(self, user_id):
        """ユーザーIDから配信タイトルを取得"""
        if not self.access_token:
            if not self.get_access_token():
                return None
        
        url = "https://api.twitch.tv/helix/streams"
        
        headers = {
            "Client-ID": self.client_id,
            "Authorization": f"Bearer {self.access_token}"
        }
        
        params = {
            "user_id": user_id
        }
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            
            if data["data"]:
                stream = data["data"][0]
                title = stream["title"]
                logger.info(f"Twitch stream title obtained: {title}")
                return title
            else:
                logger.warning("Twitch stream is not live")
                return None
                
        except Exception as e:
            logger.warning(f"Failed to get Twitch stream title: {e}")
            return None
    
    def get_title_from_url(self, url):
        """Twitch URLから配信タイトルを取得
        
        Args:
            url (str): Twitch配信URL
            
        Returns:
            str: 配信タイトル、取得失敗時はNone
        """
        # URLからユーザー名を抽出
        username = self.extract_username_from_url(url)
        if not username:
            logger.warning(f"Failed to extract username from URL: {url}")
            return None
        
        # ユーザーIDを取得
        user_id = self.get_user_id(username)
        if not user_id:
            return None
        
        # タイトルを取得
        return self.get_stream_title(user_id)
    
    @staticmethod
    def extract_username_from_url(url):
        """Twitch URLからユーザー名を抽出"""
        url = url.strip()
        
        # プロトコルを削除
        if url.startswith('https://'):
            url = url[8:]
        elif url.startswith('http://'):
            url = url[7:]
        
        # www. を削除
        if url.startswith('www.'):
            url = url[4:]
        
        # twitch.tv/ で始まるか確認
        if url.startswith('twitch.tv/'):
            username = url[10:].split('/')[0].split('?')[0]
            return username
        
        return None
    
    def get_channel_description(self, username):
        """チャンネルの説明（About）を取得
        
        Args:
            username (str): Twitchユーザー名
            
        Returns:
            str: チャンネル説明、取得失敗時は空文字列
        """
        if not self.access_token:
            if not self.get_access_token():
                return ""
        
        url = "https://api.twitch.tv/helix/users"
        
        headers = {
            "Client-ID": self.client_id,
            "Authorization": f"Bearer {self.access_token}"
        }
        
        params = {
            "login": username
        }
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            
            if data["data"]:
                user = data["data"][0]
                description = user.get("description", "")
                logger.info(f"Twitch channel description obtained for {username}")
                return description
            else:
                logger.warning(f"Twitch user not found: {username}")
                return ""
                
        except Exception as e:
            logger.warning(f"Failed to get Twitch channel description: {e}")
            return ""

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
    """YouTubeコメント受信クラス（pytchat使用）"""
    def __init__(self, settings, callback, global_settings):
        super().__init__(settings)
        self.callback = callback
        self.global_settings = global_settings
        self.livechat = None
        
    def extract_video_id(self, url):
        """URLからビデオIDを抽出"""
        video_id = None
        
        # studio.youtube.com/video/VIDEOID/livestreaming 形式（YouTube Studio）
        if 'studio.youtube.com/video/' in url:
            # /video/VIDEOID/ の部分を抽出
            parts = url.split('/video/')
            if len(parts) > 1:
                video_id = parts[1].split('/')[0].split('?')[0]
        # youtube.com/watch?v=VIDEOID 形式
        elif 'youtube.com/watch' in url:
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
            debug_print(f"DEBUG: Thread ID: {threading.current_thread().ident}")
            video_id = self.extract_video_id(self.settings.url)
            
            if not video_id:
                logger.error(f"Invalid YouTube URL: {self.settings.url}")
                debug_print(f"ERROR: Invalid YouTube URL: {self.settings.url}")
                return
                
            debug_print(f"DEBUG: Extracted video_id: {video_id}")
            debug_print(f"DEBUG: Creating pytchat.create with video_id: {video_id}")
            
            # interruptable=Falseでシグナルハンドラを無効化（スレッドで動作可能に）
            # 
            # 高速化のために内部ポーリング間隔を短縮（monkey patch）
            try:
                import pytchat.core.livechat as ptc_livechat
                # pytchatのデフォルトポーリング間隔を短縮
                # 注意: 内部実装に依存するため、バージョンによっては動作しない可能性
                if hasattr(ptc_livechat, '_POLLING_INTERVAL'):
                    original_interval = ptc_livechat._POLLING_INTERVAL
                    ptc_livechat._POLLING_INTERVAL = 1.0  # 1秒に短縮
                    debug_print(f"DEBUG: Changed pytchat polling interval from {original_interval} to 1.0")
            except Exception as patch_error:
                debug_print(f"DEBUG: Could not patch pytchat polling interval: {patch_error}")
            
            self.livechat = pytchat.create(video_id=video_id, interruptable=False)
            
            # livechatオブジェクト作成後にもポーリング間隔を設定
            try:
                if hasattr(self.livechat, 'processor'):
                    processor = self.livechat.processor
                    if hasattr(processor, 'continuation'):
                        continuation = processor.continuation
                        # continuation内部のポーリング間隔を短縮
                        if hasattr(continuation, 'fetch_interval'):
                            original = getattr(continuation, 'fetch_interval', None)
                            continuation.fetch_interval = 1.0
                            debug_print(f"DEBUG: Set livechat fetch_interval to 1.0 (was: {original})")
            except Exception as patch_error:
                debug_print(f"DEBUG: Could not patch livechat fetch_interval: {patch_error}")
            
            debug_print(f"DEBUG: pytchat.create successful, livechat object created")
            debug_print(f"DEBUG: Starting comment loop")
            
            message_count = 0
            get_call_count = 0
            
            while not self.stop_event.is_set() and self.livechat.is_alive():
                try:
                    get_call_count += 1
                    if get_call_count % 100 == 0:
                        import datetime
                        timestamp_str = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
                        debug_print(f"DEBUG: [{timestamp_str}] YouTube: get() called {get_call_count} times")
                    
                    # pytchatのget()を呼び出し
                    for comment in self.livechat.get().sync_items():
                        if self.stop_event.is_set():
                            break
                        
                        message_count += 1
                        if message_count % 10 == 0:
                            import datetime
                            timestamp_str = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
                            debug_print(f"DEBUG: [{timestamp_str}] YouTube thread: Received {message_count} comments")
                        
                        # コメントの実際の投稿時刻をログに記録
                        if message_count % 10 == 1:  # 最初のコメントと10件ごと
                            import datetime
                            now_str = datetime.datetime.now().strftime("%H:%M:%S")
                            comment_time_str = comment.datetime
                            debug_print(f"DEBUG: YouTube comment - Posted: {comment_time_str}, Received: {now_str}")
                        
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
                        
                        # GUIコールバック（メインループが終了している場合はスキップ）
                        try:
                            if not self.stop_event.is_set():
                                self.callback(comment_data)
                        except Exception as callback_error:
                            # メインループ終了時のエラーを無視
                            if "main thread is not in main loop" in str(callback_error):
                                logger.debug("Main loop already terminated, stopping receiver")
                                break
                            else:
                                logger.error(f"Error in callback: {callback_error}")
                        
                except Exception as inner_e:
                    debug_print(f"DEBUG: Error in YouTube chat loop: {inner_e}")
                    logger.error(f"Error in YouTube chat loop: {inner_e}")
                    
                # 最小限の待機（0.01秒）でget()を頻繁に呼び出す
                if self.stop_event.is_set():
                    break
                time.sleep(0.01)
                
        except KeyboardInterrupt:
            debug_print(f"DEBUG: KeyboardInterrupt detected in YouTube receiver")
            logger.info(f"YouTube receiver interrupted by KeyboardInterrupt")
        except SystemExit as e:
            debug_print(f"DEBUG: SystemExit detected in YouTube receiver: {e}")
            logger.warning(f"YouTube receiver received SystemExit: {e}")
        except Exception as e:
            logger.error(f"YouTube comment receiver error: {e}")
            debug_print(f"ERROR: YouTube comment receiver error: {e}")
            import traceback
            debug_print(f"ERROR: Traceback: {traceback.format_exc()}")
            logger.error(f"Traceback: {traceback.format_exc()}")
        finally:
            if self.livechat:
                self.livechat.terminate()
                debug_print(f"DEBUG: pytchat terminated")


class TwitchCommentReceiver(CommentReceiver):
    """Twitchコメント受信クラス（標準ライブラリのsocketでIRC接続）"""
    def __init__(self, settings, callback, global_settings):
        super().__init__(settings)
        self.callback = callback
        self.global_settings = global_settings
        self.irc_socket = None
        self.channel_name = None
        
    def extract_channel_name(self, url):
        """TwitchのURLからチャンネル名を抽出"""
        # https://www.twitch.tv/channel_name -> channel_name
        import re
        match = re.search(r'twitch\.tv/([^/\?]+)', url)
        if match:
            return match.group(1).lower()  # チャンネル名は小文字
        return None
        
    def start(self):
        """socketを使ったTwitch IRC接続でコメント受信"""
        try:
            debug_print(f"DEBUG: TwitchCommentReceiver.start() called")
            debug_print(f"DEBUG: Thread ID: {threading.current_thread().ident}")
            debug_print(f"DEBUG: URL: {self.settings.url}")
            
            # URLからチャンネル名を抽出
            self.channel_name = self.extract_channel_name(self.settings.url)
            if not self.channel_name:
                logger.error(f"Failed to extract channel name from URL: {self.settings.url}")
                return
            
            debug_print(f"DEBUG: Extracted channel name: {self.channel_name}")
            
            # Twitch IRC設定
            server = 'irc.chat.twitch.tv'
            port = 6667
            nickname = 'justinfan12345'  # 匿名接続用のニックネーム（justinfan + 数字）
            
            # IRCソケット作成
            self.irc_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.irc_socket.settimeout(1.0)  # 1秒のタイムアウト（頻繁にGILを解放）
            
            debug_print(f"DEBUG: Connecting to Twitch IRC: {server}:{port}")
            self.irc_socket.connect((server, port))
            
            # IRC接続
            self.irc_socket.send(f"NICK {nickname}\r\n".encode('utf-8'))
            self.irc_socket.send(f"JOIN #{self.channel_name}\r\n".encode('utf-8'))
            
            # タグを有効化（ユーザー情報を取得するため）
            self.irc_socket.send(b"CAP REQ :twitch.tv/tags\r\n")
            self.irc_socket.send(b"CAP REQ :twitch.tv/commands\r\n")
            
            debug_print(f"DEBUG: Connected to Twitch IRC, joined channel: {self.channel_name}")
            
            message_count = 0
            buffer = ""
            
            # メッセージ受信ループ
            while not self.stop_event.is_set():
                try:
                    # データ受信（1秒でタイムアウト）
                    response = self.irc_socket.recv(2048).decode('utf-8', errors='ignore')
                    
                    if not response:
                        debug_print("DEBUG: Connection closed by server")
                        break
                    
                    # 停止チェック
                    if self.stop_event.is_set():
                        debug_print("DEBUG: Stop event detected during receive")
                        break
                    
                    buffer += response
                    lines = buffer.split('\r\n')
                    buffer = lines.pop()  # 最後の不完全な行は次回へ
                    
                    for line in lines:
                        if not line:
                            continue
                        
                        # PINGに応答
                        if line.startswith('PING'):
                            self.irc_socket.send(b"PONG :tmi.twitch.tv\r\n")
                            continue
                        
                        # PRIVMSGメッセージを解析
                        if 'PRIVMSG' in line:
                            message_count += 1
                            
                            if message_count % 10 == 0:
                                import datetime
                                timestamp_str = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
                                debug_print(f"DEBUG: [{timestamp_str}] Twitch thread: Received {message_count} messages")
                            
                            # 最初とN件ごとに受信時刻を記録
                            if message_count % 10 == 1:
                                import datetime
                                now_str = datetime.datetime.now().strftime("%H:%M:%S")
                                debug_print(f"DEBUG: Twitch message received at: {now_str}")
                            
                            # メッセージをパース
                            author_name = None
                            message_text = None
                            is_moderator = False
                            
                            # タグからユーザー情報を抽出
                            if line.startswith('@'):
                                tags_part, rest = line.split(' :', 1)
                                tags = {}
                                for tag in tags_part[1:].split(';'):
                                    if '=' in tag:
                                        key, value = tag.split('=', 1)
                                        tags[key] = value
                                
                                # display-nameまたはloginからユーザー名を取得
                                author_name = tags.get('display-name') or tags.get('login')
                                
                                # モデレーター判定
                                badges = tags.get('badges', '')
                                if 'moderator/' in badges or 'broadcaster/' in badges:
                                    is_moderator = True
                            
                            # ユーザー名が取得できなかった場合は通常のIRC形式から抽出
                            if not author_name:
                                if '!' in line:
                                    author_name = line.split('!')[0].lstrip(':@')
                            
                            # メッセージテキストを抽出
                            if f'PRIVMSG #{self.channel_name} :' in line:
                                message_text = line.split(f'PRIVMSG #{self.channel_name} :', 1)[1]
                            
                            if not author_name or not message_text:
                                continue
                            
                            # global_settingsの管理者リストでチェック
                            for manager in self.global_settings.managers:
                                if manager['platform'] == 'twitch' and manager['id'].lower() == author_name.lower():
                                    is_moderator = True
                                    break
                            
                            # 統一フォーマットでコールバック
                            comment_data = {
                                'platform': 'twitch',
                                'author': author_name,
                                'message': message_text,
                                'timestamp': '',
                                'author_id': author_name.lower(),
                                'is_moderator': is_moderator
                            }
                            
                            # GUIコールバック
                            try:
                                if not self.stop_event.is_set():
                                    self.callback(comment_data)
                            except Exception as callback_error:
                                if "main thread is not in main loop" in str(callback_error):
                                    logger.debug("Main loop already terminated, stopping receiver")
                                    break
                                else:
                                    logger.error(f"Error in callback: {callback_error}")
                    
                except socket.timeout:
                    # タイムアウトは正常（PING/PONGで接続維持）
                    continue
                except Exception as e:
                    debug_print(f"DEBUG: Error receiving IRC message: {e}")
                    logger.error(f"Error receiving message: {e}")
                    break
            
            debug_print(f"DEBUG: Twitch IRC loop ended, total messages: {message_count}")
                    
        except KeyboardInterrupt:
            debug_print(f"DEBUG: KeyboardInterrupt detected in Twitch receiver")
            logger.info(f"Twitch receiver interrupted by KeyboardInterrupt")
        except SystemExit as e:
            debug_print(f"DEBUG: SystemExit detected in Twitch receiver: {e}")
            logger.warning(f"Twitch receiver received SystemExit: {e}")
        except Exception as e:
            logger.error(f"Twitch comment receiver error: {e}")
            debug_print(f"ERROR: Twitch receiver error: {e}")
            import traceback
            debug_print(f"ERROR: Traceback: {traceback.format_exc()}")
            logger.error(f"Traceback: {traceback.format_exc()}")
        finally:
            if self.irc_socket:
                try:
                    self.irc_socket.close()
                except:
                    pass
            debug_print(f"DEBUG: Twitch receiver cleanup")


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
        
        # プラットフォームごとに適切なReceiverを選択
        if settings.platform == 'youtube':
            debug_print(f"DEBUG: Creating YouTubeCommentReceiver (pytchat)")
            receiver = YouTubeCommentReceiver(settings, comment_callback, self.global_settings)
        elif settings.platform == 'twitch':
            debug_print(f"DEBUG: Creating TwitchCommentReceiver (socket IRC)")
            receiver = TwitchCommentReceiver(settings, comment_callback, self.global_settings)
        else:
            logger.error(f"Unknown platform: {settings.platform}")
            debug_print(f"ERROR: Unknown platform: {settings.platform}")
            return False
            
        debug_print(f"DEBUG: Created receiver, starting thread")
        self.receivers[stream_id] = receiver
        
        # スレッドラッパー関数で例外をキャッチ
        def thread_wrapper():
            try:
                logger.info(f"Comment receiver thread started for {stream_id}")
                receiver.start()
                logger.info(f"Comment receiver thread ended normally for {stream_id}")
            except Exception as e:
                logger.error(f"Comment receiver thread crashed for {stream_id}: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                # スレッドが異常終了してもメインアプリケーションは継続
        
        thread = threading.Thread(target=thread_wrapper, daemon=True)
        self.threads[stream_id] = thread
        thread.start()
        settings.is_active = True
        debug_print(f"DEBUG: Thread started for {stream_id}")
        return True
        
    def stop_stream(self, stream_id):
        """配信のコメント受信を停止"""
        if stream_id in self.receivers:
            debug_print(f"DEBUG: Stopping receiver for {stream_id}")
            self.receivers[stream_id].stop()
            
        if stream_id in self.threads:
            thread = self.threads[stream_id]
            # スレッドが終了するまで最大3秒待機
            debug_print(f"DEBUG: Waiting for thread to stop for {stream_id}")
            thread.join(timeout=3)
            if thread.is_alive():
                debug_print(f"WARNING: Thread for {stream_id} did not stop cleanly")
            else:
                debug_print(f"DEBUG: Thread stopped successfully for {stream_id}")
            del self.threads[stream_id]
            
        if stream_id in self.receivers:
            del self.receivers[stream_id]
            
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
        
        # プラットフォームごとのIDカウンター
        self.stream_id_counters = {
            'youtube': 0,
            'twitch': 0
        }
        
        # GUI初期化
        self.root = tk.Tk()
        self.root.title("Multi-Stream Comment Helper")
        
        # アプリケーションアイコンを設定
        self.setup_icon()
        
        self.root.geometry("1000x850")
        if self.global_settings.keep_on_top:
            self.root.attributes('-topmost', True)
            
        self.setup_gui()
        
        # GUIセットアップ後にリクエストリストをロード
        self.load_requests()
        
        self.setup_obs()
        self.restore_last_streams()
        
        # 終了処理の登録
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def restore_last_streams(self):
        """前回開いていた配信を復元"""
        if not self.global_settings.last_streams:
            return
        
        stream_ids = []  # 追加したstream_idを記録
        
        for url in self.global_settings.last_streams:
            platform = self.detect_platform(url)
            if platform:
                # YouTube URLの場合は通常形式に正規化
                if platform == 'youtube':
                    url = self.normalize_youtube_url(url)
                
                # プラットフォームごとの連番IDを生成
                stream_id = f"{platform}_{self.stream_id_counters[platform]}"
                self.stream_id_counters[platform] += 1
                
                # 空のタイトルで即座に追加
                stream_settings = StreamSettings(
                    stream_id=stream_id,
                    platform=platform,
                    url=url,
                    title=""  # 空のタイトルで先に追加
                )
                self.stream_manager.add_stream(stream_settings)
                self.add_stream_tab(stream_settings)
                stream_ids.append(stream_id)
        
        self.update_stream_list()
        
        # バックグラウンドで全てのタイトルを取得
        for stream_id in stream_ids:
            self.fetch_title_async(stream_id)
    
    def detect_platform(self, url):
        """URLからプラットフォームを自動判定"""
        if 'youtube.com' in url or 'youtu.be' in url:
            return 'youtube'
        elif 'twitch.tv' in url:
            return 'twitch'
        return None
    
    def normalize_youtube_url(self, url):
        """YouTube URLを通常の視聴URL形式に正規化
        
        YouTube Studio URL → 通常の視聴URL に変換
        例: https://studio.youtube.com/video/VIDEO_ID/livestreaming
            → https://www.youtube.com/watch?v=VIDEO_ID
        
        Args:
            url (str): YouTube URL（任意の形式）
            
        Returns:
            str: 正規化されたURL（通常の視聴URL形式）
        """
        # YouTube Studio URLの場合
        if 'studio.youtube.com/video/' in url:
            # video_idを抽出
            parts = url.split('/video/')
            if len(parts) > 1:
                video_id = parts[1].split('/')[0].split('?')[0]
                # 通常の視聴URL形式に変換
                return f'https://www.youtube.com/watch?v={video_id}'
        
        # youtu.be 短縮URL の場合
        elif 'youtu.be/' in url:
            video_id = url.split('/')[-1].split('?')[0]
            return f'https://www.youtube.com/watch?v={video_id}'
        
        # youtube.com/live/ の場合
        elif 'youtube.com/live/' in url:
            video_id = url.split('/live/')[-1].split('?')[0]
            return f'https://www.youtube.com/watch?v={video_id}'
        
        # 既に通常形式（youtube.com/watch?v=）の場合はそのまま返す
        return url
    
    def get_stream_title(self, platform, url):
        """配信タイトルを取得
        
        Twitchの場合: Twitch API -> BeautifulSoupフォールバック
        YouTubeの場合: BeautifulSoupでスクレイピング
        
        Args:
            platform (str): 'youtube' or 'twitch'
            url (str): 配信URL
            
        Returns:
            str: 配信タイトル（取得できない場合は空文字列）
        """
        # Twitchの場合、まずAPIを試す
        if platform == 'twitch':
            try:
                # TwitchAPIインスタンスを作成（キャッシュ）
                if not hasattr(self, 'twitch_api'):
                    self.twitch_api = TwitchAPI()
                
                # APIでタイトルを取得
                if self.twitch_api.client_id and self.twitch_api.client_secret:
                    title = self.twitch_api.get_title_from_url(url)
                    if title:
                        logger.info(f"Twitch title obtained via API: {title}")
                        return title
                    else:
                        logger.info("Twitch API returned no title, falling back to scraping")
                else:
                    logger.info("Twitch API credentials not configured, using scraping")
            except Exception as e:
                logger.warning(f"Twitch API failed: {e}, falling back to scraping")
        
        # BeautifulSoupでスクレイピング（YouTubeまたはTwitch APIのフォールバック）
        try:
            # User-Agentヘッダーを設定（ブロック回避）
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            # タイムアウト設定でページを取得（短縮: 3秒）
            response = requests.get(url, headers=headers, timeout=3)
            response.raise_for_status()
            
            # HTMLをパース
            soup = BeautifulSoup(response.text, 'html.parser')
            
            if platform == 'youtube':
                # YouTubeのタイトル取得
                # 方法1: og:titleメタタグから取得（最も確実）
                og_title = soup.find('meta', property='og:title')
                if og_title and og_title.get('content'):
                    return og_title['content']
                
                # 方法2: titleタグから取得（フォールバック）
                title_tag = soup.find('title')
                if title_tag:
                    title = title_tag.string
                    # YouTubeの場合、タイトルに " - YouTube" が付いているので削除
                    if title:
                        return title.replace(' - YouTube', '').strip()
                
            elif platform == 'twitch':
                # Twitchのタイトル取得（スクレイピング）
                # 方法1: og:titleメタタグから取得
                og_title = soup.find('meta', property='og:title')
                if og_title and og_title.get('content'):
                    return og_title['content']
                
                # 方法2: og:descriptionメタタグから取得（配信タイトルが入っている場合がある）
                og_description = soup.find('meta', property='og:description')
                if og_description and og_description.get('content'):
                    return og_description['content']
                
                # 方法3: titleタグから取得（フォールバック）
                title_tag = soup.find('title')
                if title_tag and title_tag.string:
                    return title_tag.string.strip()
            
            logger.warning(f"Could not extract title from {platform} URL: {url}")
            return ""
            
        except requests.Timeout:
            logger.warning(f"Timeout while fetching title from {url}")
            return ""
        except requests.RequestException as e:
            logger.warning(f"Error fetching title from {url}: {e}")
            return ""
        except Exception as e:
            logger.error(f"Unexpected error getting stream title: {e}")
            return ""
    
    def get_today_content(self, platform, url, content_marker):
        """配信の今日の内容を概要欄から取得
        
        BeautifulSoupでページ全体からマーカー文字列を検索し、
        その次の行を取得する
        
        Args:
            platform (str): 'youtube' or 'twitch'
            url (str): 配信URL
            content_marker (str): マーカー文字列（例: "今日の内容:"）
            
        Returns:
            str: 配信内容（取得できない場合は空文字列）
        """
        if not content_marker:
            return ""
        
        try:
            if platform == 'youtube':
                # User-Agentヘッダーを設定
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                
                # タイムアウト設定でページを取得
                response = requests.get(url, headers=headers, timeout=5)
                response.raise_for_status()
                
                # HTMLをパース
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # マーカー文字列を含むタグを検索
                target = None
                for tag in soup.find_all(True):
                    if content_marker in tag.text:
                        target = tag
                        break
                
                if not target:
                    logger.info(f"Marker '{content_marker}' not found in YouTube page")
                    return ""
                
                # タグのテキストを改行で分割してマーカーの次の行を取得
                lines = target.text.split('\\n')
                for i, line in enumerate(lines):
                    if content_marker in line:
                        # 次の行が存在するかチェック
                        if len(lines) >= i + 2:
                            today_content = lines[i + 1].strip()
                            if today_content:  # 空行でない場合
                                logger.info(f"Extracted today's content from YouTube: {today_content}")
                                return today_content
                
                logger.info(f"No content found after marker '{content_marker}' in YouTube")
                return ""
            
            elif platform == 'twitch':
                # TwitchAPIインスタンスを作成（キャッシュ）
                if not hasattr(self, 'twitch_api'):
                    self.twitch_api = TwitchAPI()
                
                # APIでチャンネル説明を取得
                if self.twitch_api.client_id and self.twitch_api.client_secret:
                    # URLからチャンネル名を抽出
                    username = TwitchAPI.extract_username_from_url(url)
                    if not username:
                        logger.warning(f"Could not extract username from Twitch URL: {url}")
                        return ""
                    
                    # チャンネル説明を取得
                    description = self.twitch_api.get_channel_description(username)
                    if not description:
                        logger.info("Twitch channel description is empty")
                        return ""
                    
                    # マーカーの次の行を抽出
                    lines = description.split('\\n')
                    for i, line in enumerate(lines):
                        if content_marker in line:
                            # 次の行が存在するかチェック
                            if len(lines) >= i + 2:
                                today_content = lines[i + 1].strip()
                                if today_content:  # 空行でない場合
                                    logger.info(f"Extracted today's content from Twitch: {today_content}")
                                    return today_content
                    
                    logger.info(f"Marker '{content_marker}' not found in Twitch channel description")
                    return ""
                else:
                    logger.info("Twitch API credentials not configured")
                    return ""
            
            return ""
            
        except requests.Timeout:
            logger.warning(f"Timeout while fetching content from {url}")
            return ""
        except requests.RequestException as e:
            logger.warning(f"Error fetching content from {url}: {e}")
            return ""
        except Exception as e:
            logger.error(f"Unexpected error getting today's content: {e}")
            return ""
    
    def update_stream_title(self, stream_id):
        """指定された配信のタイトルを更新
        
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
            
            logger.info(f"Title updated for {stream_id}: {new_title}")
        else:
            logger.warning(f"Failed to update title for {stream_id}")
    
    def fetch_title_async(self, stream_id):
        """バックグラウンドでタイトルを取得（非ブロッキング）
        
        Args:
            stream_id (str): 配信ID
        """
        def fetch_thread():
            """タイトル取得スレッド"""
            if stream_id not in self.stream_manager.streams:
                return
            
            settings = self.stream_manager.streams[stream_id]
            new_title = self.get_stream_title(settings.platform, settings.url)
            
            if new_title:
                # メインスレッドでGUI更新
                self.root.after(0, lambda: self._update_title_callback(stream_id, new_title))
        
        # バックグラウンドスレッドで実行
        thread = threading.Thread(target=fetch_thread, daemon=True)
        thread.start()
    
    def _update_title_callback(self, stream_id, new_title):
        """タイトル更新のコールバック（メインスレッドで実行）
        
        Args:
            stream_id (str): 配信ID
            new_title (str): 新しいタイトル
        """
        if stream_id not in self.stream_manager.streams:
            return
        
        settings = self.stream_manager.streams[stream_id]
        settings.title = new_title
        
        # タイトルから情報を抽出
        base_title, series = extract_title_info(
            new_title,
            self.global_settings.pattern_series,
            self.global_settings.pattern_base_title_list
        )
        
        # 抽出結果をprintで出力
        print(f"=== タイトル抽出結果 ===")
        print(f"配信ID: {stream_id}")
        print(f"元のタイトル: {new_title}")
        print(f"base_title: {base_title}")
        print(f"series: {series}")
        print(f"=====================")
        
        # ログにも記録
        logger.info(f"Title extraction for {stream_id}: base_title='{base_title}', series='{series}'")
        
        # リストを更新
        self.update_stream_list()
        
        # 選択中の配信情報を更新
        if self.selected_stream_id == stream_id:
            self.update_selected_stream_info(stream_id)
        
        logger.info(f"Title updated asynchronously for {stream_id}: {new_title}")
    
    def update_selected_stream_title(self):
        """選択された配信のタイトルを更新"""
        selection = self.stream_tree.selection()
        if not selection:
            messagebox.showwarning(self.strings["messages"]["warning"], self.strings["messages"]["select_stream"])
            return
            
        item = self.stream_tree.item(selection[0])
        stream_id = item['values'][0]
        
        # タイトル更新
        self.update_stream_title(stream_id)
    
    def tweet_stream_announcement(self):
        """選択された配信の告知をツイート"""
        selection = self.stream_tree.selection()
        if not selection:
            messagebox.showwarning(self.strings["messages"]["warning"], self.strings["messages"]["select_stream"])
            return
        
        item = self.stream_tree.item(selection[0])
        stream_id = item['values'][0]
        
        # 配信設定を取得
        settings = self.stream_manager.streams.get(stream_id)
        if not settings:
            return
        
        # ツイート内容を作成
        # 1行目: タイトル
        # 2行目: URL
        # 3行目: 空行（コメント入力用）
        title = settings.title if settings.title else "配信"
        url = settings.url
        
        # ツイート内容（改行コードは\n）
        tweet_text = f"{title}\n{url}\n"
        
        # URLエンコード
        import urllib.parse
        encoded_text = urllib.parse.quote(tweet_text)
        
        # TwitterのツイートURL
        twitter_url = f"https://twitter.com/intent/tweet?text={encoded_text}"
        
        # ブラウザで開く
        webbrowser.open(twitter_url)
        logger.info(f"Opening tweet window for stream: {stream_id}")
    
    def setup_obs(self):
        """OBS接続設定"""
        try:
            if self.obs:
                try:
                    self.obs.disconnect()
                except:
                    pass
            
            self.obs = OBSSocket(
                self.global_settings.obs_host,
                self.global_settings.obs_port,
                self.global_settings.obs_passwd
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
        
        # YouTube URLの場合は通常形式に正規化
        if platform == 'youtube':
            url = self.normalize_youtube_url(url)
            logger.info(f"YouTube URL normalized: {url}")
        
        # URL重複チェック
        for existing_stream in self.stream_manager.streams.values():
            if existing_stream.url == url:
                messagebox.showerror(self.strings["messages"]["error"], self.strings["messages"]["duplicate_url"])
                return
        
        # プラットフォームごとの連番IDを生成
        stream_id = f"{platform}_{self.stream_id_counters[platform]}"
        self.stream_id_counters[platform] += 1
        
        # StreamSettingsを作成（タイトルは空で先に追加）
        stream_settings = StreamSettings(
            stream_id=stream_id,
            platform=platform,
            url=url,
            title=""  # 空のタイトルで即座に追加
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
        
        # バックグラウンドでタイトルを取得
        self.fetch_title_async(stream_id)
    
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
            """コメント受信時のコールバック（メインスレッドで実行）"""
            comment_data['stream_id'] = stream_id
            # GUI更新はメインスレッドで実行する必要があるため、root.after()を使用
            self.root.after(0, lambda: self.process_comment(stream_id, comment_data))
        
        success = self.stream_manager.start_stream(stream_id, comment_callback)
        
        if success:
            # UI更新
            debug_print(f"DEBUG: Stream started successfully, updating UI for {stream_id}")
            settings = self.stream_manager.streams[stream_id]
            debug_print(f"DEBUG: settings.url = {settings.url}")
            debug_print(f"DEBUG: settings.is_active = {settings.is_active}")
            
            # リスト更新
            self.update_stream_list()
            
            # 選択中の配信情報を更新
            if self.selected_stream_id == stream_id:
                self.update_selected_stream_info(stream_id)
            
            # 強制的にGUI更新
            self.root.update_idletasks()
            debug_print(f"DEBUG: UI update completed")
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
        debug_print(f"DEBUG: Stopping stream {stream_id}")
        self.stream_manager.stop_stream(stream_id)
        
        # UI更新
        debug_print(f"DEBUG: Updating UI after stop")
        settings = self.stream_manager.streams.get(stream_id)
        if settings:
            debug_print(f"DEBUG: settings.is_active = {settings.is_active}")
            
            self.update_stream_list()
            
            # 選択中の配信情報を更新
            if self.selected_stream_id == stream_id:
                self.update_selected_stream_info(stream_id)
            
            # 強制的にGUI更新
            self.root.update_idletasks()
            debug_print(f"DEBUG: UI update completed")
    
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
            
            # 自動保存
            self.save_requests()
    
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
                
                # 自動保存
                self.save_requests()
    
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
                
                # 自動保存
                self.save_requests()
    
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
                
                # 自動保存
                self.save_requests()
    
    def clear_all_requests(self):
        """全リクエストをクリア"""
        if messagebox.askyesno(
            self.strings["messages"]["confirm"], 
            self.strings["messages"]["clear_requests_confirm"]
        ):
            self.common_requests.clear()
            self.update_request_display()
            self.generate_xml()
            
            # 自動保存
            self.save_requests()
            
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
    
    def generate_todo_xml(self, filename='todo.xml'):
        """リクエストリストをXML形式でファイルに出力（Ajax用）
        
        Args:
            filename (str): 出力先ファイル名
        """
        try:
            # XML宣言とルート要素
            xml_lines = ['<?xml version="1.0" encoding="utf-8"?>']
            xml_lines.append('<TODOs>')
            
            # 各リクエストをXML要素として追加
            for index, req in enumerate(self.common_requests, start=1):
                content = req.get('content', '')
                author = req.get('author', '')
                platform = req.get('platform', '')
                
                # XMLエスケープ
                content_escaped = self.escape_for_xml(content)
                author_escaped = self.escape_for_xml(author)
                platform_escaped = self.escape_for_xml(platform)
                
                xml_lines.append('<item>')
                xml_lines.append(f'    <idx>{index}</idx>')
                xml_lines.append(f'    <title>{content_escaped}</title>')
                xml_lines.append(f'    <name>{author_escaped}</name>')
                xml_lines.append(f'    <platform>{platform_escaped}</platform>')
                xml_lines.append('</item>')
            
            xml_lines.append('</TODOs>')
            
            # ファイルに書き込み
            with open(filename, 'w', encoding='utf-8') as f:
                f.write('\n'.join(xml_lines))
            
            logger.debug(f"TODO XML generated: {filename} ({len(self.common_requests)} items)")
            
        except Exception as e:
            logger.error(f"Failed to generate TODO XML: {e}")
    
    def setup_icon(self):
        """アプリケーションアイコンを設定"""
        # 方法1: .ico ファイルを試す
        try:
            icon_path = os.path.join(os.path.dirname(__file__), "icon.ico")
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
                debug_print(f"DEBUG: Loaded icon from {icon_path}")
                logger.info(f"Application icon loaded: {icon_path}")
                return
        except Exception as e:
            debug_print(f"DEBUG: Could not load .ico icon: {e}")
        
        # 方法2: .png ファイルを試す（フォールバック）
        try:
            png_path = os.path.join(os.path.dirname(__file__), "icon.png")
            if os.path.exists(png_path):
                icon_image = tk.PhotoImage(file=png_path)
                self.root.iconphoto(True, icon_image)
                debug_print(f"DEBUG: Loaded icon from {png_path}")
                logger.info(f"Application icon loaded: {png_path}")
                return
        except Exception as e:
            debug_print(f"DEBUG: Could not load .png icon: {e}")
        
        # アイコンが読み込めなかった場合（デフォルトアイコンを使用）
        debug_print("DEBUG: Using default icon (no custom icon file found)")
        logger.info("Application icon not found, using default Tk icon")
    
    def on_closing(self):
        """アプリケーション終了時の処理"""
        # ウィンドウ位置を保存
        try:
            # geometry()の戻り値は "幅x高さ+X座標+Y座標" の形式
            geometry = self.root.geometry()
            # "+X+Y" の部分を抽出
            if '+' in geometry:
                parts = geometry.split('+')
                if len(parts) >= 3:
                    self.global_settings.window_x = int(parts[1])
                    self.global_settings.window_y = int(parts[2])
                    logger.info(f"Window position saved: x={self.global_settings.window_x}, y={self.global_settings.window_y}")
        except Exception as e:
            logger.error(f"Failed to save window position: {e}")
        
        # すべての配信のURLを保存（受信中かどうかに関わらず）
        all_urls = []
        for stream_id, settings in self.stream_manager.streams.items():
            all_urls.append(settings.url)
        self.global_settings.last_streams = all_urls
        
        # 全配信を停止（各ストリームで最大3秒待機してスレッド終了を確認）
        logger.info("Stopping all streams before closing...")
        for stream_id in list(self.stream_manager.streams.keys()):
            self.stream_manager.stop_stream(stream_id)
        
        # リクエストリストを保存
        self.save_requests()
        
        # 設定保存
        self.global_settings.save()
        
        # ウィンドウを閉じる
        logger.info("Application closing")
        self.root.destroy()
    
    def save_requests(self, filename='requests.json'):
        """リクエストリストをファイルに保存
        
        Args:
            filename (str): 保存先ファイル名
        """
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.common_requests, f, indent=2, ensure_ascii=False)
            logger.info(f"Requests saved: {len(self.common_requests)} items")
        except Exception as e:
            logger.error(f"Failed to save requests: {e}")
    
    def load_requests(self, filename='requests.json'):
        """リクエストリストをファイルから読み込み
        
        Args:
            filename (str): 読み込み元ファイル名
        """
        if not os.path.exists(filename):
            logger.info(f"Request file not found: {filename} (starting with empty list)")
            return
        
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                self.common_requests = json.load(f)
            logger.info(f"Requests loaded: {len(self.common_requests)} items")
            
            # GUIが初期化されていれば表示を更新
            if hasattr(self, 'request_tree'):
                self.update_request_display()
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse request file: {e}")
            self.common_requests = []
        except Exception as e:
            logger.error(f"Failed to load requests: {e}")
            self.common_requests = []
    
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
        try:
            logger.info("Application starting mainloop")
            self.root.mainloop()
            logger.info("Mainloop ended normally")
        except KeyboardInterrupt:
            logger.info("Application interrupted by user (KeyboardInterrupt)")
            self.on_closing()
        except Exception as e:
            logger.error(f"Unexpected error in mainloop: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            self.on_closing()

if __name__ == '__main__':
    import signal
    
    # SIGINTハンドラー（Ctrl+C対策）
    def signal_handler(sig, frame):
        logger.info(f"Signal {sig} received, ignoring...")
        # 何もしない - ユーザーがウィンドウを閉じるまで動作継続
    
    # SIGINTを無視（Windowsでのコンソール終了を防ぐ）
    signal.signal(signal.SIGINT, signal_handler)
    
    updater = GitHubUpdater(
        github_author='dj-kata',
        github_repo='ytlive_helper',
        current_version=SWVER,           # 現在のバージョン
        main_exe_name="ytlive_helper.exe",  # メインプログラムのexe名
        updator_exe_name="update.exe",           # アップデート用プログラムのexe名
    )
    
    # メインプログラムから呼び出す場合
    updater.check_and_update()

    try:
        app = MultiStreamCommentHelper()
        app.run()
    except KeyboardInterrupt:
        logger.info("Application interrupted by KeyboardInterrupt in main")
    except Exception as e:
        logger.error(f"Fatal error in main: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
