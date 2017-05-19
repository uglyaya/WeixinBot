#!/usr/bin/env python
# coding: utf-8
import qrcode
from pyqrcode import QRCode
import urllib 
import http.cookiejar
import requests
import xml.dom.minidom
import json
import time
import ssl
import re
import sys
import os
import subprocess
import random
import multiprocessing
import platform
import logging
import datetime
from collections import defaultdict
from urllib.parse import urlparse
from lxml import html
from socket import timeout as timeout_error
import hashlib,shutil
from urllib.request import urlopen, urlretrieve 
import qrcode_terminal
#import pdb

# for media upload
import mimetypes
from requests_toolbelt.multipart.encoder import MultipartEncoder
from baseHandler import BaseHandler

def catchKeyboardInterrupt(fn):
    def wrapper(*args):
        try:
            return fn(*args)
        except KeyboardInterrupt:
            print('\n[*] 强制退出程序')
            logging.debug('[*] 强制退出程序')
    return wrapper


def _decode_list(data):
    rv = []
    for item in data:
        if isinstance(item, str):
            item = item.encode('utf-8')
        elif isinstance(item, list):
            item = _decode_list(item)
        elif isinstance(item, dict):
            item = _decode_dict(item)
        rv.append(item)
    return rv


def _decode_dict(data):
    rv = {}
    for key, value in data.items():
        if isinstance(key, str):
            key = key.encode('utf-8')
        if isinstance(value, str):
            value = value.encode('utf-8')
        elif isinstance(value, list):
            value = _decode_list(value)
        elif isinstance(value, dict):
            value = _decode_dict(value)
        rv[key] = value
    return rv


class WebWeixin(object):

    def __str__(self):
        description = \
            "=========================\n" + \
            "[#] Web Weixin\n" + \
            "[#] Debug Mode: " + str(self.DEBUG) + "\n" + \
            "[#] Uuid: " + self.uuid + "\n" + \
            "[#] Uin: " + str(self.uin) + "\n" + \
            "[#] Sid: " + self.sid + "\n" + \
            "[#] Skey: " + self.skey + "\n" + \
            "[#] DeviceId: " + self.deviceId + "\n" + \
            "[#] PassTicket: " + self.pass_ticket + "\n" + \
            "========================="
        return description

    def __init__(self,handler):
        self.handler = handler
        self.DEBUG = True
        self.commandLineQRCode = False
        self.uuid = ''
        self.base_uri = ''
        self.redirect_uri = ''
        self.uin = ''
        self.sid = ''
        self.skey = ''
        self.pass_ticket = ''
        self.deviceId = 'e' + repr(random.random())[2:17]
        self.BaseRequest = {}
        self.synckey = ''
        self.SyncKey = []
        self.User = []
        self.MemberList = []
        self.ContactList = []  # 好友
        self.GroupList = []  # 群
        self.GroupMemeberList = []  # 群友
        self.GroupMemeberDict = {}  # 群友,按照群id的字典  id->memberlist(dict)
        self.PublicUsersList = []  # 公众号／服务号
        self.SpecialUsersList = []  # 特殊账号
        self.autoReplyMode = False
        self.syncHost = ''
        self.user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/48.0.2564.109 Safari/537.36'
        self.interactive = False
        self.autoOpen = False
        self.saveFolder = os.path.join(os.getcwd(), 'saved')
        self.saveSubFolders = {'webwxgeticon': 'icons', 'webwxgetheadimg': 'headimgs', 'webwxgetmsgimg': 'msgimgs',
                               'webwxgetvideo': 'videos', 'webwxgetvoice': 'voices', '_showQRCodeImg': 'qrcodes'}
        self.appid = 'wx782c26e4c19acffb'
        self.lang = 'zh_CN'
        self.lastCheckTs = time.time()
        self.memberCount = 0
        self.SpecialUsers = ['newsapp', 'fmessage', 'filehelper', 'weibo', 'qqmail', 'fmessage', 'tmessage', 'qmessage', 'qqsync', 'floatbottle', 'lbsapp', 'shakeapp', 'medianote', 'qqfriend', 'readerapp', 'blogapp', 'facebookapp', 'masssendapp', 'meishiapp', 'feedsapp',
                             'voip', 'blogappweixin', 'weixin', 'brandsessionholder', 'weixinreminder', 'wxid_novlwrv3lqwv11', 'gh_22b87fa7cb3c', 'officialaccounts', 'notification_messages', 'wxid_novlwrv3lqwv11', 'gh_22b87fa7cb3c', 'wxitil', 'userexperience_alarm', 'notification_messages']
        self.TimeOut = 20  # 同步最短时间间隔（单位：秒）
        self.media_count = -1
        self.msgCount = 0 #这是本次启动的第几条消息
        self.cookie = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cookie))
        opener.addheaders = [('User-agent', self.user_agent)]
        urllib.request.install_opener(opener)


    def _safe_open(self, path):
        if self.autoOpen:
            if platform.system() == "Linux":
                os.system("xdg-open %s &" % path)
            else:
                os.system('open %s &' % path)

    def _run(self, str, func, *args):
        self._echo(str)
        if func(*args):
            print('成功')
            logging.debug('%s... 成功' % (str))
        else:
            print('失败\n[*] 退出程序')
            logging.debug('%s... 失败' % (str))
            logging.debug('[*] 退出程序')
            exit()

    def _echo(self, str):
        sys.stdout.write(str)
        sys.stdout.flush()

    def _printQR(self, mat):
        for i in mat:
            BLACK = '\033[40m  \033[0m'
            WHITE = '\033[47m  \033[0m'
            print(''.join([BLACK if j else WHITE for j in i]))

    def _str2qr(self, str):
        print(str)
        qrcode_terminal.draw(str)

#         qr = qrcode.QRCode()
#         qr.border = 1
#         qr.add_data(str)
#         qr.make()
        # img = qr.make_image()
        # img.save("qrcode.png")
        #mat = qr.get_matrix()
        #self._printQR(mat)  # qr.print_tty() or qr.print_ascii()
