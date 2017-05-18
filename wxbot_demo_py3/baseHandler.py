#!/usr/bin/env python
# coding: utf-8
import weixin
import logging 
import sys,threading
import time,sched
from threading import Timer  
# from weixin import WebWeixin

class BaseHandler():
    schedule = sched.scheduler(time.time, time.sleep) 

    def schedule_thread(self,weixin):
        pass
#         enter用来安排某事件的发生时间，从现在起第n秒开始启动 
#         self.schedule.enter( 5, 0, self.self_job, (weixin,)) 
#         # 持续运行，直到计划时间队列变成空为止 
#         self.schedule.run() 
        
    def self_job(self,weixin):
        pass
#         self.schedule.enter(5, 0, self.handler_job,(weixin,)) 
#         print ("now is", time.time() , "enter_the_box_time is")  
        
    #启动定时任务
    def handler_start_schedule(self,weixin):
        print(u"start handler_start_schedule") 
        t1 = threading.Thread(target=self.schedule_thread, args=(weixin,))
        t1.start()
        
    #处理新加好友验证
    def handler_useradd_notify(self,weixin,msg):
        print("basehandler handler_useradd_notify")
    
    #处理收到的文本消息
    def handler_text_msg(self,weixin,msg):
        print("basehandler handler_text_msg")
                  
    def handler_sys_msg(self,weixin,msg):
        print("basehandler handler_sys_msg")
# 
# if __name__ == '__main__': 
#     logger = logging.getLogger(__name__)
#     if not sys.platform.startswith('win'):
#         import coloredlogs
#         coloredlogs.install(level='DEBUG')
#         
#     webwx = WebWeixin(BaseHandler())
#     webwx.start()