# 🎬 M1racle 资源库

123云盘秒传资源库，配合 [WebDAV](https://github.com/realcwj/123Pan-Unlimited-WebDAV) 挂载播放。

> 基于 [realcwj/123Pan-Unlimited-Share](https://github.com/realcwj/123Pan-Unlimited-Share) (GPLv3)

## 更新资源库

下载最新数据库：

```
https://github.com/ldohgfsdu/M1racle-123pan-share/releases/tag/database
```

`PAN123DATABASE.latest.db` → 改名 `PAN123DATABASE.db` → 覆盖 WebDAV 目录 → 重启 `main.exe`

> 原作者的原始数据库：[realcwj/123Pan-Unlimited-Share](https://github.com/realcwj/123Pan-Unlimited-Share/releases/tag/database)

## 自己加资源

```bash
pip install -r requirements.txt
cp settings.yaml.example settings.yaml
python web.py   # http://127.0.0.1:33333
```

网页操作：从私人网盘导出 / 分享链接导出 / 导入 `*.123share`

## 参考

- [原作者项目](https://github.com/realcwj/123Pan-Unlimited-Share)
- [Web 界面教程](https://github.com/realcwj/123Pan-Unlimited-Share/blob/main/docs/WEB_TUTORIAL.md)
- [API 文档](https://github.com/realcwj/123Pan-Unlimited-Share/blob/main/docs/API_TUTORIAL.md)
- [配置说明](https://github.com/realcwj/123Pan-Unlimited-Share/blob/main/docs/SETTINGS.md)