#         qr.print_ascii(invert=True)

    def _transcoding(self, data):
        if not data:
            return data
        result = None
        if type(data) == str:
            result = data
        elif type(data) == str:
            result = data.decode('utf-8')
        return result

    def _get(self, url: object, api: object = None, timeout: object = None) -> object:
        request = urllib.request.Request(url=url)
        request.add_header('Referer', 'https://wx.qq.com/')
        if api == 'webwxgetvoice':
            request.add_header('Range', 'bytes=0-')
        if api == 'webwxgetvideo':
            request.add_header('Range', 'bytes=0-')
        try:
            response = urllib.request.urlopen(request, timeout=timeout) if timeout else urllib.request.urlopen(request)
            data = response.read().decode('utf-8')
            logging.debug(url)
            return data
        except urllib.error.HTTPError as e:
            logging.error('HTTPError = ' + str(e.code))
        except urllib.error.URLError as e:
            logging.error('URLError = ' + str(e.reason)) 
        except timeout_error as e:
            pass
        except ssl.CertificateError as e:
            pass
        except Exception:
            import traceback
            logging.error('generic exception: ' + traceback.format_exc())
        return ''

    def _post(self, url: object, params: object, jsonfmt: object = True) -> object:
        if jsonfmt:
            data = (json.dumps(params)).encode()
            
            request = urllib.request.Request(url=url, data=data)
            request.add_header(
                'ContentType', 'application/json; charset=UTF-8')
        else:
            request = urllib.request.Request(url=url, data=urllib.parse.urlencode(params).encode(encoding='utf-8'))

        try:
            response = urllib.request.urlopen(request)
            data = response.read()
            if jsonfmt:
                return json.loads(data.decode('utf-8') )#object_hook=_decode_dict)
            return data
        except urllib.error.HTTPError as e:
            logging.error('HTTPError = ' + str(e.code))
        except urllib.error.URLError as e:
            logging.error('URLError = ' + str(e.reason)) 
        except Exception:
            import traceback
            logging.error('generic exception: ' + traceback.format_exc())
        return ''

    def loadConfig(self, config):
        if config['DEBUG']:
            self.DEBUG = config['DEBUG']
        if config['autoReplyMode']:
            self.autoReplyMode = config['autoReplyMode']
        if config['user_agent']:
            self.user_agent = config['user_agent']
        if config['interactive']:
            self.interactive = config['interactive']
        if config['autoOpen']:
            self.autoOpen = config['autoOpen']

    def getUUID(self):
        url = 'https://login.weixin.qq.com/jslogin'
        params = {
            'appid': self.appid,
            'fun': 'new',
            'lang': self.lang,
            '_': int(time.time()),
        }
        #r = requests.get(url=url, params=params)
        #r.encoding = 'utf-8'
        #data = r.text
        data = self._post(url, params, False).decode("utf-8")
        if data == '':
            return False
        regx = r'window.QRLogin.code = (\d+); window.QRLogin.uuid = "(\S+?)"'
        pm = re.search(regx, data)
        if pm:
            code = pm.group(1)
            self.uuid = pm.group(2)
            return code == '200'
        return False

    def genQRCode(self):
        #return self._showQRCodeImg()
        if sys.platform.startswith('win'):
            self._showQRCodeImg('win')
        elif sys.platform.find('darwin') >= 0:
            self._showQRCodeImg('macos')
        else:
            self._str2qr('https://login.weixin.qq.com/l/' + self.uuid)

    def _showQRCodeImg(self, str):
        if self.commandLineQRCode:
            qrCode = QRCode('https://login.weixin.qq.com/l/' + self.uuid)
            self._showCommandLineQRCode(qrCode.text(1))
        else:
            url = 'https://login.weixin.qq.com/qrcode/' + self.uuid
            params = {
                't': 'webwx',
                '_': int(time.time())
            }

            data = self._post(url, params, False)
            if data == '':
                return
            QRCODE_PATH = self._saveFile('qrcode.jpg', data, '_showQRCodeImg')
            if str == 'win':
                os.startfile(QRCODE_PATH)
            elif str == 'macos':
                subprocess.call(["open", QRCODE_PATH])
            else:
                return

    def _showCommandLineQRCode(self, qr_data, enableCmdQR=2):
        try:
            b = u'\u2588'
            sys.stdout.write(b + '\r')
            sys.stdout.flush()
        except UnicodeEncodeError:
            white = 'MM'
        else:
            white = b
        black = '  '
        blockCount = int(enableCmdQR)
        if abs(blockCount) == 0:
            blockCount = 1
        white *= abs(blockCount)
        if blockCount < 0:
            white, black = black, white
        sys.stdout.write(' ' * 50 + '\r')
        sys.stdout.flush()
        qr = qr_data.replace('0', white).replace('1', black)
        sys.stdout.write(qr)
        sys.stdout.flush()
    
    def _saveFile(self, filename, data, api=None):
        fn = filename
        if self.saveSubFolders[api]:
            dirName = os.path.join(self.saveFolder, self.saveSubFolders[api])
            if not os.path.exists(dirName):
                os.makedirs(dirName)
            fn = os.path.join(dirName, filename)
            logging.debug('Saved file: %s' % fn)
            with open(fn, 'wb') as f:
                f.write(data)
                f.close()
        return fn
    #---------------------- 以下是weixin 的对外api接口
    #
    #
    #
    #--------------------------------------------------
    def waitForLogin(self, tip=1):
        time.sleep(tip)
        url = 'https://login.weixin.qq.com/cgi-bin/mmwebwx-bin/login?tip=%s&uuid=%s&_=%s' % (
            tip, self.uuid, int(time.time()))
        data = self._get(url)
        if data == '':
            return False
        pm = re.search(r"window.code=(\d+);", data)
        code = pm.group(1)

        if code == '201':
            return True
        elif code == '200':
            pm = re.search(r'window.redirect_uri="(\S+?)";', data)
            r_uri = pm.group(1) + '&fun=new'
            self.redirect_uri = r_uri
            self.base_uri = r_uri[:r_uri.rfind('/')]
            return True
        elif code == '408':
            self._echo('[登陆超时] \n')
        else:
            self._echo('[登陆异常] \n')
        return False

    def login(self):
        data = self._get(self.redirect_uri)
        if data == '':
            return False
        doc = xml.dom.minidom.parseString(data)
        root = doc.documentElement

        for node in root.childNodes:
            if node.nodeName == 'skey':
                self.skey = node.childNodes[0].data
            elif node.nodeName == 'wxsid':
                self.sid = node.childNodes[0].data
            elif node.nodeName == 'wxuin':
                self.uin = node.childNodes[0].data
            elif node.nodeName == 'pass_ticket':
                self.pass_ticket = node.childNodes[0].data

        if '' in (self.skey, self.sid, self.uin, self.pass_ticket):
            return False

        self.BaseRequest = {
            'Uin': int(self.uin),
            'Sid': self.sid,
            'Skey': self.skey,
            'DeviceID': self.deviceId,
        }
        return True

    def webwxinit(self):
        url = self.base_uri + '/webwxinit?pass_ticket=%s&skey=%s&r=%s' % (
            self.pass_ticket, self.skey, int(time.time()))
        params = {
            'BaseRequest': self.BaseRequest
        }
        dic = self._post(url, params)
        if dic == '':
            return False
        self.SyncKey = dic['SyncKey']
        self.User = dic['User']
        # synckey for synccheck
        self.synckey = '|'.join(
            [str(keyVal['Key']) + '_' + str(keyVal['Val']) for keyVal in self.SyncKey['List']])

        return dic['BaseResponse']['Ret'] == 0

    def api_webwxstatusnotify(self):
        url = self.base_uri + \
            '/webwxstatusnotify?lang=zh_CN&pass_ticket=%s' % (self.pass_ticket)
        params = {
            'BaseRequest': self.BaseRequest,
            "Code": 3,
            "FromUserName": self.User['UserName'],
            "ToUserName": self.User['UserName'],
            "ClientMsgId": int(time.time())
        }
        dic = self._post(url, params)
        if dic == '':
            return False

        return dic['BaseResponse']['Ret'] == 0

    #获取联系人
    def api_webwxgetcontact(self):
        SpecialUsers = self.SpecialUsers
        url = self.base_uri + '/webwxgetcontact?pass_ticket=%s&skey=%s&r=%s' % (
            self.pass_ticket, self.skey, int(time.time()))
        dic = self._post(url, {})
        if dic == '':
            return False

        self.MemberCount = dic['MemberCount']
        self.MemberList = dic['MemberList']
        ContactList = self.MemberList[:]
        GroupList = self.GroupList[:]
        PublicUsersList = self.PublicUsersList[:]
        SpecialUsersList = self.SpecialUsersList[:]

        for i in range(len(ContactList) - 1, -1, -1):
            Contact = ContactList[i]
            if Contact['VerifyFlag'] & 8 != 0:  # 公众号/服务号
                ContactList.remove(Contact)
                self.PublicUsersList.append(Contact)
            elif Contact['UserName'] in SpecialUsers:  # 特殊账号
                ContactList.remove(Contact)
                self.SpecialUsersList.append(Contact)
            elif '@@' in Contact['UserName']:  # 群聊
                ContactList.remove(Contact)
                self.GroupList.append(Contact)
            elif Contact['UserName'] == self.User['UserName']:  # 自己
                ContactList.remove(Contact)
        self.ContactList = ContactList

        return True

    #获取群联系人信息
    def api_webwxbatchgetcontact(self):
        url = self.base_uri + \
            '/webwxbatchgetcontact?type=ex&r=%s&pass_ticket=%s' % (
                int(time.time()), self.pass_ticket)
        params = {
            'BaseRequest': self.BaseRequest,
            "Count": len(self.GroupList),
            "List": [{"UserName": g['UserName'], "EncryChatRoomId":""} for g in self.GroupList]
        }
        dic = self._post(url, params)
        if dic == '':
            return False
 
        ContactList = dic['ContactList']
        ContactCount = dic['Count']
        self.GroupList = ContactList

        for i in range(len(ContactList) - 1, -1, -1):
            group = ContactList[i]
            MemberList = group['MemberList']
            for member in MemberList:
                self.GroupMemeberList.append(member)
            self.GroupMemeberDict[group['UserName']] = MemberList
        return True

    #根据一个聊天室id，获取该聊天室的信息。返回dict
    def getGroupInfoById(self, id):
        url = self.base_uri + \
            '/webwxbatchgetcontact?type=ex&r=%s&pass_ticket=%s' % (
                int(time.time()), self.pass_ticket)
        params = {
            'BaseRequest': self.BaseRequest,
            "Count": 1,
            "List": [{"UserName": id, "EncryChatRoomId": ""}]
        }
        dic = self._post(url, params)
        if dic == '' or len(dic['ContactList'] )==0:
            return None
        return dic['ContactList'][0]

    #检测线路情况。找一个通的链路
    def testsynccheck(self):
        SyncHost = [
                    'wx.qq.com',
                    'wx2.qq.com',
                    'webpush.wx2.qq.com',
                    'wx8.qq.com',
                    'webpush.wx8.qq.com',
                    'qq.com',
                    'webpush.wx.qq.com',
                    'web2.wechat.com',
                    'webpush.web2.wechat.com',
                    'wechat.com',
                    'webpush.web.wechat.com',
                    'webpush.weixin.qq.com',
                    'webpush.wechat.com',
                    'webpush1.wechat.com',
                    'webpush2.wechat.com',
                    'webpush.wx.qq.com',
                    'webpush2.wx.qq.com']
        for host in SyncHost:
            self.syncHost = host
            [retcode, selector] = self.api_synccheck()
            if retcode == '0':
                return True
        return False

    #同步检测心跳
    def api_synccheck(self):
        params = {
            'r': int(time.time()),
            'sid': self.sid,
            'uin': self.uin,
            'skey': self.skey,
            'deviceid': self.deviceId,
            'synckey': self.synckey,
            '_': int(time.time()),
        }
        url = 'https://' + self.syncHost + '/cgi-bin/mmwebwx-bin/synccheck?' + urllib.parse.urlencode(params)
        data = self._get(url, timeout=5)
        if data == '':
            return [-1,-1]

        pm = re.search(
            r'window.synccheck={retcode:"(\d+)",selector:"(\d+)"}', data)
        retcode = pm.group(1)
        selector = pm.group(2)
        return [retcode, selector]

    #从服务器拉取最新的一条msg
    def api_webwxsync(self):
        url = self.base_uri + \
            '/webwxsync?sid=%s&skey=%s&pass_ticket=%s' % (
                self.sid, self.skey, self.pass_ticket)
        params = {
            'BaseRequest': self.BaseRequest,
            'SyncKey': self.SyncKey,
            'rr': ~int(time.time())
        }
        dic = self._post(url, params)
        if dic == '':
            return None
        
