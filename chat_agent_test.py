import requests
import json
import time  # ✅ 1. 导入 time 模块

# 1. 定义请求URL (根据 settings.py 默认端口为 7878)
# url = "http://127.0.0.1:7878/api/chat_agent"
url = "http://172.21.224.71:7878/api/chat_agent"


# 2. 构建请求数据
# 测试智能宣发
# payload = {
#     "question": "云电脑",
#     "user": "网格通",
#     "abilityCode": 2,
#     "user_id": "test_user_001",
#     "phonenum": "13800138000",
#     "label1": "",
#     "label2": "",
#     "history": []
# }

# 测试class1-4-7
payload = {
    "question": "15020868271 交400话费",
    "user": "网格通",
    "abilityCode": 1,
    "user_id": "test_user_001",
    "phonenum": "13800138000",
    "label1": "",
    "label2": "",
    "history": []
}

# 3. 设置请求头
headers = {
    'Content-Type': 'application/json'
}

# 4. 发送请求并处理响应
try:
    print("正在发送请求...")

    # ✅ 2. 记录开始时间
    start_time = time.time()

    response = requests.post(url, json=payload, headers=headers)

    # ✅ 3. 计算耗时 (结束时间 - 开始时间)
    duration = time.time() - start_time

    # 5. 打印结果
    print(f"状态码: {response.status_code}")
    # ✅ 4. 打印耗时，保留4位小数
    print(f"返回时长: {duration:.4f} 秒")
    print("响应JSON:")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))

except requests.exceptions.ConnectionError:
    print(" 连接失败。请确保 FastAPI 服务已在本地 7878 端口运行。")
    print(" 启动命令: uvicorn main:app --reload")
except Exception as e:
    print(f" 发生错误: {e}")