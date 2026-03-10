import requests

# 测试智能问答功能
url = 'http://localhost:8000/ask'

# 测试问题
questions = [
    "张三怎么了",
    "李四的情况如何",
    "最近有什么案件"
]

for question in questions:
    print(f"\n测试问题: {question}")
    print("-" * 50)
    
    # 准备请求数据
    data = {
        "question": question
    }
    
    try:
        response = requests.post(url, json=data)
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"问题: {result['question']}")
            print(f"回答: {result['answer']}")
            print(f"分析: {result['analysis']}")
        else:
            print(f"请求失败: {response.text}")
    except Exception as e:
        print(f"请求错误: {e}")
    
    print("-" * 50)