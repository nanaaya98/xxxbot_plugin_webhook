# Webhook 对接插件

--------------------------------------------------

## 插件说明

1. Webhook 对接插件是为在原始框架上实现dow框架回调功能的替代性插件，您可以在原始框架基础上设置回调地址，对接外部程序进行信息处理。
2. 目前可实现文本消息、图片消息、语音消息、文件消息、引用消息的传递，其他需要信息传递的内容请自行对接
3. 语音消息传递请查看使用方法部分对XYBot.py部分代码进行调整，传递出的语音通过api获取的base64为silk格式
4. 引用消息无法引用语音消息的内容，针对图片、文件类型的引用消息，因无法获取引用消息的旧msgid，导致无法通过api重新下载数据，请根据引用数据中对应的值进行数据库索引处理
5. 如需配置多个回调地址请自行复制插件修改插件名称，配置多个插件进行设置
6. XXXBot项目地址：https://github.com/NanSsye/xxxbot-pad

## 插件安装 

1. 将插件文件夹复制到 `plugins` 目录，文件夹名称:Webhook_XXX
2. 编辑 `config.toml` 配置文件
3. 重启 XXXBot 或使用管理命令加载插件

## 配置说明

```toml
[Webhook]
Enable = true                           # 是否启用此功能
Webhook_url = "http://192.168.3.10:5678/webhook/xxxbot"  # 后端Webhook地址，根据自己实际情况进行调整
Robotname = "昵称"      #机器人昵称，务必设置准确，否则会影响群聊@消息的收发
#鉴权api
Auth_Name ="Authorization"    #鉴权方式，请求头中鉴权令牌的键值
Token="Bearer api-key"        #根据对接平台设置，根据平台api进行设置，如有需要，请根据api请求头要求设置Bearer前缀，保留空格
```

## 使用方法

1. 启用插件后，外部程序监听Webhook_url地址即可接收到微信消息，根据您的需求自行对接api服务来返回消息：http://wx.xianan.xin:1562/
2. 需要使用语音消息传递时，请先删除XYBot.py文件中689-706附近以下内容（文件位置：根目录\utils）（当前版本XXXBot版本 v1.5.4.2，请自行对照XYBot.py）
```
       if message["IsGroup"] or not message.get("ImgBuf", {}).get("buffer", ""):
            voiceurl, length = None, None
            try:
                root = ET.fromstring(message["Content"])
                voicemsg_element = root.find('voicemsg')
                if voicemsg_element is not None:
                    voiceurl = voicemsg_element.get('voiceurl')
                    length = int(voicemsg_element.get('length'))
            except Exception as e:
                logger.error("解析语音消息失败: {}, 内容: {}", e, message["Content"])
                return

            if voiceurl and length:
                silk_base64 = await self.bot.download_voice(message["MsgId"], voiceurl, length)
                message["Content"] = await self.bot.silk_base64_to_wav_byte(silk_base64)
        else:
            silk_base64 = message.get("ImgBuf", {}).get("buffer", "")
            message["Content"] = await self.bot.silk_base64_to_wav_byte(silk_base64)
```

## 开发者信息

- 作者：喵子柒
- 版本：1.1.0
- 许可证：MIT