#         if self.DEBUG:
#             print(json.dumps(dic, indent=4))
#             (json.dumps(dic, indent=4))

        if dic['BaseResponse']['Ret'] == 0:
            self.SyncKey = dic['SyncKey']
            self.synckey = '|'.join(
                [str(keyVal['Key']) + '_' + str(keyVal['Val']) for keyVal in self.SyncKey['List']])
        return dic

    #发送消息
    def api_webwxsendmsg(self, word, to='filehelper'):
        #return 1204 : 自己发给自己的错误，如果发送方是短id，那么可以成功。如果是长id，返回1204
        url = self.base_uri + \
            '/webwxsendmsg?pass_ticket=%s' % (self.pass_ticket)
        clientMsgId = str(int(time.time() * 1000)) + \
            str(random.random())[:5].replace('.', '')
        params = {
            'BaseRequest': self.BaseRequest,
            'Msg': {
                "Type": 1,
                "Content": self._transcoding(word),
                "FromUserName": self.User['UserName'],
                "ToUserName": to,
                "LocalID": clientMsgId,
                "ClientMsgId": clientMsgId
            }
        }
        headers = {'content-type': 'application/json; charset=UTF-8'}
        data = json.dumps(params, ensure_ascii=False).encode('utf8')
        r = requests.post(url, data=data, headers=headers)
        dic = r.json()
        return dic['BaseResponse']['Ret'] == 0
    

    #聊天室改名
    def api_webwxupdatechatroomModifyTopic(self,groupid, topic):
        url = self.base_uri + \
            '/webwxupdatechatroom?fun=modtopic&lang=zh_CN&pass_ticket=%s' % ( self.pass_ticket)
        params = {
            'BaseRequest': self.BaseRequest,
            'ChatRoomName': groupid, 
            'NewTopic': topic,  
        }
        dic = self._post(url, params)
        return dic['BaseResponse']['Ret'] == 0
    
    #聊天室踢人 del_arr 数组
    def api_webwxupdatechatroomDelMember(self, groupid,del_arr):
        url = self.base_uri + \
            '/webwxupdatechatroom?fun=delmember&lang=zh_CN&pass_ticket=%s' % ( self.pass_ticket)
        params = {
            'BaseRequest': self.BaseRequest,
            'ChatRoomName': groupid, 
            'DelMemberList':  ",".join(del_arr),  #用户id，逗号分割
        }
        dic = self._post(url, params)
        return dic['BaseResponse']['Ret'] == 0
    
    #聊天室加人 add_arr 数组
    def api_webwxupdatechatroomAddMember(self, groupid,add_arr):
        url = self.base_uri + \
            '/webwxupdatechatroom?fun=addmember&lang=zh_CN&pass_ticket=%s' % ( self.pass_ticket)
        params = {
            'BaseRequest': self.BaseRequest,
            'ChatRoomName': groupid, 
            'AddMemberList': ",".join(add_arr),  #用户id，逗号分割
        }
        dic = self._post(url, params)
        return dic['BaseResponse']['Ret'] == 0
    
    #创建聊天室
    def api_webwxcreatechatroom(self,uids,topic =''):  
        #创建聊天室会出现频繁过快明天再试的情况。
        uids = [uid for uid in uids if uid != self.User['UserName']]#uids 里面不能包含自己
        url = self.base_uri + \
            '/webwxcreatechatroom?r=%s&pass_ticket=%s' % (
                int(time.time()), self.pass_ticket)
        params = { 
            "BaseRequest": self.BaseRequest,
            "MemberCount": len(uids),
            "MemberList": [{"UserName": uid } for uid in uids  ],
            "Topic": topic,
        }
        headers = {'content-type': 'application/json; charset=UTF-8'}
        data = json.dumps(params, ensure_ascii=False).encode('utf8')
        r = requests.post(url, data=data, headers=headers)
        dic = r.json() 
        groupid = ''
        if dic['BaseResponse']['Ret'] == 0 :
            groupid = dic['ChatRoomName']
            if groupid :
                self.getGroupNameById(groupid) #新的id也顺便刷新一下
        return groupid
    
    #上传文件获取media_id
    def api_webwxuploadmedia(self, image_name,fromUserName,toUserName):
        url = 'https://file.wx.qq.com/cgi-bin/mmwebwx-bin/webwxuploadmedia?f=json'
        # 计数器
        self.media_count = self.media_count + 1
        # 文件名
        file_name = image_name
        # MIME格式
        # mime_type = application/pdf, image/jpeg, image/png, etc.
        mime_type = mimetypes.guess_type(image_name, strict=False)[0]
        # 微信识别的文档格式，微信服务器应该只支持两种类型的格式。pic和doc
        # pic格式，直接显示。doc格式则显示为文件。
        media_type = 'pic' if mime_type.split('/')[0] == 'image' else 'doc'
        # 上一次修改日期
        lastModifieDate = 'Thu Mar 17 2016 00:55:10 GMT+0800 (CST)'
        # 文件大小
        file_size = os.path.getsize(file_name)
        # PassTicket
        pass_ticket = self.pass_ticket
        # clientMediaId
        client_media_id = str(int(time.time() * 1000)) + \
            str(random.random())[:5].replace('.', '')
        # webwx_data_ticket
        webwx_data_ticket = ''
        for item in self.cookie:
            if item.name == 'webwx_data_ticket':
                webwx_data_ticket = item.value
                break
        if (webwx_data_ticket == ''):
            return "None Fuck Cookie"
        
        f = open(image_name,'rb') 
        md5obj = hashlib.md5()
        md5obj.update(f.read())
        filemd5 = md5obj.hexdigest()
        
        uploadmediarequest = json.dumps({
            "UploadType":2,
            "BaseRequest": self.BaseRequest,
            "ClientMediaId": client_media_id,
            "TotalLen": file_size,
            "StartPos": 0,
            "DataLen": file_size,
            "MediaType": 4,
            "FromUserName":fromUserName,
            "ToUserName":toUserName,
            "FileMd5":filemd5,
        }, ensure_ascii=False).encode('utf8')

        multipart_encoder = MultipartEncoder(
            fields={
                'id': 'WU_FILE_' + str(self.media_count),
                'name': file_name,
                'type': mime_type,
                'lastModifieDate': lastModifieDate,
                'size': str(file_size),
                'mediatype': media_type,
                'uploadmediarequest': uploadmediarequest,
                'webwx_data_ticket': webwx_data_ticket,
                'pass_ticket': pass_ticket,
                'filename': (file_name, open(file_name, 'rb'), mime_type.split('/')[1])
            },
            boundary='-----------------------------1575017231431605357584454111'
        )

        headers = {
            'Host': 'file.wx.qq.com',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.10; rv:42.0) Gecko/20100101 Firefox/42.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Referer': 'https://wx.qq.com/',
            'Content-Type': multipart_encoder.content_type,
            'Origin': 'https://wx.qq.com',
            'Connection': 'keep-alive',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache'
        }

        r = requests.post(url, data=multipart_encoder, headers=headers)
        response_json = r.json()
        if response_json['BaseResponse']['Ret'] == 0:
            return response_json
        return None

    #发送一张已经上传的图片给某人。
    def api_webwxsendmsgimg(self, user_id, media_id):
        url = 'https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxsendmsgimg?fun=async&f=json&pass_ticket=%s' % self.pass_ticket
        clientMsgId = str(int(time.time() * 1000)) + \
            str(random.random())[:5].replace('.', '')
        data_json = {
            "BaseRequest": self.BaseRequest,
            "Msg": {
                "Type": 3,
                "MediaId": media_id,
                "FromUserName": self.User['UserName'],
                "ToUserName": user_id,
                "LocalID": clientMsgId,
                "ClientMsgId": clientMsgId
            }
        }
        headers = {'content-type': 'application/json; charset=UTF-8'}
        data = json.dumps(data_json, ensure_ascii=False).encode('utf8')
        r = requests.post(url, data=data, headers=headers)
        dic = r.json()
        return dic['BaseResponse']['Ret'] == 0

    #给用户发一张图片，把上传图片和发送图片的方法给合成了
    def api_webwxsendmsgimgBy2in1(self,fromUserName,toUserName, image_name):
        filename = image_name
        if 'http://' in image_name :
            sufix = os.path.splitext(image_name)[1][1:]
            md5 = hashlib.md5(image_name.encode('utf8')).hexdigest()
            filename = './upload/%s.%s'%(md5,sufix)
            urlretrieve(image_name, filename)  

        result = self.api_webwxuploadmedia(filename,fromUserName,toUserName)
        if not result :
            return False
        else:
            media_id = result['MediaId']
            return self.api_webwxsendmsgimg(toUserName, media_id)
        
    #发送既定表情
    def api_webwxsendmsgemotion(self, user_id, media_id):
        url = 'https://wx2.qq.com/cgi-bin/mmwebwx-bin/webwxsendemoticon?fun=sys&f=json&pass_ticket=%s' % self.pass_ticket
        clientMsgId = str(int(time.time() * 1000)) + \
            str(random.random())[:5].replace('.', '')
        data_json = {
            "BaseRequest": self.BaseRequest,
            "Msg": {
                "Type": 47,
                "EmojiFlag": 2,
                "MediaId": media_id,
                "FromUserName": self.User['UserName'],
                "ToUserName": user_id,
                "LocalID": clientMsgId,
                "ClientMsgId": clientMsgId
            }
        }
        headers = {'content-type': 'application/json; charset=UTF-8'}
        data = json.dumps(data_json, ensure_ascii=False).encode('utf8')
        r = requests.post(url, data=data, headers=headers)
        dic = r.json()
