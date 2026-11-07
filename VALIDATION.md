# 验证记录

## 已验证的实现基线

此前独立插件版本已在macOS CI通过16项检查：原生窗口、输入校验、进程/socket查询、普通UDP固定报文与源端口、原始UDP在独占端口时的回复、助手UID/socket身份校验、授权脚本编译、双架构和临时签名归档。原生测试使用回环地址和模拟游戏socket，未运行实际文明VI或跨机VPN。

4项Python发布保护测试覆盖已有附件拒绝覆盖、版本标签校验、草稿URL发布后确认及回执不导出本机数据。

## 独立仓库 v0.1.1

原生网络与界面实现保持基线，迁移目录、构建/发布路径和仓库链接；随包说明改为ZeroTier建网、成员授权、双向ping、运行助手的完整流程。README参考并链接官方文档，未复制官方文档全文。

本地4项Python测试、Python语法、actionlint、本地Markdown链接检查通过。本地环境为Linux，Mac构建、原生执行和安装包已由新仓库macOS CI验证；最终证据见文末。

真实游戏房间发现、加入、跨机ZeroTier连通性、用户管理员授权/本地网络许可、不同macOS版本仍需用户设备实测。应用使用临时签名，未做Developer ID签名或Apple公证。

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
