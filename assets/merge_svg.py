import os
import base64

def generate_grid_svg():
    # 自动定位当前脚本所在的 assets 目录
    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_file = os.path.join(base_dir, "merged_logo.svg")
    
    # 定义四个图标的文件名
    files = [
        "apple-173-svgrepo-com.svg", "intel-icon.svg",
        "linux-svgrepo-com.svg", "macos-svgrepo-com.svg"
    ]
    
    # SVG 模板：400x400 布局
    svg_template = """<svg width="400" height="400" viewBox="0 0 400 400" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
    <rect width="100%" height="100%" fill="transparent" />
    <image xlink:href="{img0}" x="25" y="25" width="150" height="150" />
    <image xlink:href="{img1}" x="225" y="25" width="150" height="150" />
    <image xlink:href="{img2}" x="25" y="225" width="150" height="150" />
    <image xlink:href="{img3}" x="225" y="225" width="150" height="150" />
</svg>"""

    img_data = []
    for f in files:
        path = os.path.join(base_dir, f)
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as svg_file:
                content = svg_file.read()
                encoded = base64.b64encode(content.encode('utf-8')).decode('utf-8')
                img_data.append(f"data:image/svg+xml;base64,{encoded}")
        else:
            img_data.append("") 
            print(f"❌ 错误: 找不到文件 {path}")

    if len(img_data) == 4:
        final_svg = svg_template.format(
            img0=img_data[0], img1=img_data[1], 
            img2=img_data[2], img3=img_data[3]
        )
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(final_svg)
        print(f"✅ 成功！大 Logo 已生成至: {output_file}")

if __name__ == "__main__":
    generate_grid_svg()