# 文明 VI · Mac 局域网联机助手

解决 Mac《文明 VI》通过虚拟局域网联机时，**能连通好友 IP，却找不到好友房间**的问题。支持 macOS 12+、Apple Silicon（含 M4）与 Intel。

**使用顺序：ZeroTier 组网 → 双向 ping 成功 → 启动助手 → 刷新游戏房间列表。**

## 1. 创建并加入 ZeroTier 网络

官方资料：[下载安装](https://www.zerotier.com/download/) · [创建与加入网络](https://docs.zerotier.com/start/) · [设备授权](https://docs.zerotier.com/networks/)

1. **一人建网：**登录 [ZeroTier Central](https://central.zerotier.com/)，首次使用先创建组织，再打开默认网络；也可点 **New Network** 新建。保留私有网络设置，复制 **16 位 Network ID** 发给好友。
2. **所有人加入：**各自在电脑安装 ZeroTier。点击菜单栏或托盘图标 → **Join New Network…** → 输入同一个 Network ID → Join。
3. **建网者授权：**回到控制台该网络的 **Member Devices**，对自己和好友的设备逐台选择 **Authorize**。旧版控制台是在 Members 中勾选 **Auth**。
4. **确认地址：**双方连接成功并获得 **ZeroTier IP / Managed IP** 后，记录各自的 IPv4。后面只用这个地址，不用 Wi-Fi IP、Node ID 或 Network ID。

网络应启用 IPv4 分配，并避开现有 Wi-Fi、公司网络或其他 VPN 的网段。不要直接把下面的示例 IP 填入自己的配置。

## 2. 必须先验证双方互相 ping 成功

假设控制台分配的地址是：房主 `10.147.17.1`，玩家 `10.147.17.2`。请替换成你们的实际 ZeroTier IP。

**玩家 Mac 的终端：**

```bash
ping -c 5 10.147.17.1
```

**房主 Mac 的终端：**

```bash
ping -c 5 10.147.17.2
```

好友使用 Windows 时，在其终端把 `-c 5` 换成 `-n 5`。

**双方都收到对方的回复，建议均为 `0% packet loss`，再继续下一步。** 若超时、单向不通或出现 `No route to host / Host is down`，先检查设备授权、IP、网段冲突及防火墙的 ICMP 规则，参考[官方 ping 排错](https://docs.zerotier.com/faq/ping/)。ping 成功只证明基本连通，不保证游戏 UDP 已放行。

## 3. 下载助手，发现好友房间

**[下载最新 Mac 版](https://github.com/lirunan22/Civ6---Virtual-LAN-Helper/releases/latest)**，选择 `mac-universal.zip`，解压后打开 **Civ6 Discovery Helper.app**。同一个包适用于 M4 与 Intel，无需安装 Python。

1. 双方保持 ZeroTier 连接，使用兼容的游戏版本、DLC 和模组。
2. **房主：**在《文明 VI》打开「多人游戏 → 局域网」，创建房间。
3. **搜索房间的 Mac：**打开游戏和助手；填写本机与房主的 **ZeroTier IP**，点击「开始监听」。房主通常无需运行助手。
4. 等日志显示已检测到游戏、已记录原有端口，再回游戏进入或刷新「局域网」列表。
5. 看到好友房间后加入；联机后可以停止或关闭助手。

助手自动识别游戏的临时 UDP 端口，向房主 `62900` 补发发现请求，**无需手动填写端口**。若普通模式提示端口占用，停止后勾选「授权兼容模式」，按 macOS 提示授权，再开始监听并刷新列表。

## 常见问题

| 现象 | 先检查 |
| --- | --- |
| ping 不通、错误 64/65 | 返回第 2 步，先修复虚拟网络连通性；助手不能替代 VPN。 |
| 显示「已发送」，仍看不到房间 | 只表示本机接受了发送请求；确认房主已建 LAN 房间，允许游戏、本地网络访问及 UDP 62900 和返回流量。 |
| 能看到房间，但进不去 | 检查游戏版本、DLC/模组及后续会话流量；游戏通常还使用 UDP 62056。 |
| macOS 拦截打开或要求权限 | 下载包未做 Apple 公证，使用临时签名；按系统来源确认及本地网络权限提示处理，详见[使用与排错](docs/DETAILS.md)。 |

本工具只辅助发现房间，不配置 ZeroTier、路由或防火墙，也不代理游戏会话。原生启动和 UDP 回环已验证；不同游戏版本与真实跨机网络的效果需实测。

MIT 开源，参考 [Frwere/civ6-l3-discovery-helper](https://github.com/Frwere/civ6-l3-discovery-helper)，保留[原作者许可与归属](THIRD_PARTY.md)。[开发与构建](docs/DEVELOPMENT.md)
