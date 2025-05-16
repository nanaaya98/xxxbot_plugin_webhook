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
    version = "1.2.1"
    is_ai_platform = True  # 标记为 AI 平台插件，当对接webhook作为ai平台使用时建议修改为True

######################################基础配置######################################
    def __init__(self):                    #初始化方法，读取配置文件并设置属性
        super().__init__()

        self.enable = False
        self.admins = []
        self.webhook_url = None
        self.robotname = None
        self.processed_msg_ids = {}  # 将集合改为字典，键为消息 ID，值为处理时间
        self.auth_name="Authorization"
        self.token= None
        self.wxid = None

        # 读取主配置
        with open("main_config.toml", "rb") as f:
            main_config = tomllib.load(f)
            # 获取管理员列表
            self.admins = main_config.get("XYBot", {}).get("admins", [])
            self.version = main_config.get("Protocol", {}).get("version","849")

            if self.version == "849":
                self.api_type="VXAPI"
            elif self.version == "855":
                self.api_type="api"
            elif self.version == "ipad":
                self.api_type="api"
            elif self.version == "Mac":
                self.api_type="api"

        # 读取插件配置
        with open("plugins/Webhook_XXX/config.toml", "rb") as f:
            plugin_config = tomllib.load(f)

            config = plugin_config["Webhook"]

            self.enable = config["Enable"]
            self.webhook_url = config["Webhook_url"]
            self.robotname = config["Robotname"]
            self.auth_name = config["Auth_Name"]
            self.token=config["Token"]
            self.wxid=config["Wxid"]


    def clean_processed_msg_ids(self, time_window=3600):
        # 清理超过时间窗口的消息 ID
        current_time = time.time()
        expired_ids = [msg_id for msg_id, timestamp in self.processed_msg_ids.items() if current_time - timestamp > time_window]
        for msg_id in expired_ids:
            del self.processed_msg_ids[msg_id]

        
####################################处理文本消息####################################
    @on_text_message(priority=30)         #装饰器，指定消息类型和优先级
    async def handle_text(self, bot: WechatAPIClient, message: Dict):   #异步处理文本消息的方法
        if not self.enable:
            return None   
        else:
            # 使用正确的消息属性名称
            msg_id = message["MsgId"]                        
            content = message["Content"]
            sender_wxid = message["SenderWxid"]
            from_wxid = message["FromWxid"]
            is_group = message["IsGroup"]
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
            content=f"@{self.robotname} "+query
            msg = {
                "MsgId": msg_id,
                "MsgType": 1,
                "SenderWxid": sender_wxid,
                "FromWxid": from_wxid,
                "FromUserName":{"string":from_wxid},
                "Wxid":self.wxid,
                "IsGroup":is_group,
                "IsAt": is_at,
                "Content": content,
                "Query":query,                
            }

            if is_at == "group-at":
                return None
            else:
                logger.info(f"Webhook处理私聊文本消息: 消息ID:'{msg_id}'，发送人: '{sender_wxid}'，内容: '{query}'")
                return await self.send_webhook(msg)

####################################处理@消息####################################
    @on_at_message(priority=30)         #装饰器，指定消息类型和优先级
    async def handle_at(self, bot: WechatAPIClient, message: Dict):   #异步处理文本消息的方法
        # 添加日志记录消息详细信息
        if not self.enable:
            return None   
        else:
            # 使用正确的消息属性名称
            msg_id = message["MsgId" ]    
            content = message["Content"]
            sender_wxid = message["SenderWxid"]
            from_wxid = message["FromWxid"]
            is_group = message["IsGroup"]                    
            msg={ }
            if msg_id in self.processed_msg_ids:  # 检查消息 ID 是否已经处理过
                logger.info(f"消息 {msg_id} 已处理，跳过。")
                return None
            # 修改为字典操作，记录消息 ID 和处理时间
            self.processed_msg_ids[msg_id] = time.time() 

            query = content
            query = query.replace(f"@{self.robotname}", "").strip()
            content=f"@{self.robotname} "+query
            is_at = "group-at"
            msg = {
                "MsgId": msg_id,
                "MsgType": 1,
                "SenderWxid": sender_wxid,
                "FromWxid": from_wxid,
                "Wxid":self.wxid,
                "FromUserName":{"string":from_wxid},
                "IsGroup":is_group,
                "IsAt": is_at,
                "Content": content,
                "Query":query,
            }
        logger.info(f"Webhook处理群聊@消息: 消息ID:'{msg_id}'，发送人: '{sender_wxid}'，内容: '{query}'")
        return await self.send_webhook(msg)

