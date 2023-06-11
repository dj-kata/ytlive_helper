# ytlive_helperとは？
YoutubeLiveの補助用ツールです。  
コメントを受けてお題リストに追加したり、消化済みのお題をクリアしたりできます。  

動作イメージ  
https://twitter.com/cold_planet_/status/1667364119652237312
![image](https://github.com/dj-kata/ytlive_helper/assets/61326119/3ac9ffc0-e52c-46ba-aeb3-dbaea393214a)

本ツールの良い所は以下。  
- 音ゲー配信などでリスナーから貰ったお題を配信画面に表示できる
  - 全てのお題を忘れずに消化できる
  - どの順番で消化しても取りこぼしをなくせる
- 配信枠やYoutubeStudioのURLから告知ツイートを作成できる

以下の環境で動作確認しています。
- OS: Windows10 22H2
- OBS: 29.1.2
- ウイルス対策ソフト: Windows Defender

# インストール方法
Releaseページから最新のytlive_helper.zipをダウンロードし、  
好きなフォルダに解凍してください。

以下のファイルが含まれています。

|ファイル名|内容|
|---|---|
|ytlive_helper.exe|プログラム本体|
|todolist.html|お題箱をOBSで表示するためのHTML|
|icon.ico|本プログラムのアイコン|
|||
|settings.json|本プログラムの設定ファイル。初回起動時に自動生成されます。|
|todo.xml|todolist.htmlで表示するためのXMLファイル。自動生成されます。|

# 使い方
## 1. OBSの設定をする(初回のみ)
1. ソースの追加 -> ブラウザを選択する。好きな名前を付けてOK。
2. 1.で作成したブラウザソースをダブルクリックする。
3. ローカルファイルのチェックを入れ、同梱のtodolist.htmlを選択する。
4. 画面の大きさは特に変えなくてよいです(デフォ=800x600)。Alt+ドラッグでトリミングして調整できます。
5. カスタムCSSについては、デフォルト設定だと透過されてしまうので消して良いです。または、下記のように設定することで色を付けたり、フォントを変えたりもできます。

```
body{
background-color: rgba(0, 0, 0, 0.99);
font-family:"Mochiy Pop P One";
}
```

![image](https://github.com/dj-kata/ytlive_helper/assets/61326119/436c1a00-e27b-4c72-9292-a34ee8e3f27a)

## 2. お題リストの登録・削除用ワードを設定する
## 3. (必要であれば)管理者IDを設定する
## 4. URLを入力し、コメント取得を開始する

# (開発者向け)ビルド方法
Windows版Python3をインストールし、必要なパッケージをpipでインストールした上で下記を実行します。
```
pyinstaller ytlive_helper.py --clean --noconsole --onefile --icon=icon.ico
```

# ライセンス
Apache License 2.0に準じるものとします。

非営利・営利問わず配信などに使っていただいて問題ありません。  
クレジット表記も特に必要ないですが、以下のように書いて宣伝してくださると喜びます。

```
お題箱システム: ytlive_helper (https://github.com/dj-kata/ytlive_helper)
```

# 連絡先
Twitter: @[cold_planet_](https://twitter.com/cold_planet_)
