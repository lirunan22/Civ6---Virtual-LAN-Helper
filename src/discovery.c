// Protocol and new-endpoint policy adapted from Frwere/civ6-l3-discovery-helper
// (MIT). See LICENSE.upstream and THIRD_PARTY.md. macOS implementation is new.
#include "discovery.h"
#include <arpa/inet.h>
#include <errno.h>
#include <ifaddrs.h>
#include <net/if.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <sys/socket.h>
#include <unistd.h>
#ifdef __APPLE__
#include <libproc.h>
#include <sys/proc_info.h>
#include <sys/sysctl.h>
#endif

static struct sockaddr_in cd_address(uint32_t address, uint16_t port) {
    struct sockaddr_in a = {0};
#ifdef __APPLE__
    a.sin_len = sizeof(a);
#endif
    a.sin_family = AF_INET;
    a.sin_addr.s_addr = address;
    a.sin_port = htons(port);
    return a;
}

int cd_ipv4(const char *text, uint32_t *address) {
    struct in_addr a;
    if (!text || inet_pton(AF_INET, text, &a) != 1) return 0;
    uint32_t h = ntohl(a.s_addr);
    if (!h || h == UINT32_MAX || (h >> 24) == 0 || (h >> 24) == 127 || (h >> 28) >= 14)
        return 0;
    if (address) *address = a.s_addr;
    return 1;
}

int cd_private_ipv4(uint32_t address) {
    uint32_t h = ntohl(address);
    return (h >> 24) == 10 || (h >> 20) == 0xac1 || (h >> 16) == 0xc0a8 ||
           (h >> 22) == 0x191; // RFC1918 + CGNAT (Tailscale); no public targets.
}

int cd_local_ipv4(uint32_t address) {
    struct ifaddrs *list = NULL;
    if (getifaddrs(&list)) return 0;
    int found = 0;
    for (struct ifaddrs *p = list; p; p = p->ifa_next) {
        if (p->ifa_addr && p->ifa_addr->sa_family == AF_INET && (p->ifa_flags & IFF_UP) &&
            ((struct sockaddr_in *)p->ifa_addr)->sin_addr.s_addr == address) found = 1;
    }
    freeifaddrs(list);
    return found;
}

int cd_route(const char *host, char result[16]) {
    uint32_t address;
    if (!cd_ipv4(host, &address) || !cd_private_ipv4(address)) return EINVAL;
    int s = socket(AF_INET, SOCK_DGRAM, 0);
    if (s < 0) return errno;
    struct sockaddr_in target = cd_address(address, CD_PORT), local = {0};
    socklen_t size = sizeof(local);
    int error = 0;
    // UDP connect selects a route without sending any discovery packet.
    if (connect(s, (struct sockaddr *)&target, sizeof(target)) ||
        getsockname(s, (struct sockaddr *)&local, &size) ||
        !inet_ntop(AF_INET, &local.sin_addr, result, 16)) error = errno;
    close(s);
    return error;
}

int cd_game_name(const char *name) {
    const char *names[] = {"Civ6", "Civ6_Exe", "Civ6_Exe_Child", "Civilization VI", "CivilizationVI", NULL};
    for (int i = 0; names[i]; i++) if (!strcasecmp(name, names[i])) return 1;
    return 0;
}

int cd_process_allowed(pid_t pid, uid_t owner) {
#ifdef __APPLE__
    struct proc_bsdinfo info = {0};
    char path[PROC_PIDPATHINFO_MAXSIZE] = {0};
    if (pid <= 1 || proc_pidinfo(pid, PROC_PIDTBSDINFO, 0, &info, sizeof(info)) != sizeof(info) ||
        info.pbi_uid != owner || info.pbi_ruid != owner ||
        proc_pidpath(pid, path, sizeof(path)) <= 0) return 0;
    const char *leaf = strrchr(path, '/');
    return leaf && cd_game_name(leaf + 1);
#else
    (void)pid; (void)owner;
    return 0;
#endif
}

int cd_processes(uid_t owner, pid_t *pids, int capacity) {
#ifdef __APPLE__
    int bytes = proc_listpids(PROC_UID_ONLY, owner, NULL, 0);
    if (bytes <= 0) return -1;
    bytes += 1024 * (int)sizeof(pid_t);
    pid_t *all = calloc(1, (size_t)bytes);
    if (!all) return -1;
    int count = proc_listpids(PROC_UID_ONLY, owner, all, bytes) / (int)sizeof(pid_t), n = 0;
    for (int i = 0; i < count && n < capacity; i++)
        if (cd_process_allowed(all[i], owner)) pids[n++] = all[i];
    free(all);
    return n;
#else
    (void)owner; (void)pids; (void)capacity;
    errno = ENOSYS;
    return -1;
#endif
}

