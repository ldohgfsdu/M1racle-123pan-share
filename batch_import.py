"""
M1racle 批量导入脚本
用法: 把分享链接写入 links.txt（一行一个），运行本脚本即可批量导入
"""
import requests
import json
import re
import time
import os
import shutil

API = "http://127.0.0.1:33333/api/link"
DB = r"G:\M1racle-123pan-share\assets\PAN123DATABASE.db"
WEBDAV_DB = r"G:\123Pan-Unlimited-WebDAV-Windows\123Pan-Unlimited-WebDAV-Windows\PAN123DATABASE.db"

def parse_link(line):
    """解析各种格式的分享链接"""
    line = line.strip()
    if not line or line.startswith('#'):
        return None, None
    # 格式: https://www.123865.com/s/XXXX-XXXX?pwd=YYYY
    # 或: https://www.123pan.com/s/XXXX-XXXX?提取码=YYYY
    key_match = re.search(r'/s/([\w-]+)', line)
    pwd_match = re.search(r'(?:pwd|提取码)=(\w+)', line)
    return key_match.group(1) if key_match else line, pwd_match.group(1) if pwd_match else ""

def import_link(key, pwd):
    """调用本地API导入分享链接"""
    payload = {
        "shareKey": key,
        "sharePwd": pwd,
        "parentFileId": "0",
        "userSpecifiedBaseName": "",
        "generateShortCode": True,
        "shareProject": False
    }
    try:
        resp = requests.post(API, json=payload, stream=True, timeout=600)
        result = ""
        for line in resp.iter_lines():
            if line:
                data = json.loads(line.decode())
                if data.get("isFinish") == True:
                    result = data.get("message", "")
                    if isinstance(result, str) and "短" in result:
                        print(f"  ✅ 成功导入")
                    else:
                        try:
                            msg = json.loads(result)
                            root = msg.get("rootFolderName", "")
                            print(f"  ✅ {root}")
                        except:
                            print(f"  ✅ 完成")
                elif data.get("isFinish") == False:
                    print(f"  ❌ 失败: {data.get('message', '')}")
                    return False
        return True
    except Exception as e:
        print(f"  ❌ 错误: {e}")
        return False

def main():
    # 读取链接
    if not os.path.exists("links.txt"):
        with open("links.txt", "w", encoding="utf-8") as f:
            f.write("# M1racle 资源库 - 分享链接列表\n")
            f.write("# 一行一个链接，支持格式: https://www.123pan.com/s/xxxx?pwd=yyyy\n")
            f.write("# 以 # 开头的行为注释\n\n")
        print("已创建 links.txt，请填入分享链接后重新运行")
        return

    with open("links.txt", "r", encoding="utf-8") as f:
        lines = f.readlines()

    total = 0
    success = 0
    for line in lines:
        key, pwd = parse_link(line)
        if not key:
            continue
        total += 1
        print(f"\n[{total}] {key} ...")
        if import_link(key, pwd):
            success += 1

    print(f"\n{'='*50}")
    print(f"完成: {success}/{total} 成功")

    # 同步到 WebDAV 和 GitHub
    if success > 0:
        print("\n同步数据库...")
        shutil.copy2(DB, WEBDAV_DB)
        print(f"✅ 已同步到 {WEBDAV_DB}")
        print("\n手动上传 GitHub: gh release upload database assets/PAN123DATABASE.db --clobber")

if __name__ == "__main__":
    main()
