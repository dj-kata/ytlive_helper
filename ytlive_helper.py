import pytchat
import time
import sys, os
import re
import tkinter
import PySimpleGUI as sg
import threading
import json
import webbrowser, urllib, requests
from bs4 import BeautifulSoup

import logging, logging.handlers
import traceback

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
hdl = logging.handlers.RotatingFileHandler(
    './dbg.log',
    encoding='utf-8',
    maxBytes=1024*1024*20,
)
hdl.setLevel(logging.DEBUG)
hdl_formatter = logging.Formatter('%(asctime)s %(filename)s:%(lineno)5d %(funcName)s() [%(levelname)s] %(message)s')
hdl.setFormatter(hdl_formatter)
logger.addHandler(hdl)

class Settings:
    def __init__(self, lx=0, ly=0, manager=[], pushword=['お題 ', 'お題　', 'リク ', 'リク　'], pullword=['リクあり', '消化済'], ngword=[], req=[], url='', push_manager_only=False, pull_manager_only=False):
        self.lx       = lx
        self.ly       = ly
        self.manager  = manager
        self.pushword = pushword
        self.pullword = pullword
        self.ngword   = ngword
        self.req      = req
        self.url      = url
        self.push_manager_only = push_manager_only
        self.pull_manager_only = pull_manager_only

    def save(self):
        with open('settings.json', 'w') as f:
            json.dump(self.__dict__, f, indent=2)

