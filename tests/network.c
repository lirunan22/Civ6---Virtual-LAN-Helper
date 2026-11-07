#include "discovery.h"
#include <arpa/inet.h>
#include <assert.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <unistd.h>

static struct sockaddr_in address(uint32_t ip, uint16_t port) {
    struct sockaddr_in a = {0};
#ifdef __APPLE__
    a.sin_len = sizeof(a);
#endif
    a.sin_family = AF_INET; a.sin_addr.s_addr = ip; a.sin_port = htons(port);
    return a;
}
static int open_udp(uint32_t ip, uint16_t port, int reuse, uint16_t *actual) {
    int s = socket(AF_INET, SOCK_DGRAM, 0); assert(s >= 0);
    if (reuse) { int one = 1; assert(!setsockopt(s,SOL_SOCKET,SO_REUSEADDR,&one,sizeof(one))); assert(!setsockopt(s,SOL_SOCKET,SO_REUSEPORT,&one,sizeof(one))); }
    struct timeval timeout = {2,0}; assert(!setsockopt(s,SOL_SOCKET,SO_RCVTIMEO,&timeout,sizeof(timeout)));
    struct sockaddr_in a = address(ip, port); assert(!bind(s,(struct sockaddr *)&a,sizeof(a)));
    socklen_t size = sizeof(a); assert(!getsockname(s,(struct sockaddr *)&a,&size));
    if (actual) *actual = ntohs(a.sin_port);
    return s;
}
static void roundtrip(int raw, int shared) {
    uint16_t port;
    int game = open_udp(INADDR_ANY, 0, shared, &port);
    int host = open_udp(htonl(INADDR_LOOPBACK), CD_PORT, 0, NULL);
    int error = cd_send("127.0.0.1", "127.0.0.1", port, raw);
    if (!raw && !shared && error == EADDRINUSE) { close(game); close(host); return; }
    assert(!error);
    uint8_t packet[64] = {0}; struct sockaddr_in from = {0}; socklen_t size = sizeof(from);
    ssize_t n = recvfrom(host,packet,sizeof(packet),0,(struct sockaddr *)&from,&size);
    assert(n == 4 && !memcmp(packet,"\x8d\xe8\xfc\x70",4));
    assert(ntohs(from.sin_port) == port && from.sin_addr.s_addr == htonl(INADDR_LOOPBACK));
    // The response must reach the original game socket, even in exclusive/raw mode.
    assert(sendto(host,"reply",5,0,(struct sockaddr *)&from,sizeof(from)) == 5);
    assert(recv(game,packet,sizeof(packet),0) == 5 && !memcmp(packet,"reply",5));
    close(game); close(host);
}
int main(int argc, char **argv) {
    if (argc == 2 && !strcmp(argv[1],"--raw")) {
        assert(geteuid() == 0); roundtrip(1,0);
        puts("{\"rawPayload\":true,\"rawSourcePort\":true,\"exclusiveGameReply\":true}"); return 0;
    }
    uint32_t ip = 0;
    assert(cd_ipv4("10.88.66.2",&ip) && cd_private_ipv4(ip));
    for (const char **p=(const char *[]){"", "127.0.0.1", "0.0.0.0", "255.255.255.255", "224.0.0.1", "10.1", "10.0.0.1;whoami", "10.0.0.1\n", NULL}; *p; p++) assert(!cd_ipv4(*p,&ip));
    const char *private[] = {"10.1.2.3","172.16.0.1","172.31.255.254","192.168.3.1","100.64.0.1","100.127.255.254",NULL};
    for (int i=0;private[i];i++) assert(cd_ipv4(private[i],&ip) && cd_private_ipv4(ip));
    const char *public[] = {"1.1.1.1","172.15.0.1","172.32.0.1","100.63.255.1","100.128.0.1",NULL};
    for (int i=0;public[i];i++) assert(cd_ipv4(public[i],&ip) && !cd_private_ipv4(ip));
    assert(cd_game_name("Civ6_Exe_Child") && cd_game_name("Civ6") && !cd_game_name("Steam") && !cd_game_name("Civ6Helper"));
    CDEndpoint ep = {getpid(),55001,0,123};
    assert(cd_candidate(&ep,ip,49152));
    ep.port=CD_PORT;assert(!cd_candidate(&ep,ip,49152));
    ep.port=CD_SESSION_PORT;assert(!cd_candidate(&ep,ip,49152));
    ep.port=3000;assert(!cd_candidate(&ep,ip,49152));
    ep.port=55001;ep.address=htonl(0x0a000001);assert(!cd_candidate(&ep,ip,49152));
    CDRequest invalid={0,1,55001,0};assert(!cd_request_allowed(&invalid,getuid(),ip));
    roundtrip(0,1); roundtrip(0,0);
    int proc=1;
#ifdef __APPLE__
    uint16_t port;int s=open_udp(INADDR_ANY,0,0,&port);
    CDEndpoint items[CD_CAPACITY];int count=cd_endpoints(getpid(),items,CD_CAPACITY),found=0;
    CDEndpoint owned={0};
    for(int i=0;i<count;i++)if(items[i].port==port&&items[i].pid==getpid()&&items[i].socket_id){found=1;owned=items[i];}
    assert(found);assert(cd_process_allowed(getpid(),getuid()));
    CDRequest valid={CD_MAGIC,(uint64_t)getpid(),port,owned.socket_id};
    assert(cd_request_allowed(&valid,getuid(),htonl(INADDR_LOOPBACK)));
    assert(!cd_request_allowed(&valid,getuid()+1,htonl(INADDR_LOOPBACK)));
    valid.socket_id++;assert(!cd_request_allowed(&valid,getuid(),htonl(INADDR_LOOPBACK)));
    pid_t pids[64];count=cd_processes(getuid(),pids,64);found=0;
    for(int i=0;i<count;i++)if(pids[i]==getpid())found=1;
    assert(found);close(s);
#else
    proc=0;
#endif
    printf("{\"validation\":true,\"payload\":true,\"sourcePort\":true,\"replyToGame\":true,\"processSockets\":%s,\"helperValidation\":%s}\n",proc?"true":"false",proc?"true":"false");
    return 0;
}
