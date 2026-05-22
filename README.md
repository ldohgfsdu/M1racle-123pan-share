# M1racle 资源库

> 基于 [123Pan-Unlimited-Share](https://github.com/realcwj/123Pan-Unlimited-Share) 的个人资源管理工具，用于维护和分享我自己的资源库。

## 这是什么

利用 123 云盘的秒传机制，把文件的 Hash 信息记录到 SQLite 数据库，实现跨账号、不占空间的文件分享。配合 [WebDAV 挂载工具](https://github.com/realcwj/123Pan-Unlimited-WebDAV) 可直接播放资源库中的音视频。

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 首次使用：复制配置文件
cp settings.yaml.example settings.yaml
# 编辑 settings.yaml，填写必要信息

# 启动
python web.py
# 浏览器访问 http://127.0.0.1:33333
```

## 扩充资源库

访问网页界面后：

| 方式 | 说明 |
|------|------|
| 从私人网盘导出 | 登录你的 123 云盘，选择文件夹导出分享码 |
| 从分享链接导出 | 粘贴别人的 123 分享链接（如 `https://www.123pan.com/s/xxxxx`） |
| 从文件导入 | 导入 `*.123share` 文件或长分享码 |

所有资源存入 `assets/PAN123DATABASE.db`。

## 配合 WebDAV 挂载

把 `PAN123DATABASE.db` 复制到 [123Pan-Unlimited-WebDAV](https://github.com/realcwj/123Pan-Unlimited-WebDAV) 项目目录，即可挂载到：
- Windows 文件资源管理器
- 网易爆米花 / VidHub / Infuse / Conflux
- OpenList (Alist)

## 配置

见 `settings.yaml.example`：

| 参数 | 说明 |
|------|------|
| `PORT` | 网页端口，默认 `33333` |
| `ADMIN_ENTRY` | 管理后台路径 |
| `SECRET_KEY` | Cookie 加密密钥，务必修改 |

## 文档

- [Web 界面教程](docs/WEB_TUTORIAL.md)
- [API 文档](docs/API_TUTORIAL.md)
- [配置说明](docs/SETTINGS.md)

## 致谢

代码基于 [realcwj/123Pan-Unlimited-Share](https://github.com/realcwj/123Pan-Unlimited-Share)，遵循 GPLv3 协议。

## License

[GPLv3](LICENSE)
