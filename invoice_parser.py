import re
import os
import threading
import numpy as np
from pdf2image import convert_from_path
from paddleocr import PaddleOCR


# 全局 OCR 实例，避免重复加载模型（线程安全）
_ocr_instance = None
_ocr_lock = threading.Lock()


def get_ocr():
    """获取或创建 PaddleOCR 实例（单例，线程安全）"""
    global _ocr_instance
    if _ocr_instance is None:
        with _ocr_lock:
            if _ocr_instance is None:
                _ocr_instance = PaddleOCR(use_angle_cls=True, lang='ch', show_log=False)
    return _ocr_instance


def pdf_to_images(pdf_path, dpi=300):
    """将 PDF 转换为图片列表"""
    images = convert_from_path(pdf_path, dpi=dpi)
    return images


def ocr_image(image):
    """对单张图片进行 OCR 识别，返回带位置信息的文本"""
    ocr = get_ocr()
    img_array = np.array(image)
    results = ocr.ocr(img_array, cls=True)

    text_blocks = []
    if results and results[0]:
        for line in results[0]:
            box = line[0]  # [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
            text = line[1][0]
            confidence = line[1][1]
            # 计算中心坐标
            cx = sum(p[0] for p in box) / 4
            cy = sum(p[1] for p in box) / 4
            # 计算边界
            min_x = min(p[0] for p in box)
            max_x = max(p[0] for p in box)
            min_y = min(p[1] for p in box)
            max_y = max(p[1] for p in box)
            text_blocks.append({
                'text': text,
                'confidence': confidence,
                'cx': cx,
                'cy': cy,
                'min_x': min_x,
                'max_x': max_x,
                'min_y': min_y,
                'max_y': max_y,
                'box': box
            })
    return text_blocks


def find_text_near(blocks, keyword, direction='right', max_distance=500):
    """在关键字附近查找文本"""
    keyword_block = None
    for b in blocks:
        if keyword in b['text']:
            keyword_block = b
            break
    if not keyword_block:
        return None

    candidates = []
    for b in blocks:
        if b is keyword_block:
            continue
        if direction == 'right':
            # 在右侧，且 Y 坐标相近
            if (b['min_x'] > keyword_block['max_x'] - 20 and
                    abs(b['cy'] - keyword_block['cy']) < 40 and
                    b['min_x'] - keyword_block['max_x'] < max_distance):
                candidates.append((b['min_x'] - keyword_block['max_x'], b))
        elif direction == 'below':
            # 在下方，且 X 坐标相近
            if (b['min_y'] > keyword_block['max_y'] - 20 and
                    abs(b['cx'] - keyword_block['cx']) < 100 and
                    b['min_y'] - keyword_block['max_y'] < max_distance):
                candidates.append((b['min_y'] - keyword_block['max_y'], b))

    if candidates:
        candidates.sort(key=lambda x: x[0])
        return candidates[0][1]['text']
    return None


def extract_amount(text):
    """从文本中提取金额数字"""
    if not text:
        return ''
    # 去除 ¥ 符号和空格
    text = text.replace('¥', '').replace('￥', '').replace(',', '').replace(' ', '')
    # 匹配数字（含负数和小数）
    match = re.search(r'-?[\d]+\.?\d*', text)
    if match:
        return match.group()
    return text


def determine_invoice_type(blocks):
    """根据发票标题判断发票类型"""
    full_text = ' '.join(b['text'] for b in blocks)

    if '增值税专用发票' in full_text or '专用发票' in full_text:
        if '电子' in full_text:
            return '电子专票'
        return '增值税专用发票'
    elif '增值税普通发票' in full_text or '普通发票' in full_text:
        if '电子' in full_text:
            return '电子普票'
        return '增值税普通发票'
    elif '电子发票' in full_text:
        # 检查更多上下文
        if '专用' in full_text:
            return '电子专票'
        return '电子普票'

    return '未知类型'


def extract_invoice_number(blocks):
    """提取发票号码 —— 匹配20位数电发票号或传统8位号码"""
    full_text = ' '.join(b['text'] for b in blocks)

    # 先找 "发票号码" 关键字附近的内容
    number_text = find_text_near(blocks, '发票号码', 'right', max_distance=600)
    if number_text:
        # 提取连续数字
        numbers = re.findall(r'\d{8,}', number_text)
        if numbers:
            return numbers[0]

    # 全文搜索20位数字（数电发票号）
    matches_20 = re.findall(r'\d{20}', full_text)
    if matches_20:
        return matches_20[0]

    # 全文搜索8位数字
    matches_8 = re.findall(r'\d{8}', full_text)
    if matches_8:
        return matches_8[0]

    return ''


def extract_date(blocks):
    """提取开票日期"""
    # 方法1：找 "开票日期" 关键字附近
    date_text = find_text_near(blocks, '开票日期', 'right', max_distance=600)
    if date_text:
        # 尝试提取 YYYY年MM月DD日 或 YYYY-MM-DD 格式
        match = re.search(r'(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日', date_text)
        if match:
            return f"{match.group(1)}-{match.group(2).zfill(2)}-{match.group(3).zfill(2)}"
        match = re.search(r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})', date_text)
        if match:
            return match.group(1)

    # 方法2：全文搜索日期
    full_text = ' '.join(b['text'] for b in blocks)
    match = re.search(r'(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日', full_text)
    if match:
        return f"{match.group(1)}-{match.group(2).zfill(2)}-{match.group(3).zfill(2)}"

    return ''


