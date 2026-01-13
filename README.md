# ytlive_helperとは？
YoutubeLive/Twitchの配信に役に立つツールです。  
コメントを受けてお題をリストに自動追加したり、消化済みのお題を自動クリアしたりできます。  

動作イメージ  
https://twitter.com/cold_planet_/status/1667364119652237312
![image](https://github.com/dj-kata/ytlive_helper/assets/61326119/3ac9ffc0-e52c-46ba-aeb3-dbaea393214a)

本ツールの良い所は以下。  
- 音ゲー配信などでリスナーから貰ったお題を配信画面に表示できる
  - 全てのお題を忘れずに消化できる
  - どの順番で消化しても取りこぼしをなくせる
- 配信枠やYoutubeStudioのURLから告知ツイートを作成できる
- 配信枠に記載した情報を配信画面に自動で反映できる
  - 配信タイトルに記載した第XXX回のようなシリーズ番号を自動取得
  - 概要欄に記載した配信内容に関する記述を自動取得

以下の環境で動作確認しています。
- OS: Windows11 25H2
- OBS: 32.0.1
- ウイルス対策ソフト: Windows Defender

# インストール方法
[Releaseページ](https://github.com/dj-kata/ytlive_helper/releases)から最新のytlive_helper.zipをダウンロードし、  
好きなフォルダに解凍してください。

以下のファイルが含まれています。

|ファイル名|内容|
|---|---|
|ytlive_helper.exe|プログラム本体|
|icon.ico|本プログラムのアイコン|
|html/todolist.html|お題箱をOBSで表示するためのHTML|
|html/todolist_noframe.html|お題箱をOBSで表示するためのHTML(文字列のみ)|
|global_settings.json|本プログラムの設定ファイル。初回起動時に自動生成されます。|
|todo.xml|todolist.htmlで表示するためのXMLファイル。自動生成されます。|
|version.txt|本ツールのバージョン情報|

# 使い方
1～3が初回のみの設定で、設定後は基本的に4のみやればよいです。

## 1. OBSの設定をする(初回のみ)
1. ソースの追加 -> ブラウザを選択する。好きな名前を付けてOK。
2. 1.で作成したブラウザソースをダブルクリックする。
3. ローカルファイルのチェックを入れ、同梱の```html\todolist.html```を選択する。
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
ytlive_helper.exeを実行します。  
メニューバー内のファイル→設定から設定画面を開きます。  
必要に応じて、リスト登録・削除のためのwordを登録してください。
<img alt="Image" src="https://github.com/user-attachments/assets/8eb6c15b-4f35-44bd-912c-811777088ea8" />

デフォルトでは,登録用ワードに```'お題 ', 'リク '```が登録してあります。(半角スペース、全角スペース両方)  
また、デフォルトでは削除用ワードに```'リクあり', '消化済み'```が登録してあります。

上部の入力欄に単語を入力してから各**登録**ボタンを押すと登録できます。  
削除したい単語を選択してから**削除**ボタンを押すと削除できます。

デフォルト設定の場合、  
- **お題 セピアの軌跡**というコメントが来ると**セピアの軌跡**がお題リストに追加されます(登録時は先頭一致が必須)。  
- **◯◯さんリクありでした**のようにコメントするとお題リストの一番上を削除できます(削除時は指定した単語が含まれていれば良い)。  

絵文字を登録する場合は、Tkinter(GUIライブラリ)のバグのせいでうまく登録できないため、以下のように登録してください。
- アプリを終了した状態で、global_settings.jsonを開く
- push_wordsまたはpull_wordsに直接使いたい絵文字を入力する
- global_settings.jsonを保存する
<img alt="Image" src="https://github.com/user-attachments/assets/2a386c55-e4eb-40a8-8985-c958aa64dda9" />

コメント経由でのコマンドの詳細については後述。

## 3. URLを入力し、コメント取得を開始する
配信URL入力欄にURLを入力し、**追加**をクリックします。  
配信URL一覧にURLが表示されるので、行内をダブルクリック(または、右クリックメニューの受信開始を選択)すると、選択した配信のコメントを受信します。

受信中の配信は以下のように赤くハイライトされ、Statusが**●受信中**となります。  
また、メイン画面にはリクエスト一覧及び受信したコメントも表示されます。

配信URLについては、以下のURL形式に対応しています。
- https://www.youtube.com/watch?v=(配信ID)
- https://studio.youtube.com/video/(配信ID)/livestreaming
- https://studio.youtube.com/live_chat?is_popout=1&v=(配信ID)

**告知**ボタンを押すと、ブラウザから告知ツイートをすることができます。  
includeの列のチェックを入れることで、
その配信を告知ツイートに含むことができます。
<img alt="Image" src="https://github.com/user-attachments/assets/266f977b-3d01-45c3-8a54-c5388e11ea7e" />  

告知内容が決まったら、右下の**告知ツイート**をクリックすることでツイート画面が開きます。  
<img alt="Image" src="https://github.com/user-attachments/assets/8f54866e-f8d1-4859-a4c5-727b9e9bd298" />

お題リストについては、このウィンドウから登録・削除することも可能です。

## 4. (必要であれば)管理者IDを設定する
リストの登録・削除については、指定した管理者IDからしか行えないようにする設定も可能です。  
設定画面で**管理者IDのみ許可する**をチェックしてください。
(荒らし対策目的)

管理者IDを登録するには、
受信したコメントに対して登録したい人のコメントをクリックしてから、  
右クリックメニューの**管理者IDに追加**を押してください。  
<img alt="Image" src="https://github.com/user-attachments/assets/b799de83-ad9c-41a0-a88b-f5bb7941f8c6" />

設定された管理者IDについては、設定画面の権限設定タブから確認できます。  
<img alt="Image" src="https://github.com/user-attachments/assets/bf2bd35e-8df1-4035-86f9-fcfa560ade5c" />


## 告知ボタン使用時の各情報の自動セット(配信タイトル、今日のお題など)
告知ツイート時時に配信タイトル等の情報をOBSに反映する機能も用意しています。  
告知ボタンを押すだけで、タイトルや概要欄から情報を抽出し、以下赤枠の部分を書き換えます。
![image](https://github.com/dj-kata/ytlive_helper/assets/61326119/e04ffa48-216e-49ad-9b07-da450f52c388)

動作イメージは以下。  
https://twitter.com/cold_planet_/status/1672506782323990528

この機能を利用するためには、以下の設定が必要です。
### 1. OBSwebsocketの設定

[OBSwebsocket](https://github.com/obsproject/obs-websocket/releases)をインストールしておいてください。  
5.0のアルファ版は不安定らしいので、4.9系を推奨します。(2023/3/16時点)  
～～Windows-Installer.exeと書いてあるファイルをダウンロードして実行します。  
インストール後にOBSを再起動すると、メニューバー内ツールの中に**obs-websocket設定**が出てきます。

OBSのメニューバー内ツール -> obs-websocket設定 を開き、
- WebSocketサーバを有効にする にチェック
- システムトレイアラートを有効にする にチェック
- サーバーパスワードを好きな文字列に変更(ytlive_helper側でも入力するので忘れないように注意)

しておいてください。  
![image](https://user-images.githubusercontent.com/61326119/225536753-c118d425-c0dc-4555-b2a4-9a50076e5993.png)

メニューバーから設定画面を開き、OBSwebsocket関連の情報を入力してください。  
- OBS hostは基本的にlocalhostで良いはずですが、環境に応じてローカルIPアドレスを設定してください。
- OBS websocket portはOBS側と同一の値に設定してください。(OBS側を変更していなければ4444)
- OBS websocket passwordは**OBS側で設定したサーバーパスワードと同一のもの**を入力してください。ここでしか使わないような、長いだけのパスワードでいいと思います。
<img alt="Image" src="https://github.com/user-attachments/assets/62e87583-2bfe-42da-8970-2f07fc6b79ed" />

### 2. 情報抽出用設定
設定画面にて、必要に応じて情報抽出のための設定を変更します。  
<img alt="Image" src="https://github.com/user-attachments/assets/f9969407-e70f-4a7e-938e-8619cd217afb" />

タイトル抽出設定については、数字部分を[number]と指定する。  
**INF配信 #303**なら```#[number]```、**ほげほげ配信123日目**なら```[number]日目```と指定すればよいです。

base_title除外パターンについては、例えば**【】**を登録しておけば
【神回】皆伝たぬきのINFINITAS配信【超絶かわいい】という
タイトルから```皆伝たぬきのINFINITAS配信```のみを抽出できます。

配信内容取得設定については、
指定した文字列が含まれる行の次の行全体が本日の内容として使われます。  
概要欄が以下の場合、**copulaパック少しやる、12未クリア周回の続き**の部分となります。
![image](https://github.com/dj-kata/ytlive_helper/assets/61326119/ee456b39-4c6b-4cca-8983-4a26302deaf5)

### 3. 情報反映のためのOBS設定
指定したソース名のテキストソースがあれば自動で文字列を変更します。  
ソース追加->テキスト(GDI+)でテキストソースを追加し、ソース名を以下の通りに指定してください。  
(ソースを右クリック→名前を変更で変更可能)

**ソース名が完全に一致しないと動作しないので注意**。  
![image](https://github.com/dj-kata/ytlive_helper/assets/61326119/9d2bd492-6ef0-4d60-b4b0-fa2146bb582d)

|テキストソース名|内容|
|-|-|
|ythMainTitle|配信タイトルのメイン部分がセットされる。【神回】のようにカッコで囲まれた部分は削除される。上記例の場合、```九段たぬきのDP配信```が書き込まれる。|
|ythSeriesNum|配信タイトルの第XXX回目部分がセットされる。上記例の場合、```#303```が書き込まれる。|
|ythTodayContent|本日の内容がセットされる。2.の概要欄例の場合、ここに```copulaパック少しやる、12未クリア周回の続き```が書き込まれる。|

フォント・サイズ・色などのデザインは自由に変更できます。

# コメント経由でのコマンドについて
## お題リスト登録時
```[登録用ワード]お題```を拾います。  
登録用ワードが```"お題 "```の場合、```"お題 Space Dog"```というコメントに対して**Space Dog**が登録されます。  
半角スペース、全角スペースを両方登録しておくと良いと思います。

また、絵文字も登録可能です。  
```":smiling_face_with_halo: "```を登録しておけば、以下のようなコメントを拾うことができます。  
![image](https://github.com/dj-kata/ytlive_helper/assets/61326119/a3acbb86-7ab3-46cb-9a35-026e3b030b29)

お題部分については、HTMLタグがあっても削除するようにしています(XSS対策)。

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
Windows版uvをインストールし、Makefileにuvのパスを記載した上で以下のようにすればビルドできます。  
TwitchAPIのキーについては公開できないので、generate_twitch_secret.pyから必要なファイルを生成してください。
```
git clone https://github.com/dj-kata/ytlive_helper.git
cd ytlive_helper

uv sync

# (Makefile編集)
# twitch_config.jsonを準備
uv run generate_twitch_secret.py

make
```

# ライセンス
Apache License 2.0に準じるものとします。

非営利・営利問わず配信などに使っていただいて問題ありません。  
クレジット表記も特に必須とはしませんが、以下のように書いて宣伝してくださるととても喜びます。

```
お題箱システム: ytlive_helper
https://github.com/dj-kata/ytlive_helper
```

# 連絡先
Twitter: @[cold_planet_](https://twitter.com/cold_planet_)
