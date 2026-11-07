# 开发与构建

这是一个独立的原生 Mac 项目。运行不需要桌宠或 Python；Python 仅用于开发构建。

## 目录

```text
src/             AppKit 界面、BSD UDP、libproc、系统授权脚本
tests/           UDP 回环与发布保护测试
build.py         构建 Universal App、原生验证、生成安装包与源码包
release.py       发布前后校验、不可覆盖附件、固定 CI 回执
docs/            详细排错与开发说明
```

## 本地构建

需要 macOS 12+、Xcode Command Line Tools 和 Python 3。

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
python3 build.py
```

输出在 `artifacts/`。`python3 build.py --test` 用于一次性 macOS CI，会运行进程/socket 查询、普通 UDP 回环、通过 `sudo -n` 执行的原始 UDP 回环及原生 GUI 冒烟。所有测试包仅发往回环地址；不尝试连接实际游戏或外部 VPN。

## 发布

修改 `build.py` 中的 `VERSION` 后，提交并推送对应的 `v版本号` 标签。GitHub Actions 自动重新验证并创建公开 Release，附上通用 Mac ZIP、源码 ZIP 和 `SHA256SUMS.txt`。已有附件大小或摘要不符时拒绝覆盖。

签名为 ad-hoc，不含 Developer ID 或 Apple 公证。真实游戏、双方 VPN、防火墙许可与用户管理员授权窗口需要另行实测。完整边界见 [VALIDATION.md](../VALIDATION.md)。
