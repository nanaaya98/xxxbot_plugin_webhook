# Webhook 对接插件

--------------------------------------------------

## 插件说明

1. Webhook 对接插件是为在原始框架上实现dow框架回调功能的替代性插件，您可以在原始框架基础上设置回调地址，对接外部程序进行信息处理。
2. 目前可直接实现文本消息、图片消息、文件消息、引用消息的传递，其他需要信息传递的内容请自行对接
3. 引用消息无法引用语音消息的内容，针对图片、文件类型的引用消息，自行构筑数据库引用
4. 可直接利用插件进行文本消息、图片消息、语音消息答复，body构筑详见使用方法
5. 长文本答复分段发送，如需整段发送请自行修改代码
6. 如需配置多个回调地址请自行复制插件修改插件名称，配置多个插件进行设置
7. XXXBot项目地址：https://github.com/NanSsye/xxxbot-pad

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
Wxid = "wxid_27q2wvyh9j1p21"              #机器人Wxid
#鉴权api
Auth_Name ="Authorization"    #鉴权方式，请求头中鉴权令牌的键值
Token="Bearer api-key"        #根据对接平台设置，根据平台api进行设置，如有需要，请根据api请求头要求设置Bearer前缀，保留空格
```

## 使用方法

1. 启用插件后，外部程序监听Webhook_url地址即可接收到微信消息，根据您的需求自行对接api服务来返回消息：http://wx.xianan.xin:1562/
2. 针对XXXBot版本 v1.5.5，可自行替换XYBot.py实现语音消息传递和图片消息xml获取
3. 消息答复body结构：
```
###文本消息###
{
    output_type:"text",
    output:"输出内容"
}
###图片消息###
{
    output_type:"image",
    output:"图片base64"
}
###语音消息###
{
    output_type:"voice",
    output:"语音base64",
    voice_type:"MP3"      #AMR, MP3, SILK, WAV
}
###链接消息###
{
    output_type:"link",
    output:"链接的url",
}

```

## 开发者信息

- 作者：喵子柒
- 版本：1.2.5
- 许可证：MIT

