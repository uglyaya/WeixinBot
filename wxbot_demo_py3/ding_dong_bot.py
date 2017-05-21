#!/usr/bin/env python
# coding: utf-8  
from weixin import WebWeixin
import re
import logging
import random
import sys ,urllib ,json,time,threading
from baseHandler import BaseHandler
import urllib.request

WXGENRE_ID = '1'  #微信项目的id。
# WX_SERVER_HOST = 'http://localhost:8000'
WX_SERVER_HOST = 'http://api.wule.mobi'

def getNightChatOrders():
    url = WX_SERVER_HOST+"/orders" 
    resp=urllib.request.urlopen(url)
    data = resp.read().decode('utf-8')
    data= json.loads(data)
    return data

#从聊天室机器人返回需要回复的内容
def getChatbotReplyContent(roomname,content):
    url = WX_SERVER_HOST+"/fitness/chat_bot?genreid=%s&chatroomname=%s&content=%s"%(WXGENRE_ID,urllib.parse.quote(roomname), urllib.parse.quote(content)) 
    resp=urllib.request.urlopen(url)
    data = resp.read().decode('utf-8')
    data= json.loads(data) 
    return data['REPLY']

def getChatroomConfig():
    url = WX_SERVER_HOST+"/fitness/get_chatroom_config?genreid="+WXGENRE_ID 
    resp=urllib.request.urlopen(url)
    data = resp.read().decode('utf-8')
    data= json.loads(data)
    return data
    
def getChatRoomNamePrefix():
    url = WX_SERVER_HOST+"/fitness/get_chatroom_prefix?genreid="+WXGENRE_ID 
    resp=urllib.request.urlopen(url)
    data = resp.read().decode('utf-8')
    data= json.loads(data)
    return (data['RoomNamePrefix'])

def getChatRoomName():
    url = WX_SERVER_HOST+"/fitness/create_chatroom?genreid="+WXGENRE_ID 
    resp=urllib.request.urlopen(url)
    data = resp.read().decode('utf-8')
    data= json.loads(data)
    return (data['RoomName'])

class DingDongBot(BaseHandler):
    HAVE_NEW_USER_DICT = {}  #是否有新用户加入,key是聊天室名称，value是bool的 对象，用来控制edu msg
    #处理新加好友验证
    def handler_useradd_notify(self,weixin,msg):
        info = msg['RecommendInfo']
        nickname= info['NickName'] #对方昵称
        addcontent = info['Content']  #验证的内容
        verifyUserId = info['UserName']
        verifyUserTicket = info['Ticket']
    #     if addcontent == '口令' :
        weixin.api_webwxverifyuser(verifyUserId,verifyUserTicket)
    
    #处理收到的文本消息
    def handler_text_msg(self,weixin,msg):
        print(" ding dong bot")
        chatroomName = getChatRoomNamePrefix() #聊天室前缀
        groups = weixin.getGroupListByName(chatroomName) #获取该聊天室前缀的聊天室
        """
        消息发送分4种情况：
        1、我-》A  ：  from=我，to=A  ；content=内容
        2、A-》我 ： from=A ，to=我  ；content=内容
        3、我-》群 ： from=我 ，to=群id， content=内容
        4、群A-》我 ： from=群id，to=我， content= 群A<br/>内容 
        """ 
        fromUserName = msg['FromUserName']   
        toUserName =msg['ToUserName']
        content = msg['Content'].replace('&lt;', '<').replace('&gt;', '>')   
        groupUserName = ''
        isGroupMsg = '@@' in fromUserName + toUserName
        if isGroupMsg :
            groupUserName = fromUserName if '@@' in fromUserName else toUserName
            fromUserName = fromUserName if len(content.split(':<br/>')) ==1 else content.split(':<br/>')[0]
        content =  content.split(':<br/>')[-1]
        content = content.strip()
        if content == 'ding'  :
            print('%s -> %s : %s'%(fromUserName,toUserName,content))
            weixin.api_webwxsendmsg("""
[bot]目前支持指令
1。创建聊天室
2。扫描聊天室
3。聊天室加人
4。聊天室删人
5。聊天室改名
6。聊天室艾特
7。聊天室发图
8。聊天室数量
9。午夜订购量
                    """, groupUserName if isGroupMsg else fromUserName)
        
        if content == '午夜订购量' : 
            orderinfo = getNightChatOrders()
            msg = """
[bot]订单数:%s
LastInfo:
Id:%s
Idfa:%s
订购:%s
过期:%s
            """%(orderinfo['receipt_count'],
                 orderinfo['last_receipt']['original_transaction_id'],
                 orderinfo['last_receipt']['idfa'],
                 orderinfo['last_receipt']['purchase_date'], 
                 orderinfo['last_receipt']['expires_date'], 
                 )
            weixin.api_webwxsendmsg(msg, groupUserName if isGroupMsg else fromUserName)
            
        if content == '聊天室发图' : 
            weixin.api_webwxsendmsgimgBy2in1(
                weixin.User['UserName'],
                groupUserName if isGroupMsg else fromUserName, 
                'pic.png')
            
        if content == '聊天室艾特' :
            nickname = weixin.getUserRemarkNameById(fromUserName)
            weixin.api_webwxsendmsg('[bot]@%s 你好[微笑]'%nickname, groupUserName if isGroupMsg else fromUserName)
    
        if content == '创建聊天室' : 
            if weixin.User['NickName'] =='阿妖':
                uid = weixin.getUserIDByName('波特')
                uid2 = weixin.getUserIDByName('丁丁') 
                roomname = getChatRoomName()
                if roomname == '':
                    weixin.api_webwxsendmsg('[bot]创建聊天室失败：聊天室名称获取为空', groupUserName if isGroupMsg else fromUserName)
                else:
                    groupid = weixin.api_webwxcreatechatroom([uid2,uid],roomname)
                    if groupid !='' :
                        weixin.api_webwxsendmsg('[bot]创建聊天室成功', groupid)
                        weixin.api_webwxsendmsg('[bot]创建聊天室成功', groupUserName if isGroupMsg else fromUserName)
                        weixin.api_webwxsendmsg('[bot]创建成功:'+roomname , groupUserName if isGroupMsg else fromUserName)
                    else:
                        weixin.api_webwxsendmsg('[bot]创建聊天室失败', groupUserName if isGroupMsg else fromUserName)
            else:
                weixin.api_webwxsendmsg('[bot]创建聊天室需要阿妖登录bot', groupUserName if isGroupMsg else fromUserName)

        if content == '聊天室数量':
