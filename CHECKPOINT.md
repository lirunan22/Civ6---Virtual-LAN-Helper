# 项目进度

当前状态：v0.1.1 已公开发布并完成匿名下载校验；最终证据见本文末尾。

## 初始准备记录

本项目用于辅助解决 Mac《文明 VI》在已连通的虚拟局域网内找不到好友房间的问题。README 按 ZeroTier 建网与加入、逐台授权、双向 ping、下载并运行助手组织，详细技术和排错单独放入 docs。

仓库：`lirunan22/Civ6---Virtual-LAN-Helper`。用户已明确确认此项目公开发布；代码和 Release 均可公开访问。原生实现沿用既有已通过回环测试的版本，独立调整构建/发布路径与随包说明，版本 v0.1.1。

本地4项Python发布保护、语法、actionlint、本地Markdown链接校验通过。README 61行，官方链接与示例地址已核对；尚待首次push、macOS CI原生验收及Release附件确认，不冒称真实游戏或跨机网络已验证。

## v0.1.1 Mac 预检通过

运行42372493585，候选ee90eabc46f93d0b89806569e67e04a769db7886，固定回执ci-status/native/42372493585-1。stage complete、build success，16项原生检查全部true。4项Python发布保护通过；通用App、普通/原始UDP回环、进程/socket、授权脚本、原生GUI、签名和解压归档验证完成。准备创建v0.1.1，最终标签将重新运行全部检查后上传，尚未声称Release附件已发布。没有运行真实游戏或跨机ZeroTier。


## v0.1.1 已公开发布

仓库：[lirunan22/Civ6---Virtual-LAN-Helper](https://github.com/lirunan22/Civ6---Virtual-LAN-Helper)。用户明确授权此独立项目公开，源码及安装包无需仓库权限即可访问。

最终发行运行 [42372658627](https://github.com/lirunan22/Civ6---Virtual-LAN-Helper/actions/runs/42372658627)，应用提交 `7458d2643c3e8bb2ad565090a0095772ced0b05e`，标签 `v0.1.1`，固定回执 `ci-status/v0.1.1/42372658627-1`：status success、stage/publishStage complete，16项原生检查全true，build与publish均success，4项Python发布保护通过。最终标签重新验证Mac原生窗口、输入、进程/socket、普通/原始UDP及游戏源端口与回包、授权脚本、双架构、临时签名和解压归档。

以未登录方式实际下载全部3个公开附件，大小、SHA256、清单与ZIP CRC全部匹配。已确认最新发行链接指向v0.1.1，安装包版本正确，随包中文说明包含ZeroTier/双向ping和新仓库下载链接，详细文档亦包含在App中。Linux检查脚本按ditto文件名的实际UTF-8字节解析中文路径；未改动已发布安装包。

| 附件 | 字节 | SHA-256 |
| --- | ---: | --- |
| Civ6-Discovery-Helper-0.1.1-mac-universal.zip | 79481 | a3351eb7f925ac6a8e3a549932104233987ed6b118027acd91f9413715d56fae |
| Civ6-Discovery-Helper-0.1.1-source.zip | 36216 | 21e2383bc797e9dae54beb186fc069433665d5991abca9b8e01cd936604bba31 |
| SHA256SUMS.txt | 217 | 06a358c7105ae942a350f02a3e5a27aad70bf692a0dc0cc5624f4e1b02b48094 |

[Release与下载](https://github.com/lirunan22/Civ6---Virtual-LAN-Helper/releases/tag/v0.1.1)。README按ZeroTier创建/加入、逐台授权、实际ZT IP双向ping、下载助手及刷新LAN列表编排，官方文档链接齐全；保持61行正文，详细排错与开发文档独立。部署密钥与缓存不在Git或源码归档中，发布记录不包含原始CI日志或用户网络数据。

实际文明VI房间发现、加入、跨机ZeroTier、用户管理员授权和本地网络许可仍需用户设备实测；此次没有把CI回环当作真实联机验收。签名为ad-hoc，未做Developer ID或Apple公证。独立迁移、推送、公开Release、匿名下载校验完成。
