#import <Cocoa/Cocoa.h>
#include "discovery.h"
#include <arpa/inet.h>
#include <errno.h>
#include <ifaddrs.h>
#include <net/if.h>
#include <poll.h>
#include <signal.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>

@interface CDSession : NSObject
@property(atomic) BOOL stopped;
@property int helperFD;
@property(nonatomic, strong) NSTask *authorization;
@end
@implementation CDSession
- (instancetype)init { if ((self = [super init])) _helperFD = -1; return self; }
- (void)stop {
    self.stopped = YES;
    @synchronized(self) {
        if (self.helperFD >= 0) shutdown(self.helperFD, SHUT_RDWR);
        if (self.authorization.running) [self.authorization terminate];
    }
}
- (void)disconnect {
    @synchronized(self) {
        if (self.helperFD >= 0) { close(self.helperFD); self.helperFD = -1; }
    }
}
@end

static NSString *trim(NSString *s) {
    return [s stringByTrimmingCharactersInSet:NSCharacterSet.whitespaceAndNewlineCharacterSet];
}
static NSString *shellQuote(NSString *s) {
    return [NSString stringWithFormat:@"'%@'", [s stringByReplacingOccurrencesOfString:@"'" withString:@"'\\''"]];
}
static NSString *endpointKey(CDEndpoint e) {
    return [NSString stringWithFormat:@"%d:%llu:%u", e.pid, (unsigned long long)e.socket_id, e.port];
}

// Native administrator dialog, opened only after the user selects compatibility
// mode and presses Start. Passwords are handled by macOS, never read by this app.
static int authorizeSender(CDSession *session, NSString *local, NSString *host) {
    char folder[] = "/tmp/civ6-discovery.XXXXXX";
    if (!mkdtemp(folder)) return errno;
    NSString *socketPath = [@(folder) stringByAppendingPathComponent:@"sender.sock"];
    int listener = socket(AF_UNIX, SOCK_STREAM, 0), result = ECANCELED;
    if (listener < 0) { rmdir(folder); return errno; }
    struct sockaddr_un address = {0};
    address.sun_family = AF_UNIX; address.sun_len = sizeof(address);
    strlcpy(address.sun_path, socketPath.fileSystemRepresentation, sizeof(address.sun_path));
    if (bind(listener, (struct sockaddr *)&address, sizeof(address)) || listen(listener, 1)) {
        result = errno; close(listener); unlink(address.sun_path); rmdir(folder); return result;
    }
    NSString *helper = [NSBundle.mainBundle.bundlePath stringByAppendingPathComponent:@"Contents/Helpers/civ6-sender"];
    NSString *command = [@[shellQuote(helper), shellQuote(socketPath),
        shellQuote(@(getpid()).stringValue), shellQuote(local), shellQuote(host)] componentsJoinedByString:@" "];
    NSTask *task = [NSTask new];
    task.executableURL = [NSURL fileURLWithPath:@"/usr/bin/osascript"];
    task.arguments = @[[NSBundle.mainBundle.resourcePath stringByAppendingPathComponent:@"authorize.scpt"], command];
    task.standardOutput = [NSFileHandle fileHandleWithNullDevice];
    task.standardError = [NSFileHandle fileHandleWithNullDevice];
    NSError *launchError = nil;
    @synchronized(session) {
        if (!session.stopped) { session.authorization = task; [task launchAndReturnError:&launchError]; }
    }
    if (launchError) result = EIO;
    NSDate *deadline = [NSDate dateWithTimeIntervalSinceNow:120];
    while (!launchError && !session.stopped && deadline.timeIntervalSinceNow > 0) {
        if (!task.running) break;
        struct pollfd wait = {listener, POLLIN, 0};
        if (poll(&wait, 1, 100) <= 0) continue;
        int client = accept(listener, NULL, NULL);
        uid_t uid; gid_t gid;
        if (client < 0) continue;
        if (getpeereid(client, &uid, &gid) || uid != 0) { close(client); continue; }
        struct timeval timeout = {2, 0};
        setsockopt(client, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout));
        setsockopt(client, SOL_SOCKET, SO_SNDTIMEO, &timeout, sizeof(timeout));
        uint32_t ready = 1;
        result = cd_transfer(client, &ready, sizeof(ready), 0);
        if (!result && !ready && !session.stopped) {
            @synchronized(session) { session.helperFD = client; }
            result = 0; break;
        }
        close(client); result = ECANCELED;
    }
    close(listener); unlink(address.sun_path); rmdir(folder);
    if (result) [session stop];
    return result;
}

