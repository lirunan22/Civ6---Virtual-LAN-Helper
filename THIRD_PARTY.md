# 来源与许可

参考 [Frwere/civ6-l3-discovery-helper](https://github.com/Frwere/civ6-l3-discovery-helper)，固定版本 `6fdcb74dac6ba2ed6c775b0e53e3e6b0ad358871`。该项目使用 MIT License，版权属于 `Copyright (c) 2026 Frwere Li`，完整许可证见随包附带的 [LICENSE.upstream](LICENSE.upstream)。

沿用其协议常量（UDP 62900，`8d e8 fc 70`）、以游戏新 UDP 端口发一次请求的思路、先记录基线的行为。Windows 的 ToolHelp / GetExtendedUdpTable / tkinter 均未直接移植；本项目重新实现了 macOS AppKit UI、libproc 进程/socket 查询、BSD 发包及可选的原始 UDP 发送助手。

Apple 的 [libproc API 声明](https://github.com/apple-oss-distributions/xnu/blob/main/libsyscall/wrappers/libproc/libproc.h)、[socket 查询结构](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/sys/proc_info.h)及[端口复用文档](https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man2/setsockopt.2.html)用于核对系统接口；不复制或分发 Apple 内核源码。

新实现沿用本仓库 MIT License。文明 VI 和相关商标属于各权利人；本项目为独立辅助工具。

本项目原始 Mac 实现从桌面伙伴项目的独立插件拆分，保留其 MIT 版权与许可。
