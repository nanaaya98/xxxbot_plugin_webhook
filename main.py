import re                                  #用于正则表达式操作
import tomllib                              #用于解析TOML格式的配置文件
import aiohttp                              #异步HTTP客户端库
import logging                              #用于记录日志信息
import time                                 #用于时间相关操作
import xml.etree.ElementTree as ET          #用于解析XML格式的配置文件

from WechatAPI import WechatAPIClient       #微信API模块
from utils.decorators import *              #装饰器模块
from utils.plugin_base import PluginBase    #插件必备模块
from typing import Dict, List, Optional, Union, Any  #类型提示模块
from loguru import logger                    #日志记录模块



################Webhook对接插件，用于将系统与外部服务通过Webhook进行集成################
class Webhook_XXX(PluginBase):                 #定义Webhook类，继承PluginBase类
    name = "Webhook_XXX"
    description = "Webhook对接插件"
    author = "喵子柒"
    version = "1.1.0"
    is_ai_platform = False  # 标记为 AI 平台插件，当对接webhook作为ai平台使用时建议修改为True

######################################基础配置######################################
    def __init__(self):                    #初始化方法，读取配置文件并设置属性
        super().__init__()

        self.enable = False
        self.admins = []
        self.webhook_url = None
        self.robotname = None
        self.processed_msg_ids = {}  # 将集合改为字典，键为消息 ID，值为处理时间

        # 读取主配置
        with open("main_config.toml", "rb") as f:
            main_config = tomllib.load(f)
            # 获取管理员列表
            self.admins = main_config.get("XYBot", {}).get("admins", [])

        # 读取插件配置
        with open("plugins/Webhook_XXX/config.toml", "rb") as f:
            plugin_config = tomllib.load(f)

            config = plugin_config["Webhook"]

            self.enable = config["Enable"]
            self.webhook_url = config["Webhook_url"]
            self.robotname = config["Robotname"]


    def clean_processed_msg_ids(self, time_window=3600):
        # 清理超过时间窗口的消息 ID
        current_time = time.time()
        expired_ids = [msg_id for msg_id, timestamp in self.processed_msg_ids.items() if current_time - timestamp > time_window]
        for msg_id in expired_ids:
            del self.processed_msg_ids[msg_id]

        
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
                is_at = "group-chat"
                    # 是否群聊@机器人或私聊
                if f"@{self.robotname}" in query:
                    query = query.replace(f"@{self.robotname}", "").strip()
                    is_at = "group-at"
            else:
                is_at = "one-one-chat"
            msg = {
                "MsgId": msg_id,
                "MsgType": 1,
                "SenderWxid": sender_wxid,
                "FromWxid": from_wxid,
                "IsGroup":is_group,
                "IsAt": is_at,
                "Content": query,
            }

            if is_at == "group-at":
                return None
            else:
                logger.info(f"Webhook处理私聊文本消息: 消息ID:'{msg_id}'，发送人: '{sender_wxid}'，内容: '{query}'")
                return await self.send_webhook(msg)

####################################处理@消息####################################
    @on_at_message(priority=60)         #装饰器，指定消息类型和优先级
    async def handle_at(self, bot: WechatAPIClient, message: Dict):   #异步处理文本消息的方法
        # 添加日志记录消息详细信息
        logger.info(f"收到处理@消息请求，消息内容: {message}")
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

            if msg_id in self.processed_msg_ids:  # 检查消息 ID 是否已经处理过
                logger.info(f"消息 {msg_id} 已处理，跳过。")
                return None
            # 修改为字典操作，记录消息 ID 和处理时间
            self.processed_msg_ids[msg_id] = time.time() 

            query = content
            query = query.replace(f"@{self.robotname}", "").strip()
            is_at = "group-at"
            msg = {
                "MsgId": msg_id,
                "MsgType": 1,
                "SenderWxid": sender_wxid,
                "FromWxid": from_wxid,
                "IsGroup":is_group,
                "IsAt": is_at,
                "Content": query,
            }
        logger.info(f"Webhook处理群聊@消息: 消息ID:'{msg_id}'，发送人: '{sender_wxid}'，内容: '{query}'")
        return await self.send_webhook(msg)

####################################处理图片消息#################################### 
    @on_image_message(priority=50)
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

            if is_group:    # 是否群聊
                is_at = "group-chat"
            else:
                is_at = "one-one-chat"

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
                "MsgId":msg_id,
                "MsgType":3,
                "SenderWxid":sender_wxid,
                "FromWxid":from_wxid,
                "IsGroup":is_group,
                "IsAt":is_at,
                "Content":content,
                "Data":data,
                }
        logger.info(f"Webhook处理图片消息: 消息ID:'{msg_id}'，来自: '{from_wxid}',aeskey: '{aeskey}',length: '{length}',md5: '{md5}'")
        return await self.send_webhook(msg)

