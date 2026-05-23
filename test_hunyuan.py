import os
import base64
from openai import OpenAI

def encode_image_file(image_path):
    """将图片文件读取并统一转为 Base64 字符串"""
    with open(image_path, 'rb') as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

# 发票信息的提取提示词（与你在 invoice_parser.py 中的应用保持一致）
INVOICE_PROMPT = """你是一个专业的发票识别助手。请识别这张发票图片中的信息。

【极其重要的输出要求】
1. 只能输出一个合法的 JSON 对象，不要输出任何其他内容。
2. 禁止使用 Markdown 格式，禁止使用 ```json 或 ``` 包裹，禁止使用任何代码块标记。
3. 禁止输出任何分析、解释、说明、注释性文字。
4. 直接以 { 开头，以 } 结尾，中间是 JSON 内容。
5. JSON 的键名必须严格遵守下面的中文名称，不要使用英文键名！

请返回包含以下固定键名的 JSON：
- "发票日期"（格式为 YYYY-MM-DD）
- "发票类型"（如：增值税专用发票、增值税普通发票、电子专票、电子普票等）
- "发票号码"（或数电发票号码）
- "供应商名称"（销售方名称）
- "金额"（不含税金额，仅提取数字，无逗号）
- "税额"（仅提取数字，无逗号）
- "价税合计"（仅提取数字，无逗号）
- "有效抵扣税额"（如果是专用发票，等于"税额"，否则等于"0"）"""

def test_hunyuan_invoice(image_path):
    if not os.path.exists(image_path):
        print(f"[Error] 找不到图片文件: {image_path}\n请修改脚本最后的 TEST_IMAGE_PATH 为你本地真实的测试发票图片路径。")
        return

    print(f"[Info] 正在读取并编码图片: {image_path} ...")
    base64_image = encode_image_file(image_path)
    
    # 简单通过扩展名判断 MIME type，默认用 image/jpeg
    ext = os.path.splitext(image_path)[1].lower()
    mime_type = "image/png" if ext == ".png" else "image/jpeg"
    image_url = f"data:{mime_type};base64,{base64_image}"

    print("[Info] 正在连接腾讯混元 API 进行识别 ...")
    # 构造 client
    client = OpenAI(
        # 默认从环境变量读取，也可以直接在这里将 "你的混元API_KEY" 替换成真实的 Key 测试
        api_key=os.environ.get("HUNYUAN_API_KEY", ""),
        base_url="https://api.hunyuan.cloud.tencent.com/v1", # 混元 endpoint
    )

    try:
        completion = client.chat.completions.create(
            model="hunyuan-vision",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": INVOICE_PROMPT
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image_url
                            }
                        }
                    ]
                },
            ],
            temperature=0.0 # 建议设为 0，保证信息提取字段稳定性
        )
        print("\n========== [识别结果] ==========\n")
        print(completion.choices[0].message.content)
        print("\n=================================")
    except Exception as e:
        print(f"[Error] API 调用失败: {e}")

if __name__ == "__main__":
    # >>> 请在这里填入你本地的一张测试发票图片的路径 <<<
    TEST_IMAGE_PATH = r"D:\code\toP\fapiao2.png"
    
    test_hunyuan_invoice(TEST_IMAGE_PATH)