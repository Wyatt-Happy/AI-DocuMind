import requests
import json

BASE_URL = 'http://localhost:8000'

def test_business_types():
    """测试业务类型管理"""
    print("\n" + "="*50)
    print("测试业务类型管理")
    print("="*50)
    
    # 1. 创建业务类型
    print("\n1. 创建业务类型")
    business_type = {
        "name": "刑事案件",
        "description": "刑事案件相关的档案"
    }
    response = requests.post(f"{BASE_URL}/business-types", json=business_type)
    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        print(f"创建成功: {response.json()}")
    else:
        print(f"创建失败: {response.text}")
    
    # 2. 创建另一个业务类型
    print("\n2. 创建另一个业务类型")
    business_type = {
        "name": "民事案件",
        "description": "民事案件相关的档案"
    }
    response = requests.post(f"{BASE_URL}/business-types", json=business_type)
    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        print(f"创建成功: {response.json()}")
    else:
        print(f"创建失败: {response.text}")
    
    # 3. 获取所有业务类型
    print("\n3. 获取所有业务类型")
    response = requests.get(f"{BASE_URL}/business-types")
    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        print(f"业务类型列表: {response.json()}")
    else:
        print(f"获取失败: {response.text}")
    
    # 4. 删除业务类型
    print("\n4. 删除业务类型")
    response = requests.delete(f"{BASE_URL}/business-types/民事案件")
    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        print(f"删除成功: {response.json()}")
    else:
        print(f"删除失败: {response.text}")
    
    # 5. 再次获取所有业务类型
    print("\n5. 再次获取所有业务类型")
    response = requests.get(f"{BASE_URL}/business-types")
    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        print(f"业务类型列表: {response.json()}")
    else:
        print(f"获取失败: {response.text}")

def test_save_business_type():
    """测试保存文件业务类型"""
    print("\n" + "="*50)
    print("测试保存文件业务类型")
    print("="*50)
    
    # 保存文件业务类型
    print("\n1. 保存文件业务类型")
    file_business_type = {
        "filename": "test_file.pdf",
        "business_type": "刑事案件",
        "split": True
    }
    response = requests.post(f"{BASE_URL}/save-business-type", json=file_business_type)
    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        print(f"保存成功: {response.json()}")
    else:
        print(f"保存失败: {response.text}")

def test_qa():
    """测试智能问答"""
    print("\n" + "="*50)
    print("测试智能问答")
    print("="*50)
    
    # 提交问题
    print("\n1. 提交问题")
    question = {
        "question": "张三怎么了？"
    }
    response = requests.post(f"{BASE_URL}/ask", json=question)
    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"问题: {result['question']}")
        print(f"回答: {result['answer']}")
        print(f"分析: {result['analysis']}")
    else:
        print(f"处理失败: {response.text}")

def test_person_query():
    """测试人员查询"""
    print("\n" + "="*50)
    print("测试人员查询")
    print("="*50)
    
    # 查询人员履历
    print("\n1. 查询人员履历")
    response = requests.get(f"{BASE_URL}/query", params={"person_id": "张三", "query": "履历"})
    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"人员ID: {result['person_id']}")
        print(f"查询: {result['query']}")
        print(f"结果: {result['results']}")
    else:
        print(f"查询失败: {response.text}")
    
    # 查询时间轴
    print("\n2. 查询时间轴")
    response = requests.get(f"{BASE_URL}/timeline/张三")
    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"人员ID: {result['person_id']}")
        print(f"时间轴事件数量: {len(result['timeline'])}")
        for i, event in enumerate(result['timeline'][:3]):  # 只显示前3个事件
            print(f"  {i+1}. 时间: {event.get('time', event.get('date'))}, 事件: {event.get('event_type', event.get('event'))}")
    else:
        print(f"查询失败: {response.text}")

if __name__ == "__main__":
    try:
        # 测试业务类型管理
        test_business_types()
        
        # 测试保存文件业务类型
        test_save_business_type()
        
        # 测试智能问答
        test_qa()
        
        # 测试人员查询
        test_person_query()
        
        print("\n" + "="*50)
        print("所有测试完成")
        print("="*50)
    except Exception as e:
        print(f"测试过程中出错: {e}")
        import traceback
        traceback.print_exc()