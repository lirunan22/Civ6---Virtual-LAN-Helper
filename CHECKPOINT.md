# 项目进度

## 独立公开仓库 v0.1.1（准备中）

本项目用于辅助解决 Mac《文明 VI》在已连通的虚拟局域网内找不到好友房间的问题。README 按 ZeroTier 建网与加入、逐台授权、双向 ping、下载并运行助手组织，详细技术和排错单独放入 docs。

仓库：`lirunan22/Civ6---Virtual-LAN-Helper`。用户已明确确认此项目公开发布；代码和 Release 均可公开访问。原生实现沿用既有已通过回环测试的版本，独立调整构建/发布路径与随包说明，版本 v0.1.1。

本地4项Python发布保护、语法、actionlint、本地Markdown链接校验通过。README 61行，官方链接与示例地址已核对；尚待首次push、macOS CI原生验收及Release附件确认，不冒称真实游戏或跨机网络已验证。

## v0.1.1 Mac 预检通过

运行42372493585，候选ee90eabc46f93d0b89806569e67e04a769db7886，固定回执ci-status/native/42372493585-1。stage complete、build success，16项原生检查全部true。4项Python发布保护通过；通用App、普通/原始UDP回环、进程/socket、授权脚本、原生GUI、签名和解压归档验证完成。准备创建v0.1.1，最终标签将重新运行全部检查后上传，尚未声称Release附件已发布。没有运行真实游戏或跨机ZeroTier。
