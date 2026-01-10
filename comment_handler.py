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
    
    def process_request_commands(self, stream_id, comment_data):
        """コメントからリクエスト追加/削除コマンドを処理"""
        message = comment_data['message']
        author = comment_data['author']
        platform = comment_data['platform']
        author_id = comment_data.get('author_id', '')
        
        # 管理者チェック（新形式）
        is_manager = False
        for manager in self.global_settings.managers:
            if manager['platform'] == platform and manager['id'] == author_id:
                is_manager = True
                break
        
        # プッシュワードチェック
        for pushword in self.global_settings.pushwords:
            if message.startswith(pushword):
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
            if pullword in message:
                # 権限チェック
                if self.global_settings.pull_manager_only and not is_manager:
                    logger.info(f"Request remove denied: {author} is not a manager")
                    continue
                
                # リクエスト内容を抽出
                request_content = message.replace(pullword, '').strip()
                if request_content:
                    # マッチするリクエストを削除
                    for req in self.common_requests[:]:
                        if req['content'] == request_content:
                            self.common_requests.remove(req)
                            
                            # 配信タブのリクエスト処理数を更新
                            settings = self.stream_manager.streams.get(stream_id)
                            if settings and hasattr(settings, 'request_count_label'):
                                settings.processed_requests += 1
                                settings.request_count_label.config(text=str(settings.processed_requests))
                            
                            self.update_request_display()
                            self.generate_xml()
                            logger.info(f"Request removed: {request_content} by {author}")
                            break
                break
