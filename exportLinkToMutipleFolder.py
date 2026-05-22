import requests, time, os, base64, json
from tqdm import tqdm
from Pan123 import Pan123

from getGlobalLogger import logger

# 假设文件结构

# 番剧收藏合集 (ID: 666666)
# |
# ├─ 番剧1 (ID: 222222)
# |  ├─ 1.mp4 (ID: xxxxxx)
# |  ├─ 2.mp4 (ID: xxxxxx)
# |  └─ ...
# |
# ├─ 番剧2 (ID: 333333)
# |  ├─ 1.mp4 (ID: xxxxxx)
# |  ├─ 2.mp4 (ID: xxxxxx)
# |  └─ ...
# |
# └─ ...

# 本程序输入ID: 666666, 首先爬取目录内的所有文件夹 ID (获取 222222(番剧1) 和 333333(番剧2))
# 然后依次爬取所有子文件夹内的所有文件和文件夹ID
# 分别导出多条数据到对应的 番剧1.123share 和 番剧2.123share 文件中


# 此功能仅作为兼容现有分享链接的作用, 后续会删除, 不会加入到主程序中


if __name__ == "__main__":
    # 模式: "folder" 根据文件夹ID导出, "file:后缀": 根据文件逐个导出
    mode = "folder"
    # mode = "file:mp4"
    # 分享链接
    shareKey = ""
    # 分享密码
    sharePwd = ""
    # 文件夹ID集合
    parentFileIds = []
    # 保存到哪个文件夹里
    saveFolderPath = "export/"
    # 前缀
    fileNamePrefix = ""


    # saveFolderPath = os.path.abspath(saveFolderPath) # 使用完整路径似乎会爆长度限制
    if not os.path.exists(saveFolderPath):
        os.makedirs(saveFolderPath)
    for parentFileId in parentFileIds:
        print(f"开始导出 {parentFileId} 下的所有文件")
        # 初始化
        driver = Pan123()
        # 获取 parentFileId 下的所有文件夹名和ID
        page = 0
        body = {
            "limit":          "100",
            "next":           "0",
            "orderBy":        "file_id",
            "orderDirection": "desc",
            "parentFileId":   parentFileId,
            "Page":           None,
            "shareKey":       shareKey,
            "SharePwd":       sharePwd,
        }
        ALL_ITEMS = []
        
        while True:
            # 更新Page参数
            page += 1
            body.update({"Page": f"{page}"})
            logger.info(f"获取文件列表中：正在获取第{page}页")
            # 发送请求
            response_data = requests.get(
                url = driver.getActionUrl("ShareList"),
                headers = driver.headers,
                params = body
            ).json()
            if response_data.get("code") == 0:
                response_data = response_data.get("data")
                # 把文件列表添加到ALL_FILES
                ALL_ITEMS.extend(response_data.get("InfoList"))
                # 如果没有下一页，就退出循环
                if (response_data.get("Next") == "-1") or (len(response_data.get("InfoList")) == 0):
                    logger.info("已是最后一页")
                    break
                # 否则进入下一页 (等待 self.sleepTime 秒, 防止被封)
                else:
                    logger.debug("等待 0.1 秒后进入下一页")
                    time.sleep(0.1)
            else:
                logger.error(f"获取文件列表失败: {json.dumps(response_data, ensure_ascii=False)}")
                break

        if mode == "folder":
            PROCESSED_DATA = {} # 用于存储处理后的数据 {FileId: FileName}
            # 递归获取子文件夹下的文件
            for sub_file in ALL_ITEMS:
                if sub_file.get("Type") == 1:
                    logger.info(f"发现文件夹: {fileNamePrefix}{sub_file.get('FileName')} (ID: {sub_file.get('FileId')})")
                    PROCESSED_DATA[sub_file.get("FileId")] = sub_file.get("FileName")
            # logger.info("按回车键继续导出...")
            print("共计: ", len(PROCESSED_DATA), "个文件夹")
            print("按回车键继续导出...")
            input()
            for FileId, FileName in tqdm(PROCESSED_DATA.items()):
                driver.listShareVisited = {}
                # print(f"导出 {FileName} (ID: {FileId}) 到 {FileName}.123share")
                # tqdm 在进度条下面打印进度
                FileName = FileName.replace("/", "-").replace("\\", "-").replace(":", "-").replace("*", "-").replace("?", "-").replace('"', "-").replace("<", "-").replace(">", "-").replace("|", "-").replace("\n", "").replace("\r", "").replace("\t", "")
                tqdm.write(f"导出 {FileName} (ID: {FileId}) 到 {fileNamePrefix}{FileName}.123share")
                if os.path.exists(os.path.join(saveFolderPath, f"{fileNamePrefix}{FileName}.123share")):
                    continue
                    print("文件已存在, 是否覆盖")
                    res = input("y/[n]>>> ")
                    if res == "y":
                        print("覆盖")
                        # logger.warning(f"文件 {fileNamePrefix}{FileName}.123share 已存在, 覆盖")
                    else:
                        print("跳过")
                        # logger.warning(f"文件 {fileNamePrefix}{FileName}.123share 已存在, 跳过")
                        continue
                # logger.info(f"导出 {FileName} (ID: {FileId}) 到 {fileNamePrefix}{FileName}.123share")
                for currentState in driver.exportShare(parentFileId=FileId,
                                                    shareKey=shareKey,
                                                    sharePwd=sharePwd):
                    if currentState.get("isFinish"):
                        # data = json.loads(base64.urlsafe_b64decode(currentState["message"]))
                        # 如果已存在内容:
                        
                        with open(os.path.join(saveFolderPath, f"{fileNamePrefix}{FileName}.123share"), "w", encoding="utf-8") as f:
                            f.write(currentState["message"])
                            # f.write(json.dumps(data, indent=4, ensure_ascii=False))
                        tqdm.write("导出成功")
                        # logger.info(f"文件 {fileNamePrefix}{FileName}.123share 导出成功。")
                    else:
                        tqdm.write(currentState["message"])
                        # logger.info(f"导出进度 ({FileName}): {currentState['message']}")
        else:
            suffix = mode.split(":")[1]
            for sub_file in ALL_ITEMS:
                if sub_file.get("Type") == 0 and sub_file.get("FileName").endswith(suffix):
                    # print(f"文件 {sub_file.get('FileName')} (ID: {sub_file.get('FileId')})")
                    driver.listShareVisited = {}
                    tqdm.write(f"导出 {sub_file.get('FileName')} (ID: {sub_file.get('FileId')}) 到 {fileNamePrefix}{sub_file.get('FileName')}.123share")
                    sub_file.update({"parentFileId": 1, "AbsPath": "0", "FileId": 0})
                    data = json.dumps([sub_file], indent=4, ensure_ascii=False)
                    data = base64.urlsafe_b64encode(data.encode("utf-8")).decode("utf-8")
                    # print(data)
                    # 过滤文件名里的非法字符
                    sub_file["FileName"] = sub_file["FileName"].replace("/", "-").replace("\\", "-").replace(":", "-").replace("*", "-").replace("?", "-").replace('"', "-").replace("<", "-").replace(">", "-").replace("|", "-").replace("\n", "").replace("\r", "").replace("\t", "")
                    # 过滤最大文件名长度
                    if len(sub_file["FileName"]) > 200:
                        sub_file["FileName"] = sub_file["FileName"][:190] + "..."
                        tqdm.write(f"文件名过长, 已截取为: {sub_file['FileName']}")
                        # logger.warning(f"文件名过长, 已截取为: {sub_file['FileName']}")
                    
                    # 如果已存在内容:
                    if os.path.exists(os.path.join(saveFolderPath, f"{fileNamePrefix}{sub_file.get('FileName')}.123share")):
                        print("文件已存在, 是否覆盖")
                        res = input("y/[n]>>> ")
                        if res == "y":
                            print("覆盖")
                            # logger.warning(f"文件 {fileNamePrefix}{FileName}.123share 已存在, 覆盖")
                        else:
                            print("跳过")
                            # logger.warning(f"文件 {fileNamePrefix}{FileName}.123share 已存在, 跳过")
                            continue
                    with open(os.path.join(saveFolderPath, f"{fileNamePrefix}{sub_file.get('FileName')}.123share"), "w", encoding="utf-8") as f:
                        f.write(data)
                        # f.write(json.dumps(data, indent=4, ensure_ascii=False))