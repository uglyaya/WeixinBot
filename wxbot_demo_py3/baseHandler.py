#!/usr/bin/env python
# coding: utf-8
import weixin  
import logging
import random
import sys
from weixin import WebWeixin

class BaseHandler():
    #处理新加好友验证
    def handler_useradd_notify(self,weixin,msg):
        print("basehandler handler_useradd_notify")
    
    #处理收到的文本消息
    def handler_text_msg(self,weixin,msg):
        print("basehandler handler_text_msg")
                  
    def handler_sys_msg(self,weixin,msg):
        print("basehandler handler_sys_msg")

if __name__ == '__main__': 
    logger = logging.getLogger(__name__)
    if not sys.platform.startswith('win'):
        import coloredlogs
        coloredlogs.install(level='DEBUG')
        
    webwx = WebWeixin(BaseHandler())
    webwx.start()