def extract_supplier_name(blocks):
    """提取销售方/供应商名称"""
    # 方法1：找 "销售方" 或 "销" 下面的 "名称" 后面的内容
    for i, b in enumerate(blocks):
        if '销售方' in b['text'] or ('销' in b['text'] and '方' in b['text']):
            # 找附近的 "名称" 块
            for b2 in blocks:
                if '名称' in b2['text'] and abs(b2['cy'] - b['cy']) < 80:
                    # 在名称后面找公司名
                    name_text = find_text_near(blocks, '名称', 'right', max_distance=800)
                    # 可能名称和值在同一个文本块里
                    if b2['text'] and ':' in b2['text']:
                        parts = b2['text'].split(':')
                        if len(parts) > 1 and parts[1].strip():
                            return parts[1].strip()
                    if b2['text'] and '：' in b2['text']:
                        parts = b2['text'].split('：')
                        if len(parts) > 1 and parts[1].strip():
                            return parts[1].strip()
                    if name_text and '名称' not in name_text:
                        return name_text.replace(':', '').replace('：', '').strip()

    # 方法2：全文搜索包含 "公司" 的文本，取销售方区域的
    # 在页面右半区域找包含 "公司" 的文本
    company_blocks = [b for b in blocks if '公司' in b['text'] or '有限' in b['text']]

    if company_blocks:
        # 找到 "销" 字的位置来确定销售方区域
        sell_blocks = [b for b in blocks if '销' in b['text'] and ('方' in b['text'] or '售' in b['text'])]
        if sell_blocks:
            sell_y = sell_blocks[0]['cy']
            # 在销售方区域的公司名
            nearby = [b for b in company_blocks if abs(b['cy'] - sell_y) < 80]
            if nearby:
                name = nearby[0]['text']
                # 清理前缀
                name = re.sub(r'^.*?名称[：:]?\s*', '', name)
                return name.strip()

    # 方法3: 查找 "名称:" 模式
    for b in blocks:
        text = b['text']
        match = re.search(r'名称[：:]\s*(.+(?:公司|企业|集团|工厂|商行|商店))', text)
        if match:
            return match.group(1).strip()

    return ''


def extract_amounts(blocks):
    """提取合计金额和税额"""
    amount = ''
    tax = ''
    total = ''

    # 找 "合计" 行
    for i, b in enumerate(blocks):
        if b['text'].strip() == '合计' or ('合' in b['text'] and '计' in b['text'] and '价税' not in b['text'] and len(b['text']) <= 4):
            # 在合计行右侧找金额
            row_blocks = [b2 for b2 in blocks
                          if abs(b2['cy'] - b['cy']) < 30
                          and b2['min_x'] > b['max_x'] - 20
                          and b2 is not b]
            row_blocks.sort(key=lambda x: x['min_x'])

            amounts = []
            for rb in row_blocks:
                amt = extract_amount(rb['text'])
                if amt and re.match(r'-?[\d.]+$', amt):
                    amounts.append(amt)

            if len(amounts) >= 2:
                amount = amounts[-2]  # 倒数第二个是金额
                tax = amounts[-1]     # 最后一个是税额
            elif len(amounts) == 1:
                amount = amounts[0]
            break

    # 找 "价税合计" 行
    for b in blocks:
        if '价税合计' in b['text']:
            # 在右侧找金额
            row_blocks = [b2 for b2 in blocks
                          if abs(b2['cy'] - b['cy']) < 30
                          and b2['min_x'] > b['max_x'] - 50
                          and b2 is not b]
            row_blocks.sort(key=lambda x: x['min_x'])

            for rb in row_blocks:
                text = rb['text']
                # 匹配 (小写) ¥xxx 格式
                match = re.search(r'[¥￥]\s*([\d,.]+)', text)
                if match:
                    total = match.group(1).replace(',', '')
                    break
                # 匹配纯数字
                amt = extract_amount(text)
                if amt and re.match(r'-?[\d.]+$', amt):
                    total = amt
                    break
            break

    # 如果只有合计没有找到单独金额和税额，尝试其他方式
    if not amount:
        for b in blocks:
            if '金额' in b['text'] and '税' not in b['text'] and '价' not in b['text']:
                amt_text = find_text_near(blocks, '金额', 'right')
                if amt_text:
                    amount = extract_amount(amt_text)
                break

    return amount, tax, total


def parse_invoice(pdf_path):
    """解析单个发票 PDF，返回结构化数据"""
    try:
        images = pdf_to_images(pdf_path)
    except Exception as e:
        return {'error': f'PDF 转图片失败: {str(e)}'}

    if not images:
        return {'error': 'PDF 页面为空'}

    # 通常发票只有1页，取第一页
    image = images[0]
    blocks = ocr_image(image)

    if not blocks:
        return {'error': 'OCR 识别失败，未检测到文本'}

    # 提取各字段
    invoice_date = extract_date(blocks)
    invoice_type = determine_invoice_type(blocks)
    invoice_number = extract_invoice_number(blocks)
    supplier_name = extract_supplier_name(blocks)
    amount, tax, total = extract_amounts(blocks)

    # 判断有效抵扣税额
    deductible_tax = ''
    if tax:
        if '专' in invoice_type:
            deductible_tax = tax  # 专票可抵扣
        else:
            deductible_tax = '0'  # 普票不可抵扣

    result = {
        '发票日期': invoice_date,
        '发票类型': invoice_type,
        '发票号码': invoice_number,
        '数电发票号码': invoice_number,  # 数电票号码与发票号码相同
        '供应商名称': supplier_name,
        '金额': amount,
        '税额': tax,
        '有效抵扣税额': deductible_tax,
        '价税合计': total,
    }

    return result


def parse_multiple_invoices(pdf_paths):
    """批量解析多个发票 PDF"""
    results = []
    for path in pdf_paths:
        result = parse_invoice(path)
        result['文件名'] = os.path.basename(path)
        results.append(result)
    return results