#             groups = weixin.getGroupListByName(chatroomName)
            weixin.api_webwxsendmsg(u"[bot]聊天室%s个，前缀：%s"%(len(groups),chatroomName), groupUserName if isGroupMsg else fromUserName)

        if content == '扫描聊天室' :
#             groups = weixin.getGroupListByName(chatroomName)
            for group in groups: 
                weixin.api_webwxsendmsg('[bot]我在这里[微笑]', group['UserName'])
        
        if content == '聊天室改名' :
            groups = weixin.getGroupListByName('AYA')
            for group in groups: 
                weixin.api_webwxupdatechatroomModifyTopic(group['UserName'], "AYA"+str(random.random()))
                
        if content == '聊天室加人' : 
            uid = weixin.getUserIDByName('李慰') 
#             groups = weixin.getGroupListByName(chatroomName)
            for group in groups: 
                weixin.api_webwxupdatechatroomAddMember(group['UserName'],[uid])
            weixin.api_webwxsendmsg('[bot]聊天室加人成功', groupUserName if isGroupMsg else fromUserName)

        if content == '聊天室删人' : 
            uid = weixin.getUserIDByName('李慰') 
#             groups = weixin.getGroupListByName(chatroomName)
            for group in groups: 
                weixin.api_webwxupdatechatroomDelMember(group['UserName'],[uid])     
            weixin.api_webwxsendmsg('[bot]聊天室删人成功', groupUserName if isGroupMsg else fromUserName)
    
        #如果是发到观察聊天室里面的文字消息，那么需要走一边机器人看看有没有需要返回的内容。 
        if isGroupMsg and  fromUserName != weixin.User['UserName']:
            for group in groups: 
                if group['UserName'] == groupUserName :
                    reply = getChatbotReplyContent(group['NickName'],content)
                    weixin.api_webwxsendmsg('[bot]%s'%reply, groupUserName if isGroupMsg else fromUserName)
                    
    #处理系统消息
    def handler_sys_msg(self,weixin,msg):
        fromUserName = msg['FromUserName']
        toUserName =msg['ToUserName']
        groupUserName=''
        isGroupMsg = '@@' in fromUserName + toUserName
        if isGroupMsg :
            groupUserName = fromUserName if '@@' in fromUserName else toUserName 
        m = re.search(r'邀请(.+)加入了群聊', msg['Content'])
        if m:
            name = m.group(1)
            print("%s 加入了群聊: %s"%(name,toUserName))
        
        m = re.search(r'(.+)修改群名为“(.+)”', msg['Content'])
        if m:
            name = m.group(1)
            toname = m.group(2)
            print("修改群名为: %s|%s"%(name,toname))

        m = re.search(r'"(.+)"通过扫描.+二维码加入群聊', msg['Content'])
        if m:
            name = m.group(1)
            chatroomName = weixin.getGroupNameById(groupUserName)
            weixin.api_webwxsendmsg("[bot]欢迎'%s'加入我们"%name,  groupUserName)
            print("%s 加入了群聊: %s"%(name, groupUserName if isGroupMsg else fromUserName))
            self.HAVE_NEW_USER_DICT[chatroomName]  = True
            
    #发送一次教育用户的消息 
    def sendEduMsg(self,weixin):   
        configdata = getChatroomConfig()
        data = configdata['SCHEDULE_EDU_MSG']
        scheduleInterval = data['SCHEDULE_INTERVAL']
        chatroomName = getChatRoomNamePrefix()
        groups = weixin.getGroupListByName(chatroomName)
        for group in groups: 
            chatroomName = weixin.getGroupNameById(group['UserName'])
            if chatroomName in self.HAVE_NEW_USER_DICT and self.HAVE_NEW_USER_DICT[chatroomName]:
                self.HAVE_NEW_USER_DICT[chatroomName]  = False
                weixin.api_webwxsendmsg(data['VALUE']+str(int(time.time())), group['UserName']) 
                if data['IMAGE_URL'] !='':
                    weixin.api_webwxsendmsgimgBy2in1(
                    weixin.User['UserName'],
                    group['UserName'],
                    data['IMAGE_URL'] )
                self.schedule.enter( configdata['SCHEDULE_EDU_ADD_TO_GROUP']['SCHEDULE_INTERVAL'], 0, self.sendEduAdd2Group, (weixin,group['UserName']))    
            else:
                print("这个时间段内没有新用户，不需要教育")
        if scheduleInterval <= 0 :
            scheduleInterval =  60*60 #如果没有设置间隔。那么 就缺省定一个1个小时的间隔。
        self.schedule.enter(scheduleInterval, 0, self.sendEduMsg, (weixin,)) #重新加入队列
    
    #在发欢迎消息一定时间后。会发一个加群的消息
    def sendEduAdd2Group(self,weixin,chatroomUserName):   
        print("增加了一条sendEduAdd2Group：%s"%chatroomUserName)
        configdata = getChatroomConfig()
        data = configdata['SCHEDULE_EDU_ADD_TO_GROUP']
        weixin.api_webwxsendmsg(data['VALUE'] +"   时间戳" +str(int(time.time())), chatroomUserName) 
        if data['IMAGE_URL'] !='':
            weixin.api_webwxsendmsgimgBy2in1(
            weixin.User['UserName'],
            chatroomUserName,
            data['IMAGE_URL'] ) 
          
    #启动schedule
    def schedule_thread(self,weixin):
        # enter用来安排某事件的发生时间，从现在起第n秒开始启动 
        self.schedule.enter(60, 0, self.sendEduMsg, (weixin,)) 
        self.schedule.enter(60, 0, self.nullJob, (weixin,)) 
        # 持续运行，直到计划时间队列变成空为止 
        self.schedule.run() 
        
    #先写一个空的job放着。这个方法可以后续修改
    def nullJob(self,weixin):
#         self.schedule.enter(60, 0, self.nullJob,(weixin,)) 
        print("null job ")

    #启动定时任务
    def handler_start_schedule(self,weixin):
        print(u"start handler_start_schedule") 
        t1 = threading.Thread(target=self.schedule_thread, args=(weixin,))
        t1.start()
        
if __name__ == '__main__':
    logger = logging.getLogger(__name__)
    if not sys.platform.startswith('win'):
        import coloredlogs
        coloredlogs.install(level='DEBUG')
        
    webwx = WebWeixin(DingDongBot())
    webwx.start()