// Short-lived, explicitly authorized sender. No daemon, installation or listener.
#include "discovery.h"
#include <arpa/inet.h>
#include <errno.h>
#include <libproc.h>
#include <poll.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/proc_info.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <sys/un.h>
#include <time.h>
#include <unistd.h>

int main(int argc, char **argv) {
    if (argc != 5 || geteuid() != 0) return 64;
    const char *path = argv[1], *local = argv[3], *host = argv[4];
    char *end = NULL;
    long owner_pid = strtol(argv[2], &end, 10);
    uint32_t local_address, host_address;
    struct proc_bsdinfo owner = {0};
    if (*end || owner_pid <= 1 || owner_pid > INT32_MAX || strlen(path) >= sizeof(((struct sockaddr_un *)0)->sun_path) ||
        !cd_ipv4(local, &local_address) || !cd_ipv4(host, &host_address) ||
        !cd_private_ipv4(local_address) || !cd_private_ipv4(host_address) || local_address == host_address ||
        !cd_local_ipv4(local_address) ||
        proc_pidinfo((pid_t)owner_pid, PROC_PIDTBSDINFO, 0, &owner, sizeof(owner)) != sizeof(owner) ||
        owner.pbi_uid == 0 || owner.pbi_uid != owner.pbi_ruid) return 65;
    signal(SIGPIPE, SIG_IGN);
    int fd = socket(AF_UNIX, SOCK_STREAM, 0);
    if (fd < 0) return 66;
    struct sockaddr_un address = {0};
    address.sun_family = AF_UNIX; address.sun_len = sizeof(address);
    strlcpy(address.sun_path, path, sizeof(address.sun_path));
    if (connect(fd, (struct sockaddr *)&address, sizeof(address))) { close(fd); return 67; }
    uid_t peer_uid; gid_t peer_gid; pid_t peer_pid = 0;
    socklen_t size = sizeof(peer_pid);
    if (getpeereid(fd, &peer_uid, &peer_gid) || peer_uid != owner.pbi_uid ||
        getsockopt(fd, SOL_LOCAL, LOCAL_PEERPID, &peer_pid, &size) || peer_pid != owner_pid) {
        close(fd); return 68;
    }
    struct timeval timeout = {2, 0};
    setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout));
    setsockopt(fd, SOL_SOCKET, SO_SNDTIMEO, &timeout, sizeof(timeout));
    uint32_t ready = 0;
    if (cd_transfer(fd, &ready, sizeof(ready), 1)) { close(fd); return 69; }
    // A closed UI connection terminates this process, including after app crashes.
    // Absolute lifetime also bounds a stalled client. The GUI must start anew.
    time_t deadline = time(NULL) + 1800;
    while (time(NULL) < deadline) {
        struct pollfd wait = {fd, POLLIN, 0};
        int polled = poll(&wait, 1, 1000);
        if (polled < 0 && errno == EINTR) continue;
        if (polled < 0 || (wait.revents & (POLLHUP | POLLERR | POLLNVAL))) break;
        if (!polled) continue;
        CDRequest request = {0};
        if (cd_transfer(fd, &request, sizeof(request), 0)) break;
        uint32_t error = EPERM;
        if (cd_request_allowed(&request, owner.pbi_uid, local_address))
            error = (uint32_t)cd_send(local, host, (uint16_t)request.port, 1);
        if (cd_transfer(fd, &error, sizeof(error), 1)) break;
        // Fixed protocol and target, at most ten probes/second, no generic data.
        usleep(100000);
    }
    close(fd);
    return 0;
}