int cd_endpoints(pid_t pid, CDEndpoint *items, int capacity) {
#ifdef __APPLE__
    int bytes = proc_pidinfo(pid, PROC_PIDLISTFDS, 0, NULL, 0);
    if (bytes <= 0) return -1;
    bytes += 128 * (int)sizeof(struct proc_fdinfo);
    struct proc_fdinfo *fds = calloc(1, (size_t)bytes);
    if (!fds) return -1;
    int got = proc_pidinfo(pid, PROC_PIDLISTFDS, 0, fds, bytes);
    if (got <= 0) { free(fds); return -1; }
    int count = got / (int)sizeof(*fds), n = 0;
    for (int i = 0; i < count && n < capacity; i++) {
        if (fds[i].proc_fdtype != PROX_FDTYPE_SOCKET) continue;
        struct socket_fdinfo s = {0};
        if (proc_pidfdinfo(pid, fds[i].proc_fd, PROC_PIDFDSOCKETINFO, &s, sizeof(s)) != sizeof(s)) continue;
        if (s.psi.soi_kind != SOCKINFO_IN || s.psi.soi_type != SOCK_DGRAM ||
            s.psi.soi_protocol != IPPROTO_UDP) continue;
        struct in_sockinfo *in = &s.psi.soi_proto.pri_in;
        if (!(in->insi_vflag & INI_IPV4) || in->insi_fport) continue;
        items[n++] = (CDEndpoint){pid, ntohs((uint16_t)in->insi_lport),
                                in->insi_laddr.ina_46.i46a_addr4.s_addr,
                                in->insi_gencnt ? in->insi_gencnt : s.psi.soi_so};
    }
    free(fds);
    return n;
#else
    (void)pid; (void)items; (void)capacity;
    errno = ENOSYS;
    return -1;
#endif
}

uint16_t cd_dynamic_first(void) {
    int first = 49152;
#ifdef __APPLE__
    size_t size = sizeof(first);
    if (sysctlbyname("net.inet.ip.portrange.first", &first, &size, NULL, 0)) first = 49152;
#endif
    return (uint16_t)(first >= 1024 && first <= 65535 ? first : 49152);
}

int cd_candidate(const CDEndpoint *item, uint32_t local, uint16_t first) {
    return item->port >= first && item->port != CD_PORT && item->port != CD_SESSION_PORT &&
           (!item->address || item->address == local);
}

int cd_send(const char *local, const char *host, uint16_t port, int raw) {
    struct in_addr source, destination;
    if (port < 1024 || port == CD_PORT || port == CD_SESSION_PORT ||
        inet_pton(AF_INET, local, &source) != 1 || inet_pton(AF_INET, host, &destination) != 1) return EINVAL;
    int s = socket(AF_INET, raw ? SOCK_RAW : SOCK_DGRAM, raw ? IPPROTO_UDP : 0);
    if (s < 0) return errno;
    int one = 1, error = 0;
    if (!raw) {
        if (setsockopt(s, SOL_SOCKET, SO_REUSEADDR, &one, sizeof(one)) ||
            setsockopt(s, SOL_SOCKET, SO_REUSEPORT, &one, sizeof(one))) error = errno;
    }
    // With raw IPPROTO_UDP, Darwin builds the IPv4 header. We supply only the
    // UDP header, retaining the game's source port without binding that port.
    struct sockaddr_in from = cd_address(source.s_addr, raw ? 0 : port);
    struct sockaddr_in to = cd_address(destination.s_addr, raw ? 0 : CD_PORT);
    if (!error && bind(s, (struct sockaddr *)&from, sizeof(from))) error = errno;
    const uint8_t magic[] = {0x8d, 0xe8, 0xfc, 0x70};
    uint8_t packet[12] = {0};
    uint16_t value = htons(port); memcpy(packet, &value, 2);
    value = htons(CD_PORT); memcpy(packet + 2, &value, 2);
    value = htons(sizeof(packet)); memcpy(packet + 4, &value, 2);
    // IPv4 permits a zero UDP checksum. No IP_HDRINCL / Darwin ip_len ambiguity.
    memcpy(packet + 8, magic, sizeof(magic));
    const void *payload = raw ? packet : magic;
    size_t size = raw ? sizeof(packet) : sizeof(magic);
    if (!error && sendto(s, payload, size, 0, (struct sockaddr *)&to, sizeof(to)) != (ssize_t)size)
        error = errno ? errno : EIO;
    close(s); // Close immediately so a normal socket cannot consume game replies.
    return error;
}

int cd_transfer(int fd, void *buffer, size_t bytes, int writing) {
    uint8_t *p = buffer;
    while (bytes) {
        ssize_t n = writing ? write(fd, p, bytes) : read(fd, p, bytes);
        if (n < 0 && errno == EINTR) continue;
        if (n <= 0) return n == 0 ? ECONNRESET : errno;
        p += n; bytes -= (size_t)n;
    }
    return 0;
}

int cd_request_allowed(const CDRequest *r, uid_t owner, uint32_t local) {
    if (r->magic != CD_MAGIC || r->pid > INT32_MAX || r->port > UINT16_MAX ||
        !cd_local_ipv4(local) || !cd_process_allowed((pid_t)r->pid, owner)) return 0;
    CDEndpoint items[CD_CAPACITY];
    int count = cd_endpoints((pid_t)r->pid, items, CD_CAPACITY);
    for (int i = 0; i < count; i++)
        if (items[i].socket_id == r->socket_id && items[i].port == r->port &&
            cd_candidate(&items[i], local, cd_dynamic_first())) return 1;
    return 0;
}
