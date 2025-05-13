import tomllib                              #用于解析TOML格式的配置文件
import aiohttp                              #异步HTTP客户端库
import logging                              #用于记录日志信息
import xml.etree.ElementTree as ET          #用于解析XML格式的配置文件

from WechatAPI import WechatAPIClient       #微信API模块
from utils.decorators import *              #装饰器模块
from utils.plugin_base import PluginBase    #插件必备模块
from typing import Dict, List, Optional, Union, Any  #类型提示模块
from loguru import logger                    #日志记录模块



################Webhook对接插件，用于将系统与外部服务通过Webhook进行集成################
class Webhook(PluginBase):                 #定义Webhook类，继承PluginBase类
    name = "Webhook"
    description = "Webhook对接插件"
    author = "喵子柒"
    version = "1.0.0"
    is_ai_platform = False  # 标记为 AI 平台插件，当对接webhook作为ai平台使用时建议修改为True

######################################基础配置######################################
    def __init__(self):                    #初始化方法，读取配置文件并设置属性
        super().__init__()

        self.enable = False
        self.admins = []
        self.webhook_url = None
        self.priority_set = 50
        self.robot_names=[]

        # 读取主配置
        with open("main_config.toml", "rb") as f:
            main_config = tomllib.load(f)
            # 获取管理员列表
            self.admins = main_config.get("XYBot", {}).get("admins", [])

        # 读取插件配置
        with open("plugins/Webhook/config.toml", "rb") as f:
            plugin_config = tomllib.load(f)

            config = plugin_config["Webhook"]

            self.enable = config["Enable"]
            self.webhook_url = config["Webhook_url"]
            self.priority_set = config["Priority"]
            self.robot_names=config.get("Robot_names",[])
        
####################################处理文本消息####################################
    @on_text_message(priority=50)         #装饰器，指定消息类型和优先级
    async def handle_text(self, bot: WechatAPIClient, message: Dict):   #异步处理文本消息的方法
        if not self.enable:
            return None   
        else:
            # 使用正确的消息属性名称
            msg_id = message.get("MsgId", "")                         
            content = message.get("Content", "")
            sender_wxid = message.get("SenderWxid", "")
            from_wxid = message.get("FromWxid", "")
            is_group = message.get("IsGroup", False)
            msg={ }
            query = content

            # 处理特殊空格字符 \\u2005（四分之一em空格）
            if '\\u2005' in query:
                query = query.replace('\\u2005', " ").strip()

            if is_group:    # 是否群聊
                return None
            else:
                is_at = "one-one-chat"
            msg = {
                "msg_id": msg_id,
                "msg_type": 1,
                "sender_wxid": sender_wxid,
                "from_wxid": from_wxid,
                "is_at": is_at,
                "content": query,
            }
            logger.info(f"Webhook处理私聊文本消息: 消息ID:'{msg_id}'，发送人: '{sender_wxid}'，内容: '{query}'")
            return await self.send_webhook(msg)

####################################处理@消息####################################
    @on_at_message(priority=50)         #装饰器，指定消息类型和优先级
    async def handle_at(self, bot: WechatAPIClient, message: Dict):   #异步处理文本消息的方法
        if not self.enable:
            return None   
        else:
            # 使用正确的消息属性名称
            msg_id = message.get("MsgId", "")                         
            content = message.get("Content", "")
            sender_wxid = message.get("SenderWxid", "")
            from_wxid = message.get("FromWxid", "")
            is_group = message.get("IsGroup", False)
            msg={ }
            query = content
            is_at = "group-no_at"


            # 处理特殊空格字符 \\u2005（四分之一em空格）
            if '\\u2005' in query:
                query = query.replace('\\u2005', " ").strip()

            # 是否群聊@机器人或私聊
            for robot_name in self.robot_names:
                if f"@{robot_name}" in query:
                    query = query.replace(f"@{robot_name}", "").strip()
                    is_at = "group-at"
                    logger.info(f"Webhook处理群聊@消息: 消息ID:'{msg_id}'，来自: '{from_wxid}'，发送人: '{sender_wxid}'，内容: '{query}'")
                    break
            msg = {
                "msg_id": msg_id,
                "msg_type": 1,
                "sender_wxid": sender_wxid,
                "from_wxid": from_wxid,
                "is_at": is_at,
                "content": query,
            }
            logger.info(f"Webhook处理私聊文本消息: 消息ID:'{msg_id}'，发送人: '{sender_wxid}'，内容: '{query}'")
            return await self.send_webhook(msg)

####################################处理图片消息#################################### 
    @on_image_message
    async def handle_image(self, bot: WechatAPIClient, message: Dict):
        if not self.enable:
            return  None
        else:
            # 使用正确的消息属性名称
            msg_id = message.get("MsgId", "")            
            content = message.get("Content", "")
            sender_wxid = message.get("SenderWxid", "")
            from_wxid = message.get("FromWxid", "")
            is_group = message.get("IsGroup", False)
            data = {}

            aeskey, cdnmidimgurl, length, md5 = None, None, None, None
            
            root = ET.fromstring(content)
            img_element = root.find('img')
            if img_element is not None:
                aeskey = img_element.get('aeskey')
                cdnmidimgurl = img_element.get('cdnmidimgurl')
                cdnthumbaeskey = img_element.get('cdnthumbaeskey')
                length = img_element.get('length')
                md5 = img_element.get('md5')

                data={
                    "aeskey":aeskey,
                    "cdnmidimgurl":cdnmidimgurl,
                    "cdnthumbaeskey":cdnthumbaeskey,
                    "length":length,
                    "md5":md5
                }                
            msg={
                "msg_id":msg_id,
                "msg_type":3,
                "sender_wxid":sender_wxid,
                "from_wxid":from_wxid,
                "is_group":is_group,
                "content":content,
                "data":data,
                }
            logger.info(f"Webhook处理图片消息: 消息ID:'{msg_id}'，来自: '{from_wxid}',aeskey: '{aeskey}',length: '{length}',md5: '{md5}'")
            return await self.send_webhook(msg)


####################################调用Webhook####################################              
    async def send_webhook(self, msg):
        if self.webhook_url:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(self.webhook_url, json=msg) as response:
                        if response.status != 200:
                            logger.error(f'Webhook 请求失败，状态码: {response.status}')
            except Exception as e:
                logger.error(f'发送 Webhook 请求时出错: {e}')
        else:
            logger.error('Webhook URL 未设置')
        return await response.json()