####################################处理图片消息#################################### 
    @on_image_message(priority=30)
    async def handle_image(self, bot: WechatAPIClient, message: Dict):
        if not self.enable:
            return  None
        else:
            # 使用正确的消息属性名称
            msg_id = message["MsgId"]    
            content = message.get("Xml","")
            sender_wxid = message["SenderWxid"]
            from_wxid = message["FromWxid"]
            is_group = message["IsGroup"]
            data = {}

            md5=message["ImageMD5"]
            path=message["ImagePath"]
            base64=message["Content"]

            if is_group:    # 是否群聊
                is_at = "group-chat"
            else:
                is_at = "one-one-chat"

                data={
                    "base64":base64,
                    "path":path,
                    "md5":md5
                }                
            msg={
                "MsgId":msg_id,
                "MsgType":3,
                "SenderWxid":sender_wxid,
                "FromWxid":from_wxid,
                "Wxid":self.wxid,
                "FromUserName":{"string":from_wxid},
                "IsGroup":is_group,
                "IsAt":is_at,
                "Content":content,
                "Data":data,
                }
        logger.info(f"Webhook处理图片消息: 消息ID:'{msg_id}'，来自: '{from_wxid}',md5: '{md5}'")
        return await self.send_webhook(msg)

####################################处理文件消息#################################### 
    @on_xml_message(priority=30)
    async def handle_xml(self, bot: WechatAPIClient, message: Dict):
        if not self.enable:
            return  None
        else:
            # 使用正确的消息属性名称
            msg_id = message["MsgId"]
            content = message["Content"]
            sender_wxid = message["SenderWxid"]
            from_wxid = message["FromWxid"]
            is_group = message["IsGroup"]
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
                msg_type = 6  
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
                    "totallen":int(totallen),
                    "fileext":fileext,
                }
                logger.info(f"Webhook处理文件消息: 消息ID:'{msg_id}'，发送人: '{sender_wxid}'，内容: '{title}'")
                
            msg={
                "MsgId":msg_id,
                "MsgType":msg_type,
                "SenderWxid":sender_wxid,
                "FromWxid":from_wxid,
                "FromUserName":{"string":from_wxid},
                "Wxid":self.wxid,
                "IsGroup":is_group,
                "IsAt":is_at,
                "Content":content,
                "Data":data,
            }
        return await self.send_webhook(msg)
         
####################################处理引用消息#################################### 
    @on_quote_message(priority=30)         #装饰器，指定消息类型和优先级
    async def handle_quote(self, bot: WechatAPIClient, message: Dict):   #异步处理引用消息的方法
        if not self.enable:
            return None   
        else:
            # 使用正确的消息属性名称
            msg_id = message["MsgId"]  
            content = message["Content"]
            sender_wxid = message["SenderWxid"]
            from_wxid = message["FromWxid"]
            is_group = message["IsGroup"]
            quote_data = message["Quote"]
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
            content=f"@{self.robotname} "+query
            msg = {
                "MsgId": msg_id,
                "MsgType": 49,
                "SenderWxid": sender_wxid,
                "FromWxid": from_wxid,
                "IsGroup":is_group,
                "FromUserName":{"string":from_wxid},
                "Wxid":self.wxid,
                "IsAt": is_at,
                "Content": content,
                "Query":query,
                "QuotedMessage":quote_data
            }

        logger.info(f"Webhook处理引用消息: 消息ID:'{msg_id}'，发送人: '{sender_wxid}'，内容: '{query}'")
        return await self.send_webhook(msg)

####################################处理语音消息####################################
    @on_voice_message(priority=30)         #装饰器，指定消息类型和优先级
    async def handle_voice(self, bot: WechatAPIClient, message: Dict):   #异步处理语音消息的方法
        if not self.enable:
            return None   
        else:
              msg = message
        return await self.send_webhook(msg)

####################################调用Webhook####################################              
    async def send_webhook(self, msg):
        result = None  # 初始化 result 变量
        if self.webhook_url:            
            try:
                if self.token is None:
                    headers = {
                        'Content-Type': 'application/json',  # 基础 JSON 格式声明
                        }
                headers = {
                    'Content-Type': 'application/json',  # 基础 JSON 格式声明
                    f'{self.auth_name}': f'{self.token}',  # 示例：添加认证令牌
                    }
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(self.webhook_url, json=msg,headers=headers) as response:
                        if response.status != 200:
                            logger.error(f'Webhook 请求失败，状态码: {response.status}')
                        else:
                            
                            result = await response.json()
                            logger.info(f'Webhook 请求成功，状态码: {response.status}, 响应: {result}')

