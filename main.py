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
from datetime import datetime               #用于日期和时间操作

import base64                                #用于Base64编码解码操作
import wave                                  #用于处理WAV音频文件
import io                                     #用于输入输出操作
import argparse                              #用于解析命令行参数



################Webhook对接插件，用于将系统与外部服务通过Webhook进行集成################
class Webhook_XXX(PluginBase):                 #定义Webhook类，继承PluginBase类
    name = "Webhook_XXX"
    description = "Webhook对接插件"
    author = "喵子柒"
    version = "1.2.5"
    is_ai_platform = True  # 标记为 AI 平台插件，当对接webhook作为ai平台使用时建议修改为True

######################################基础配置######################################
    def __init__(self):                    #初始化方法，读取配置文件并设置属性
        super().__init__()

        self.enable = False
        self.admins = []
        self.webhook_url = None
        self.robotname = None
        self.processed_msg_ids = {}
        self.auth_name = "Authorization"
        self.token = None
        self.wxid = None
        self.api_type = None

        self._load_main_config()
        self._load_plugin_config()

    def _load_main_config(self):
        with open("main_config.toml", "rb") as f:
            main_config = tomllib.load(f)
            self.admins = main_config.get("XYBot", {}).get("admins", [])
            self.version = main_config.get("Protocol", {}).get("version","849")

            if self.version == "849":
                self.api_type="VXAPI"
            else:
                self.api_type="api"



    def _load_plugin_config(self):
        with open("plugins/Webhook_XXX/config.toml", "rb") as f:
            plugin_config = tomllib.load(f)
            config = plugin_config["Webhook"]

            self.enable = config["Enable"]
            self.webhook_url = config["Webhook_url"]
            self.robotname = config["Robotname"]
            self.auth_name = config["Auth_Name"]
            self.token = config["Token"]
            self.wxid = config["Wxid"]


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
                    content=f"@{self.robotname} "+query
            else:
                is_at = "one-one-chat"
            
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
                return await self.send_webhook(msg,bot)

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
        return await self.send_webhook(msg,bot)

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
        return await self.send_webhook(msg,bot)

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
        return await self.send_webhook(msg,bot)
         
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
                        content=f"@{self.robotname} "+query
            else:
                is_at = "one-one-chat"
            
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
        return await self.send_webhook(msg,bot)

####################################处理语音消息####################################
    @on_voice_message(priority=30)         #装饰器，指定消息类型和优先级
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
            silk_base64=""
            wav_base64=""
            silk_base64 = await self.bot.download_voice(msg_id, voiceurl, length)
            audio_data = base64.b64decode(silk_base64)
            # 创建内存中的WAV文件
            with io.BytesIO() as wav_buffer:
                with wave.open(wav_buffer, 'wb') as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(8000)
                    wf.writeframes(audio_data)
            
                # 获取WAV文件的二进制数据
                wav_binary = wav_buffer.getvalue()
                # 将WAV二进制数据编码为Base64
                wav_base64 = base64.b64encode(wav_binary).decode('utf-8')
            data={
                "voice_length":voice_length,
                "bufid":bufid,
                "voiceformat":voiceformat,
                "length":length,
                "aeskey":aeskey,
                "voiceurl":voiceurl,   
                "wav_base64":wav_base64, 
            }

            msg = {
                "MsgId": msg_id,
                "MsgType": 34,
                "SenderWxid": sender_wxid,
                "FromWxid": from_wxid,
                "Wxid":self.wxid,
                "IsGroup":is_group,
                "IsAt": is_at,
                "Content": query,
                "Data":data
            }
        return await self.send_webhook(msg,bot)

####################################调用Webhook####################################              
    async def send_webhook(self, msg, bot: WechatAPIClient):
        result = None  # 初始化 result 变量
        if self.webhook_url:            
            try:
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
                            return await self.res_msg(msg,result,bot)
            except Exception as e:
                logger.error(f'发送 Webhook 请求时出错: {e}')
        else:
            logger.error('Webhook URL 未设置')

####################################返回消息####################################
    async def res_msg(self, msg, result,bot: WechatAPIClient):
        output_type = result.get("output_type",None)
        base_url=f'http://127.0.0.1:9011/{self.api_type}'
        if output_type is None:
            logger.error(f'Webhook 回复消息失败，未获取到输出类型')
        else:
            ###########################返回文本消息###########################
            if output_type == "text":
                output= result.get("output",None)
                if  "[思考结束]" in output:
                    parts = output.split("[思考结束]")
                    output = parts[1].strip()
                 
                soft_limit = 100    # 分割量
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
                        # 截取内容到双换行符之前，并移动游标跳过双换行符
                        fragments.append(output[cursor:newline_pos])
                        cursor = newline_pos + 2
                    else:
                        # 无后续双换行符时取剩余全部
                        fragments.append(output[cursor:])
                        break

                # 检查fragments是否为空
                if not fragments:
                    logger.warning("分割后的消息片段为空，跳过发送")
                    await bot.send_text_message(msg["FromWxid"], output)

                for fragment in fragments:
                    current_fragment = fragment.replace(f"\n\n", "\n").strip() 
                    try:
                        await bot.send_text_message(msg["FromWxid"], current_fragment)
                        
                    except Exception as e:
                        logger.error(f' Webhook 回复时请求出错: {e}')  
                        return True
                return False
                                                                           
            ###########################返回图片消息###########################
            elif output_type == "image":
                output= result.get("output",None)
                try:
                    await bot.send_image_message(msg["FromWxid"], output)
                    return False
                except Exception as e:
                    logger.error(f' Webhook 回复时请求出错: {e}')
                    return True
                               
            ###########################返回语音消息###########################
            elif output_type == "voice":
                output= result.get("output",None)
                voice_type=result.get("type","mp3")
                try:
                    await bot.send_voice_message(msg["FromWxid"], voice=output, format=voice_type)
                    return False
                except Exception as e:
                    logger.error(f' Webhook 回复时请求出错: {e}')
                    return True
            ###########################返回link消息###########################
            elif output_type == "link":
                output= result.get("output",None)
                pic_re_url=f'{base_url}/Friend/GetContractDetail' 
                pic_re_msg={
                    "Wxid":self.wxid,
                    "Towxids":self.wxid
                }

                async with aiohttp.ClientSession() as session:
                    async with session.post(pic_re_url, json=pic_re_msg) as response:
                        json_resp = await response.json()
                        contact_list = json_resp.get("Data", {}).get("ContactList", [])
                        thumb_url = contact_list[0].get("SmallHeadImgUrl") if contact_list else None
                        

                title=f"👏文本内容👏"
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                desc=f"点击查看内容\n⌚时间：{now}"
                simple_xml = f"<appmsg><title>{title}</title><des>{desc}</des><type>5</type><url>{output}</url><thumburl>{thumb_url}</thumburl></appmsg>"
                res_url=f'{base_url}/Msg/SendApp'

                          
                res_msg={
                    "Type": 5,
                    "Xml": simple_xml,
                    "ToWxid": msg["FromWxid"],
                    "Wxid":msg["Wxid"],
                }
                async with aiohttp.ClientSession() as session:
                    async with session.post(res_url, json=res_msg) as response:
                        if response.status != 200:
                            logger.error(f'Webhook app消息返回失败，状态码: {response.status}')
                            return True
                        else:                            
                            logger.info(f'Webhook app消息返回成功，状态码: {response.status},响应：{res_msg}')
                            return False        





