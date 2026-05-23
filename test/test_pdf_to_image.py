import os
import sys

# 引入项目根目录以加载所需的库
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pdf2image import convert_from_path

def convert_pdf_to_images(pdf_path, output_dir, dpi=300):
    if not os.path.exists(pdf_path):
        print(f"[Error] 找不到 PDF 文件: {pdf_path}")
        print("请修改脚本底部的 TEST_PDF_PATH 为真实的 PDF 路径。")
        return
        
    os.makedirs(output_dir, exist_ok=True)
    print(f"[Info] 正在以 DPI={dpi} 把 {pdf_path} 转成图片...")
    
    # 完全模拟系统里面的提取逻辑
    images = convert_from_path(pdf_path, dpi=dpi)
    
    saved_files = []
    for i, image in enumerate(images):
        output_path = os.path.join(output_dir, f"rendered_page_{i+1}.jpg")
        image = image.convert("RGB")
        # 强制高画质保存
        image.save(output_path, format="JPEG", quality=98, subsampling=0)
        saved_files.append(output_path)
        print(f"[Success] 第 {i+1} 页已保存到: {output_path}")
        
    return saved_files

if __name__ == "__main__":
    # >>> 请在这里填入你本地的一张测试发票 PDF 的路径 <<<
    TEST_PDF_PATH = r"D:\code\toP\电子发票1.pdf" 
    
    # 存放在本脚本所在目录 (test 文件夹)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    saved_images = convert_pdf_to_images(TEST_PDF_PATH, script_dir, dpi=300)
    
    if saved_images:
        print("\n完成！你可以使用这几张导出的图片放入原来的 test_hunyuan.py 中跑一下看看结果差距在哪。")