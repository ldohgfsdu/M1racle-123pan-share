import requests
import json
import os
from bs4 import BeautifulSoup
import urllib.parse
from tqdm import tqdm
from Pan123 import Pan123
from Pan123Database import Pan123Database
from utils import getStringHash, generateContentTree
from loadSettings import loadSettings

from getGlobalLogger import logger

def getContent(channel_name, after_id):

    base_url = f"https://t.me/s/{channel_name}"
    
    headers = {
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
        'Cookie': 'stel_ssid=114514', # 待研究
        'DNT': '1',
        'Origin': 'https://t.me',
        'Priority': 'u=1, i',
        'Sec-CH-UA': '"Chromium";v="136", "Google Chrome";v="136", "Not.A/Brand";v="99"',
        'Sec-CH-UA-Mobile': '?0',
        'Sec-CH-UA-Platform': '"Windows"',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest'
    }

    request_url = f"{base_url}?after={after_id}"

    # 设置动态 Referer
    # headers['Referer'] = f"{base_url}?after={after_id - 22}" # 待研究, 似乎差值是固定22
    # 这个似乎不重要？？？

    response = requests.post(request_url, headers=headers, data="", timeout=10)
    response.raise_for_status()  # 对 4XX 或 5XX 响应会抛出 HTTPError
    
    xml_data = json.loads(response.text)
    
    # return xml_data
    
    logger.debug(f"getContent 请求: {request_url}")
    
    # 返回的内容有以下几种情况：
    ## 第一种：后面还有东西，存在"tgme_widget_message_centered js-messages_more_wrap"字段，指向下一页
    ## 第二种：后面还有东西，但是不足20条，不存在"tgme_widget_message_centered js-messages_more_wrap"字段
    ## 第三种：啥都没有，xml_data=""
    
    # 处理第三种情况
    if xml_data == "":
        return {}, None

    # 存储消息内容：{int(id): "<div>...</div>", int(id): "<div>...</div>", ...}
    message_dict = {}
    
    xml_data = xml_data.split("\n")
    pos = 0
    while pos < len(xml_data):
        line = xml_data[pos]
        
        if "tgme_widget_message_text js-message_text" in line:
            # 向后几行寻找 f"https://t.me/{channel_name}/" (message底部, 显示xx人已观看的位置)
            id_keyword = f"https://t.me/{channel_name}/"
            pos += 1 # 从下一行开始搜索
            current_message_id = None
            while pos < len(xml_data):
                search_line = xml_data[pos]
                if id_keyword in search_line:
                    current_message_id = search_line.split(id_keyword)[1].split("\"")[0]
                    current_message_id = int(current_message_id) # 转换为 int, 此处还可以确保分割正确
                    break
                pos += 1
            if current_message_id is None:
                raise ValueError("找不到消息id")
            else:
                message_dict[current_message_id] = line
            logger.debug(f"getContent 存储消息: {current_message_id}")
            continue
        # 处理第一种情况
        elif "tgme_widget_message_centered js-messages_more_wrap" in line:
            # 截取 data-after="xxxx" 中的 xxxx
            line = line.split("data-after=\"")[1].split("\"")[0]
            line = int(line) # 转换为 int, 此处还可以确保分割正确
            logger.debug(f"getContent 下一页: {line}")
            return message_dict, line
        else:
            pos+=1
            continue

    # 处理第二种情况
    return message_dict, None

def beautifyXML(xml_text):
    # 使用 BeautifulSoup 解析 HTML
    soup = BeautifulSoup(xml_text, 'html.parser')
    # 获取每行的文本
    text_content = soup.get_text(separator='\n', strip=True)
    lines = [line.strip() for line in text_content.split('\n') if line.strip()]
    # 获取所有的链接
    links = []
    for a_tag in soup.find_all('a', href=True):
        raw_link = a_tag['href']
        decoded_link = urllib.parse.unquote(raw_link) # Decode the URL
        links.append(decoded_link)

    return lines + links

def getNameLinkPwd(content_list):
    # 乱七八糟的, 有没有大佬帮忙优化一下
    name = content_list[0].replace("：", ":").replace("名称:", "").replace("资源名称:", "").replace("标题:", "")
    if any([i in name for i in ["automatically deleted", "com/s/", "无法进入群聊"]]):
        name = ""
    link = ""
    pwd = ""
    raw_link = ""
    for line in content_list:
        # 替换中文符号
        line = line.replace("？", "?").replace("！", "!").replace("：", ":").replace("，", ",").replace("。", ".").replace("（", "(").replace("）", ")")
        # if "名称" in line[:20]:
        #     name = line.split(":")[-1]
        #     if debug:
        #         print("这里替换了name变量")
        #         print(f"原文>>>{line}")
        #         print(f"名称>>>{name}")
        if ".com/s/" in line:
            raw_link = line
            line = line.replace("提取码", "?提取码")
            # print(f"原文>>>{line}")
            line = line.split(".com/s/")[1]
            # print(f"链接>>>{line}")
            if "提取码" in line:
                link = line.split("?")[0]
                pwd = line.split(":")[1]
            else:
                link = line.strip()
    # 有的文件名有多个空格, 替换为一个空格
    name = name.replace("  ", " ").replace("  ", " ").replace("  ", " ")
    return {"name": name, "link": link, "pwd": pwd, "raw_link": raw_link, "processed": False}