class GetComment:
    def __init__(self):
        self.window = False
        self.autoscroll  = True
        self.table_comment = []
        if os.path.exists('settings.json'):
            with open('settings.json', 'r') as f:
                tmp = json.load(f)
                self.settings = Settings(**tmp)

    # icon用
    def ico_path(self, relative_path):
        try:
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)

    def get_liveid(self, url):
        if re.search('www.youtube.com.*v=', url):
            self.liveid = re.sub('.*v=', '', url)
        elif re.search('livestreaming\Z', url):
            self.liveid = url.split('/')[-2]
        
    def get_comment(self):
        # managerリストからID部分だけを抽出
        # リストにはDJかた(UC～～～～)みたいな形式で入っている
        self.manager_id = [self.settings.manager[i][-25:-1] for i in range(len(self.settings.manager))]
        logger.debug(f'self.manager_id = {self.manager_id}')
        self.stop_thread = False
        self.get_liveid(self.window['input_url'].get())

        regular_url = f"https://www.youtube.com/watch?v={self.liveid}"
        r = requests.get(regular_url)
        soup = BeautifulSoup(r.text,features="html.parser")
        title = re.sub(' - YouTube\Z', '', soup.find('title').text)
        self.window['live_title'].update(title)

        self.table_comment = []
        self.window['table_comment'].update(self.table_comment)
        while True:
            print('main thread start')
            logger.debug('main thread start')
            livechat = pytchat.create(video_id = self.liveid, interruptable=False)
            logger.debug(f'self.manager_id = {self.manager_id}, self.liveid = {self.liveid}')
            while livechat.is_alive():
                chatdata = livechat.get()
                for c in chatdata.items:
                    print(c.author.name, c.author.channelId, c.message, )
                    self.table_comment.append([c.author.name, c.message, c.datetime, c.author.channelId])
                    # TKinterの機能を使ってコメント用リストを差分更新
                    self.window['table_comment'].Widget.insert('', 'end', iid=len(self.table_comment),values=[c.author.name, c.message, c.datetime, c.author.channelId])
                    if self.autoscroll:
                        self.window['table_comment'].set_vscroll_position(len(self.table_comment)-1)
                    # リクエスト追加処理
                    if (not self.settings.push_manager_only) or (self.settings.push_manager_only and (c.author.channelId in self.manager_id)): # 許可されたIDからしか受け付けない
                        if c.message.startswith(tuple(self.settings.pushword)):
                            req = c.message
                            for q in self.settings.pushword: # 全pushwordを先頭から取り除く
                                req = re.sub(f'\A{q}', '', req).strip()
                            req = re.sub('<[^>]*?>', '', req)
                            req = req.replace('&', '&amp;').replace('<','&lt;').replace('>','&gt;').replace('"','&quot;').replace("'",'&apos;')
                            self.settings.req.append(f"{req} ({c.author.name}さん)")
                            self.window['list_req'].update(self.settings.req)
                    # リクエスト削除処理
                    if (not self.settings.pull_manager_only) or (self.settings.pull_manager_only and (c.author.channelId in self.manager_id)): # 許可されたIDからしか受け付けない
                        for q in self.settings.pullword: 
                            if q in c.message: # 削除用ワードを含む(先頭一致ではない)
                                submsg = re.findall('\S+', c.message.strip())
                                if len(submsg) == 1: # 削除用ワードのみのコメント
                                    self.settings.req.pop(0)
                                    self.window['list_req'].update(self.settings.req)
                                else: # 削除ワード subcmdの場合(ややこしいので1つしか受け付けない)
                                    try:
                                        excmd = submsg[1] # 追加コマンド, 削除 1-3なら1-3の部分
                                        if ('-' in excmd) or ('ー' in excmd):
                                            st,ed = list(map(int, re.findall('\d+', excmd)))
                                            for ii in range(st, ed+1):
                                                if len(self.settings.req) > st-1:
                                                    self.settings.req.pop(st-1)
                                        else:
                                            st = int(excmd) - 1
                                            self.settings.req.pop(st)
                                        self.window['list_req'].update(self.settings.req)
                                    except Exception:
                                        logger.debug(traceback.format_exc())
                                        continue
                                break
                    self.gen_xml()

                if self.stop_thread:
                    break
                time.sleep(1)
            if self.stop_thread:
                break
            else:
                logger.debug('再接続します')
                del livechat
        print('### main thread end!!!')
        logger.debug('### main thread end!!!')

    def gen_xml(self):
        with open('todo.xml', 'w', encoding='utf-8') as f:
            f.write(f'<?xml version="1.0" encoding="utf-8"?>\n')
            f.write("<TODOs>\n")
            for item in self.settings.req:
                f.write(f"<item>{item}</item>\n")
            f.write("</TODOs>\n")

    def gui_settings(self):
        self.mode = 'settings'
        layout = []
        layout_push_description = [
            [sg.Text('リスト登録用word', tooltip='ここに書いた単語が先頭にあるメッセージをリクエストと扱う。\n例:"リクエスト"を登録している場合、"リクエスト セピアの軌跡"を拾ってセピアの軌跡をリストに登録する')],
            [sg.Button('登録', key='btn_add_push', enable_events=True),sg.Button('削除', key='btn_delete_push', enable_events=True)],
            [sg.Checkbox('管理者IDのみ許可する', key='push_manager_only', default=self.settings.push_manager_only)]
        ]
        layout_pull_description = [
            [sg.Text('リスト削除用word', tooltip='ここに書いた単語が先頭にあるメッセージをリスト削除命令と扱う。\n例:"リクあり"を登録している場合、使用可能IDによる"リクありでした！"コメを拾ってリストの一番上を削除する')],
            [sg.Button('登録', key='btn_add_pull', enable_events=True),sg.Button('削除', key='btn_delete_pull', enable_events=True)],
            [sg.Checkbox('管理者IDのみ許可する', key='pull_manager_only', default=self.settings.pull_manager_only)]
        ]
        layout_trigger =[
            [sg.Text('入力した単語を登録:'), sg.Input('', key='input_trigger')],
            [
                sg.Column(layout_push_description),
                sg.Column([[sg.Listbox(self.settings.pushword, size=(30,5), key='list_push')]], vertical_scroll_only=True),
                sg.Column(layout_pull_description),
                sg.Column([[sg.Listbox(self.settings.pullword, size=(30,5), key='list_pull')]], vertical_scroll_only=True),
            ]
        ]
        layout.append([sg.Frame('リスト登録用word登録', layout=layout_trigger)])
        layout.append([sg.Column([[sg.Text('管理者ID', tooltip='メイン画面で、コメントを選択して右クリック→管理者IDに追加で登録できます。'), sg.Listbox(self.settings.manager, size=(50,5), key='list_manager')]], vertical_scroll_only=True),sg.Button('削除', key='btn_delete_manager', enable_events=True)])
        layout.append([sg.Button('閉じる', enable_events=True, key='btn_close_setting')])
        #layout.append([sg.Column([[sg.Text('NGワード'), sg.Listbox([], size=(50,10), key='list_ngword')]], vertical_scroll_only=True),])
        if self.window != False:
            self.window.close()
        self.window = sg.Window('YoutubeLive Helper 設定'
                                ,layout
                                ,grab_anywhere=True
                                ,return_keyboard_events=True
                                ,resizable=True
                                ,finalize=True
                                ,enable_close_attempted_event=True
                                ,icon=self.ico_path('icon.ico')
                                ,size=(800,400)
                                ,location=(self.settings.lx, self.settings.ly)
        )

    def gui_main(self):
        self.mode = 'main'
        sg.theme('SystemDefault')
        menuitems = [['ファイル',['設定','配信を告知する','終了']]]
        right_click_menu = ['&Right', ['管理者IDに追加']]
        layout = []
        layout.append([sg.Menubar(menuitems, key='menu')])
        layout.append([sg.Text('配信URL'), sg.Input(self.settings.url, key='input_url', size=(50,1)), sg.Button('告知', key='btn_tweet', enable_events=True), sg.Button('start', key='btn_start', enable_events=True)])
        layout.append([sg.Text('', size=(10,1), key='is_active', text_color="#ff0000"), sg.Text('Title:'), sg.Text('', key='live_title')])
        layout.append([sg.Text('お題リスト'), sg.Text('手動入力用:'), sg.Input('', key='input_req')])
        layout.append([sg.Listbox(self.settings.req, key='list_req', size=(80, 10)), sg.Button('追加', key='btn_add_req', enable_events=True), sg.Button('削除', key='btn_delete_req', enable_events=True), sg.Button('リセット', key='btn_reset_req', enable_events=True)])
        layout.append([sg.Table(
            []
            ,key='table_comment'
            ,headings=['user', 'msg', 'date', 'id']
            ,auto_size_columns=False
            ,col_widths=[15, 60, 10, 20]
            ,justification='left'
            ,enable_events=True
            ,right_click_menu=right_click_menu
        )])
        if self.window != False:
            self.window.close()
        self.window = sg.Window('YoutubeLive Helper'
                                ,layout
                                ,grab_anywhere=True
                                ,return_keyboard_events=True
                                ,resizable=True
                                ,finalize=True
                                ,enable_close_attempted_event=True
                                ,icon=self.ico_path('icon.ico')
                                ,size=(800,600)
                                ,location=(self.settings.lx, self.settings.ly)
        )
        self.window['table_comment'].expand(expand_x=True, expand_y=True)
    
    def main(self):
        self.gui_main()
        th = False
        while True:
            ev, val = self.window.read()
            logger.debug(f"ev = {ev}, val={val}")
            if ev in (sg.WIN_CLOSED, 'Escape:27', '-WINDOW CLOSE ATTEMPTED-', 'btn_close_setting', '終了'):
                if self.mode == 'settings':
                    self.settings.push_manager_only = val['push_manager_only']
                    self.settings.pull_manager_only = val['pull_manager_only']
                    self.gui_main()
                else:
                    if th != False:
                        self.stop_thread = True
                        th.join()
                    self.settings.lx,self.settings.ly = self.window.current_location()
                    self.settings.url = val['input_url']
                    self.settings.save()
                    break
            elif ev == 'btn_start':
                if th == False:
                    self.stop_thread = False
                    th = threading.Thread(target=self.get_comment, daemon=True)
                    th.start()
                    self.window[ev].update('stop')
                    self.window['is_active'].update('●active')
                else:
                    self.stop_thread = True
                    th.join()
                    del th
                    th = False
                    self.window['is_active'].update('')
                    self.window['live_title'].update('')
                    self.window[ev].update('start')
            elif ev in ('btn_tweet', '配信を告知する'): # 告知する
                try:
                    self.get_liveid(self.window['input_url'].get())
                    regular_url = f"https://www.youtube.com/watch?v={self.liveid}"
                    r = requests.get(regular_url)
                    soup = BeautifulSoup(r.text,features="html.parser")
                    title = re.sub(' - YouTube\Z', '', soup.find('title').text)
                    regular_url = f"https://www.youtube.com/watch?v={self.liveid}"
                    encoded_title = urllib.parse.quote(f"{title}\n{regular_url}\n")
                    webbrowser.open(f"https://twitter.com/intent/tweet?text={encoded_title}")
                except Exception:
                    sg.popup('対応していないURLです。\nYoutubeLiveのURLを入力してください。')
            elif ev == 'MouseWheel:Up':
                self.autoscroll = False
            elif ev == 'MouseWheel:Down':
                self.autoscroll = True
            elif ev == '設定':
                if th != False:
                    self.stop_thread = True
                    th.join()
                    del th
                    th = False
                    self.window['is_active'].update('')
                    self.window['live_title'].update('')
                self.gui_settings()
            elif ev == '管理者IDに追加':
                if len(val['table_comment']) > 0:
                    tmp = self.table_comment[val['table_comment'][0]]
                    key = f"{tmp[0]}({tmp[3]})"
                    if key not in self.settings.manager:
                        self.settings.manager.append(key)
                        sg.popup(f"{tmp[0]}を管理者IDに追加しました。")
                    else:
                        sg.popup(f"{tmp[0]}は既に管理者に追加されています。")
                else:
                    sg.popup(f"コメントが選択されていません。")
            elif ev == 'btn_add_push':
                if val['input_trigger'] != "" and val['input_trigger'] not in self.settings.pushword:
                    self.settings.pushword.append(val['input_trigger'])
                    self.window['list_push'].update(self.settings.pushword)
            elif ev == 'btn_add_pull':
                if val['input_trigger'] != "" and val['input_trigger'] not in self.settings.pullword:
                    self.settings.pullword.append(val['input_trigger'])
                    self.window['list_pull'].update(self.settings.pullword)
            elif ev == 'btn_add_req':
                if val['input_req'] != "" and val['input_req'] not in self.settings.req:
                    #self.settings.req.append(f"{len(self.settings.req)}: {val['input_req'].strip()}")
                    self.settings.req.append(f"{val['input_req'].strip()}")
                    self.window['list_req'].update(self.settings.req)
                    self.window['input_req'].update('')
                    self.gen_xml()
            elif ev == 'btn_delete_push':
                if len(val['list_push']) > 0:
                    self.settings.pushword.pop(self.settings.pushword.index(val['list_push'][0]))
                    self.window['list_push'].update(self.settings.pushword)
            elif ev == 'btn_delete_pull':
                if len(val['list_pull']) > 0:
                    self.settings.pullword.pop(self.settings.pullword.index(val['list_pull'][0]))
                    self.window['list_pull'].update(self.settings.pullword)
            elif ev == 'btn_delete_manager':
                if len(val['list_manager']) > 0:
                    self.settings.manager.pop(self.settings.manager.index(val['list_manager'][0]))
                    self.window['list_manager'].update(self.settings.manager)
            elif ev == 'btn_delete_req':
                if len(val['list_req']) > 0:
                    self.settings.req.pop(self.settings.req.index(val['list_req'][0]))
                    self.window['list_req'].update(self.settings.req)
                    self.gen_xml()
            elif ev == 'btn_reset_req':
                self.settings.req = []
                self.window['list_req'].update(self.settings.req)
                self.gen_xml()


a = GetComment()
a.main()
