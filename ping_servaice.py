from flask import Flask, request, Response, jsonify
import requests
import re
import io
from PIL import Image, ImageDraw, ImageFont

app = Flask(__name__)

# **节点列表**
NODES = {
    "local": {"ip": "localhost", "alias": "本机"},
}

# **远程 API 端口**
BACKEND_PORT = 48080

# **颜色映射（用于 PIL）**
ANSI_COLOR_MAP = {
    "\033[34m": (0, 0, 255),   # 蓝色（标题）
    "\033[32m": (0, 200, 0),   # 绿色（延迟）
    "\033[33m": (255, 200, 0), # 黄色（TTL）
    "\033[31m": (255, 0, 0),   # 红色（丢包）
    "\033[36m": (0, 200, 200), # 青色（服务器信息）
    "\033[0m": (255, 255, 255) # 默认白色
}

def get_node_ip(node_name):
    """ 获取节点 IP 地址 """
    return NODES.get(node_name, {}).get("ip")

def get_node_alias(node_name):
    """ 获取节点别名 """
    return NODES.get(node_name, {}).get("alias", "未知节点")

def clean_ansi(text):
    """ 移除 ANSI 颜色代码，避免乱码 """
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

def parse_ansi_text(text):
    """ 解析 ANSI 颜色代码，返回 (文本, 颜色) 列表 """
    segments = []
    color = (255, 255, 255)  # 默认白色
    ansi_pattern = re.compile(r'(\033\[[0-9;]*m)')
    parts = ansi_pattern.split(text)

    for part in parts:
        if part in ANSI_COLOR_MAP:
            color = ANSI_COLOR_MAP[part]  # 更新颜色
        else:
            clean_part = clean_ansi(part)
            if clean_part.strip():  # 仅存储非空文本
                segments.append((clean_part, color))

    return segments

def generate_image_from_text(text, node_name):
    """ 解析文本 & ANSI 颜色并生成图片，并在顶部添加 `节点（别名）` """
    lines = text.split("\n")
    node_info = f"节点：{node_name}（{get_node_alias(node_name)}）"
    lines.insert(0, node_info)  # 在第一行添加节点信息

    max_width = max(len(clean_ansi(line)) for line in lines) * 14  # 动态调整宽度
    img_width, img_height = max(900, max_width), max(40 * len(lines), 200)  # 确保不会裁剪
    img = Image.new("RGB", (img_width, img_height), (0, 0, 0))  # 黑色背景
    draw = ImageDraw.Draw(img)

    # **使用支持中英文的字体**
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc", 22)
    except:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 22)

    y_offset = 10
    for line in lines:
        x_offset = 10
        segments = parse_ansi_text(line)

        for text_segment, color in segments:
            draw.text((x_offset, y_offset), text_segment, font=font, fill=color)
            x_offset += draw.textlength(text_segment, font=font)  # 计算文本宽度并移动 x 位置

        y_offset += 36  # 增加行距

    return img

@app.route("/nodes")
def get_nodes():
    """ 返回节点列表（仅名称和别名，不包含 IP） """
    node_list = [{"name": name, "alias": node["alias"]} for name, node in NODES.items()]
    return jsonify(node_list)

