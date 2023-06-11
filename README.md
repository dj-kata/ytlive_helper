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
[Releaseページ](https://github.com/dj-kata/ytlive_helper/releases)から最新のytlive_helper.zipをダウンロードし、  
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
1～3が初回のみの設定で、設定後は基本的に4のみやればよいです。

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
![image](https://github.com/dj-kata/ytlive_helper/assets/61326119/3bb09152-0306-4784-855c-23f1c982ab77)

todolist.htmlの77行目付近について、

```
<!-- 配信画面にコマンドを書くなら以下のような感じか -->
<!-- <td>お題箱 ("お題 楽曲名"でリクエスト可)</td> -->
<td>お題箱</td>
```

となっていますが、以下のようにすることでお題箱の横にコマンド例を書くこともできます。必要に応じて編集してください。  

```
<td>お題箱 ("お題 楽曲名"でリクエスト可)</td>
```

## 2. お題リストの登録・削除用ワードを設定する
メニューバー内のファイル→設定から設定画面を開きます。  
必要に応じて、リスト登録・削除のためのwordを登録してください。
![image](https://github.com/dj-kata/ytlive_helper/assets/61326119/87d3a735-9ded-46b8-add2-f0a4f361e72a)

デフォルトでは,登録用ワードに```'お題 ', 'リク '```が登録してあります。(半角スペース、全角スペース両方)  
また、デフォルトでは削除用ワードに```'リクあり', '消化済み'```が登録してあります。

上部の入力欄に単語を入力してから各**登録**ボタンを押すと登録できます。  
削除したい単語を選択してから**削除**ボタンを押すと削除できます。

デフォルト設定の場合、  
- **お題 セピアの軌跡**というコメントが来ると**セピアの軌跡**がお題リストに追加されます(登録時は先頭一致が必須)。  
- **◯◯さんリクありでした**のようにコメントするとお題リストの一番上を削除できます(削除時は指定した単語が含まれていれば良い)。  

コメント経由でのコマンドの詳細については後述。

## 3. (必要であれば)管理者IDを設定する
リストの登録・削除については、指定した管理者IDからしか行えないようにする設定も可能です。  
設定画面で**管理者IDのみ許可する**をチェックしてください。  
(荒らし対策目的)

管理者IDを登録するには、  
メイン画面でライブ配信のURLを入力して*start*をクリックし、  
登録したい人のコメントをクリックしてから、  
右クリックメニューの**管理者IDに追加**を押してください。  
(コメント取得スレッド実行中には管理者ID一覧を修正できないので、反映したい場合は一度**stop**を押してから再度**start**してください。)
![image](https://github.com/dj-kata/ytlive_helper/assets/61326119/d36691f3-9f88-4dd4-9de1-a83d7e90b789)

設定された管理者IDについては、設定画面から以下のように確認できます。  
![image](https://github.com/dj-kata/ytlive_helper/assets/61326119/ae46aaee-fd00-45a0-9322-5b474331f2f5)


## 4. URLを入力し、コメント取得を開始する
メイン画面の配信URL入力欄にURLを入力し、**start**をクリックします。  

配信中は**●active**の文字と、配信タイトルが表示されます。  
また、画面真ん中にお題リストが、画面下部にYoutubeLiveのコメントが表示されます。
![image](https://github.com/dj-kata/ytlive_helper/assets/61326119/29fed43b-efd6-45a7-9ef4-125f271b82b5)

配信URLについては、以下のURL形式に対応しています。
- https://www.youtube.com/watch?v=(配信ID)
- https://studio.youtube.com/video/(配信ID)/livestreaming
- https://studio.youtube.com/live_chat?is_popout=1&v=(配信ID)

告知ボタンを押すと、ブラウザから告知ツイートをすることができます。  
![image](https://github.com/dj-kata/ytlive_helper/assets/61326119/11b0a4f6-c300-4eea-bd3d-33ce2b0669b0)

お題リストについては、このウィンドウから登録・削除することも可能です。

# コメント経由でのコマンドについて
## お題リスト登録時
```[登録用ワード]お題```を拾います。  
登録用ワードが```"お題 "```の場合、```"お題 Space Dog"```というコメントに対して**Space Dog**が登録されます。  
半角スペース、全角スペースを両方登録しておくと良いと思います。

また、絵文字も登録可能です。  
```":smiling_face_with_halo: "```を登録しておけば、以下のようなコメントを拾うことができます。  
![image](https://github.com/dj-kata/ytlive_helper/assets/61326119/a3acbb86-7ab3-46cb-9a35-026e3b030b29)

## お題リスト削除時
以下の形式に対応しています
- ```.*[削除用ワード].*``` -> 一番上のお題を削除
- ```.*[削除用ワード].* A``` -> A番目のお題を削除
- ```.*[削除用ワード].* B-C``` -> B-C番目のお題を削除(C≧B)

削除については、先頭一致を必須としていないため、  
```DJかたさんリクありでした～！```のように書いても拾うことができます。

削除用ワードの後に数字を入れることで、  
一番上以外のお題を消したり、複数のお題を消したりもできます。  
- ```"リクありでした 3"```とコメントすると3番目のお題が消えます。  
- ```"消化済み 2-5"```とコメントすると、2～5番目のお題が全て消えます。

ここで、**削除用ワードの後にはスペースを入れることが必須**となります。  
また、**ここで指定する数字は半角数字のみ対応**となっている点にもご注意ください。

お題の削除コマンドに若干柔軟性を持たせているため、  
**削除だけは管理者IDだけが行えるように**したほうが安全かもしれません。

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
