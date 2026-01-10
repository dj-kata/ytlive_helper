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
from chat_downloader import ChatDownloader  # Twitch用（軽量で高速）

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
            video_id = self.extract_video_id(self.settings.url)
            
            if not video_id:
                logger.error(f"Invalid YouTube URL: {self.settings.url}")
                debug_print(f"ERROR: Invalid YouTube URL: {self.settings.url}")
                return
                
            debug_print(f"DEBUG: Extracted video_id: {video_id}")
            debug_print(f"DEBUG: Creating pytchat.create with video_id: {video_id}")
            
            # interruptable=Falseでシグナルハンドラを無効化（スレッドで動作可能に）
            self.livechat = pytchat.create(video_id=video_id, interruptable=False)
            debug_print(f"DEBUG: pytchat.create successful, livechat object created")
            debug_print(f"DEBUG: Starting comment loop")
            
            message_count = 0
            
            while not self.stop_event.is_set() and self.livechat.is_alive():
                try:
                    for comment in self.livechat.get().sync_items():
                        if self.stop_event.is_set():
                            break
                        
                        message_count += 1
                        if message_count % 10 == 0:
                            debug_print(f"DEBUG: Received {message_count} YouTube comments")
                        
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
                        
                        self.callback(comment_data)
                        
                except Exception as inner_e:
                    debug_print(f"DEBUG: Error in YouTube chat loop: {inner_e}")
                    logger.error(f"Error in YouTube chat loop: {inner_e}")
                    
                time.sleep(1)
                
        except KeyboardInterrupt:
            debug_print(f"DEBUG: KeyboardInterrupt detected in YouTube receiver")
            logger.info(f"YouTube receiver interrupted by user")
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
    """Twitchコメント受信クラス（chat-downloader使用）"""
    def __init__(self, settings, callback, global_settings):
        super().__init__(settings)
        self.callback = callback
        self.global_settings = global_settings
        self.chat_downloader = None
        
    def start(self):
        """chat-downloaderを使ったコメント受信"""
        try:
            debug_print(f"DEBUG: TwitchCommentReceiver.start() called")
            debug_print(f"DEBUG: URL: {self.settings.url}")
            
            # chat-downloaderでチャットを取得
            self.chat_downloader = ChatDownloader()
            
            # タイムアウト設定でチャットを取得
            chat = self.chat_downloader.get_chat(
                self.settings.url,
                timeout=30  # 接続タイムアウト（秒）
            )
            
            debug_print(f"DEBUG: Chat downloader created for Twitch, starting message loop")
            
            message_count = 0
            error_count = 0
            max_errors = 10  # 連続エラー上限
            
            for message in chat:
                # 停止フラグチェック
                if self.stop_event.is_set():
                    debug_print(f"DEBUG: Stop event detected, breaking loop")
                    break
                
                # 連続エラーが多すぎる場合は停止
                if error_count >= max_errors:
                    debug_print(f"ERROR: Too many consecutive errors ({error_count}), stopping")
                    break
                
                try:
                    # メッセージをパース
                    author_name = message.get('author', {}).get('name', 'Unknown')
                    author_id = message.get('author', {}).get('id', author_name)
                    message_text = message.get('message', '')
                    timestamp = message.get('time_text', '')
                    
                    message_count += 1
                    error_count = 0  # 成功したのでエラーカウントをリセット
                    
                    if message_count % 10 == 0:
                        debug_print(f"DEBUG: Received {message_count} Twitch messages")
                    
                    # 管理者判定
                    is_moderator = False
                    for manager in self.global_settings.managers:
                        if manager['platform'] == 'twitch' and manager['id'] == author_id:
                            is_moderator = True
                            break
                    
                    # モデレーターバッジチェック
                    if not is_moderator and message.get('author', {}).get('is_moderator', False):
                        is_moderator = True
                    
                    # 統一フォーマットでコールバック
                    comment_data = {
                        'platform': 'twitch',
                        'author': author_name,
                        'message': message_text,
                        'timestamp': timestamp,
                        'author_id': author_id,
                        'is_moderator': is_moderator
                    }
                    
                    self.callback(comment_data)
                    
                except KeyError as ke:
                    error_count += 1
                    debug_print(f"DEBUG: Missing key in Twitch message: {ke}")
                    logger.warning(f"Missing key in message: {ke}")
                except Exception as inner_e:
                    error_count += 1
                    debug_print(f"DEBUG: Error processing Twitch message: {inner_e}")
                    logger.error(f"Error processing message: {inner_e}")
                    
            debug_print(f"DEBUG: Twitch message loop ended, total messages: {message_count}")
                    
        except KeyboardInterrupt:
            debug_print(f"DEBUG: KeyboardInterrupt detected in Twitch receiver")
            logger.info(f"Twitch receiver interrupted by user")
        except Exception as e:
            logger.error(f"Twitch comment receiver error: {e}")
            debug_print(f"ERROR: Twitch receiver error: {e}")
            import traceback
            debug_print(f"ERROR: Traceback: {traceback.format_exc()}")
        finally:
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
            debug_print(f"DEBUG: Creating TwitchCommentReceiver (chat-downloader)")
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
        
        stream_ids = []  # 追加したstream_idを記録
        
        for url in self.global_settings.last_streams:
            platform = self.detect_platform(url)
            if platform:
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
            # YouTube StudioのURLの場合は通常の視聴URLに変換
            if platform == 'youtube' and 'studio.youtube.com/video/' in url:
                # video_idを抽出
                parts = url.split('/video/')
                if len(parts) > 1:
                    video_id = parts[1].split('/')[0].split('?')[0]
                    # 通常の視聴URLに変換
                    url = f'https://www.youtube.com/watch?v={video_id}'
            
            # User-Agentヘッダーを設定（ブロック回避）
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            # タイムアウト設定でページを取得（短縮: 5秒）
            response = requests.get(url, headers=headers, timeout=5)
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
        
        # タイトルラベルが存在すれば更新
        if hasattr(settings, 'title_label'):
            settings.title_label.config(text=new_title)
        
        # リストを更新
        self.update_stream_list()
        
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
            self.update_stream_list()
            settings = self.stream_manager.streams[stream_id]
            if hasattr(settings, 'status_label'):
                settings.status_label.config(
                    text=self.strings["stream_info"]["status_running"], 
                    foreground="red"
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
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            logger.info("Application interrupted by user")
            self.on_closing()

if __name__ == '__main__':
    try:
        app = MultiStreamCommentHelper()
        app.run()
    except KeyboardInterrupt:
        print("Application interrupted by user")
        import sys
        sys.exit(0)