####################################处理文件消息#################################### 
    @on_xml_message(priority=50)
    async def handle_xml(self, bot: WechatAPIClient, message: Dict):
        if not self.enable:
            return  None
        else:
            # 使用正确的消息属性名称
            msg_id = message.get("MsgId", "")            
            content = message.get("Content", "")
            sender_wxid = message.get("SenderWxid", "")
            from_wxid = message.get("FromWxid", "")
            is_group = message.get("IsGroup", False)
            xml_content = content
            msg_type=None
            data = {}
            if is_group:    # 是否群聊
                is_at = "group-chat"
            else:
                is_at = "one-one-chat"

            if message.get("Quote"):
                return None
            elif not message.get("Quote"):

                msg_type=6,
                 # 提取title
                title_match = re.search(r'<title>(.*?)</title>', xml_content)
                if title_match:
                    title = title_match.group(1)      

                # 提取md5
                md5_match = re.search(r'<md5>(.*?)</md5>', xml_content)
                if md5_match:
                    md5 = md5_match.group(1)    
        
                # 提取appid
                appid_match = re.search(r'<appmsg appid="([^"]*)"', xml_content)
                if appid_match:
                    appid = appid_match.group(1)

                attach_id_match = re.search(r'<attachid>(.*?)</attachid>', xml_content)
                if attach_id_match:
                    attach_id = attach_id_match.group(1)                    
        
                # 提取totallen
                totallen_match = re.search(r'<totallen>(.*?)</totallen>', xml_content)
                if totallen_match:
                    totallen = int(totallen_match.group(1))

                fileext_match = re.search(r'<fileext>(.*?)</fileext>', xml_content)
                if fileext_match:
                    fileext = fileext_match.group(1)     
                
                data={
                    "Content":title,
                    "md5":md5,
                    "appid":appid,
                    "attachid":attach_id,
                    "totallen":totallen,
                    "fileext":fileext,
                }
                logger.info(f"Webhook处理文件消息: 消息ID:'{msg_id}'，发送人: '{sender_wxid}'，内容: '{title}'")
                
            msg={
                "MsgId":msg_id,
                "MsgType":msg_type,
                "SenderWxid":sender_wxid,
                "FromWxid":from_wxid,
                "IsGroup":is_group,
                "IsAt":is_at,
                "Content":content,
                "Data":data,
            }
        return await self.send_webhook(msg)
         
####################################处理引用消息#################################### 
    @on_quote_message(priority=50)         #装饰器，指定消息类型和优先级
    async def handle_quote(self, bot: WechatAPIClient, message: Dict):   #异步处理引用消息的方法
        if not self.enable:
            return None   
        else:
            # 使用正确的消息属性名称
            msg_id = message.get("MsgId", "")                         
            content = message.get("Content", "")
            sender_wxid = message.get("SenderWxid", "")
            from_wxid = message.get("FromWxid", "")
            is_group = message.get("IsGroup", False)
            quote_data = message.get("Quote", {})
            msg={ }
            is_at = "group-chat"
            query = content
            # 处理特殊空格字符 \\u2005（四分之一em空格）
            if '\\u2005' in query:
                query = query.replace('\\u2005', " ").strip()

            if is_group:    # 是否群聊
                # 是否群聊@机器人或私聊
                    if f"@{self.robotname}" in query:
                        query = query.replace(f"@{self.robotname}", "").strip()
                        is_at = "group-at"
            else:
                is_at = "one-one-chat"

            msg = {
                "MsgId": msg_id,
                "MsgType": 49,
                "SenderWxid": sender_wxid,
                "FromWxid": from_wxid,
                "IsGroup":is_group,
                "IsAt": is_at,
                "Content": query,
                "QuotedMessage":quote_data
            }

        logger.info(f"Webhook处理引用消息: 消息ID:'{msg_id}'，发送人: '{sender_wxid}'，内容: '{query}'")
        return await self.send_webhook(msg)

####################################处理语音消息####################################
    @on_voice_message(priority=50)         #装饰器，指定消息类型和优先级
    async def handle_voice(self, bot: WechatAPIClient, message: Dict):   #异步处理语音消息的方法
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

            if is_group:    # 是否群聊
                is_at = "group-chat"
            else:
                is_at = "one-one-chat"
            
            voice_length = None
            bufid = None
            voiceformat = None
            length = None
            aeskey = None
            voiceurl = None
 

            # 提取VoiceLength
            voicelength_match = re.search(r'voicelength="(\d+)"', query)
            if voicelength_match:
                voice_length = int(voicelength_match.group(1))
        
            # 提取BufId
            bufid_match = re.search(r'bufid="([^"]*)"', query)
            if bufid_match:
                bufid = bufid_match.group(1)

            # 提取voiceformat
            voiceformat_match = re.search(r'voiceformat="([^"]*)"', query)
            if voiceformat_match:
                voiceformat = voiceformat_match.group(1)

            # 提取Length
            length_match = re.search(r'length="(\d+)"', query)
            if length_match:
                length = int(length_match.group(1))

            # 提取aeskey
            aeskey_match = re.search(r'aeskey="([^"]*)"', query)
            if aeskey_match:
                aeskey = aeskey_match.group(1)   
            
            # 提取voiceurl
            voiceurl_match = re.search(r'voiceurl="([^"]*)"', query)
            if voiceurl_match:
                voiceurl = voiceurl_match.group(1)   
            
            data={
                "voice_length":voice_length,
                "bufid":bufid,
                "voiceformat":voiceformat,
                "length":length,
                "aeskey":aeskey,
                "voiceurl":voiceurl,    
            }

            msg = {
                "MsgId": msg_id,
                "MsgType": 34,
                "SenderWxid": sender_wxid,
                "FromWxid": from_wxid,
                "IsGroup":is_group,
                "IsAt": is_at,
                "Content": query,
                "Data":data
            }
        logger.info(f"Webhook处理语音消息: 消息ID:'{msg_id}'，发送人: '{sender_wxid}'，内容: '{query}'")
        return await self.send_webhook(msg)

####################################调用Webhook####################################              
    async def send_webhook(self, msg):
        if self.webhook_url:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(self.webhook_url, json=msg) as response:
                        if response.status != 200:
                            logger.error(f'Webhook 请求失败，状态码: {response.status}')
                        else:
                            logger.info(f'Webhook 请求成功，状态码: {response.status}')
                            result = await response.json()
            except Exception as e:
                logger.error(f'发送 Webhook 请求时出错: {e}')
        else:
            logger.error('Webhook URL 未设置')
        return await response.json()
