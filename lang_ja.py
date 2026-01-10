# -*- coding: utf-8 -*-
"""
日本語UI文字列定義
"""

STRINGS = {
    # メニューバー
    "menu": {
        "file": "ファイル",
        "settings": "設定",
        "exit": "終了",
        "language": "Language",
    },
    
    # 配信管理
    "stream": {
        "title": "配信管理",
        "url_label": "配信URL:",
        "add_button": "追加",
        "platform_auto": "プラットフォーム: 自動判定",
        "start": "開始",
        "stop": "停止",
        "delete": "削除",
        "edit_url": "URLを編集",
        "status_receiving": "● 受信中",
        "status_stopped": "○ 停止中",
        "help_text": "※ダブルクリックで受信ON/OFF切り替え、URL列ダブルクリックでURL編集、右クリックでメニュー表示",
    },
    
    # リストビューのカラム名
    "columns": {
        "id": "ID",
        "platform": "Platform",
        "title": "タイトル",
        "url": "URL",
        "status": "Status",
        "number": "番号",
        "request_content": "リクエスト内容",
        "user": "ユーザー",
        "datetime": "日時",
        "comment": "コメント",
        "stream_id": "配信ID",
    },
    
    # リクエスト管理
    "request": {
        "title": "リクエスト一覧（全配信）",
        "manual_add_label": "手動追加:",
        "add_button": "追加",
        "delete_button": "削除",
        "move_up": "上に移動",
        "move_down": "下に移動",
        "clear": "クリア",
    },
    
    # コメント管理
    "comment": {
        "title": "コメント一覧（全配信）",
        "clear_button": "クリア",
        "auto_scroll": "自動スクロール",
    },
    
    # 右クリックメニュー
    "context_menu": {
        "cut": "カット",
        "copy": "コピー",
        "paste": "ペースト",
        "select_all": "全て選択",
        "add_manager": "管理者IDに追加",
        "add_ng_user": "NGユーザに追加",
        "start_receive": "受信開始",
        "stop_receive": "受信停止",
    },
    
    # 配信情報タブ
    "stream_info": {
        "title": "配信情報",
        "stream_title": "タイトル:",
        "url": "URL:",
        "platform": "プラットフォーム:",
        "status": "ステータス:",
        "status_running": "実行中",
        "status_stopped": "停止中",
        "title_loading": "(取得中...)",
    },
    
    # 統計情報
    "stats": {
        "title": "統計情報",
        "comment_count": "受信コメント数:",
        "request_count": "処理したリクエスト数:",
    },
    
    # 設定ダイアログ
    "settings": {
        "title": "設定",
        "obs_tab": "OBS設定",
        "trigger_tab": "トリガーワード",
        "permission_tab": "権限設定",
        "ng_user_tab": "NGユーザ設定",
        "obs_connection": "OBS接続設定",
        "host": "ホスト:",
        "port": "ポート:",
        "password": "パスワード:",
        "other_settings": "その他の設定",
        "keep_on_top": "ウィンドウを最前面に表示",
        "debug_settings": "デバッグ設定",
        "debug_mode": "デバッグモードを有効にする（再起動が必要）",
        "push_word": "リクエスト追加ワード（全配信共通）",
        "pull_word": "リクエスト削除ワード（全配信共通）",
        "add_button": "追加",
        "delete_button": "削除",
        "permission_title": "権限設定（全配信共通）",
        "push_manager_only": "リクエスト追加を管理者のみ許可",
        "pull_manager_only": "リクエスト削除を管理者のみ許可",
        "manager_title": "管理者設定",
        "manager_note": "※コメントから右クリックで管理者IDに追加することもできます",
        "ng_user_title": "NGユーザ管理",
        "ng_user_note": "※コメント一覧から右クリックでNGユーザに追加できます",
        "save_button": "保存",
        "cancel_button": "キャンセル",
    },
    
    # メッセージ
    "messages": {
        "error": "エラー",
        "warning": "警告",
        "success": "成功",
        "confirm": "確認",
        "info": "情報",
        "url_required": "URLを入力してください",
        "unsupported_url": "対応していないURLです。\nYouTubeまたはTwitchのURLを入力してください。",
        "select_stream": "配信を選択してください",
        "delete_stream_confirm": "配信 {stream_id} を削除しますか？",
        "started_stream": "配信 {stream_id} を開始しました",
        "start_failed": "配信 {stream_id} の開始に失敗しました",
        "stopped_stream": "配信 {stream_id} を停止しました",
        "url_updated": "URLを更新しました。",
        "url_updated_running": "URLを更新しました。\n\n配信が実行中です。変更を反映するには、一度停止して再度開始してください。",
        "invalid_port": "正しいport番号を入力してください",
        "debug_restart_required": "デバッグ設定の変更を反映するには、アプリケーションを再起動してください。",
        "clear_requests_confirm": "全てのリクエストをクリアしますか？",
        "clear_comments_confirm": "全てのコメントをクリアしますか？",
        "manager_added": "{author}を管理者に追加しました。",
        "manager_exists": "{author}は既に管理者に登録されています。",
        "ng_user_added": "{author}をNGユーザに追加しました。",
        "ng_user_exists": "{author}は既にNGユーザに登録されています。",
    },
    
    # ダイアログ
    "dialog": {
        "url_edit_title": "URL編集",
        "new_url_label": "新しいURL:",
        "ok_button": "OK",
        "cancel_button": "キャンセル",
        "add_word_title": "追加",
        "add_push_word_prompt": "リクエスト追加ワードを入力:",
        "add_pull_word_prompt": "リクエスト削除ワードを入力:",
    },
}
