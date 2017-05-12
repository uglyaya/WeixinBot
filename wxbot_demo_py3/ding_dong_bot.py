#!/usr/bin/env python
# coding: utf-8 
from weixin import WebWeixin
import re
import logging
import random
import sys 
from baseHandler import BaseHandler

class DingDongBot(BaseHandler):
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
       
        if content == 'ding'  :
            print('%s -> %s : %s'%(fromUserName,toUserName,content))
            weixin.api_webwxsendmsg("""
            目前支持指令
            1。创建聊天室
            2。扫描聊天室
            3。聊天室加人
            4。聊天室删人
            5。聊天室改名
            6。聊天室艾特
            7。聊天室发图
                    """, groupUserName if isGroupMsg else fromUserName)
        
        if content == '聊天室发图' : 
            weixin.api_webwxsendmsgimgBy2in1(
                weixin.User['UserName'],
                groupUserName if isGroupMsg else fromUserName, 
                'pic.png')
            
        if content == '聊天室艾特' :
            nickname = weixin.getUserRemarkNameById(fromUserName)
            weixin.api_webwxsendmsg('@%s 你好[微笑]'%nickname, groupUserName if isGroupMsg else fromUserName)
    
        if content == '创建聊天室' :
            uid = weixin.getUserIDByName('小丁丁')
            uid2 = weixin.getUserIDByName('丁')
            uid3 = fromUserName
            topic = "AYA"+str(msg['MsgId'])
            groupid = weixin.api_webwxcreatechatroom([uid3,uid2,uid],topic)
            weixin.api_webwxsendmsg('创建聊天室创建成功', groupid)
            
        if content == '扫描聊天室' :
            groups = weixin.getGroupListByName('AYA')
            for group in groups: 
                weixin.api_webwxsendmsg('我在这里[微笑]', group['UserName'])
        
        if content == '聊天室改名' :
            groups = weixin.getGroupListByName('AYA')
            for group in groups: 
                weixin.api_webwxupdatechatroomModifyTopic(group['UserName'], "AYA"+str(random.random()))
                
        if content == '聊天室加人' : 
            uid = weixin.getUserIDByName('丁丁')
            uid2 = weixin.getUserIDByName('丁')
            groups = weixin.getGroupListByName('AYA')
            for group in groups: 
                weixin.api_webwxupdatechatroomAddMember(group['UserName'],[uid,uid2])
                
        if content == '聊天室删人' : 
            uid = weixin.getUserIDByName('丁丁')
            uid2 = weixin.getUserIDByName('丁')
            groups = weixin.getGroupListByName('AYA')
            for group in groups: 
                weixin.api_webwxupdatechatroomDelMember(group['UserName'],[uid,uid2])     
                  
    def handler_sys_msg(self,weixin,msg):
        fromUserName = msg['FromUserName']
        toUserName =msg['ToUserName']
        m = re.search(r'邀请(.+)加入了群聊', msg['Content'])
        if m:
            name = m.group(1)
            print("%s 加入了群聊: %s"%(name,toUserName))
        
        m = re.search(r'(.+)修改群名为“(.+)”', msg['Content'])
        if m:
            name = m.group(1)
            toname = m.group(2)
            print("修改群名为: %s|%s"%(name,toname))

if __name__ == '__main__':
    logger = logging.getLogger(__name__)
    if not sys.platform.startswith('win'):
        import coloredlogs
        coloredlogs.install(level='DEBUG')
        
    webwx = WebWeixin(DingDongBot())
    webwx.start()