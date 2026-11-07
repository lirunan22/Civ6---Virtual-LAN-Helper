#ifndef CIV6_DISCOVERY_H
#define CIV6_DISCOVERY_H
#include <stdint.h>
#include <sys/types.h>
#define CD_PORT 62900
#define CD_SESSION_PORT 62056
#define CD_CAPACITY 1024
#define CD_MAGIC UINT64_C(0x434956364c414e31)
typedef struct {
    int32_t pid;
    uint16_t port;
    uint32_t address;
    uint64_t socket_id;
} CDEndpoint;
typedef struct { uint64_t magic, pid, port, socket_id; } CDRequest;
int cd_ipv4(const char *text, uint32_t *address);
int cd_private_ipv4(uint32_t address);
int cd_local_ipv4(uint32_t address);
int cd_route(const char *host, char result[16]);
int cd_game_name(const char *name);
int cd_process_allowed(pid_t pid, uid_t owner);
int cd_processes(uid_t owner, pid_t *pids, int capacity);
int cd_endpoints(pid_t pid, CDEndpoint *items, int capacity);
int cd_candidate(const CDEndpoint *item, uint32_t local, uint16_t first);
uint16_t cd_dynamic_first(void);
int cd_send(const char *local, const char *host, uint16_t port, int raw);
int cd_transfer(int fd, void *buffer, size_t bytes, int writing);
int cd_request_allowed(const CDRequest *request, uid_t owner, uint32_t local);
#endif