#         if self.DEBUG:
#             print(json.dumps(dic, indent=4))
#             logging.debug(json.dumps(dic, indent=4))
        return dic['BaseResponse']['Ret'] == 0

    #通过加好友的验证
    def api_webwxverifyuser(self,verifyUserId, verifyUserTicket):
        url = self.base_uri +'/webwxverifyuser?r=%s&pass_ticket=%s'%(
            int(time.time())*1000, self.pass_ticket)
        params = {
            "BaseRequest": self.BaseRequest,
            "Opcode":3,
            "VerifyUserListSize":1,
            "VerifyUserList":[{
                    "Value":verifyUserId,
                    "VerifyUserTicket":verifyUserTicket,
                }],
            "VerifyContent":"",
            "SceneListCount":1,
            "SceneList":[33],
            "skey":self.skey
        }
        dic = self._post(url, params) 
        return dic['BaseResponse']['Ret'] == 0
    

    #暂时不知道用途        
    def api_webwxgeticon(self, id):
        url = self.base_uri + \
            '/webwxgeticon?username=%s&skey=%s' % (id, self.skey)
        data = self._get(url)
        if data == '':
            return ''
        fn = 'img_' + id + '.jpg'
        return self._saveFile(fn, data, 'webwxgeticon')

    #获取用户头像
    def api_webwxgetheadimg(self, id):
        url = self.base_uri + \
            '/webwxgetheadimg?username=%s&skey=%s' % (id, self.skey)
        data = self._get(url)
        if data == '':
            return ''
        fn = 'img_' + id + '.jpg'
        return self._saveFile(fn, data, 'webwxgetheadimg')

    def webwxgetmsgimg(self, msgid):
        url = self.base_uri + \
            '/webwxgetmsgimg?MsgID=%s&skey=%s' % (msgid, self.skey)
        data = self._get(url)
        if data == '':
            return ''
        fn = 'img_' + msgid + '.jpg'
        return self._saveFile(fn, data, 'webwxgetmsgimg')

    # Not work now for weixin haven't support this API
    def webwxgetvideo(self, msgid):
        url = self.base_uri + \
            '/webwxgetvideo?msgid=%s&skey=%s' % (msgid, self.skey)
        data = self._get(url, api='webwxgetvideo')
        if data == '':
            return ''
        fn = 'video_' + msgid + '.mp4'
        return self._saveFile(fn, data, 'webwxgetvideo')

    def webwxgetvoice(self, msgid):
        url = self.base_uri + \
            '/webwxgetvoice?msgid=%s&skey=%s' % (msgid, self.skey)
        data = self._get(url)
        if data == '':
            return ''
        fn = 'voice_' + msgid + '.mp3'
        return self._saveFile(fn, data, 'webwxgetvoice')

    #按照提供的 聊天室名字的前缀进行扫描。返回一个list
    def getGroupListByName(self,groupname_prefix):
        return [group for group in self.GroupList if group['NickName'] and group['NickName'].startswith(groupname_prefix) ]
        
    #根据id获取聊天室的名字
    def getGroupNameById(self, id):
        name = '未知群'
        for group in self.GroupList:
            if group['UserName'] == id:
                name = group['NickName']
        if name == '未知群':
            # 现有群里面查不到 
            group = self.getGroupInfoById(id)
            if group:
                self.GroupList.append(group)
                if group['UserName'] == id:
                    name = group['NickName']
                    MemberList = group['MemberList']
                    for member in MemberList:
                        self.GroupMemeberList.append(member)
                    self.GroupMemeberDict[id] = MemberList
        return name

    #获取用户的昵称，如果是在群id那么获取群的名称。如果是个人用户，如果在群里面就获取displayname或者nickname。
    def getUserRemarkNameById(self, id):
        name = '未知群' if id[:2] == '@@' else '陌生人'
        if id == self.User['UserName']:
            return self.User['NickName']  # 自己

        if id[:2] == '@@':
            # 群
            name = self.getGroupNameById(id)
        else:
            # 特殊账号
            for member in self.SpecialUsersList:
                if member['UserName'] == id:
                    name = member['RemarkName'] if member[
                        'RemarkName'] else member['NickName']

            # 公众号或服务号
            for member in self.PublicUsersList:
                if member['UserName'] == id:
                    name = member['RemarkName'] if member[
                        'RemarkName'] else member['NickName']

            # 直接联系人
            for member in self.ContactList:
                if member['UserName'] == id:
                    name = member['RemarkName'] if member[
                        'RemarkName'] else member['NickName']
            # 群友
            for member in self.GroupMemeberList:
                if member['UserName'] == id:
                    name = member['DisplayName'] if member[
                        'DisplayName'] else member['NickName']

        if name == '未知群' or name == '陌生人':
            logging.debug(id)
        return name

    #根据好友的昵称nickname返回他的user_id
    def getUserIDByName(self, name):
        for member in self.MemberList:
            if name == member['RemarkName'] or name == member['NickName']:
                return member['UserName']
        return None

    #当好友或者是聊天室信息有变更的时候需要处理变更联系人的请求
    def handleModifyMsg(self, r):
        # ModContactCount: 变更联系人或群聊成员数目
        # ModContactList: 变更联系人或群聊列表，或群名称改变  
        for m in r['ModContactList']:
            if m['UserName'][:2] == '@@':
                # group
                in_list = False
                g_id = m['UserName']
                for g in self.GroupList:
                    # group member change
                    if g_id == g['UserName']:
                        g['MemberCount'] = m['MemberCount']
                        g['NickName'] = m['NickName']
                        g['MemberList'] = m['MemberList']
                        in_list = True 
                        break
                if not in_list:
                    # a new group
                    self.GroupList.append(m)
                    self.GroupMemeberDict[g_id] = m['MemberList']
                    for member in m['MemberList'] :
                        self.GroupMemeberList.append(member)

            elif m['UserName'][0] == '@':
                # user
                in_list = False
                for u in self.MemberList:
                    u_id = m['UserName']
                    if u_id == u['UserName']:
                        u = m
                        in_list = True
                        break
                # if don't have then add it
                if not in_list:
                    self.MemberList.append(m)
                    
    #显示消息内容
    def _showMsg(self, message):
        srcName = None
        dstName = None
        groupName = None
        content = None

        msg = message
        logging.debug(msg)

        if msg['raw_msg']:
            srcName = self.getUserRemarkNameById(msg['raw_msg']['FromUserName'])
            dstName = self.getUserRemarkNameById(msg['raw_msg']['ToUserName'])
            content = msg['raw_msg']['Content'].replace(
                '&lt;', '<').replace('&gt;', '>')
            message_id = msg['raw_msg']['MsgId']

            if content.find('http://weixin.qq.com/cgi-bin/redirectforward?args=') != -1:
                # 地理位置消息
                data = self._get(content)
                if data == '':
                    return
                data.decode('gbk').encode('utf-8')
                pos = self._searchContent('title', data, 'xml')
                temp = self._get(content)
                if temp == '':
                    return
                tree = html.fromstring(temp)
                url = tree.xpath('//html/body/div/img')[0].attrib['src']

                for item in urlparse(url).query.split('&'):
                    if item.split('=')[0] == 'center':
                        loc = item.split('=')[-1:]

                content = '%s 发送了一个 位置消息 - 我在 [%s](%s) @ %s]' % (
                    srcName, pos, url, loc)

            if msg['raw_msg']['ToUserName'] == 'filehelper':
                # 文件传输助手
                dstName = '文件传输助手'

            if msg['raw_msg']['FromUserName'][:2] == '@@':
                # 接收到来自群的消息
                if ":<br/>" in content:
                    [people, content] = content.split(':<br/>', 1)
                    groupName = srcName
                    srcName = self.getUserRemarkNameById(people)
                    dstName = 'GROUP'
                else:
                    groupName = srcName
                    srcName = 'SYSTEM'
            elif msg['raw_msg']['ToUserName'][:2] == '@@':
                # 自己发给群的消息
                groupName = dstName
                dstName = 'GROUP'

            # 收到了红包
            if content == '收到红包，请在手机上查看':
                msg['message'] = content

            # 指定了消息内容
            if 'message' in list(msg.keys()):
                content = msg['message']

        if groupName != None:
            print('%s |%s| %s -> %s: %s' % (message_id, groupName.strip(), srcName.strip(), dstName.strip(), content.replace('<br/>', '\n')))
            logging.info('%s |%s| %s -> %s: %s' % (message_id, groupName.strip(),
                                                   srcName.strip(), dstName.strip(), content.replace('<br/>', '\n')))
        else:
            print('%s %s -> %s: %s' % (message_id, srcName.strip(), dstName.strip(), content.replace('<br/>', '\n')))
            logging.info('%s %s -> %s: %s' % (message_id, srcName.strip(),
                                              dstName.strip(), content.replace('<br/>', '\n')))

    #处理消息的主函数。在这里进行消息的处理和分发
    def handleMsg(self, r):
        for msg in r['AddMsgList']:
            self.msgCount += 1
            print('[*] 你有新的消息，请注意查收')
            logging.debug('[*] 你有新的消息，请注意查收')

            if self.DEBUG:
                filename = str(datetime.datetime.strftime(datetime.datetime.now(), '%Y%m%d%Y%H%M%S')) +'-'+ str(self.msgCount) + '.json'
                fn = self.saveFolder + '/msgbak/msg' +filename
                with open(fn, 'w') as f:
                    f.write(json.dumps(msg))
                print('[*] 该消息已储存到文件: ' + filename)
                logging.debug('[*] 该消息已储存到文件: %s' % (filename))

            msgType = msg['MsgType']
            name = self.getUserRemarkNameById(msg['FromUserName'])
            content = msg['Content'].replace('&lt;', '<').replace('&gt;', '>')
            msgid = msg['MsgId']

            if msgType == 1:
                raw_msg = {'raw_msg': msg}
                self._showMsg(raw_msg) 
                self.handler.handler_text_msg(self,msg) 
            elif msgType == 3:
                image = self.webwxgetmsgimg(msgid)
                raw_msg = {'raw_msg': msg,
                           'message': '%s 发送了一张图片: %s' % (name, image)}
                self._showMsg(raw_msg)
                self._safe_open(image)
            elif msgType == 34:
                voice = self.webwxgetvoice(msgid)
                raw_msg = {'raw_msg': msg,
                           'message': '%s 发了一段语音: %s' % (name, voice)}
                self._showMsg(raw_msg)
                self._safe_open(voice)
            elif msgType == 37:
                info = msg['RecommendInfo']
                nickname= info['NickName']
                addcontent = info['Content']
                print("收到一条好友【%s】添加的验证消息【%s】"%(nickname,addcontent))
                self.handler.handler_useradd_notify(self, msg) #交由第三方处理
            elif msgType == 42:
                info = msg['RecommendInfo']
                print('%s 发送了一张名片:' % name)
                print('=========================')
                print('= 昵称: %s' % info['NickName'])
                print('= 微信号: %s' % info['Alias'])
                print('= 地区: %s %s' % (info['Province'], info['City']))
                print('= 性别: %s' % ['未知', '男', '女'][info['Sex']])
                print('=========================')
                raw_msg = {'raw_msg': msg, 'message': '%s 发送了一张名片: %s' % (
                    name.strip(), json.dumps(info))}
                self._showMsg(raw_msg)
            elif msgType == 47:
                url = self._searchContent('cdnurl', content)
                raw_msg = {'raw_msg': msg,
                           'message': '%s 发了一个动画表情，点击下面链接查看: %s' % (name, url)}
                self._showMsg(raw_msg)
                self._safe_open(url)
            elif msgType == 49:
                appMsgType = defaultdict(lambda: "")
                appMsgType.update({5: '链接', 3: '音乐', 7: '微博'})
                print('%s 分享了一个%s:' % (name, appMsgType[msg['AppMsgType']]))
                print('=========================')
                print('= 标题: %s' % msg['FileName'])
                print('= 描述: %s' % self._searchContent('des', content, 'xml'))
                print('= 链接: %s' % msg['Url'])
                print('= 来自: %s' % self._searchContent('appname', content, 'xml'))
                print('=========================')
                card = {
                    'title': msg['FileName'],
                    'description': self._searchContent('des', content, 'xml'),
                    'url': msg['Url'],
                    'appname': self._searchContent('appname', content, 'xml')
                }
                raw_msg = {'raw_msg': msg, 'message': '%s 分享了一个%s: %s' % (
                    name, appMsgType[msg['AppMsgType']], json.dumps(card))}
                self._showMsg(raw_msg)
            elif msgType == 51:
                raw_msg = {'raw_msg': msg, 'message': '[*] 成功获取联系人信息'}
                #判断是否需要拉取最近聊天记录信息。这里面包含了所有的群相关信息
                statusNotifyUserName = msg['StatusNotifyUserName'] 
                userlist = statusNotifyUserName.split(',') 
                if len(userlist) > 0: 
                    reflesh = False
                    for username in userlist:
                        if username.find('@@') != -1: 
                            reflesh =True
                            self.getGroupNameById(username)
                    if reflesh :
                        print("[*]拉取最近联系人%d"%(len(userlist)))
                        self._echo('[*] 共有 %d 个群 | 共有 %d 个群成员 | %d 个直接联系人 | %d 个特殊账号 ｜ %d 公众号或服务号' % (len(self.GroupList),len(self.GroupMemeberList),
                                                                         len(self.ContactList), len(self.SpecialUsersList), len(self.PublicUsersList)))
                    print()
                self._showMsg(raw_msg)
            elif msgType == 62:
                video = self.webwxgetvideo(msgid)
                raw_msg = {'raw_msg': msg,
                           'message': '%s 发了一段小视频: %s' % (name, video)}
                self._showMsg(raw_msg)
                self._safe_open(video)
            elif msgType == 10000:  #系统消息 
                raw_msg = {'raw_msg': msg,  'message': '收到一条系统消息'}
                self._showMsg(raw_msg)
                self.handler.handler_sys_msg(self,msg) 
            elif msgType == 10002:
                raw_msg = {'raw_msg': msg, 'message': '%s 撤回了一条消息' % name}
                self._showMsg(raw_msg)
            else:
                logging.debug('[*] 该消息类型为: %d，可能是表情，图片, 链接或红包: %s' %
                              (msg['MsgType'], json.dumps(msg)))
                raw_msg = {
                    'raw_msg': msg, 'message': '[*] 该消息类型为: %d，可能是表情，图片, 链接或红包' % msg['MsgType']}
                self._showMsg(raw_msg)

    def listenMsgMode(self):
        print('[*] 进入消息监听模式 ... 成功')
        logging.debug('[*] 进入消息监听模式 ... 成功')
        self._run('[*] 进行同步线路测试 ... ', self.testsynccheck) 
        while True:
            self.lastCheckTs = time.time()
            [retcode, selector] = self.api_synccheck()
            if self.DEBUG:
                print('retcode: %s, selector: %s' % (retcode, selector))
            logging.debug('retcode: %s, selector: %s' % (retcode, selector))
            if retcode == '1100':
                print('[*] 你在手机上登出了微信，债见')
                logging.debug('[*] 你在手机上登出了微信，债见')
                break
            if retcode == '1101':
                print('[*] 你在其他地方登录了 WEB 版微信，债见')
                logging.debug('[*] 你在其他地方登录了 WEB 版微信，债见')
                break
            elif retcode == '0':
                if selector == '1' : #todo：这里好像是获取机主的信息
                    r = self.api_webwxsync() 
                    print('[*] 这里好像是获取机主的信息，需要同步' ) 
                elif selector == '2':
                    r = self.api_webwxsync()
                elif selector == '3':
                    r = self.api_webwxsync()
                    print('[*] 可能是挂了' )
                elif selector == '4' :
                    # 保存群聊到通讯录
                    # 修改群名称
                    # 新增或删除联系人
                    # 群聊成员数目变化
                    r = self.api_webwxsync()
                    print('[*] 相关内容有变更，需要同步 %s'%selector) 
                elif selector == '6':
                    # 这里下面同步上来的一条消息里面AddMsgLIst会是空。但是会有其他的一些变更的信息。好像是在同步个人、聊天室、群的信息变更。暂时可以不处理。
                    r = self.api_webwxsync() 
                    print('[*] 相关内容有变更，需要同步 %s'%selector) 
                elif selector == '7':
                    print('[*] 相关内容有变更，需要同步 %s'%selector) 
                    r = self.api_webwxsync()
                elif selector == '0':
                    time.sleep(1)
                #上面获取的消息这里统一处理。分成2部分，        
                if r is not None:
                    self.handleMsg(r)  #这部分处理AddMsgList消息体
                    self.handleModifyMsg(r)  #这部分处理ModContactList消息体
                    
            if (time.time() - self.lastCheckTs) <= 20:
                time.sleep(time.time() - self.lastCheckTs)

    def clearOldMsgBak(self):
        path = self.saveFolder + '/msgbak'
        shutil.rmtree(path)
        os.mkdir(path)
        
    @catchKeyboardInterrupt
    def start(self):
        self._echo('[*] 微信网页版 ... 开动')
        print()
        logging.debug('[*] 微信网页版 ... 开动')
        self.clearOldMsgBak()
        while True:
            self._run('[*] 正在获取 uuid ... ', self.getUUID)
            self._echo('[*] 正在获取二维码 ... 成功')
            print()
            logging.debug('[*] 微信网页版 ... 开动')
            self.genQRCode()
            print('[*] 请使用微信扫描二维码以登录 ... ')
            if not self.waitForLogin():
                continue
                print('[*] 请在手机上点击确认以登录 ... ')
            if not self.waitForLogin(0):
                continue
            break

        self._run('[*] 正在登录 ... ', self.login)
        self._run('[*] 微信初始化 ... ', self.webwxinit)
        self._run('[*] 开启状态通知 ... ', self.api_webwxstatusnotify)
        self._run('[*] 获取联系人 ... ', self.api_webwxgetcontact)
        self._echo('[*] 应有 %s 个联系人，读取到联系人 %d 个' %
                   (self.MemberCount, len(self.MemberList)))
        print()
        self._echo('[*] 共有 %d 个群 | 共有 %d 个群成员 | %d 个直接联系人 | %d 个特殊账号 ｜ %d 公众号或服务号' % (len(self.GroupList),len(self.GroupMemeberList),
                                                                         len(self.ContactList), len(self.SpecialUsersList), len(self.PublicUsersList)))
        print()
        self._run('[*] 获取群 ... ', self.api_webwxbatchgetcontact)
        logging.debug('[*] 微信网页版 ... 开动')
        if self.DEBUG:
            print(self)
        logging.debug(self)
        #启动定时任务
        self.handler.handler_start_schedule(self)
        #开启进程监听消息
        if sys.platform.startswith('win'):
            import _thread
            _thread.start_new_thread(self.listenMsgMode())
        else:
            listenProcess = multiprocessing.Process(target=self.listenMsgMode)
            listenProcess.start()
  