@interface CDApp : NSObject <NSApplicationDelegate>
@property(nonatomic, strong) NSWindow *window;
@property(nonatomic, strong) NSTextField *host;
@property(nonatomic, strong) NSTextField *local;
@property(nonatomic, strong) NSTextField *status;
@property(nonatomic, strong) NSTextField *summary;
@property(nonatomic, strong) NSPopUpButton *interfaces;
@property(nonatomic, strong) NSButton *route;
@property(nonatomic, strong) NSButton *start;
@property(nonatomic, strong) NSButton *stop;
@property(nonatomic, strong) NSButton *compatibility;
@property(nonatomic, strong) NSTextView *log;
@property(nonatomic, strong) CDSession *session;
@property NSUInteger sent, failed;
@property BOOL smoke;
@end

@implementation CDApp
- (NSTextField *)label:(NSString *)text size:(CGFloat)size {
    NSTextField *label = [NSTextField wrappingLabelWithString:text];
    label.font = [NSFont systemFontOfSize:size]; return label;
}
- (NSButton *)button:(NSString *)title action:(SEL)action {
    NSButton *button = [NSButton buttonWithTitle:title target:self action:action];
    button.bezelStyle = NSBezelStyleRounded; return button;
}
- (void)applicationDidFinishLaunching:(NSNotification *)notice {
    (void)notice;
    self.window = [[NSWindow alloc] initWithContentRect:NSMakeRect(0, 0, 710, 670)
        styleMask:NSWindowStyleMaskTitled | NSWindowStyleMaskClosable | NSWindowStyleMaskMiniaturizable | NSWindowStyleMaskResizable
        backing:NSBackingStoreBuffered defer:NO];
    self.window.title = @"文明 VI · 联机发现助手";
    self.window.minSize = NSMakeSize(660, 620);
    NSStackView *stack = [NSStackView new]; stack.orientation = NSUserInterfaceLayoutOrientationVertical;
    stack.alignment = NSLayoutAttributeLeading; stack.spacing = 12;
    stack.translatesAutoresizingMaskIntoConstraints = NO;
    [self.window.contentView addSubview:stack];
    [NSLayoutConstraint activateConstraints:@[
        [stack.leadingAnchor constraintEqualToAnchor:self.window.contentView.leadingAnchor constant:24],
        [stack.trailingAnchor constraintEqualToAnchor:self.window.contentView.trailingAnchor constant:-24],
        [stack.topAnchor constraintEqualToAnchor:self.window.contentView.topAnchor constant:24],
        [stack.bottomAnchor constraintEqualToAnchor:self.window.contentView.bottomAnchor constant:-24]]];
    NSTextField *heading = [self label:@"找到朋友的文明 VI 房间" size:24];
    heading.font = [NSFont systemFontOfSize:24 weight:NSFontWeightSemibold]; [stack addArrangedSubview:heading];
    [stack addArrangedSubview:[self label:@"先连好 VPN，房主创建局域网房间；在搜索房间的这台 Mac 运行本工具。" size:13]];
    self.host = [NSTextField new]; self.host.placeholderString = @"房主的虚拟网 IPv4，例如 10.88.66.3";
    self.host.accessibilityLabel = @"房主 IP";
    self.local = [NSTextField new]; self.local.placeholderString = @"本机虚拟网 IPv4，可自动选择或手动填写";
    self.local.accessibilityLabel = @"本机 IP";
    [stack addArrangedSubview:[self label:@"1 · 填写房主地址" size:14]]; [stack addArrangedSubview:self.host];
    [self.host.widthAnchor constraintEqualToAnchor:stack.widthAnchor].active = YES;
    [stack addArrangedSubview:[self label:@"2 · 选择本机的虚拟网地址" size:14]]; [stack addArrangedSubview:self.local];
    [self.local.widthAnchor constraintEqualToAnchor:stack.widthAnchor].active = YES;
    self.interfaces = [NSPopUpButton new]; self.interfaces.target = self; self.interfaces.action = @selector(chooseInterface:);
    self.route = [self button:@"按房主地址自动选择" action:@selector(detectRoute:)];
    NSStackView *network = [NSStackView stackViewWithViews:@[self.interfaces, self.route,
        [self button:@"刷新网卡" action:@selector(refreshInterfaces:)]]]; network.spacing = 8;
    [stack addArrangedSubview:network];
    self.compatibility = [NSButton checkboxWithTitle:@"授权兼容模式（普通模式提示端口占用时使用）" target:nil action:nil];
    [stack addArrangedSubview:self.compatibility];
    [stack addArrangedSubview:[self label:@"兼容模式会弹出 macOS 管理员授权。仅临时补发发现包；停止、关闭工具或 30 分钟后结束。" size:12]];
    self.start = [self button:@"开始监听" action:@selector(startMonitoring:)]; self.start.keyEquivalent = @"\r";
    self.stop = [self button:@"停止" action:@selector(stopMonitoring:)]; self.stop.enabled = NO;
    NSStackView *controls = [NSStackView stackViewWithViews:@[self.start, self.stop,
        [self button:@"使用说明" action:@selector(showHelp:)]]]; controls.spacing = 10;
    [stack addArrangedSubview:controls];
    self.status = [self label:@"准备好后开始监听，再回游戏刷新局域网列表。" size:13];
    self.summary = [self label:@"已发送 0 · 失败 0" size:12];
    [stack addArrangedSubview:self.status]; [stack addArrangedSubview:self.summary];
    NSScrollView *scroll = [NSScrollView new]; scroll.hasVerticalScroller = YES; scroll.borderType = NSBezelBorder;
    self.log = [[NSTextView alloc] initWithFrame:NSMakeRect(0, 0, 620, 180)];
    self.log.editable = NO; self.log.font = [NSFont monospacedSystemFontOfSize:11 weight:NSFontWeightRegular];
    self.log.autoresizingMask = NSViewWidthSizable; self.log.textContainer.widthTracksTextView = YES;
    scroll.documentView = self.log; [stack addArrangedSubview:scroll];
    [scroll.widthAnchor constraintEqualToAnchor:stack.widthAnchor].active = YES;
    [scroll.heightAnchor constraintGreaterThanOrEqualToConstant:120].active = YES;
    [stack addArrangedSubview:[self label:@"发包成功仅代表请求已发送。能否发现、加入房间，仍取决于游戏版本、VPN 和双方防火墙。" size:12]];
    [self refreshInterfaces:nil];
    NSMenu *menu = [NSMenu new], *application = [NSMenu new];
    NSMenuItem *root = [NSMenuItem new]; root.submenu = application; [menu addItem:root];
    [application addItemWithTitle:@"退出联机发现助手" action:@selector(terminate:) keyEquivalent:@"q"];
    NSMenuItem *edit = [[NSMenuItem alloc] initWithTitle:@"编辑" action:nil keyEquivalent:@""];
    edit.submenu = [NSMenu new];
    [edit.submenu addItemWithTitle:@"剪切" action:@selector(cut:) keyEquivalent:@"x"];
    [edit.submenu addItemWithTitle:@"复制" action:@selector(copy:) keyEquivalent:@"c"];
    [edit.submenu addItemWithTitle:@"粘贴" action:@selector(paste:) keyEquivalent:@"v"];
    [edit.submenu addItemWithTitle:@"全选" action:@selector(selectAll:) keyEquivalent:@"a"];
    [menu addItem:edit]; NSApp.mainMenu = menu;
    [self.window center]; [self.window makeKeyAndOrderFront:nil]; [NSApp activateIgnoringOtherApps:YES];
    if (self.smoke) [self performSelector:@selector(smokeTest) withObject:nil afterDelay:0.3];
}
- (void)refreshInterfaces:(id)sender {
    (void)sender; [self.interfaces removeAllItems]; [self.interfaces addItemWithTitle:@"从网卡选择本机 IPv4…"];
    struct ifaddrs *list = NULL;
    if (getifaddrs(&list)) return;
    for (struct ifaddrs *p = list; p; p = p->ifa_next) {
        if (!p->ifa_addr || p->ifa_addr->sa_family != AF_INET || !(p->ifa_flags & IFF_UP)) continue;
        struct in_addr a = ((struct sockaddr_in *)p->ifa_addr)->sin_addr;
        if (!cd_private_ipv4(a.s_addr)) continue;
        char address[16]; inet_ntop(AF_INET, &a, address, sizeof(address));
        [self.interfaces addItemWithTitle:[NSString stringWithFormat:@"%s · %s", p->ifa_name, address]];
        self.interfaces.lastItem.representedObject = @(address);
    }
    freeifaddrs(list);
}
- (void)chooseInterface:(id)sender {
    (void)sender; NSString *ip = self.interfaces.selectedItem.representedObject;
    if (ip) self.local.stringValue = ip;
}
- (void)detectRoute:(id)sender {
    (void)sender; char result[16] = {0};
    int error = cd_route(trim(self.host.stringValue).UTF8String, result);
    if (error) { self.status.stringValue = @"请填写房主的私网 IPv4，并确认 VPN 已连接。"; return; }
    self.local.stringValue = @(result); self.status.stringValue = @"已按系统路由选择地址，请确认这是 VPN 的本机 IP。";
}
- (void)append:(NSString *)message {
    NSString *line = [NSString stringWithFormat:@"%@  %@\n", [NSDateFormatter localizedStringFromDate:NSDate.date dateStyle:NSDateFormatterNoStyle timeStyle:NSDateFormatterMediumStyle], message];
    [self.log.textStorage appendAttributedString:[[NSAttributedString alloc] initWithString:line attributes:@{NSFontAttributeName:self.log.font}]];
    if (self.log.string.length > 24000) [self.log.textStorage deleteCharactersInRange:NSMakeRange(0, self.log.string.length - 18000)];
    [self.log scrollRangeToVisible:NSMakeRange(self.log.string.length, 0)];
}
- (void)message:(NSString *)message session:(CDSession *)session {
    dispatch_async(dispatch_get_main_queue(), ^{ if (self.session == session) [self append:message]; });
}
- (void)setBusy:(BOOL)busy {
    self.start.enabled = !busy; self.stop.enabled = busy; self.host.enabled = !busy;
    self.local.enabled = !busy; self.route.enabled = !busy; self.interfaces.enabled = !busy; self.compatibility.enabled = !busy;
}
- (void)startMonitoring:(id)sender {
    (void)sender; if (self.session) return;
    NSString *local = trim(self.local.stringValue), *host = trim(self.host.stringValue);
    uint32_t l, h;
    if (!cd_ipv4(host.UTF8String, &h) || !cd_private_ipv4(h)) {
        self.status.stringValue = @"房主 IP 需为私网 IPv4（10、172.16–31、192.168，或 VPN 的 100.64–127 网段）。"; return;
    }
    if (!cd_ipv4(local.UTF8String, &l) || !cd_private_ipv4(l) || !cd_local_ipv4(l) || l == h) {
        self.status.stringValue = @"本机 IP 必须是这台 Mac 当前网卡上的私网地址，并与房主不同。"; return;
    }
    CDSession *session = [CDSession new]; self.session = session;
    BOOL raw = self.compatibility.state == NSControlStateValueOn;
    self.sent = self.failed = 0; self.summary.stringValue = @"已发送 0 · 失败 0";
    [self setBusy:YES];
    self.status.stringValue = raw ? @"等待 macOS 授权；可点停止取消。" : @"正在查找本机文明 VI 进程…";
    [self append:[NSString stringWithFormat:@"%@ → %@:%d · %@", local, host, CD_PORT, raw ? @"授权兼容模式" : @"普通模式"]];
    dispatch_async(dispatch_get_global_queue(QOS_CLASS_USER_INITIATED, 0), ^{
        if (raw && authorizeSender(session, local, host)) {
            [self message:@"授权已取消、超时或发送助手未启动。可取消兼容模式后重试普通模式。" session:session];
        } else {
            [self monitor:session local:local host:host raw:raw];
        }
        [session disconnect];
        dispatch_async(dispatch_get_main_queue(), ^{
            if (self.session != session) return;
            self.session = nil; [self setBusy:NO];
            self.status.stringValue = @"已停止。可调整地址或模式后重新开始。";
        });
    });
}
- (void)monitor:(CDSession *)session local:(NSString *)local host:(NSString *)host raw:(BOOL)raw {
    uint32_t localAddress = 0; cd_ipv4(local.UTF8String, &localAddress);
    uint16_t first = cd_dynamic_first();
    NSMutableDictionary<NSNumber *, NSSet<NSString *> *> *known = [NSMutableDictionary new];
    NSMutableSet<NSNumber *> *denied = [NSMutableSet new];
    pid_t pids[64]; int count = 0; double nextRefresh = 0, burst = 0;
    NSArray *lastPids = nil;
    [self message:@"监听已启动。先保留已有端口作为基线，再回游戏刷新局域网列表。" session:session];
    while (!session.stopped) { @autoreleasepool {
        double now = NSProcessInfo.processInfo.systemUptime;
        if (now >= nextRefresh) {
            count = cd_processes(getuid(), pids, 64); nextRefresh = now + 1;
            NSMutableArray *currentPids = [NSMutableArray new];
            for (int i = 0; i < count; i++) [currentPids addObject:@(pids[i])];
            if (![currentPids isEqual:lastPids]) {
                for (NSNumber *old in known.allKeys) if (![currentPids containsObject:old]) { [known removeObjectForKey:old]; [denied removeObject:old]; }
                lastPids = currentPids; burst = now + 3;
                [self message:count > 0 ? [NSString stringWithFormat:@"检测到游戏进程 %@，请刷新局域网列表。", [currentPids componentsJoinedByString:@", "]] : @"未检测到原生文明 VI。请先打开游戏；Steam/Aspyr 启动器本身不是游戏进程。" session:session];
            }
        }
        if (!cd_local_ipv4(localAddress)) { [self message:@"本机地址已离线，监听停止。请重连 VPN 并重新选择本机 IP。" session:session]; break; }
        for (int i = 0; i < count && !session.stopped; i++) {
            CDEndpoint items[CD_CAPACITY]; int n = cd_endpoints(pids[i], items, CD_CAPACITY);
            NSNumber *pid = @(pids[i]);
            if (n < 0) {
                if (![denied containsObject:pid]) { [denied addObject:pid]; [self message:@"暂时无法读取游戏 UDP 端口；进程可能已退出，或 macOS 限制读取。" session:session]; }
                continue; // Keep baseline on transient failure; never resend old ports.
            }
            NSMutableSet *keys = [NSMutableSet new];
            for (int j = 0; j < n; j++) if (cd_candidate(&items[j], localAddress, first)) [keys addObject:endpointKey(items[j])];
            NSSet *previous = known[pid]; known[pid] = keys;
            if (!previous) { [self message:[NSString stringWithFormat:@"PID %@ · 已记录 %lu 个原有端口，新端口起始 %u。", pid, (unsigned long)keys.count, first] session:session]; continue; }
            if (![keys isEqualToSet:previous]) burst = now + 3;
            NSMutableSet *attempted = [previous mutableCopy];
            for (int j = 0; j < n && !session.stopped; j++) {
                CDEndpoint ep = items[j];
                if (!cd_candidate(&ep, localAddress, first) || [attempted containsObject:endpointKey(ep)]) continue;
                [attempted addObject:endpointKey(ep)];
                int error;
                if (raw) {
                    CDRequest request = {CD_MAGIC, (uint64_t)ep.pid, ep.port, ep.socket_id}; uint32_t reply = 0;
                    error = cd_transfer(session.helperFD, &request, sizeof(request), 1);
                    if (!error) error = cd_transfer(session.helperFD, &reply, sizeof(reply), 0);
                    if (!error) error = (int)reply;
                    if (error == ECONNRESET || error == EPIPE || error == EBADF) session.stopped = YES;
                } else error = cd_send(local.UTF8String, host.UTF8String, ep.port, 0);
                NSString *message = error ? [NSString stringWithFormat:@"发送失败 · 端口 %u · %s (%d)%@", ep.port, strerror(error), error, error == EADDRINUSE ? @"。游戏未允许端口复用，请停止后开启授权兼容模式，再刷新列表。" : @""] : [NSString stringWithFormat:@"已发送 · %@:%u → %@:%d · 8d e8 fc 70", local, ep.port, host, CD_PORT];
                dispatch_async(dispatch_get_main_queue(), ^{
                    if (self.session != session) return;
                    if (error) self.failed++; else self.sent++;
                    self.summary.stringValue = [NSString stringWithFormat:@"已发送 %lu · 失败 %lu", (unsigned long)self.sent, (unsigned long)self.failed];
                    self.status.stringValue = error ? @"发现请求未发送，请查看下面的原因。" : @"请求已发送；请在游戏内查看房间列表。";
                    [self append:message];
                });
            }
        }
        usleep(count <= 0 ? 200000 : (now < burst ? 20000 : 100000));
    }}
    [self message:@"监听结束，发送助手已断开。若兼容模式达到 30 分钟，请重新开始。" session:session];
}
- (void)stopMonitoring:(id)sender {
    (void)sender; [self.session stop]; self.stop.enabled = NO; self.status.stringValue = @"正在停止…";
}
- (void)showHelp:(id)sender {
    (void)sender;
    NSString *file = [NSBundle.mainBundle.resourcePath stringByAppendingPathComponent:@"使用说明.md"];
    [NSWorkspace.sharedWorkspace openURL:[NSURL fileURLWithPath:file]];
}
- (BOOL)applicationShouldTerminateAfterLastWindowClosed:(NSApplication *)sender { (void)sender; return YES; }
- (NSApplicationTerminateReply)applicationShouldTerminate:(NSApplication *)sender { (void)sender; [self.session stop]; return NSTerminateNow; }
- (void)smokeTest {
    BOOL initial = self.start.enabled && !self.stop.enabled && self.compatibility.state == NSControlStateValueOff;
    self.host.stringValue = @"bad; $(echo no)"; [self startMonitoring:nil];
    BOOL validation = !self.session && self.start.enabled && [self.status.stringValue containsString:@"房主 IP"];
    BOOL native = self.window.visible && self.window.contentView.subviews.count > 0;
    BOOL files = [NSFileManager.defaultManager isExecutableFileAtPath:[NSBundle.mainBundle.bundlePath stringByAppendingPathComponent:@"Contents/Helpers/civ6-sender"]] &&
        [NSFileManager.defaultManager fileExistsAtPath:[NSBundle.mainBundle.resourcePath stringByAppendingPathComponent:@"使用说明.md"]];
    printf("{\"gui\":%s,\"inputValidation\":%s,\"defaultUnprivileged\":%s,\"bundledFiles\":%s}\n", native ? "true" : "false", validation ? "true" : "false", initial ? "true" : "false", files ? "true" : "false");
    fflush(stdout); exit(native && validation && initial && files ? 0 : 1);
}
@end

int main(int argc, const char *argv[]) {
    @autoreleasepool {
        signal(SIGPIPE, SIG_IGN);
        [NSApplication sharedApplication]; [NSApp setActivationPolicy:NSApplicationActivationPolicyRegular];
        __attribute__((objc_precise_lifetime)) CDApp *delegate = [CDApp new]; delegate.smoke = argc == 2 && !strcmp(argv[1], "--smoke-test");
        NSApp.delegate = delegate; [NSApp run];
    }
    return 0;
}
