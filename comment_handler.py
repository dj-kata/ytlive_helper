# -*- coding: utf-8 -*-
"""
Comment Handler Module
コメント処理、管理者/NGユーザ管理、リクエスト処理を担当
"""

import tkinter as tk
from tkinter import messagebox
import datetime
import logging

logger = logging.getLogger(__name__)


class CommentHandler:
    """コメント処理と管理を担当するMixinクラス"""
    
    def process_comment(self, stream_id, comment_data):
        """コメントを処理"""
        logger.debug(f"DEBUG: process_comment called for stream_id: {stream_id}")
        logger.debug(f"DEBUG: comment_data: {comment_data}")
        
        # NGユーザチェック
        for ng_user in self.global_settings.ng_users:
            if (ng_user['platform'] == comment_data['platform'] and 
                ng_user['id'] == comment_data['author_id']):
                logger.info(f"NG user detected: {comment_data['author']}, comment ignored")
                return
        
        # StreamSettingsを取得
        settings = self.stream_manager.streams.get(stream_id)
        if not settings:
            return
        
        # コメントをストリームに保存
        settings.comments.append(comment_data)
        
        # GUI更新（共通コメント表示エリア）
        self.update_comment_display(comment_data)
        
        # 配信タブのコメント数を更新
        if hasattr(settings, 'comment_count_label'):
            settings.comment_count_label.config(text=str(len(settings.comments)))
        
        # リクエスト処理
        self.process_request_commands(stream_id, comment_data)
    
    def update_comment_display(self, comment_data):
        """共通コメント表示エリアにコメントを追加"""
        # タイムスタンプがあればフォーマット、なければ現在時刻
        if 'timestamp' in comment_data and comment_data['timestamp']:
            try:
                # ISO形式の文字列をdatetimeオブジェクトに変換
                dt = datetime.datetime.fromisoformat(comment_data['timestamp'])
                # 表示用にフォーマット
                time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                time_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        else:
            time_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Treeviewに追加（tagsに author_id と platform を格納）
        self.comment_tree.insert('', tk.END, 
            values=(
                comment_data['author'],
                comment_data['message'],
                comment_data.get('stream_id', ''),
                comment_data['platform'],
                time_str
            ),
            tags=(comment_data.get('author_id', ''), comment_data['platform'])
        )
        
        # 自動スクロール
        if self.auto_scroll.get():
            self.comment_tree.yview_moveto(1.0)
    
    def add_manager_from_comment(self):
        """選択されたコメントのユーザーを管理者に追加"""
        selection = self.comment_tree.selection()
        if not selection:
            return
            
        item_id = selection[0]
        values = self.comment_tree.item(item_id)['values']
        tags = self.comment_tree.item(item_id)['tags']
        
        if len(values) >= 2 and len(tags) >= 2:
            author = values[0]  # ユーザー名（列順序変更に対応）
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
                    messagebox.showinfo(
                        self.strings["messages"]["info"], 
                        self.strings["messages"]["manager_exists"].format(author=author)
                    )
                    return
            
            self.global_settings.managers.append(manager_entry)
            self.global_settings.save()
            messagebox.showinfo(
                self.strings["messages"]["info"], 
                self.strings["messages"]["manager_added"].format(author=author)
            )

    def add_ng_user_from_comment(self):
        """選択されたコメントのユーザーをNGユーザに追加"""
        selection = self.comment_tree.selection()
        if not selection:
            return

        item_id = selection[0]
        values = self.comment_tree.item(item_id)['values']
        tags = self.comment_tree.item(item_id)['tags']

        if len(values) >= 2 and len(tags) >= 2:
            author = values[0]  # ユーザー名（列順序変更に対応）
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
                    messagebox.showinfo(
                        self.strings["messages"]["info"], 
                        self.strings["messages"]["ng_user_exists"].format(author=author)
                    )
                    return

            self.global_settings.ng_users.append(ng_entry)
            self.global_settings.save()
            messagebox.showinfo(
                self.strings["messages"]["info"], 
                self.strings["messages"]["ng_user_added"].format(author=author)
            )
    
    def parse_request_numbers(self, text):
        """リクエスト番号のテキストをパースして番号リストを返す
        
        例:
            "1-3" → [1, 2, 3]
            "1 3-4" → [1, 3, 4]
            "1,2,3" → [1, 2, 3]
            "1, 3-5, 7" → [1, 3, 4, 5, 7]
        
        Args:
            text (str): 番号を含むテキスト
            
        Returns:
            list[int]: 番号のリスト（重複なし、ソート済み）
        """
        import re
        
        numbers = []
        
        # カンマとスペースで分割
        parts = re.split(r'[,\s]+', text.strip())
        
        for part in parts:
            if not part:
                continue
            
            # 範囲指定（例: "1-3"）
            if '-' in part:
                try:
                    start, end = part.split('-', 1)
                    start_num = int(start.strip())
                    end_num = int(end.strip())
                    
                    # 範囲を展開
                    for num in range(start_num, end_num + 1):
                        if num not in numbers:
                            numbers.append(num)
                except ValueError:
                    logger.warning(f"Invalid range format: {part}")
                    continue
            else:
                # 単一の数字
                try:
                    num = int(part.strip())
                    if num not in numbers:
                        numbers.append(num)
                except ValueError:
                    logger.warning(f"Invalid number format: {part}")
                    continue
        
        # ソートして返す
        return sorted(numbers)
    
    def process_request_commands(self, stream_id, comment_data):
        """コメントからリクエスト追加/削除コマンドを処理"""
        message = comment_data['message']
        author = comment_data['author']
        platform = comment_data['platform']
        author_id = comment_data.get('author_id', '')
        
        # 常に出力されるINFOレベルのログ
        logger.info(f"Processing command: '{message}' from {author}")
        
        logger.debug(f"DEBUG: process_request_commands called")
        logger.debug(f"DEBUG:   message: {message}")
        logger.debug(f"DEBUG:   author: {author} (id: {author_id})")
        logger.debug(f"DEBUG:   platform: {platform}")
        
        # 管理者チェック（新形式）
        is_manager = False
        for manager in self.global_settings.managers:
            if manager['platform'] == platform and manager['id'] == author_id:
                is_manager = True
                break
        
        logger.debug(f"DEBUG:   is_manager: {is_manager}")
        logger.debug(f"DEBUG:   pushwords: {self.global_settings.pushwords}")
        logger.debug(f"DEBUG:   pullwords: {self.global_settings.pullwords}")
        logger.debug(f"DEBUG:   push_manager_only: {self.global_settings.push_manager_only}")
        logger.debug(f"DEBUG:   pull_manager_only: {self.global_settings.pull_manager_only}")
        
        # プッシュワードチェック
        for pushword in self.global_settings.pushwords:
            if message.startswith(pushword):
                logger.debug(f"DEBUG: Pushword matched: '{pushword}'")
                logger.info(f"Pushword matched: '{pushword}'")
                # 権限チェック
                if self.global_settings.push_manager_only and not is_manager:
                    logger.info(f"Request add denied: {author} is not a manager")
                    continue
                
                # リクエスト内容を抽出
                request_content = message[len(pushword):].strip()
                if request_content:
                    # 辞書形式でリクエストを追加
                    request_data = {
                        'content': request_content,
                        'author': author,
                        'platform': platform,
                        'stream_id': stream_id
                    }
                    self.common_requests.append(request_data)
                    
                    # 配信タブのリクエスト処理数を更新
                    settings = self.stream_manager.streams.get(stream_id)
                    if settings and hasattr(settings, 'request_count_label'):
                        settings.processed_requests += 1
                        settings.request_count_label.config(text=str(settings.processed_requests))
                    
                    self.update_request_display()
                    self.generate_xml()
                    logger.info(f"Request added: {request_content} by {author}")
                break
        
        # プルワードチェック
        for pullword in self.global_settings.pullwords:
            logger.debug(f"DEBUG: Checking pullword: '{pullword}' in '{message}'")
            if pullword in message:
                logger.debug(f"DEBUG: Pullword matched: '{pullword}'")
                logger.info(f"Pullword matched: '{pullword}' in message: '{message}'")
                
                # 権限チェック
                if self.global_settings.pull_manager_only and not is_manager:
                    logger.info(f"Request remove denied: {author} is not a manager")
                    logger.debug(f"DEBUG: Permission denied, continuing to next pullword")
                    continue
                
                logger.debug(f"DEBUG: Permission OK, processing removal")
                logger.info(f"Permission OK, processing removal for: '{message}'")
                
                # プルワード以降の部分を取得
                remaining_text = message.split(pullword, 1)[1].strip()
                logger.debug(f"DEBUG: Remaining text after pullword: '{remaining_text}'")
                logger.info(f"Remaining text after pullword: '{remaining_text}'")
                
                # 番号指定パターンをチェック
                import re
                
                # パターン判定
                if not remaining_text:
                    # 番号なし → デフォルトで1番を削除
                    logger.info(f"No number specified, defaulting to #1")
                    numbers = [1]
                    is_number_deletion = True
                elif re.match(r'^[\d\s,\-]+$', remaining_text):
                    # 数字のみ → 番号指定削除
                    logger.info(f"Number-based deletion detected for: '{remaining_text}'")
                    numbers = self.parse_request_numbers(remaining_text)
                    is_number_deletion = True
                else:
                    # 文字を含む → 内容一致削除
                    logger.info(f"Content-based deletion for: '{remaining_text}'")
                    numbers = None
                    is_number_deletion = False
                
                # 番号指定削除の処理
                if is_number_deletion and numbers:
                    logger.debug(f"DEBUG: Pattern matched as number-based deletion")
                    logger.debug(f"DEBUG: Parsed numbers: {numbers}")
                    logger.info(f"Parsed numbers: {numbers}")
                    
                    removed_count = 0
                    removed_items = []
                    
                    logger.info(f"Current request count: {len(self.common_requests)}")
                    
                    # リクエストリストは1始まり
                    for num in numbers:
                        index = num - 1  # 0ベースのインデックスに変換
                        if 0 <= index < len(self.common_requests):
                            removed_item = self.common_requests[index]
                            removed_items.append((index, removed_item))
                    
                    logger.debug(f"DEBUG: Items to remove: {len(removed_items)}")
                    logger.info(f"Items to remove: {len(removed_items)}")
                    
                    # 逆順で削除（インデックスのズレを防ぐ）
                    for index, item in sorted(removed_items, reverse=True):
                        self.common_requests.pop(index)
                        removed_count += 1
                        logger.info(f"Request #{index+1} removed: {item['content']} by {author}")
                    
                    if removed_count > 0:
                        # 配信タブのリクエスト処理数を更新
                        settings = self.stream_manager.streams.get(stream_id)
                        if settings and hasattr(settings, 'request_count_label'):
                            settings.processed_requests += removed_count
                            settings.request_count_label.config(text=str(settings.processed_requests))
                        
                        self.update_request_display()
                        self.generate_xml()
                        logger.info(f"Removed {removed_count} requests by numbers: {numbers}")
                    else:
                        logger.info(f"No requests removed - numbers may be out of range")
                
                # 内容一致削除の処理
                elif not is_number_deletion:
                    logger.debug(f"DEBUG: Pattern matched as content-based deletion")
                    # 従来の内容一致での削除
                    request_content = remaining_text
                    logger.debug(f"DEBUG: Looking for request with content: '{request_content}'")
                    
                    if request_content:
                        # マッチするリクエストを削除
                        found = False
                        logger.info(f"Searching in {len(self.common_requests)} requests")
                        for req in self.common_requests[:]:
                            logger.debug(f"DEBUG: Comparing '{req['content']}' with '{request_content}'")
                            if req['content'] == request_content:
                                logger.debug(f"DEBUG: Match found, removing request")
                                logger.info(f"Match found! Removing request: '{request_content}'")
                                self.common_requests.remove(req)
                                found = True
                                
                                # 配信タブのリクエスト処理数を更新
                                settings = self.stream_manager.streams.get(stream_id)
                                if settings and hasattr(settings, 'request_count_label'):
                                    settings.processed_requests += 1
                                    settings.request_count_label.config(text=str(settings.processed_requests))
                                
                                self.update_request_display()
                                self.generate_xml()
                                logger.info(f"Request removed: {request_content} by {author}")
                                break
                        
                        if not found:
                            logger.debug(f"DEBUG: No matching request found for content: '{request_content}'")
                            logger.info(f"No matching request found for content: '{request_content}'")
                break
