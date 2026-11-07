# Civ6 Mac LAN Helper

This standalone macOS AppKit/C application helps Civilization VI discover LAN
rooms across an already working virtual network. Keep the README short and user
oriented: ZeroTier setup, explicit authorization of every device, mutual ping,
then app download and LAN discovery. Link official ZeroTier documentation.

Do not configure VPNs, route tables, firewalls, other repositories, credentials,
platform instances or startup services. Keep the normal mode unprivileged and
compatibility mode explicitly opted into through the native administrator prompt.
The helper may send only the fixed discovery request to one configured private IP.

Preserve upstream MIT attribution. Distinguish kernel send acceptance from room
discovery. Do not claim real-game, remote-VPN, administrator-dialog or Developer
ID/notarization testing without evidence. Network tests use loopback only.

Use macOS CI to build, sign ad hoc, launch and validate both architectures. Keep
release assets immutable and verify digests. Fixed CI receipts may contain only
allowlisted stages, booleans and expected attachment metadata; never export logs,
IP addresses or credentials. Record meaningful progress in CHECKPOINT.md and
test boundaries in VALIDATION.md. The user has authorized GitHub management.
