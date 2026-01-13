#!/usr/bin/python3
import obsws_python as obsws
#import base64
import numpy as np
from PIL import Image
import traceback, os, io
import logging, logging.handlers
import base64

os.makedirs('log', exist_ok=True)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
hdl = logging.handlers.RotatingFileHandler(
    f'log/{os.path.basename(__file__).split(".")[0]}.log',
    encoding='utf-8',
    maxBytes=1024*1024*2,
    backupCount=1,
)
hdl.setLevel(logging.DEBUG)
hdl_formatter = logging.Formatter('%(asctime)s %(filename)s:%(lineno)5d %(funcName)s() [%(levelname)s] %(message)s')
hdl.setFormatter(hdl_formatter)
logger.addHandler(hdl)

class OBSSocket():
    def __init__(self,hostIP,portNum,passWord,inf_source=None,dst_screenshot=None):
        self.host = hostIP
        self.port = portNum
        self.passwd = passWord
        self.picw=1920
        self.pich=1080
        self.inf_source = inf_source
        self.dst_screenshot = dst_screenshot
        self.ws = None
        self.ev = None
        self.active = False
        
        try:
            self.ws = obsws.ReqClient(host=self.host,port=self.port,password=self.passwd)
            self.active = True
            self.ev = obsws.EventClient(host=self.host,port=self.port,password=self.passwd)
            self.ev.callback.register([self.on_exit_started,])
            logger.debug(f'OBS connected - host:{self.host}, port:{self.port}')
        except ConnectionRefusedError as e:
            logger.warning(f'OBS connection refused - OBS may not be running or WebSocket not enabled: {e}')
            raise  # 例外を再発生させて、呼び出し元でキャッチできるようにする
        except Exception as e:
            logger.error(f'OBS connection failed: {e}')
            logger.debug(traceback.format_exc())
            raise  # 例外を再発生させて、呼び出し元でキャッチできるようにする

    def close(self):
        try:
            if self.ws:
                del self.ws
            if self.ev:
                self.ev.unsubscribe()
                del self.ev
            return True
        except Exception:
            logger.debug(traceback.format_exc())
            return False

    def change_scene(self,name:str):
        if not self.ws:
            return False
        try:
            self.ws.set_current_program_scene(name)
            return True
        except Exception:
            logger.debug(traceback.format_exc())
            return False

    def get_scenes(self):
        if not self.ws:
            return []
        try:
            res = self.ws.get_scene_list()
            ret = res.scenes
            return res.scenes
        except Exception:
            logger.debug(traceback.format_exc())
            return []

    def get_sources(self, scene):
        if not self.ws:
            return []
        ret = []
        try:
            allitem = self.ws.get_scene_item_list(scene).scene_items
            for x in allitem:
                if x['isGroup']:
                    grp = self.ws.get_group_scene_item_list(x['sourceName']).scene_items
                    for y in grp:
                        ret.append(y['sourceName'])
                ret.append(x['sourceName'])
        except Exception:
            logger.debug(traceback.format_exc())
        ret.reverse()
        return ret

    def change_text(self, source, text):
        if not self.ws:
            return False
        try:
            logger.debug(source, text)
            res = self.ws.set_input_settings(source, {'text':text}, True)
            return True
        except Exception:
            logger.debug(traceback.format_exc())
            return False
    
    def set_text_gdi_plus_properties(self, source, text):
        """GDI+テキストソースのテキストを設定（change_textのエイリアス）"""
        return self.change_text(source, text)

    def save_screenshot(self):
        if not self.ws:
            return False
        #logger.debug(f'dst:{self.dst_screenshot}')
        try:
            res = self.ws.save_source_screenshot(self.inf_source, 'png', self.dst_screenshot, self.picw, self.pich, 100)
            return res
        except Exception:
            logger.debug(traceback.format_exc())
            return False

    def save_screenshot_dst(self, dst):
        if not self.ws:
            return False
        try:
            res = self.ws.save_source_screenshot(self.inf_source, 'png', dst, self.picw, self.pich, 100)
            return res
        except Exception:
            logger.debug(traceback.format_exc())
            return False

    # 設定されたソースを取得し、PIL.Image形式で返す
    def get_screenshot(self):
        if not self.ws:
            return None
        try:
            b = self.ws.get_source_screenshot(self.inf_source, 'jpeg', self.picw, self.pich, 100).image_data
            b = b.split(',')[1]
            c = base64.b64decode(b) # バイナリ形式のはず？
            tmp = io.BytesIO(c)
            img = Image.open(tmp)
            return img
        except Exception:
            logger.debug(traceback.format_exc())
            return None

    def enable_source(self, scenename, sourceid): # グループ内のitemはscenenameにグループ名を指定する必要があるので注意
        if not self.ws:
            return False
        try:
            res = self.ws.set_scene_item_enabled(scenename, sourceid, enabled=True)
            return True
        except Exception as e:
            logger.debug(traceback.format_exc())
            return False

    def disable_source(self, scenename, sourceid):
        if not self.ws:
            return False
        try:
            res = self.ws.set_scene_item_enabled(scenename, sourceid, enabled=False)
            return True
        except Exception as e:
            logger.debug(traceback.format_exc())
            return False
        
    def refresh_source(self, sourcename):
        if not self.ws:
            return False
        try:
            self.ws.press_input_properties_button(sourcename, 'refreshnocache')
            return True
        except Exception:
            logger.debug(traceback.format_exc())
            return False

    def on_exit_started(self, _):
        print("OBS closing!")
        self.active = False
        if self.ev:
            self.ev.unsubscribe()

    def search_itemid(self, scene, target):
        if not self.ws:
            return scene, None
        ret = scene, None # グループ名, ID
        try:
            allitem = self.ws.get_scene_item_list(scene).scene_items
            for x in allitem:
                if x['sourceName'] == target:
                    ret = scene, x['sceneItemId']
                if x['isGroup']:
                    grp = self.ws.get_group_scene_item_list(x['sourceName']).scene_items
                    for y in grp:
                        if y['sourceName'] == target:
                            ret = x['sourceName'], y['sceneItemId']

        except:
            pass
        return ret
    
    def get_scene_collection_list(self):
        """OBSに設定されたシーンコレクションの一覧をListで返す

        Returns:
            list: シーンコレクション名の文字列
        """
        if not self.ws:
            return []
        try:
            return self.ws.get_scene_collection_list().scene_collections
        except Exception:
            logger.debug(traceback.format_exc())
            return []
        
    def set_scene_collection(self, scene_collection:str):
        """シーンコレクションを引数で指定したものに変更する。

        Args:
            scene_collection (str): シーンコレクション名

        Returns:
            bool: 成功ならTrue,失敗したらFalse
        """
        if not self.ws:
            return False
        try:
            self.ws.set_current_scene_collection(scene_collection)
            return True
        except Exception:
            logger.debug(traceback.format_exc())
            return False

if __name__ == "__main__":
    #a = OBSSocket('localhost', '4455', 'panipaninoakuma','たぬきお休み.png','tmp.png')
    #a.save_screenshot('メインモニタ', 'png', 'C:\\Users\\katao\\OneDrive\\デスクトップ\\hoge.png')
    #tmp = a.get_screenshot('メインモニタ', 'png')
    #print(a.search_itemid('2. DP_NEW', 'history_cursong'))
    #for i in range(100):
    #    img = a.get_screenshot()# image_data # base64文字列
    #img.save('tmp.png')
    a = OBSSocket('localhost', '4455', 'panipaninoakuma','ゲーム画面_FHD','tmp.png')
    a.picw=2560
    a.pich=1440
    b = a.get_screenshot()
    b.save('tmp.png')
    #print(a.search_itemid('6. SDVX', 'sdvx_stats_v2.html'))
    print(a.search_itemid('縦画面設定テスト', 'sdvx_stats_v2.html (2)'))