def startSpider(channel_name, message_after_id=None, save_interval=10, mode="database"):

    # 如果没有填写channel_name, 直接跳过
    if not channel_name:
        logger.info("[Telegram爬虫] 没有填写channel_name, 跳过爬取。")
        return

    file_path = f"{channel_name}_message_raw.json"
    total_json_raw_data = {}
    next_page = message_after_id

    if os.path.exists(file_path):
        if message_after_id is not None:
            logger.info(f"已存在原始消息文件 {file_path}, 将从Json文件中记录的最大消息ID开始爬取。")
            message_after_id = None
        with open(file_path, "r", encoding="utf-8") as f:
            total_json_raw_data = json.load(f)
        # 从Json的最大的一个数字开始爬
        next_page = max(total_json_raw_data.keys())

    count = 0
    while True:
        logger.info(f"开始爬取 Telegram 频道 '{channel_name}', 起始 after_id: {next_page} (第 {int(next_page)+1} 条开始)")
        message_dict, next_page = getContent(
            channel_name=channel_name,
            after_id=next_page
        )
        total_json_raw_data.update(message_dict)
        count += 1
        if count % save_interval == 0:
            # 保存到Json文件
            logger.info(f"已爬取 {count}批 消息, 触发间隔保存到原始消息文件: {file_path}")
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(total_json_raw_data, f, ensure_ascii=False, indent=4)
        # 退出条件: next_page is None（没有下一页了）
        if next_page is None:
            break
    # 保存到Json文件
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(total_json_raw_data, f, ensure_ascii=False, indent=4)

    # 用于保存处理后的数据
    total_json_processed_data = {}

    # 数据清洗，批量得到name, link, pwd
    for key, value in tqdm(total_json_raw_data.items(), desc="获取资源名称/链接/密码中..."):
        result = getNameLinkPwd(beautifyXML(value))
        if len(result.get("name")) and len(result.get("link")):
            total_json_processed_data[key] = result
    
    # 加载已有的 f"{channel_name}_message_processed.json", 覆盖
    if os.path.exists(f"{channel_name}_message_processed.json"):
        with open(f"{channel_name}_message_processed.json", "r", encoding="utf-8") as f:
            old_total_json_processed_data = json.load(f)
        # 合并两个字典
        total_json_processed_data.update(old_total_json_processed_data)
    
    # 删除total_json_raw_data(后面也用不到了), 防止内容太多爆内存
    del total_json_raw_data
    
    # 保存到Json文件
    with open(f"{channel_name}_message_processed.json", "w", encoding="utf-8") as f:
        json.dump(total_json_processed_data, f, ensure_ascii=False, indent=4)

    # 调用 Pan123 导入数据到数据库
    db = Pan123Database(dbpath=loadSettings("DATABASE_PATH"))
    for key, value in total_json_processed_data.items():
        # 如果处理过了，跳过
        if value.get("processed"):
            logger.debug(f"[{key}] 跳过对 '{value.get('name')}' 的导入, 原因：已标记为处理过。")
            continue
        value["processed"] = True
        # 如果name已经存在, 则跳过
        # if len(db.queryName(rootFolderName=value.get("name"))):
        #     logger.info(f"[{key}] 跳过对 '{value.get('name')}' 的导入, 原因：数据库内已同名存在。")
        #     continue
        logger.info(f"[{key}] 尝试导入新增内容: '{value.get('name')}', 链接Key: {value.get('link')}, 密码: {value.get('pwd')}")
        driver = Pan123()
        iter_driver = driver.exportShare(shareKey=value.get("link"), sharePwd=value.get("pwd"), parentFileId=0)
        for current_state in iter_driver:
            if current_state.get("isFinish"):
                b64string = current_state.get("message")
                # 获取目录树
                content_tree = generateContentTree(b64string)["message"]
                content_tree = "\n".join([i[0] for i in content_tree])
                logger.info(f"[{key}] 为 '{value.get('name')}' 生成的目录树:\n{content_tree}")
                if mode == "database":
                    res = input(f"资源名称 >>> {value.get('name')}\n\n是否导入? (y/[n]) >>>")
                    res = res if res else "n"
                    if res != "y":
                        logger.info(f"[{key}] 用户取消导入: '{value.get('name')}'")
                        continue
                    else:                
                        db.insertData(
                            codeHash=getStringHash(b64string),
                            rootFolderName=value.get("name"),
                            visibleFlag=True,
                            shareCode=current_state.get("message")
                            )
                        # print(f"[{key}] 导入成功：{value.get('name')}")
                elif mode == "file":
                    if not os.path.exists("export"):
                        os.mkdir("export")
                    filename = value.get('name').replace(":", "：").replace("/", "／").replace("\\", "＼").replace("*", "＊").replace("?", "？")
                    with open(f"./export/{filename}.123share", "w", encoding="utf-8") as f:
                        f.write(b64string)
                    with open(f"./export/{filename}.123share.md", "w", encoding="utf-8") as f:
                        f.write(content_tree)
                    logger.info(f"[{key}] 导出成功：{filename}")
                else:
                    raise ValueError("mode只能是 'database' 或 'file'")
            elif current_state.get("isFinish") is None:
                continue
            else:
                logger.error(f"[{key}] 导入失败: '{value.get('name')}', 原因: {current_state.get('message')}")
                break
        # 保存到Json文件
        with open(f"{channel_name}_message_processed.json", "w", encoding="utf-8") as f:
            json.dump(total_json_processed_data, f, ensure_ascii=False, indent=4)

    # 保存到Json文件
    with open(f"{channel_name}_message_processed.json", "w", encoding="utf-8") as f:
        json.dump(total_json_processed_data, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":

    channel_name = "" # 大家应该都知道是telegram的哪个群, 自己填入（@xxxx的xxxx部分）, GitHub不明说了
    message_after_id = 8050 # 从 8050 开始爬, 因为之前的内容【全】【都】【失】【效】【了】

    startSpider(channel_name=channel_name, message_after_id=message_after_id, mode="database")