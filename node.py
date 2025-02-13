from flask import Flask, request, Response
import subprocess
import re

app = Flask(__name__)

def run_command(command):
    """ 运行系统命令并返回结果 """
    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=15)
        return result.stdout.strip() if result.returncode == 0 else result.stderr.strip()
    except subprocess.TimeoutExpired:
        return "命令执行超时"

def remove_ansi_codes(text):
    """ 移除 ANSI 颜色代码 """
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

@app.route("/ping")
def ping():
    """ 执行 ping 并格式化输出 """
    ip = request.args.get("address")
    if not ip:
        return Response("错误：缺少 address 参数", mimetype="text/plain", status=400)
    
    raw_output = run_command(["ping", "-c", "10", ip])
    matches = re.findall(r'time=([\d.]+) ms', raw_output)
    ttl_matches = re.findall(r'ttl=(\d+)', raw_output)
    packet_loss_match = re.search(r'(\d+)% packet loss', raw_output)

    if not matches:
        return Response(f"Ping 失败：\n{raw_output}", mimetype="text/plain", status=500)

    times = [float(t) for t in matches]
    ttls = ttl_matches[:len(times)]  # 取前 n 个 TTL
    packet_loss = packet_loss_match.group(1) if packet_loss_match else "0"

    response = (
        f"\033[34m【PING 测试】\033[0m ping {ip} 结果：\n"
        + "\n".join([f"第 {i+1} 次：\033[32m{times[i]}ms ({times[i] / 1000:.3f}s)\033[0m TTL: \033[33m{ttls[i]}\033[0m" for i in range(len(times))])
        + f"\n\n丢包率：\033[31m{packet_loss}%\033[0m\n"
        + f"最高：\033[32m{max(times)}ms ({max(times) / 1000:.3f}s)\033[0m，最低：\033[32m{min(times)}ms ({min(times) / 1000:.3f}s)\033[0m，平均：\033[32m{sum(times)/len(times):.2f}ms ({sum(times)/len(times) / 1000:.3f}s)\033[0m"
    )

    return Response(response, mimetype="text/plain")


@app.route("/curl_ping_test")
def curl_ping_test():
    """ 执行 curl 10 次并格式化输出，展示详细访问信息 """
    url = request.args.get("address")
    if not url:
        return Response("错误：缺少 address 参数", mimetype="text/plain", status=400)
    
    times = []
    outputs = []

    # **检查文件大小，避免下载大文件**
    size_check_output = run_command(["curl", "-sI", url])
    content_length_match = re.search(r"Content-Length: (\d+)", size_check_output, re.IGNORECASE)
    content_length = int(content_length_match.group(1)) if content_length_match else 0
    if content_length > 5_000_000:  # **限制 5MB**
        return Response("错误：文件过大，拒绝访问", mimetype="text/plain", status=403)

    # **执行 10 次 curl 测试**
    for _ in range(10):
        raw_output = run_command([
            "curl", "-o", "/dev/null", "-s", "-w",
            "time_total:%{time_total}, http_code:%{http_code}, size_download:%{size_download}, ssl_verify:%{ssl_verify}, remote_ip:%{remote_ip}\n",
            "--max-time", "10", "--limit-rate", "500k",  # **限制超时时间 & 限速**
            url
        ])
        outputs.append(raw_output)
        match = re.search(r"time_total:([\d.]+)", raw_output)
        if match:
            total_time = float(match.group(1))
            times.append(total_time)

    # **获取完整请求信息**
    http_info_output = run_command([
        "curl", "-s", "-o", "/dev/null", "-D", "-", "-w",
        "http_code:%{http_code}, size_download:%{size_download}, remote_ip:%{remote_ip}, time_total:%{time_total}, content_type:%{content_type}, redirect_url:%{redirect_url}, ssl_verify:%{ssl_verify}, method:%{method}\n",
        "--max-time", "10", "--limit-rate", "500k",
        url
    ])

    # **获取网页前 500 个字符**
    full_page_output = run_command(["curl", "-s", "--max-time", "10", "--limit-rate", "500k", url])
    page_content = full_page_output[:500] if full_page_output else "(无法获取内容)"

    response = (
        f"\033[34m【CURL 测试】\033[0m curl {url} 结果：\n"
        + "\n".join([f"第 {i+1} 次：\033[32m{times[i] * 1000:.2f}ms ({times[i]:.3f}s)\033[0m" for i in range(len(times))])
        + f"\n\n最高：\033[32m{max(times) * 1000:.2f}ms ({max(times):.3f}s)\033[0m，最低：\033[32m{min(times) * 1000:.2f}ms ({min(times):.3f}s)\033[0m，平均：\033[32m{sum(times)/len(times) * 1000:.2f}ms ({sum(times)/len(times):.3f}s)\033[0m\n"
        + f"\n\033[36m【访问信息】\033[0m\n{http_info_output}"
        + f"\n\033[36m【页面内容 (前 500 字符)】\033[0m\n{page_content}"
    )

    return Response(response, mimetype="text/plain")


@app.route("/traceroute")
def traceroute():
    """ 执行 nexttrace 并返回带颜色的结果 """
    ip = request.args.get("address")
    if not ip:
        return Response("错误：缺少 address 参数", mimetype="text/plain", status=400)

    raw_output = run_command(["nexttrace", ip])
    return Response(raw_output, mimetype="text/plain")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=48080)
