#!/usr/bin/env python
# coding: utf-8

#===================================================
from utils import *
from wechat_apis import WXAPI
from config import ConfigManager
from config import Constant
from config import Log
#---------------------------------------------------
import json
import re
import sys
import os
import time
import random
from collections import defaultdict
from datetime import timedelta
import traceback
import Queue
import threading
#===================================================


class WeChat(WXAPI):

    def __str__(self):
        description = \
            "=========================\n" + \
            "[#] Web WeChat\n" + \
            "[#] UUID: " + self.uuid + "\n" + \
            "[#] Uin: " + str(self.uin) + "\n" + \
            "[#] Sid: " + self.sid + "\n" + \
            "[#] Skey: " + self.skey + "\n" + \
            "[#] DeviceId: " + self.device_id + "\n" + \
            "[#] PassTicket: " + self.pass_ticket + "\n" + \
            "========================="
        return description

    def __init__(self, host='wx.qq.com'):
        super(WeChat, self).__init__(host)

        self.db = None
        self.save_data_folder = ''  # 保存图片，语音，小视频的文件夹
        self.last_login = 0  # 上次退出的时间
        self.time_out = 5  # 同步时间间隔（单位：秒）
        self.msg_handler = None
        self.start_time = time.time()
        self.bot = None

        cm = ConfigManager()
        self.save_data_folders = cm.get_wechat_media_dir()
        self.cookie_file = cm.get_cookie()
        self.pickle_file = cm.get_pickle_files()
        self.log_mode = cm.get('setting', 'log_mode') == 'True'
        self.exit_code = 0

    def start(self):
        echo(Constant.LOG_MSG_START)
        run(Constant.LOG_MSG_RECOVER, self.recover) #从conf文件里面恢复配置信息。

        timeOut = time.time() - self.last_login
        echo(Constant.LOG_MSG_TRY_INIT)
        #先根据配置文件里面的参数信息pass_ticket, self.skey 这2个参数尝试初始化。如果干活成功，那么就从pickle文件里面恢复联系人信息。
        if self.webwxinit():
            echo(Constant.LOG_MSG_SUCCESS)
            run(Constant.LOG_MSG_RECOVER_CONTACT, self.recover_contacts) #从pickle文件里面恢复联系人信息。
        else:
            echo(Constant.LOG_MSG_FAIL)

            while True:
                # 初始化失败后，先尝试从uin 进行登录。这步不需要扫描二维码。
                # first try to login by uin without qrcode
                echo(Constant.LOG_MSG_ASSOCIATION_LOGIN)
                if self.association_login():
                    echo(Constant.LOG_MSG_SUCCESS)
                else:
                    echo(Constant.LOG_MSG_FAIL)
                    # scan qrcode to login
                    run(Constant.LOG_MSG_GET_UUID, self.getuuid) # 先获取uuid
                    echo(Constant.LOG_MSG_GET_QRCODE)
                    self.genqrcode()  #根据uuid获取登录二维码。这步还分成window和非windows两个平台
                    echo(Constant.LOG_MSG_SCAN_QRCODE)
                
                #等待手机确认登录。如果没有确认，那么重新再生成二维码。目前这里二维码生成速度比较快，可以等待一下。不知道二维码的有效期多久。
                #这个扫描二维码的接口和手机端确认的接口在server端都有超时等待，http请求本身就会在server端被等待手机端的确认，有一个超时的时间
                #所以在代码里面就不需要在自己增加一个超时的时间了。这个也是之前没有想明白的地方。
                if not self.waitforlogin():  
                    continue
                echo(Constant.LOG_MSG_CONFIRM_LOGIN)
                if not self.waitforlogin(0): #用户手机端确认以后，server端会返回一个redirect_uri
                    continue
                break
            
            #根据上面获取的redirect_uri 进行一次登录操作。获取登录以后的用户令牌信息。其中包括skey、wxsid、wxuin、pass_ticket
            run(Constant.LOG_MSG_LOGIN, self.login)
            # init可以获取机主个个人信息。这里面还可以获取最近的聊天联系人的记录。ChatSet和ContactList
            run(Constant.LOG_MSG_INIT, self.webwxinit)
            #通知手机，网页版已经登录成功
            run(Constant.LOG_MSG_STATUS_NOTIFY, self.webwxstatusnotify)
            #获取联系人，这里是可以获取全部的联系人、全部的公众号信息、特殊用户。但是这里无法获取群聊信息。
            run(Constant.LOG_MSG_GET_CONTACT, self.webwxgetcontact)
            echo(Constant.LOG_MSG_CONTACT_COUNT % (
                    self.MemberCount, len(self.MemberList)
                ))
            echo(Constant.LOG_MSG_OTHER_CONTACT_COUNT % (
                    len(self.GroupList), len(self.ContactList),
                    len(self.SpecialUsersList), len(self.PublicUsersList)
                ))
            #目前看这里获取不到群联系放人
            run(Constant.LOG_MSG_GET_GROUP_MEMBER, self.fetch_group_contacts) #把群联系人存到数据库里面。
        #把获取到的登录信息和联系人信息都暂存一下。
        run(Constant.LOG_MSG_SNAPSHOT, self.snapshot)
