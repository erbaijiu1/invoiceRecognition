import os
import io
import uuid
import logging
import tempfile
from flask import Flask, request, jsonify, send_file, send_from_directory
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from invoice_parser import parse_invoice

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='static', static_url_path='')

# 上传目录
UPLOAD_FOLDER = tempfile.mkdtemp(prefix='invoice_ocr_')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB


@app.route('/')
def index():
    """返回前端页面"""
    return send_from_directory('static', 'index.html')


@app.route('/api/upload', methods=['POST'])
def upload_invoice():
    """上传并识别发票 PDF"""
    if 'files' not in request.files:
        return jsonify({'error': '没有上传文件'}), 400

    files = request.files.getlist('files')
    if not files or files[0].filename == '':
        return jsonify({'error': '没有选择文件'}), 400

    results = []
    for file in files:
        if not file.filename.lower().endswith('.pdf'):
            results.append({
                '文件名': file.filename,
                'error': '仅支持 PDF 格式'
            })
            continue

        # 保存临时文件（用 UUID 避免并发冲突）
        ext = os.path.splitext(file.filename)[1]
        safe_name = f"{uuid.uuid4().hex}{ext}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], safe_name)
        file.save(filepath)

        try:
            logger.info(f'开始识别: {file.filename}')
            result = parse_invoice(filepath)
            result['文件名'] = file.filename
            results.append(result)
        except Exception as e:
            results.append({
                '文件名': file.filename,
                'error': f'识别失败: {str(e)}'
            })
        finally:
            # 清理临时文件
            if os.path.exists(filepath):
                os.remove(filepath)

    return jsonify({'results': results})


@app.route('/api/download', methods=['POST'])
def download_excel():
    """将识别结果导出为 Excel"""
    data = request.get_json()
    if not data or 'results' not in data:
        return jsonify({'error': '没有数据'}), 400

    results = data['results']

    # 创建 Excel
    wb = Workbook()
    ws = wb.active
    ws.title = '发票识别结果'

    # 表头
    headers = ['发票日期', '发票类型', '发票号码', '数电发票号码',
                '供应商名称', '金额', '税额', '有效抵扣税额', '价税合计']

    # 表头样式
    header_font = Font(name='微软雅黑', size=11, bold=True, color='FFFFFF')
    header_fill = PatternFill(start_color='2B5797', end_color='2B5797', fill_type='solid')
    header_alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    thin_border = Border(
        left=Side(style='thin', color='B0B0B0'),
        right=Side(style='thin', color='B0B0B0'),
        top=Side(style='thin', color='B0B0B0'),
        bottom=Side(style='thin', color='B0B0B0')
    )

    # 写入表头
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thin_border

    # 写入数据
    data_font = Font(name='微软雅黑', size=10)
    data_alignment = Alignment(horizontal='center', vertical='center')
    amount_alignment = Alignment(horizontal='right', vertical='center')

    for row_idx, result in enumerate(results, 2):
        if 'error' in result and result.get('error'):
            ws.cell(row=row_idx, column=1, value=result.get('文件名', ''))
            ws.cell(row=row_idx, column=2, value=f"错误: {result['error']}")
            continue

        for col_idx, header in enumerate(headers, 1):
            value = result.get(header, '')
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.font = data_font
            cell.border = thin_border

            # 金额列右对齐
            if header in ['金额', '税额', '有效抵扣税额', '价税合计']:
                cell.alignment = amount_alignment
                # 尝试转数值
                try:
                    cell.value = float(value) if value else ''
                    cell.number_format = '#,##0.00'
                except (ValueError, TypeError):
                    pass
            else:
                cell.alignment = data_alignment

    # 设置列宽
    col_widths = [14, 12, 24, 24, 35, 14, 14, 14, 14]
    for i, width in enumerate(col_widths, 1):
        ws.column_dimensions[chr(64 + i)].width = width

    # 冻结首行
    ws.freeze_panes = 'A2'

    # 保存到内存
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='发票识别结果.xlsx'
    )


if __name__ == '__main__':
    print("=" * 50)
    print("  发票识别系统已启动")
    print("  访问 http://localhost:8999")
    print("=" * 50)
    app.run(host='0.0.0.0', port=8999, debug=True)
