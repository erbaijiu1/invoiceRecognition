import os
import io
import json
import base64
import logging
import re
from PIL import Image
from pdf2image import convert_from_path
from openai import OpenAI

logger = logging.getLogger(__name__)

# 获取 LLM 环境变量，支持自定义 Base URL 接入大厂或者本地模型
API_KEY = os.environ.get("OPENAI_API_KEY", "<你的阿里云API_KEY>")
BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
MODEL_NAME = os.environ.get("LLM_MODEL_NAME", "hunyuan-vision")
HUNYUAN_API_KEY = os.environ.get("HUNYUAN_API_KEY", "")

# 支持的模型列表（前端下拉框使用）
AVAILABLE_MODELS = [
    {"id": "hunyuan-vision", "name": "Hunyuan-Vision（腾讯混元视觉）"},
    {"id": "qwen3.7-max", "name": "Qwen3.7-Max（高精度视觉推理）"},
    {"id": "qwen3.6-plus", "name": "Qwen3.6-Plus（新一代主力机器视觉）"},
    {"id": "qwen-vl-plus", "name": "Qwen-VL-Plus（通义千问视觉）"},
    {"id": "qwen-vl-max", "name": "Qwen-VL-Max（通义千问视觉旗舰）"},
]

# 支持的图片格式
SUPPORTED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.webp', '.tiff', '.tif'}


def get_available_models():
    """返回可用模型列表"""
    return AVAILABLE_MODELS


def get_llm_client(model_id):
    if model_id and model_id.startswith("hunyuan"):
        return OpenAI(
            api_key=HUNYUAN_API_KEY,
            base_url="https://api.hunyuan.cloud.tencent.com/v1"
        )
    else:
        return OpenAI(
            api_key=API_KEY,
            base_url=BASE_URL if BASE_URL else None
        )


def encode_image(image):
    """将 PIL Image 转为 Base64 字符串"""
    buffered = io.BytesIO()
    image = image.convert("RGB")
    image.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')


def encode_image_file(image_path):
    """将图片文件直接读取并转为 Base64 字符串"""
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')


def _get_image_mime_type(file_path):
    """根据文件扩展名获取 MIME 类型"""
    ext = os.path.splitext(file_path)[1].lower()
    mime_map = {
        '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
        '.png': 'image/png', '.bmp': 'image/bmp',
        '.webp': 'image/webp', '.tiff': 'image/tiff', '.tif': 'image/tiff',
    }
    return mime_map.get(ext, 'image/jpeg')


def _build_image_content(base64_str, mime_type='image/jpeg'):
    """构建 image_url 消息内容"""
    return {
        "type": "image_url",
        "image_url": {
            "url": f"data:{mime_type};base64,{base64_str}"
        }
    }


def _get_invoice_prompt():
    """返回发票识别的 prompt"""
    return '''你是一个专业的发票识别助手。请识别这张发票图片中的信息。

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
- "有效抵扣税额"（如果是专用发票，等于"税额"，否则等于"0"）
'''


def parse_invoice(file_path, model_name=None):
    """解析发票文件（支持 PDF 和图片格式）
    
    Args:
        file_path: 文件路径（PDF 或图片）
        model_name: 指定模型名称，不传则使用环境变量中的默认模型
    """
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext == '.pdf':
        return _parse_pdf_invoice(file_path, model_name)
    elif ext in SUPPORTED_IMAGE_EXTENSIONS:
        return _parse_image_invoice(file_path, model_name)
    else:
        return {'error': f'不支持的文件格式: {ext}，仅支持 PDF 和常见图片格式'}


def _parse_image_invoice(image_path, model_name=None):
    """解析图片格式的发票"""
    base64_image = encode_image_file(image_path)
    mime_type = _get_image_mime_type(image_path)
    
    use_model = model_name or MODEL_NAME
    client = get_llm_client(use_model)
    prompt = _get_invoice_prompt()

    try:
        response = client.chat.completions.create(
            model=use_model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        _build_image_content(base64_image, mime_type)
                    ]
                }
            ],
            temperature=0.0
        )
        return _process_llm_response(response)
    except Exception as e:
        logger.error(f"LLM 识别出错: {e}")
        return {'error': f'LLM 识别发生错误: {str(e)}'}


