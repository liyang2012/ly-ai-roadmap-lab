import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

try:
    client = OpenAI(
        # 智谱 AI API Key，从环境变量读取
        api_key=os.getenv("ZHIPUAI_API_KEY"),
        # 智谱 AI API 地址
        base_url="https://open.bigmodel.cn/api/coding/paas/v4",
    )

    completion = client.chat.completions.create(
        model="glm-5.1",  # 智谱 AI 模型名称
        messages=[
            {"role": "system", "content": "你是一个非常耐心的老师"},
            {"role": "user", "content": "你是谁？"},
        ],
    )
    print(completion.choices[0].message.content)
    # 如需查看完整响应，请取消下列注释
    # print(completion.model_dump_json())
except Exception as e:
    print(f"错误信息：{e}")
    print("请参考文档：https://help.aliyun.com/zh/model-studio/developer-reference/error-code")