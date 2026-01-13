#!/usr/bin/env python3
"""
Twitch API 秘密情報生成スクリプト

Client ID と Client Secret を暗号化して config_secret.py を生成します。
このスクリプトで生成されたファイルはGitにコミットせず、ビルド時に含めます。

使い方:
1. twitch_config.json に Client ID/Secret を設定
2. このスクリプトを実行
3. config_secret.py が生成される
4. config_secret.py を .gitignore に追加
"""

import base64
import json
import os


def xor_encrypt(text, key="ytlive_helper_twitch_secret_key_2026"):
    """XOR暗号化
    
    Args:
        text (str): 暗号化する文字列
        key (str): 暗号化キー
        
    Returns:
        str: Base64エンコードされた暗号化文字列
    """
    encrypted = bytearray()
    for i, char in enumerate(text.encode('utf-8')):
        encrypted.append(char ^ ord(key[i % len(key)]))
    return base64.b64encode(bytes(encrypted)).decode('ascii')


def xor_decrypt(encrypted_text, key="ytlive_helper_twitch_secret_key_2026"):
    """XOR復号化
    
    Args:
        encrypted_text (str): Base64エンコードされた暗号化文字列
        key (str): 復号化キー
        
    Returns:
        str: 復号化された文字列
    """
    encrypted_bytes = base64.b64decode(encrypted_text)
    decrypted = bytearray()
    for i, byte in enumerate(encrypted_bytes):
        decrypted.append(byte ^ ord(key[i % len(key)]))
    return decrypted.decode('utf-8')


def generate_config_secret(client_id, client_secret):
    """config_secret.py を生成
    
    Args:
        client_id (str): Twitch Client ID
        client_secret (str): Twitch Client Secret
    """
    # 暗号化
    encrypted_id = xor_encrypt(client_id)
    encrypted_secret = xor_encrypt(client_secret)
    
    # Pythonコードを生成
    code = f'''# -*- coding: utf-8 -*-
"""
Twitch API 秘密情報（暗号化済み）

⚠️ 重要: このファイルは .gitignore に追加してください
⚠️ このファイルをGitにコミットしないでください

生成日時: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

# 暗号化されたClient ID と Client Secret
ENCRYPTED_TWITCH_CLIENT_ID = "{encrypted_id}"
ENCRYPTED_TWITCH_CLIENT_SECRET = "{encrypted_secret}"


def get_twitch_credentials():
    """復号化してTwitch認証情報を取得
    
    Returns:
        tuple: (client_id, client_secret)
    """
    import base64
    
    def decrypt(encrypted_text):
        """XOR復号化"""
        key = "ytlive_helper_twitch_secret_key_2026"
        encrypted_bytes = base64.b64decode(encrypted_text)
        decrypted = bytearray()
        for i, byte in enumerate(encrypted_bytes):
            decrypted.append(byte ^ ord(key[i % len(key)]))
        return decrypted.decode('utf-8')
    
    client_id = decrypt(ENCRYPTED_TWITCH_CLIENT_ID)
    client_secret = decrypt(ENCRYPTED_TWITCH_CLIENT_SECRET)
    
    return client_id, client_secret
'''
    
    # ファイルに書き込み
    with open('config_secret.py', 'w', encoding='utf-8') as f:
        f.write(code)
    
    print("✅ config_secret.py を生成しました")
    print()
    print("⚠️  重要な次のステップ:")
    print("   1. config_secret.py を .gitignore に追加")
    print("   2. このファイルをGitにコミットしない")
    print("   3. ビルド時には config_secret.py を含める")
    print()
    print("📝 .gitignore に以下を追加:")
    print("   # Twitch API秘密情報")
    print("   config_secret.py")
    print("   twitch_config.json")


def verify_config():
    """生成された config_secret.py を検証"""
    try:
        import config_secret
        
        client_id, client_secret = config_secret.get_twitch_credentials()
        
        print("\n" + "=" * 80)
        print("検証結果")
        print("=" * 80)
        print(f"✅ config_secret.py のインポート成功")
        print(f"✅ Client ID: {client_id[:10]}..." + "*" * (len(client_id) - 10))
        print(f"✅ Client Secret: {client_secret[:10]}..." + "*" * (len(client_secret) - 10))
        print()
        print("🎉 正常に動作しています")
        
        return True
        
    except ImportError:
        print("❌ config_secret.py が見つかりません")
        return False
    except Exception as e:
        print(f"❌ 検証エラー: {e}")
        return False


def main():
    """メイン処理"""
    
    print("=" * 80)
    print("Twitch API 秘密情報生成スクリプト")
    print("=" * 80)
    print()
    
    # twitch_config.json を読み込む
    if not os.path.exists('twitch_config.json'):
        print("❌ twitch_config.json が見つかりません")
        print()
        print("次のステップ:")
        print("1. twitch_config.json を作成")
        print("2. Client ID と Client Secret を設定")
        print("3. このスクリプトを再実行")
        return False
    
    try:
        with open('twitch_config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        client_id = config.get('client_id')
        client_secret = config.get('client_secret')
        
        if not client_id or not client_secret:
            print("❌ twitch_config.json に client_id または client_secret がありません")
            return False
        
        if client_id == 'your_client_id_here' or client_secret == 'your_client_secret_here':
            print("❌ Client ID と Client Secret を設定してください")
            return False
        
        print(f"✅ twitch_config.json 読み込み成功")
        print(f"   Client ID: {client_id[:10]}..." + "*" * (len(client_id) - 10))
        print(f"   Client Secret: {client_secret[:10]}..." + "*" * (len(client_secret) - 10))
        print()
        
        # 暗号化して config_secret.py を生成
        generate_config_secret(client_id, client_secret)
        
        # 検証
        return verify_config()
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON解析エラー: {e}")
        return False
    except Exception as e:
        print(f"❌ エラー: {e}")
        return False


def test_encryption():
    """暗号化・復号化のテスト"""
    
    print("\n" + "=" * 80)
    print("暗号化・復号化テスト")
    print("=" * 80)
    
    test_data = [
        ("test_client_id_123", "テストClient ID"),
        ("test_secret_xyz789", "テストClient Secret"),
        ("日本語テスト", "日本語文字列"),
    ]
    
    for original, description in test_data:
        print(f"\n{description}:")
        print(f"  元の文字列: {original}")
        
        encrypted = xor_encrypt(original)
        print(f"  暗号化: {encrypted}")
        
        decrypted = xor_decrypt(encrypted)
        print(f"  復号化: {decrypted}")
        
        if original == decrypted:
            print(f"  ✅ 一致")
        else:
            print(f"  ❌ 不一致")
            return False
    
    print("\n✅ 暗号化・復号化テスト成功")
    return True


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        # テストモード
        success = test_encryption()
        sys.exit(0 if success else 1)
    else:
        # 通常モード
        success = main()
        sys.exit(0 if success else 1)