#         if self.interactive and input('[*] 是否开启自动回复模式(y/n): ') == 'y':
#             self.autoReplyMode = True
#             print('[*] 自动回复模式 ... 开启')
#             logging.debug('[*] 自动回复模式 ... 开启')
#         else:
#             print('[*] 自动回复模式 ... 关闭')
#             logging.debug('[*] 自动回复模式 ... 关闭')


#         while True:
#             text = input('请输入：')
#             if text == 'quit':
#                 listenProcess.terminate()
#                 print('[*] 退出微信')
#                 logging.debug('[*] 退出微信')
#                 exit()
#             elif text[:2] == '->':
#                 [name, word] = text[2:].split(':')
#                 if name == 'all':
#                     self.sendMsgToAll(word)
#                 else:
#                     self.sendMsg(name, word)
#             elif text[:3] == 'm->':
#                 [name, file] = text[3:].split(':')
#                 self.sendMsg(name, file, True)
#             elif text[:3] == 'f->':
#                 print('发送文件')
#                 logging.debug('发送文件')
#             elif text[:3] == 'i->':
#                 print('发送图片')
#                 [name, file_name] = text[3:].split(':')
#                 self.sendImg(name, file_name)
#                 logging.debug('发送图片')
#             elif text[:3] == 'e->':
#                 print('发送表情')
#                 [name, file_name] = text[3:].split(':')
#                 self.sendEmotion(name, file_name)
#                 logging.debug('发送表情')
 
    def _searchContent(self, key, content, fmat='attr'):
        if fmat == 'attr':
            pm = re.search(key + '\s?=\s?"([^"<]+)"', content)
            if pm:
                return pm.group(1)
        elif fmat == 'xml':
            pm = re.search('<{0}>([^<]+)</{0}>'.format(key), content)
            if not pm:
                pm = re.search(
                    '<{0}><\!\[CDATA\[(.*?)\]\]></{0}>'.format(key), content)
            if pm:
                return pm.group(1)
        return '未知'


class UnicodeStreamFilter:
    def __init__(self, target):
        self.target = target
        self.encoding = 'utf-8'
        self.errors = 'replace'
        self.encode_to = self.target.encoding

    def write(self, s):
        if type(s) == str:
            s = s.encode().decode('utf-8')
        s = s.encode(self.encode_to, self.errors).decode(self.encode_to)
        self.target.write(s)

    def flush(self):
        self.target.flush()

if sys.stdout.encoding == 'cp936':
    sys.stdout = UnicodeStreamFilter(sys.stdout)
 
