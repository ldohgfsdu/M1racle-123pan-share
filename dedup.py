"""
M1racle 资源库 - 智能替换工具
如果数据库已有同名 rootFolderName，用新导入的替换旧的
"""
import sqlite3
import sys

DB = r"G:\M1racle-123pan-share\assets\PAN123DATABASE.db"

def dedup_dry_run():
    """预览重复项"""
    conn = sqlite3.connect(DB)
    cur = conn.execute("""
        SELECT rootFolderName, COUNT(*) as cnt 
        FROM PAN123DATABASE 
        GROUP BY rootFolderName 
        HAVING cnt > 1
        ORDER BY cnt DESC
        LIMIT 30
    """)
    rows = cur.fetchall()
    if rows:
        print(f"发现 {len(rows)} 组重复:")
        for name, cnt in rows:
            print(f"  {name} ×{cnt}")
    else:
        print("✅ 无重复项")
    conn.close()

def dedup_replace():
    """删除旧版，只保留最新的"""
    conn = sqlite3.connect(DB)
    cur = conn.execute("""
        SELECT rootFolderName, COUNT(*) as cnt
        FROM PAN123DATABASE
        GROUP BY rootFolderName
        HAVING cnt > 1
    """)
    dups = cur.fetchall()
    total_del = 0
    for name, cnt in dups:
        # 保留 timeStamp 最新的，删其他的
        cur2 = conn.execute("""
            SELECT rowid, timeStamp FROM PAN123DATABASE 
            WHERE rootFolderName = ? 
            ORDER BY timeStamp DESC
        """, (name,))
        all_rows = cur2.fetchall()
        keep = all_rows[0]  # 最新的
        for row in all_rows[1:]:  # 旧的
            conn.execute("DELETE FROM PAN123DATABASE WHERE rowid = ?", (row[0],))
            total_del += 1
    conn.commit()
    print(f"已删除 {total_del} 条旧记录，保留最新版")
    conn.close()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--dry":
        dedup_dry_run()
    else:
        print("预览: python dedup.py --dry")
        print("执行: python dedup.py --do")
        if len(sys.argv) > 1 and sys.argv[1] == "--do":
            dedup_replace()
