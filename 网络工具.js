// ==UserScript==
// @name         网络工具
// @version      1.2.3
// @description  向后端服务器发送请求，执行多节点的 curl、ping 和 traceroute 测试
// @author       雪桃
// @timestamp    2025-02-13
// @license      MIT
// @homepageURL  https://github.com/LoranaAurelia/sdjs_nettool.plug
// ==/UserScript==

(function () {
    let ext = seal.ext.find("net_tool");
    if (!ext) {
        ext = seal.ext.new("net_tool", "雪桃", "1.2.3");
        seal.ext.register(ext);
    }

    function registerCommand(name, handler) {
        const cmd = seal.ext.newCmdItemInfo();
        cmd.name = name;
        cmd.desc = "网络工具 - 执行 curl/ping/traceroute 或获取节点列表";
        cmd.solve = handler;
        ext.cmdMap[name] = cmd;
    }

    async function handleNetworkTool(ctx, msg, cmdArgs) {
        const msgId = msg.rawId; // 获取消息 ID

        if (cmdArgs.length === 0 || !cmdArgs.getArgN(1)) {
            seal.replyToSender(ctx, msg, `[CQ:reply,id=${msgId}]网络工具使用帮助：
- .网络工具 curl/ping/traceroute 地址 节点
  使用指定节点，向你提供的 IP 地址，执行 curl/ping/traceroute
- .网络工具 节点/节点列表
  获取节点列表`.trim());  // **修正换行问题**
            return seal.ext.newCmdExecuteResult(true);
        }

        const subCommand = (cmdArgs.getArgN(1) || "").trim().toLowerCase();  // **防止 undefined 导致异常**
        if (["curl", "ping", "traceroute"].includes(subCommand)) {
            const address = (cmdArgs.getArgN(2) || "").trim();
            const node = (cmdArgs.getArgN(3) || "").trim();

            if (!address) {
                seal.replyToSender(ctx, msg, `[CQ:reply,id=${msgId}]请输入地址！格式：网络工具 ${subCommand} 地址 节点`.trim());
                return seal.ext.newCmdExecuteResult(true);
            }

            if (!node) {
                seal.replyToSender(ctx, msg, `[CQ:reply,id=${msgId}]请输入节点！格式：网络工具 ${subCommand} 地址 节点
你可以使用"网络工具 节点列表"获取可用节点`.trim());
                return seal.ext.newCmdExecuteResult(true);
            }

            const encodedAddress = encodeURIComponent(address);
            const encodedNode = encodeURIComponent(node);
            const apiPath = subCommand === "curl" ? "/curl_ping_test"
                : subCommand === "ping" ? "/ping"
                    : "/traceroute";

            const apiUrl = `http://127.0.0.1:48081${apiPath}?address=${encodedAddress}&node=${encodedNode}`;

            seal.replyToSender(ctx, msg, `[CQ:reply,id=${msgId}]${subCommand} 请求已发送，正在执行，请稍等...`.trim());

            const result = await fetchImageResult(apiUrl, msgId, `${subCommand} 结果`);
            seal.replyToSender(ctx, msg, result.trim()); // **修正可能的额外空格**
            return seal.ext.newCmdExecuteResult(true);
        }

        if (subCommand === "节点" || subCommand === "节点列表") {
            const apiUrl = "http://127.0.0.1:48081/nodes_image";
            seal.replyToSender(ctx, msg, `[CQ:reply,id=${msgId}]正在获取节点列表，请稍等...`.trim());

            const result = await fetchImageResult(apiUrl, msgId, "节点列表");
            seal.replyToSender(ctx, msg, result.trim()); // **确保返回的 CQ 码无额外空格**
            return seal.ext.newCmdExecuteResult(true);
        }

        seal.replyToSender(ctx, msg, `[CQ:reply,id=${msgId}]未知命令，请使用"网络工具"查看帮助`.trim());
        return seal.ext.newCmdExecuteResult(true);
    }

    async function fetchImageResult(apiUrl, msgId, description) {
        try {
            // 手动实现超时
            const timeoutPromise = new Promise((_, reject) => {
                setTimeout(() => reject(new Error("请求超时")), 40000);
            });

            const fetchPromise = fetch(apiUrl);
            const response = await Promise.race([fetchPromise, timeoutPromise]); // 取最先完成的

            if (!response.ok) throw new Error("服务器返回错误");

            const imageUrl = response.url; // 假设返回的是图片 URL
            return `[CQ:reply,id=${msgId}]${description}：[CQ:image,file=${imageUrl}]`.trim();
        } catch (error) {
            return `[CQ:reply,id=${msgId}]${description} 获取失败：${error.message}`.trim();
        }
    }

    registerCommand("网络工具", handleNetworkTool);
})();