####################################返回消息####################################
                            output_type = result.get("output_type",None)
                            output= result.get("output",None)
                            res_base_url=f"http://127.0.0.1:9011/{self.api_type}" 
                            if output_type is not None:

                                ###########################返回文本消息###########################
                                if output_type == "text":
                                    if len(output) > 1000:
                                        if  "[思考结束]" in output:
                                            parts = output.split("[思考结束]")
                                            output = parts[1].strip()

                                        soft_limit=300
                                        fragments = []
                                        cursor = 0
                                        output_len = len(output)
                                            
                                        while cursor < output_len:
                                        # 剩余长度不足时直接取剩余部分
                                            if output_len - cursor <= soft_limit:
                                                fragments.append(output[cursor:])
                                                break
                                            
                                            search_start = cursor + soft_limit                                            
                                            newline_pos = output.find('\n\n', search_start)                                                   
                                            if newline_pos != -1:
                                                # 包含双换行符本身
                                                fragments.append(output[cursor:newline_pos + 2])
                                                cursor = newline_pos + 2  # 移动游标到双换行符之后
                                            else:
                                                # 无后续双换行符时取剩余全部
                                                fragments.append(output[cursor:])
                                                break

                                        # 检查fragments是否为空
                                        if not fragments:
                                            logger.warning("分割后的消息片段为空，跳过发送")

                                        for fragment in fragments:
                                            current_fragment = fragment
                                            try:
                                                res_url=f"{res_base_url}/Msg/SendTxt"
                                                body={
                                                    "Wxid":msg["Wxid"],
                                                    "ToWxid":msg["FromWxid"],
                                                    "Type":1,
                                                    "Content":current_fragment,
                                                    }
                                                async with aiohttp.ClientSession() as session:
                                                    async with session.post(res_url, json=body) as response:
                                                        if response.status!= 200:
                                                            logger.error(f'Webhook 回复消息失败，状态码: {response.status}')
                                                        else:
                                                            logger.info(f'Webhook 回复消息成功，状态码: {response.status}, 响应: {body}')  
                                                            await asyncio.sleep(2)  # 等待2秒
                                            except Exception as e:
                                                logger.error(f' Webhook 回复时请求出错: {e}')  
                                            
                                    else:
                                        try:
                                            res_url=f"{res_base_url}/Msg/SendTxt"
                                            body={
                                                "Wxid":msg["Wxid"],
                                                "ToWxid":msg["FromWxid"],
                                                "Type":1,
                                                "Content":output,
                                                }
                                            async with aiohttp.ClientSession() as session:
                                                async with session.post(res_url, json=body) as response:
                                                    if response.status!= 200:
                                                        logger.error(f'Webhook 回复消息失败，状态码: {response.status}')
                                                    else:
                                                        logger.info(f'Webhook 回复消息成功，状态码: {response.status}, 响应: {body}')  
                                        except Exception as e:
                                            logger.error(f' Webhook 回复时请求出错: {e}')
                                
                                ###########################返回图片消息###########################
                                elif output_type == "image":
                                    try:
                                        res_url=f"{res_base_url}/Msg/UploadImg"
                                        body={
                                            "Wxid":msg["Wxid"],
                                            "ToWxid":msg["FromWxid"],
                                            "Base64":output,
                                            }
                                        async with aiohttp.ClientSession() as session:
                                            async with session.post(res_url, json=body) as response:
                                                if response.status!= 200:
                                                    logger.error(f'Webhook 回复消息失败，状态码: {response.status}')
                                                else:
                                                    logger.info(f'Webhook 回复消息成功，状态码: {response.status}, 响应: {body}')   
                                    except Exception as e:
                                        logger.error(f' Webhook 回复时请求出错: {e}')
                               
                                ###########################返回语音消息###########################
                                elif output_type == "voice":
                                    try:
                                        voice_type=result.get("type",None)
                                        voice_time=result.get("time",None)
                                        res_url=f"{res_base_url}/Msg/SendVoice"
                                        body={
                                            "Wxid":msg["Wxid"],
                                            "ToWxid":msg["FromWxid"],
                                            "Type":voice_type,         #Type： AMR = 0, MP3 = 2, SILK = 4, SPEEX = 1, WAVE = 3
                                            "VoiceTime":voice_time,
                                            "Base64":output,
                                            }
                                        async with aiohttp.ClientSession() as session:
                                            async with session.post(res_url, json=body) as response:
                                                if response.status!= 200:
                                                    logger.error(f'Webhook 回复消息失败，状态码: {response.status}')
                                                else:
                                                    logger.info(f'Webhook 回复消息成功，状态码: {response.status}, 响应: {body}')
                                    except Exception as e:
                                        logger.error(f' Webhook 回复时请求出错: {e}')


            except Exception as e:
                logger.error(f'发送 Webhook 请求时出错: {e}')
        else:
            logger.error('Webhook URL 未设置')
        
        return 