#--------------------------以上是登录和初始化操作

        while True:
            [retcode, selector] = self.synccheck()
            Log.debug('retcode: %s, selector: %s' % (retcode, selector))
            self.exit_code = int(retcode)

            if retcode == '1100':
                echo(Constant.LOG_MSG_LOGOUT)
                break
            if retcode == '1101':
                echo(Constant.LOG_MSG_LOGIN_OTHERWHERE)
                break
            if retcode == '1102':
                echo(Constant.LOG_MSG_QUIT_ON_PHONE)
                break
            elif retcode == '0':
                if selector == '2':
                    r = self.webwxsync()
                    if r is not None:
                        try:
                            self.handle_msg(r)
                        except:
                            Log.error(traceback.format_exc())
                elif selector == '7':
                    r = self.webwxsync()
                elif selector == '0':
                    time.sleep(self.time_out)
                elif selector == '4':
                    # 保存群聊到通讯录
                    # 修改群名称
                    # 新增或删除联系人
                    # 群聊成员数目变化
                    r = self.webwxsync()
                    if r is not None:
                        try:
                            self.handle_mod(r)
                        except:
                            Log.error(traceback.format_exc())
                elif selector == '3' or selector == '6':
                    break
            else:
                r = self.webwxsync()
                Log.debug('webwxsync: %s\n' % json.dumps(r))

            # 执行定时任务
            if self.msg_handler:
                self.msg_handler.check_schedule_task()

            # if self.bot:
            #     r = self.bot.time_schedule()
            #     if r:
            #         for g in self.GroupList:
            #             echo('[*] 推送 -> %s: %s' % (g['NickName'], r))
            #             g_id = g['UserName']
            #             self.webwxsendmsg(r, g_id)

    def get_run_time(self):
        """
        @brief      get how long this run
        @return     String
        """
        totalTime = int(time.time() - self.start_time)
        t = timedelta(seconds=totalTime)
        return '%s Day %s' % (t.days, t)

    def stop(self):
        """
        @brief      Save some data and use shell to kill this process
        """
        run(Constant.LOG_MSG_SNAPSHOT, self.snapshot)
        echo(Constant.LOG_MSG_RUNTIME % self.get_run_time())
        # close database connect
        self.db.close()

    def fetch_group_contacts(self):
        """
        @brief      Fetches all groups contacts.
        @return     Bool: whether operation succeed.
        @note       This function must be finished in 180s
        """
        Log.debug('fetch_group_contacts')
        # clean database
        if self.msg_handler:
            self.msg_handler.clean_db()

        # sqlite
        # ----------------------------------------------------
        # group max_thread_num  max_fetch_group_num    time(s)
        # 197      10                 10               108
        # 197      10                 15               95
        # 197      20                 10               103
        # 197      10                 20               55
        # 197       5                 30               39
        # 197       4                 50               35
        # ----------------------------------------------------
        # mysql
        # ----------------------------------------------------
        # group max_thread_num  max_fetch_group_num    time(s)
        # 197       4                 50               20
        # ----------------------------------------------------

        max_thread_num = 1 #4
        max_fetch_group_num = 50
        group_list_queue = Queue.Queue()

        class GroupListThread(threading.Thread):

            def __init__(self, group_list_queue, wechat):
                threading.Thread.__init__(self)
                self.group_list_queue = group_list_queue
                self.wechat = wechat

            def run(self):
                while not self.group_list_queue.empty():
                    g_list = self.group_list_queue.get()
                    gid_list = []
                    g_dict = {}
                    for g in g_list:
                        gid = g['UserName']
                        gid_list.append(gid)
                        g_dict[gid] = g

                    # 通过 webwxbatchgetcontact 这个接口获取群相关信息
                    group_member_list = self.wechat.webwxbatchgetcontact(gid_list)

                    for member_list in group_member_list:
                        gid = member_list['UserName']
                        g = g_dict[gid]
                        g['MemberCount'] = member_list['MemberCount']
                        g['OwnerUin'] = member_list['OwnerUin']
                        g['HeadImgUrl'] = member_list['HeadImgUrl']
                        g['NickName'] = member_list['NickName'] #群名称，如果为空 那么表示未定名
                        g['IsOwner'] = member_list['IsOwner']   #=1 自己是群主 ， =0不是
                        self.wechat.GroupMemeberList[gid] = member_list['MemberList']

                        # 如果使用 Mysql 则可以在多线程里操作数据库
                        # 否则请注释下列代码在主线程里更新群列表
                        # -----------------------------------
                        # 处理群成员
                        if self.wechat.msg_handler:
                            self.wechat.msg_handler.handle_group_member_list(gid, member_list['MemberList'])
                        # -----------------------------------
                    run(Constant.LOG_MSG_SNAPSHOT, self.wechat.snapshot)
                    self.group_list_queue.task_done()

        #把groupList按照 max_fetch_group_num 为长度截取。因为后面的可以分段的通过webwxbatchgetcontact 这个接口来获取群聊的详细信息
        for g_list in split_array(self.GroupList, max_fetch_group_num):
            group_list_queue.put(g_list)

        #启动 max_thread_num 个线程去获取
        for i in range(max_thread_num):
            t = GroupListThread(group_list_queue, self)
            t.setDaemon(True)
            t.start()

        group_list_queue.join()
        #等待所有的线程返回然后交给第三方handler处理。
        if self.msg_handler:
            # 处理群
            if self.GroupList:
                self.msg_handler.handle_group_list(self.GroupList)
            # 这个是用 sqlite 来存储群列表，sqlite 对多线程的支持不太好
            # ----------------------------------------------------
            # 处理群成员
            for (gid, member_list) in self.GroupMemeberList.items():
                self.msg_handler.handle_group_member_list(gid, member_list)
            # ----------------------------------------------------
        return True

    def snapshot(self):
        """
        @brief      Save basic infos for next login.
        @return     Bool: whether operation succeed.
        """
        try:
            conf = {
                'uuid': self.uuid,
                'redirect_uri': self.redirect_uri,
                'uin': self.uin,
                'sid': self.sid,
                'skey': self.skey,
                'pass_ticket': self.pass_ticket,
                'synckey': self.synckey,
                'device_id': self.device_id,
                'last_login': time.time(),
            }
            cm = ConfigManager()
            Log.debug('save wechat config')
            cm.set_wechat_config(conf)

            # save cookie
            Log.debug('save cookie')
            if self.cookie:
                self.cookie.save(ignore_discard=True)

            # save contacts
            Log.debug('save contacts')
            self.save_contacts()
        except Exception, e:
            Log.error(traceback.format_exc())
            return False
        return True

    def recover(self):
        """
        @brief      Recover from snapshot data.
        @return     Bool: whether operation succeed.
        """
        cm = ConfigManager()
        [self.uuid, self.redirect_uri, self.uin,
        self.sid, self.skey, self.pass_ticket,
        self.synckey, device_id, self.last_login] = cm.get_wechat_config()

        if device_id:
            self.device_id = device_id

        self.base_request = {
            'Uin': int(self.uin),
            'Sid': self.sid,
            'Skey': self.skey,
            'DeviceID': self.device_id,
        }

        # set cookie
        Log.debug('set cookie')
        self.cookie = set_cookie(self.cookie_file)

        return True

    def save_contacts(self):
        """
        @brief      Save contacts.
        """
        pickle_save(self.User, self.pickle_file['User'])
        pickle_save(self.MemberList, self.pickle_file['MemberList'])
        pickle_save(self.GroupList, self.pickle_file['GroupList'])
        pickle_save(self.GroupMemeberList, self.pickle_file['GroupMemeberList'])
        pickle_save(self.SpecialUsersList, self.pickle_file['SpecialUsersList'])

    def recover_contacts(self):
        """
        @brief      recover contacts.
        @return     Bool: whether operation succeed.
        """
        try:
            self.User = pickle_load(self.pickle_file['User'])
            self.MemberList = pickle_load(self.pickle_file['MemberList'])
            self.GroupList = pickle_load(self.pickle_file['GroupList'])
            self.GroupMemeberList = pickle_load(self.pickle_file['GroupMemeberList'])
            self.SpecialUsersList = pickle_load(self.pickle_file['SpecialUsersList'])
            return True
        except Exception, e:
            Log.error(traceback.format_exc())
        return False

    def handle_mod(self, r):
        # ModContactCount: 变更联系人或群聊成员数目
        # ModContactList: 变更联系人或群聊列表，或群名称改变
        Log.debug('handle modify')
        self.handle_msg(r)
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
                        self.GroupMemeberList[g_id] = m['MemberList']
                        in_list = True
                        if self.msg_handler:
                            self.msg_handler.handle_group_member_change(g_id, m['MemberList'])
                        break
                if not in_list:
                    # a new group
                    self.GroupList.append(m)
                    self.GroupMemeberList[g_id] = m['MemberList']
                    if self.msg_handler:
                        self.msg_handler.handle_group_list_change(m)
                        self.msg_handler.handle_group_member_change(g_id, m['MemberList'])

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

    def handle_msg(self, r):
        """
        @brief      Recover from snapshot data.
        @param      r  Dict: message json
        """
        #先调用注册进来的处理消息的handler。这个可以作为第三方处理函数的接口。
        Log.debug('handle message')
        if self.msg_handler:
            self.msg_handler.handle_wxsync(r)

        #以下是wechat 对象本身的处理逻辑
        n = len(r['AddMsgList'])
        if n == 0:
            return

        if self.log_mode:
            echo(Constant.LOG_MSG_NEW_MSG % n)
        print r['AddMsgList']
        for msg in r['AddMsgList']:
            msgType = msg['MsgType']
            msgId = msg['MsgId']
            content = msg['Content'].replace('&lt;', '<').replace('&gt;', '>')
            raw_msg = None

            if msgType == self.wx_conf['MSGTYPE_TEXT']:
                # 地理位置消息
                if content.find('pictype=location') != -1:
                    location = content.split('<br/>')[1][:-1]
                    raw_msg = {
                        'raw_msg': msg,
                        'location': location,
                        'log': Constant.LOG_MSG_LOCATION % location
                    }
                # 普通文本消息
                else:
                    text = content.split(':<br/>')[-1]
                    raw_msg = {
                        'raw_msg': msg,
                        'text': text,
                        'log': text.replace('<br/>', '\n')
                    }
            elif msgType == self.wx_conf['MSGTYPE_IMAGE']:
                data = self.webwxgetmsgimg(msgId)
                fn = 'img_' + msgId + '.jpg'
                dir = self.save_data_folders['webwxgetmsgimg']
                path = save_file(fn, data, dir)
                raw_msg = {'raw_msg': msg,
                           'image': path,
                           'log': Constant.LOG_MSG_PICTURE % path}
            elif msgType == self.wx_conf['MSGTYPE_VOICE']:
                data = self.webwxgetvoice(msgId)
                fn = 'voice_' + msgId + '.mp3'
                dir = self.save_data_folders['webwxgetvoice']
                path = save_file(fn, data, dir)
                raw_msg = {'raw_msg': msg,
                           'voice': path,
                           'log': Constant.LOG_MSG_VOICE % path}
            elif msgType == self.wx_conf['MSGTYPE_SHARECARD']:
                info = msg['RecommendInfo']
                card = Constant.LOG_MSG_NAME_CARD % (
                    info['NickName'],
                    info['Alias'],
                    info['Province'], info['City'],
                    Constant.LOG_MSG_SEX_OPTION[info['Sex']]
                )
                namecard = '%s %s %s %s %s' % (
                    info['NickName'], info['Alias'], info['Province'],
                    info['City'], Constant.LOG_MSG_SEX_OPTION[info['Sex']]
                )
                raw_msg = {
                    'raw_msg': msg,
                    'namecard': namecard,
                    'log': card
                }
            elif msgType == self.wx_conf['MSGTYPE_EMOTICON']:
                url = search_content('cdnurl', content)
                raw_msg = {'raw_msg': msg,
                           'emoticon': url,
                           'log': Constant.LOG_MSG_EMOTION % url}
            elif msgType == self.wx_conf['MSGTYPE_APP']:
                card = ''
                # 链接, 音乐, 微博
                if msg['AppMsgType'] in [
                    self.wx_conf['APPMSGTYPE_AUDIO'],
                    self.wx_conf['APPMSGTYPE_URL'],
                    self.wx_conf['APPMSGTYPE_OPEN']
                ]:
                    card = Constant.LOG_MSG_APP_LINK % (
                        Constant.LOG_MSG_APP_LINK_TYPE[msg['AppMsgType']],
                        msg['FileName'],
                        search_content('des', content, 'xml'),
                        msg['Url'],
                        search_content('appname', content, 'xml')
                    )
                    raw_msg = {
                        'raw_msg': msg,
                        'link': msg['Url'],
                        'log': card
                    }
                # 图片
                elif msg['AppMsgType'] == self.wx_conf['APPMSGTYPE_IMG']:
                    data = self.webwxgetmsgimg(msgId)
                    fn = 'img_' + msgId + '.jpg'
                    dir = self.save_data_folders['webwxgetmsgimg']
                    path = save_file(fn, data, dir)
                    card = Constant.LOG_MSG_APP_IMG % (
                        path,
                        search_content('appname', content, 'xml')
                    )
                    raw_msg = {
                        'raw_msg': msg,
                        'image': path,
                        'log': card
                    }
                else:
                    raw_msg = {
                        'raw_msg': msg,
                        'log': Constant.LOG_MSG_UNKNOWN_MSG % (msgType, content)
                    }
            #这里在第一次登录后会第一次触发一次群聊的信息的拉取。AddMsgList-》StatusNotifyUserName 会把所有的最近的群聊信息都拉回。
            elif msgType == self.wx_conf['MSGTYPE_STATUSNOTIFY']: #MsgType=51
                Log.info(Constant.LOG_MSG_NOTIFY_PHONE)
                statusNotifyUserName = msg['StatusNotifyUserName'] 
                userlist = statusNotifyUserName.split(',')
                needflush = False
                if len(userlist) > 0: 
                    for username in userlist:
                        if username.find('@@') != -1: 
                            user ={}
                            user['UserName']=username
                            group = self.get_group_by_id(username)
                            if group and int(group['MemberCount']) == 0:
                                self.GroupList.append(user)
                                needflush =True
                    if needflush:
                        run(Constant.LOG_MSG_GET_GROUP_MEMBER, self.fetch_group_contacts) #把群联系人存到数据库里面。
    
            elif msgType == self.wx_conf['MSGTYPE_MICROVIDEO']:
                data = self.webwxgetvideo(msgId)
                fn = 'video_' + msgId + '.mp4'
                dir = self.save_data_folders['webwxgetvideo']
                path = save_file(fn, data, dir)
                raw_msg = {'raw_msg': msg,
                           'video': path,
                           'log': Constant.LOG_MSG_VIDEO % path}
            elif msgType == self.wx_conf['MSGTYPE_RECALLED']:
                recall_id = search_content('msgid', content, 'xml')
                text = Constant.LOG_MSG_RECALL
                raw_msg = {
                    'raw_msg': msg,
                    'text': text,
                    'recall_msg_id': recall_id,
                    'log': text
                }
            elif msgType == self.wx_conf['MSGTYPE_SYS']:
                raw_msg = {
                    'raw_msg': msg,
                    'sys_notif': content,
                    'log': content
                }
            elif msgType == self.wx_conf['MSGTYPE_VERIFYMSG']:
                name = search_content('fromnickname', content)
                raw_msg = {
                    'raw_msg': msg,
                    'log': Constant.LOG_MSG_ADD_FRIEND % name
                }
            else:
                raw_msg = {
                    'raw_msg': msg,
                    'log': Constant.LOG_MSG_UNKNOWN_MSG % (msgType, content)
                }

            isGroupMsg = '@@' in msg['FromUserName']+msg['ToUserName']
            if self.msg_handler and raw_msg:
                if isGroupMsg:
                    # handle group messages
                    g_msg = self.make_group_msg(raw_msg)
                    self.msg_handler.handle_group_msg(g_msg)
                else:
                    # handle personal messages
                    self.msg_handler.handle_user_msg(raw_msg)

            if self.log_mode:
                self.show_msg(raw_msg)

    def make_group_msg(self, msg):
        """
        @brief      Package the group message for storage.
        @param      msg  Dict: raw msg
        @return     raw_msg Dict: packged msg
        """
        Log.debug('make group message')
        raw_msg = {
            'raw_msg': msg['raw_msg'],
            'msg_id': msg['raw_msg']['MsgId'],
            'group_owner_uin': '',
            'group_name': '',
            'group_count': '',
            'from_user_name': msg['raw_msg']['FromUserName'],
            'to_user_name': msg['raw_msg']['ToUserName'],
            'user_attrstatus': '',
            'user_display_name': '',
            'user_nickname': '',
            'msg_type': msg['raw_msg']['MsgType'],
            'text': '',
            'link': '',
            'image': '',
            'video': '',
            'voice': '',
            'emoticon': '',
            'namecard': '',
            'location': '',
            'recall_msg_id': '',
            'sys_notif': '',
            'time': '',
            'timestamp': '',
            'log': '',
        }
        content = msg['raw_msg']['Content'].replace(
            '&lt;', '<').replace('&gt;', '>')

        group = None
        src = None

        if msg['raw_msg']['FromUserName'][:2] == '@@':
            # 接收到来自群的消息
            g_id = msg['raw_msg']['FromUserName']
            group = self.get_group_by_id(g_id)

            if re.search(":<br/>", content, re.IGNORECASE):
                u_id = content.split(':<br/>')[0]
                src = self.get_group_user_by_id(u_id, g_id)

        elif msg['raw_msg']['ToUserName'][:2] == '@@':
            # 自己发给群的消息
            g_id = msg['raw_msg']['ToUserName']
            u_id = msg['raw_msg']['FromUserName']
            src = self.get_group_user_by_id(u_id, g_id)
            group = self.get_group_by_id(g_id)

        if src:
            raw_msg['user_attrstatus'] = src['AttrStatus']
            raw_msg['user_display_name'] = src['DisplayName']
            raw_msg['user_nickname'] = src['NickName']
        if group:
            raw_msg['group_count'] = group['MemberCount']
            raw_msg['group_owner_uin'] = group['OwnerUin']
            raw_msg['group_name'] = group['ShowName']

        raw_msg['timestamp'] = msg['raw_msg']['CreateTime']
        t = time.localtime(float(raw_msg['timestamp']))
        raw_msg['time'] = time.strftime("%Y-%m-%d %H:%M:%S", t)

        for key in [
            'text', 'link', 'image', 'video', 'voice',
            'emoticon', 'namecard', 'location', 'log',
            'recall_msg_id', 'sys_notif'
        ]:
            if key in msg:
                raw_msg[key] = msg[key]

        return raw_msg

    def show_msg(self, message):
        """
        @brief      Log the message to stdout
        @param      message  Dict
        """
        msg = message
        src = None
        dst = None
        group = None

        if msg and msg['raw_msg']:

            content = msg['raw_msg']['Content']
            content = content.replace('&lt;', '<').replace('&gt;', '>')
            msg_id = msg['raw_msg']['MsgId']

            if msg['raw_msg']['FromUserName'][:2] == '@@':
                # 接收到来自群的消息
                g_id = msg['raw_msg']['FromUserName']
                group = self.get_group_by_id(g_id)

                if re.search(":<br/>", content, re.IGNORECASE):
                    u_id = content.split(':<br/>')[0]
                    src = self.get_group_user_by_id(u_id, g_id)
                    dst = {'ShowName': 'GROUP'}
                else:
                    u_id = msg['raw_msg']['ToUserName']
                    src = {'ShowName': 'SYSTEM'}
                    dst = self.get_group_user_by_id(u_id, g_id)
            elif msg['raw_msg']['ToUserName'][:2] == '@@':
                # 自己发给群的消息
                g_id = msg['raw_msg']['ToUserName']
                u_id = msg['raw_msg']['FromUserName']
                group = self.get_group_by_id(g_id)
                src = self.get_group_user_by_id(u_id, g_id)
                dst = {'ShowName': group['ShowName']}
            else:
                # 非群聊消息
                src = self.get_user_by_id(msg['raw_msg']['FromUserName'])
                dst = self.get_user_by_id(msg['raw_msg']['ToUserName'])

            if group:
                echo('%s |%s| %s -> %s: %s\n' % (
                    msg_id,
                    trans_emoji(group['ShowName']),
                    trans_emoji(src['ShowName']),
                    dst['ShowName'],
                    trans_emoji(msg['log'])
                ))
            else:
                echo('%s %s -> %s: %s\n' % (
                    msg_id,
                    trans_emoji(src['ShowName']),
                    trans_emoji(dst['ShowName']),
                    trans_emoji(msg['log'])
                ))