def _parse_pdf_invoice(pdf_path, model_name=None):
    """解析 PDF 格式的发票（支持多页，所有页面发送给模型）"""
    try:
        images = convert_from_path(pdf_path, dpi=200)
    except Exception as e:
        return {'error': f'PDF 转图片失败: {str(e)}'}

    if not images:
        return {'error': 'PDF 页面为空'}

    use_model = model_name or MODEL_NAME
    client = get_llm_client(use_model)
    prompt = _get_invoice_prompt()

    # 构建多图消息内容（所有页面一起发送）
    content = [{"type": "text", "text": prompt}]
    
    if len(images) == 1:
        # 单页 PDF
        base64_image = encode_image(images[0])
        content.append(_build_image_content(base64_image, 'image/jpeg'))
    else:
        # 多页 PDF：所有页面作为多图输入
        prompt_multi = prompt + '\n注意：此发票包含多页，请综合所有页面信息进行识别。'
        content[0] = {"type": "text", "text": prompt_multi}
        for img in images:
            base64_image = encode_image(img)
            content.append(_build_image_content(base64_image, 'image/jpeg'))

    try:
        response = client.chat.completions.create(
            model=use_model,
            messages=[{"role": "user", "content": content}],
            temperature=0.0
        )
        return _process_llm_response(response)
    except Exception as e:
        logger.error(f"LLM 识别出错: {e}")
        return {'error': f'LLM 识别发生错误: {str(e)}'}


def _process_llm_response(response):
    """处理 LLM 响应，提取并解析 JSON 结果"""
    result_text = response.choices[0].message.content.strip()
    logger.info(f"LLM 原始响应:\n{result_text}")

    extracted_json = _extract_json(result_text)
    if extracted_json is None:
        logger.error(f"无法从 LLM 响应中提取 JSON，原始内容:\n{result_text[:500]}")
        return {'error': 'LLM 返回内容中无法解析出 JSON，请重试'}

    try:
        result_data = json.loads(extracted_json)
    except json.JSONDecodeError:
        cleaned = re.sub(r',\s*([}\]])', r'\1', extracted_json)
        try:
            result_data = json.loads(cleaned)
        except json.JSONDecodeError as je:
            logger.error(f"JSON 解析失败：{extracted_json[:500]}")
            return {'error': f'JSON解析失败，大模型返回格式不合法: {str(je)}'}

    result = _normalize_keys(result_data)
    logger.info(f"解析结果: {result}")
    return result


def _extract_json(text):
    """从 LLM 响应文本中提取纯 JSON 字符串，支持多种容错策略"""
    # 策略1：去除 markdown 代码块标记后提取
    cleaned = re.sub(r'```(?:json|JSON)?\s*', '', text)
    cleaned = cleaned.replace('```', '').strip()
    
    # 策略2：用非贪婪正则匹配最外层 JSON 对象
    match = re.search(r'\{[\s\S]*\}', cleaned)
    if match:
        candidate = match.group(0)
        # 验证是否为合法 JSON
        try:
            json.loads(candidate)
            return candidate
        except json.JSONDecodeError:
            pass
    
    # 策略3：在原始文本中直接查找 JSON
    match = re.search(r'\{[\s\S]*\}', text)
    if match:
        candidate = match.group(0)
        try:
            json.loads(candidate)
            return candidate
        except json.JSONDecodeError:
            pass
    
    # 策略4：逐字符查找匹配的 JSON 边界
    start = text.find('{')
    if start == -1:
        return None
    depth = 0
    in_string = False
    escape_next = False
    for i in range(start, len(text)):
        ch = text[i]
        if escape_next:
            escape_next = False
            continue
        if ch == '\\' and in_string:
            escape_next = True
            continue
        if ch == '"' and not escape_next:
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                candidate = text[start:i+1]
                try:
                    json.loads(candidate)
                    return candidate
                except json.JSONDecodeError:
                    return None
    return None


def _normalize_keys(result_data):
    """兼容大模型可能返回的中英文键名"""
    # 中英文键名映射表
    key_map = {
        '发票日期': ['issue_date', 'date', '开票日期'],
        '发票类型': ['invoice_type', 'type'],
        '发票号码': ['invoice_number', 'invoice_no', 'number'],
        '供应商名称': ['seller_name', 'seller', '销售方名称'],
        '金额': ['amount', 'total_amount', 'total', '合计金额'],
        '税额': ['tax_amount', 'tax', 'tax_total', '合计税额'],
        '有效抵扣税额': ['deductible_tax', 'valid_tax'],
        '价税合计': ['grand_total', 'total_with_tax', 'total_amount_with_tax', '价税合计小写'],
    }
    
    result = {}
    for cn_key, en_keys in key_map.items():
        value = result_data.get(cn_key, '')
        if not value:
            for en_key in en_keys:
                value = result_data.get(en_key, '')
                if value:
                    break
        result[cn_key] = value
    
    # 数电发票号码兼容
    result['数电发票号码'] = result.get('发票号码', result_data.get('发票号码', ''))
    
    return result

def parse_multiple_invoices(pdf_paths):
    """批量解析多个发票 PDF"""
    results = []
    for path in pdf_paths:
        result = parse_invoice(path)
        result['文件名'] = os.path.basename(path)
        results.append(result)
    return results
