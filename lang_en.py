# -*- coding: utf-8 -*-
"""
English UI Strings Definition
"""

STRINGS = {
    # Menu bar
    "menu": {
        "file": "File",
        "settings": "Settings",
        "exit": "Exit",
        "language": "Language",
    },
    
    # Stream management
    "stream": {
        "title": "Stream Management",
        "url_label": "Stream URL:",
        "add_button": "Add",
        "platform_auto": "Platform: Auto-detect",
        "start": "Start",
        "stop": "Stop",
        "delete": "Delete",
        "edit_url": "Edit URL",
        "update_title": "Update Title",
        "status_receiving": "● Receiving",
        "status_stopped": "○ Stopped",
        "help_text": "※Double-click to toggle receive ON/OFF, Double-click URL column to edit, Right-click for menu",
    },
    
    # List view column names
    "columns": {
        "id": "ID",
        "platform": "Platform",
        "title": "Title",
        "url": "URL",
        "status": "Status",
        "number": "No.",
        "request_content": "Request",
        "user": "User",
        "datetime": "Date/Time",
        "comment": "Comment",
        "stream_id": "Stream ID",
    },
    
    # Request management
    "request": {
        "title": "Request List (All Streams)",
        "manual_add_label": "Manual Add:",
        "add_button": "Add",
        "delete_button": "Delete",
        "move_up": "Move Up",
        "move_down": "Move Down",
        "clear": "Clear",
    },
    
    # Comment management
    "comment": {
        "title": "Comment List (All Streams)",
        "clear_button": "Clear",
        "auto_scroll": "Auto Scroll",
    },
    
    # Context menu
    "context_menu": {
        "cut": "Cut",
        "copy": "Copy",
        "paste": "Paste",
        "select_all": "Select All",
        "add_manager": "Add to Managers",
        "add_ng_user": "Add to NG Users",
        "start_receive": "Start Receiving",
        "stop_receive": "Stop Receiving",
        "tweet_announcement": "Tweet Announcement",
    },
    
    # Stream info tab
    "stream_info": {
        "title": "Stream Information",
        "stream_title": "Title:",
        "url": "URL:",
        "platform": "Platform:",
        "status": "Status:",
        "status_running": "Running",
        "status_stopped": "Stopped",
        "title_loading": "(Loading...)",
    },
    
    # Statistics
    "stats": {
        "title": "Statistics",
        "comment_count": "Comments Received:",
        "request_count": "Requests Processed:",
    },
    
    # Settings dialog
    "settings": {
        "title": "Settings",
        "obs_tab": "OBS Settings",
        "trigger_tab": "Trigger Words",
        "permission_tab": "Permissions",
        "ng_user_tab": "NG Users",
        "obs_connection": "OBS Connection Settings",
        "host": "Host:",
        "port": "Port:",
        "password": "Password:",
        "other_settings": "Other Settings",
        "keep_on_top": "Keep window on top",
        "debug_settings": "Debug Settings",
        "debug_mode": "Enable debug mode (restart required)",
        "push_word": "Request Add Words (Common)",
        "pull_word": "Request Remove Words (Common)",
        "add_button": "Add",
        "delete_button": "Delete",
        "permission_title": "Permission Settings (Common)",
        "push_manager_only": "Allow only managers to add requests",
        "pull_manager_only": "Allow only managers to remove requests",
        "manager_title": "Manager Settings",
        "manager_note": "※You can also add managers via right-click on comments",
        "ng_user_title": "NG User Management",
        "ng_user_note": "※You can also add NG users via right-click on comments",
        "save_button": "Save",
        "cancel_button": "Cancel",
    },
    
    # Messages
    "messages": {
        "error": "Error",
        "warning": "Warning",
        "success": "Success",
        "confirm": "Confirm",
        "info": "Information",
        "url_required": "Please enter a URL",
        "unsupported_url": "Unsupported URL.\nPlease enter a YouTube or Twitch URL.",
        "duplicate_url": "This URL has already been added.",
        "select_stream": "Please select a stream",
        "delete_stream_confirm": "Delete stream {stream_id}?",
        "started_stream": "Started stream {stream_id}",
        "start_failed": "Failed to start stream {stream_id}",
        "stopped_stream": "Stopped stream {stream_id}",
        "url_updated": "URL updated.",
        "url_updated_running": "URL updated.\n\nThe stream is currently running. Please stop and restart to apply changes.",
        "invalid_port": "Please enter a valid port number",
        "debug_restart_required": "Please restart the application to apply debug setting changes.",
        "clear_requests_confirm": "Clear all requests?",
        "clear_comments_confirm": "Clear all comments?",
        "manager_added": "Added {author} to managers.",
        "manager_exists": "{author} is already registered as a manager.",
        "ng_user_added": "Added {author} to NG users.",
        "ng_user_exists": "{author} is already registered as an NG user.",
    },
    
    # Dialogs
    "dialog": {
        "url_edit_title": "Edit URL",
        "new_url_label": "New URL:",
        "ok_button": "OK",
        "cancel_button": "Cancel",
        "add_word_title": "Add",
        "add_push_word_prompt": "Enter request add word:",
        "add_pull_word_prompt": "Enter request remove word:",
    },
}
