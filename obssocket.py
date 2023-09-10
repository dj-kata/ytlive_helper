#!/usr/bin/python3
import obsws_python as obsws

class OBSSocket():
    def __init__(self,hostIP,portNum,passWord):
        self.host = hostIP
        self.port = portNum
        self.passwd = passWord
        self.ws = obsws.ReqClient(host=self.host,port=self.port,password=self.passwd)
        self.active = True
        self.ev = obsws.EventClient(host=self.host,port=self.port,password=self.passwd)
        self.ev.callback.register([self.on_exit_started,])

    def close(self):
        del self.ws

    def change_scene(self,name:str):
        self.ws.set_current_program_scene(name)

    def get_scenes(self):
        res = self.ws.get_scene_list()
        print(res.scenes)

    def change_text(self, source, text):
        try:
            res = self.ws.set_input_settings(source, {'text':text}, True)
            return True
        except Exception:
            return False

    def enable_source(self, scenename, sourceid): # グループ内のitemはscenenameにグループ名を指定する必要があるので注意
        try:
            res = self.ws.set_scene_item_enabled(scenename, sourceid, enabled=True)
        except Exception as e:
            return e

    def disable_source(self, scenename, sourceid):
        try:
            res = self.ws.set_scene_item_enabled(scenename, sourceid, enabled=False)
        except Exception as e:
            return e
        
    def refresh_source(self, sourcename):
        try:
            self.obs.ws.press_input_properties_button(sourcename, 'refreshnocache')
        except Exception:
            pass

    def on_exit_started(self, _):
        print("OBS closing!")
        self.active = False
        self.ev.unsubscribe()

    def search_itemid(self, scene, target):
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
