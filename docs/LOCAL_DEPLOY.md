# [123云盘](https://www.123pan.com) 无限制分享工具（本地部署文档）

## 目录

- [123云盘 无限制分享工具（本地部署文档）](#123云盘-无限制分享工具本地部署文档)
  - [目录](#目录)
  - [重要提示](#重要提示)
  - [一、解压文件](#一解压文件)
  - [二、配置文件](#二配置文件)
  - [三、运行程序](#三运行程序)
  - [四、访问网站](#四访问网站)

## 重要提示

- ⚠️ 使用 `web.exe` 本地部署仅限本人使用，在公网服务器上部署请使用 `gunicorn`（参考：[123云盘无限制分享工具（服务器 `gunicorn` 部署教程）](./WEB_DEPLOY.md)），否则可能会出现奇怪的 Bug

- 请确保您的 IP 地址不属于中国大陆IP，软件将会从 GitHub 加载最新的公共资源库。

## 一、解压文件

- 打包好的程序发布在 [GitHub Releases](https://github.com/realcwj/123Pan-Unlimited-Share/releases) 中

- 下载最新版本的压缩包，解压后得到 `123Pan-Unlimited-Share` 文件夹，文件夹内应该有一个 `web.exe` 文件和一个 `settings.yaml` 文件

## 二、配置文件

- 打开 `settings.yaml` 文件，参考文档 [123云盘无限制分享工具（配置参数介绍文档）](./SETTINGS.md) 修改配置

- 提示：如果你是本地部署，并且仅自己使用，全部保持默认参数就行，可以不修改 `settings.yaml` 文件。

## 三、运行程序

- 双击 `web.exe` 文件即可运行程序

## 四、访问网站

- 网页地址请看程序运行窗口，例如

    ```shell
    (py312) d:\123Pan-Unlimited-Share>python web.py
    * Serving Flask app 'web'
    * Debug mode: off
    WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
    * Running on all addresses (0.0.0.0)
    * Running on http://127.0.0.1:33333        <<< 访问连接在这里（本机）
    * Running on http://198.18.0.1:33333       <<< 访问连接在这里（局域网）
    Press CTRL+C to quit
    ```

- 网站页面操作请参考 [123云盘无限制分享工具（Web界面使用教程）](./WEB_TUTORIAL.md)