@app.route("/nodes_image")
def get_nodes_image():
    """ 生成带颜色和排版优化的节点列表图片 """
    # **颜色定义**
    TITLE_COLOR = (100, 200, 255)  # 亮蓝色
    NODE_NAME_COLOR = (255, 200, 0)  # 黄色
    NODE_ALIAS_COLOR = (255, 255, 255)  # 白色
    BG_COLOR = (20, 20, 20)  # 黑色背景

    # **构造文本数据**
    node_lines = [("节点列表", TITLE_COLOR)]
    for name, node in NODES.items():
        node_lines.append((f"{name} - {node['alias']}", NODE_NAME_COLOR, NODE_ALIAS_COLOR))

    # **加载字体**
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc", 30)
    except:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 30)

    # **创建一个空白画布，用于计算文本宽度**
    img_temp = Image.new("RGB", (1, 1))
    draw_temp = ImageDraw.Draw(img_temp)

    # **计算最大文本宽度**
    padding = 20
    line_height = 50  # 每行高度
    max_text_width = max(
        sum(draw_temp.textbbox((0, 0), part, font=font)[2] for part in line if isinstance(part, str))
        for line in node_lines
    )

    img_width = max(800, max_text_width + padding * 2)  # 适应最长文本，确保不换行
    img_height = line_height * len(node_lines) + padding * 2  # 计算图片高度

    # **创建正式图片**
    img = Image.new("RGB", (img_width, img_height), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # **绘制文本**
    y_offset = padding
    for line in node_lines:
        x_offset = padding
        if len(line) == 2:  # 标题
            draw.text((x_offset, y_offset), line[0], font=font, fill=line[1])
        else:  # 正常行：节点名 - 别名
            node_name, alias = line[0].split(" - ", 1)
            draw.text((x_offset, y_offset), node_name, font=font, fill=NODE_NAME_COLOR)
            x_offset += draw_temp.textbbox((0, 0), node_name, font=font)[2] + 10  # 添加间距
            draw.text((x_offset, y_offset), "- " + alias, font=font, fill=NODE_ALIAS_COLOR)
        y_offset += line_height

    # **返回图片**
    img_io = io.BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    return Response(img_io.getvalue(), mimetype='image/png')

@app.route("/ping")
def ping():
    """ 代理 Ping 请求并返回图像 """
    ip = request.args.get("address")
    node = request.args.get("node")

    if not ip or not node:
        return jsonify({"error": "Missing address or node parameter"}), 400

    node_ip = get_node_ip(node)
    if not node_ip:
        return jsonify({"error": "Node not found"}), 404

    try:
        backend_url = f"http://{node_ip}:{BACKEND_PORT}/ping?address={ip}"
        response = requests.get(backend_url, timeout=40)
        text_output = response.text

        # 解析 ANSI 并生成图片
        img = generate_image_from_text(text_output, node)

        # 返回图片
        img_io = io.BytesIO()
        img.save(img_io, 'PNG')
        img_io.seek(0)
        return Response(img_io.getvalue(), mimetype='image/png')
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 500

@app.route("/curl_ping_test")
def curl_ping_test():
    """ 代理 Curl 请求并返回图像 """
    url = request.args.get("address")
    node = request.args.get("node")

    if not url or not node:
        return jsonify({"error": "Missing address or node parameter"}), 400

    node_ip = get_node_ip(node)
    if not node_ip:
        return jsonify({"error": "Node not found"}), 404

    try:
        backend_url = f"http://{node_ip}:{BACKEND_PORT}/curl_ping_test?address={url}"
        response = requests.get(backend_url, timeout=40)
        text_output = response.text

        # 解析 ANSI 并生成图片
        img = generate_image_from_text(text_output, node)

        # 返回图片
        img_io = io.BytesIO()
        img.save(img_io, 'PNG')
        img_io.seek(0)
        return Response(img_io.getvalue(), mimetype='image/png')
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 500

@app.route("/traceroute")
def traceroute():
    """ 代理 Traceroute 请求并返回图像 """
    ip = request.args.get("address")
    node = request.args.get("node")

    if not ip or not node:
        return jsonify({"error": "Missing address or node parameter"}), 400

    node_ip = get_node_ip(node)
    if not node_ip:
        return jsonify({"error": "Node not found"}), 404

    try:
        backend_url = f"http://{node_ip}:{BACKEND_PORT}/traceroute?address={ip}"
        response = requests.get(backend_url, timeout=40)
        text_output = clean_ansi(response.text)  # **彻底移除 ANSI 控制字符**

        # 解析 ANSI 并生成图片
        img = generate_image_from_text(text_output, node)

        # 返回图片
        img_io = io.BytesIO()
        img.save(img_io, 'PNG')
        img_io.seek(0)
        return Response(img_io.getvalue(), mimetype='image/png')
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=48081)
