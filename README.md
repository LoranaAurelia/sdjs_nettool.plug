本项目仅支持 Linux。

本项目包含两个主要的后端组件：

1. `node.py`：提供基本的 ping、curl 访问测试以及 traceroute（使用 nexttrace）
2. `ping_servaice.py`：用于代理 `node.py` 进行访问，并生成可视化图像（需 PIL 和字体支持）

## 1. 依赖安装

所有 VPS 需要带有 Python 运行环境，运行 node.py 的节点 vps 需要安装 `nexttrace` 来支持Traceroute，运行 ping_servaice.py 的主机需要 PIL 与字体支持。

### 1.1 安装 `nexttrace`（仅节点 vps )

```bash
curl nxtrace.org/nt | bash
```

### 1.2 安装 Python 依赖

所有 VPS 需安装基本 Python 依赖：

```bash
apt update && apt install -y python3 python3-pip
pip install flask requests
```

#### 如果部署 `ping_servaice.py`，还需额外安装：

```bash
apt install -y fonts-noto-cjk fonts-dejavu
pip install pillow
```

## 2. 部署 `node.py`

适用于所有 VPS，提供基本 ping、curl 访问测试及 traceroute。

### 2.1 启动 `node.py`

```bash
python3 node.py
```

默认监听 `48080` 端口。

### 2.2 创建 `systemd` 服务

```bash
cat <<EOF > /etc/systemd/system/node.service
[Unit]
Description=Node Backend Service
After=network.target

[Service]
ExecStart=/usr/bin/python3 /path/to/node.py
Restart=always
User=root
WorkingDirectory=/path/to/

[Install]
WantedBy=multi-user.target
EOF
```

然后启动并设置开机自启：

```bash
systemctl daemon-reload
systemctl enable node
systemctl start node
```

## 3. 部署 `ping_servaice.py`

适用于主控端，用于可视化 `node.py` 返回的数据。

### 3.1 启动 `ping_servaice.py`

```bash
python3 ping_servaice.py
```

默认监听 `48081` 端口。

### 3.2 创建 `systemd` 服务

```bash
cat <<EOF > /etc/systemd/system/ping_servaice.service
[Unit]
Description=Ping Service Backend
After=network.target

[Service]
ExecStart=/usr/bin/python3 /path/to/ping_servaice.py
Restart=always
User=root
WorkingDirectory=/path/to/

[Install]
WantedBy=multi-user.target
EOF
```

然后启动并设置开机自启：

```bash
systemctl daemon-reload
systemctl enable ping_servaice
systemctl start ping_servaice
```

## 4. 端口修改

- `node.py` 监听 `48080`，如需修改，请更改 `node.py` 代码：
  ```python
  app.run(host="0.0.0.0", port=新端口)
  ```
- `ping_servaice.py` 监听 `48081`，如需修改，请更改 `ping_servaice.py` 代码：
  ```python
  app.run(host="0.0.0.0", port=新端口)
  ```

## 5. 修改 `ping_servaice.py` 节点列表

`ping_servaice.py` 的 `NODES` 变量存储了可用的 `node.py` 服务器：

```python
NODES = {
    "local": {"ip": "localhost", "alias": "本机"},
}
```

如果你有多个 VPS 运行 `node.py`，需要在 `NODES` 中添加它们，例如：

```python
NODES = {
    "local": {"ip": "localhost", "alias": "本机"},
    "vps1": {"ip": "192.168.1.10", "alias": "东京服务器"},
    "vps2": {"ip": "192.168.1.11", "alias": "纽约服务器"},
}
```

接下来，你就可以直接在 `Sealdice` 中安装 JS 插件来调用，或者也可以自行开发其他前端调用。
