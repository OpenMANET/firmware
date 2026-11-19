#define _GNU_SOURCE
#include <arpa/inet.h>
#include <errno.h>
#include <linux/if_packet.h>
#include <net/if.h>
#include <net/if_arp.h>
#include <netinet/if_ether.h>
#include <poll.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/socket.h>
#include <time.h>
#include <unistd.h>

#define GROUP "239.255.42.99"
#define PORT 39081
#define PROTOCOL 0x88b5

static void check(int ok, const char *operation)
{
    if (!ok) { perror(operation); exit(1); }
}

static int64_t now_ns(void)
{
    struct timespec now;
    check(clock_gettime(CLOCK_MONOTONIC, &now) == 0, "clock_gettime");
    return (int64_t)now.tv_sec * 1000000000 + now.tv_nsec;
}

int main(int argc, char **argv)
{
    if (argc != 8) return 2;
    int send_mode = !strcmp(argv[1], "send");
    int raw = !strcmp(argv[2], "raw");
    if ((!send_mode && strcmp(argv[1], "recv")) || (!raw && strcmp(argv[2], "udp"))) return 2;
    const char *iface = argv[3];
    unsigned index = if_nametoindex(iface);
    uint32_t token = htonl(strtoul(argv[4], NULL, 10));
    int seconds = atoi(argv[5]), rate = atoi(argv[6]), voice_per_group = atoi(argv[7]);
    if (!index || seconds < 1 || seconds > 600 || rate < 1 || rate > 1000 ||
        voice_per_group < 1 || voice_per_group >= rate) return 2;
    int count = seconds * rate;
    int fd = socket(raw ? AF_PACKET : AF_INET, raw ? SOCK_RAW : SOCK_DGRAM,
                    raw ? htons(PROTOCOL) : 0);
    check(fd >= 0, "socket");
    struct sockaddr_ll link = {.sll_family = AF_PACKET, .sll_protocol = htons(PROTOCOL),
                               .sll_ifindex = (int)index, .sll_halen = ETH_ALEN};
    struct sockaddr_in group = {.sin_family = AF_INET, .sin_port = htons(PORT),
                                .sin_addr.s_addr = inet_addr(GROUP)};
    unsigned char frame[ETH_HLEN + 512] = {0};
    size_t offset = raw ? ETH_HLEN : 0;
    struct sockaddr *dest = raw ? (struct sockaddr *)&link : (struct sockaddr *)&group;
    socklen_t dest_len = raw ? sizeof(link) : sizeof(group);
    if (raw) {
        check(bind(fd, dest, dest_len) == 0, "bind packet socket");
        struct ifreq info = {0};
        snprintf(info.ifr_name, sizeof(info.ifr_name), "%s", iface);
        check(ioctl(fd, SIOCGIFHWADDR, &info) == 0, "SIOCGIFHWADDR");
        memset(frame, 0xff, ETH_ALEN);
        memset(link.sll_addr, 0xff, ETH_ALEN);
        memcpy(frame + ETH_ALEN, info.ifr_hwaddr.sa_data, ETH_ALEN);
        frame[12] = PROTOCOL >> 8;
        frame[13] = PROTOCOL & 0xff;
    } else {
        struct ip_mreqn membership = {.imr_multiaddr = group.sin_addr, .imr_ifindex = (int)index};
        check(setsockopt(fd, SOL_SOCKET, SO_BINDTODEVICE, iface, strlen(iface) + 1) == 0,
              "SO_BINDTODEVICE");
        if (send_mode) {
            unsigned char ttl = 1;
            check(setsockopt(fd, IPPROTO_IP, IP_MULTICAST_IF, &membership, sizeof(membership)) == 0,
                  "IP_MULTICAST_IF");
            check(setsockopt(fd, IPPROTO_IP, IP_MULTICAST_TTL, &ttl, sizeof(ttl)) == 0,
                  "IP_MULTICAST_TTL");
        } else {
            struct sockaddr_in any = {.sin_family = AF_INET, .sin_port = htons(PORT)};
            check(bind(fd, (struct sockaddr *)&any, sizeof(any)) == 0, "bind UDP socket");
            check(setsockopt(fd, IPPROTO_IP, IP_ADD_MEMBERSHIP, &membership, sizeof(membership)) == 0,
                  "IP_ADD_MEMBERSHIP");
        }
    }

    int64_t start = now_ns();
    if (send_mode) {
        memcpy(frame + offset, "OMCT", 4);
        memcpy(frame + offset + 4, &token, sizeof(token));
        for (int i = 0; i < count; i++) {
            int64_t next = start + (int64_t)i * 1000000000 / rate;
            struct timespec at = {next / 1000000000, next % 1000000000};
            int rc;
            do { rc = clock_nanosleep(CLOCK_MONOTONIC, TIMER_ABSTIME, &at, NULL); } while (rc == EINTR);
            if (rc) { errno = rc; check(0, "clock_nanosleep"); }
            uint32_t sequence = htonl(i);
            memcpy(frame + offset + 8, &sequence, sizeof(sequence));
            int cot_rate = rate - voice_per_group;
            size_t size = (int64_t)i * cot_rate / rate != (int64_t)(i + 1) * cot_rate / rate ? 512 : 96;
            check(sendto(fd, frame, size + offset, 0, dest, dest_len) == (ssize_t)(size + offset),
                  "sendto");
        }
        printf("sent %d elapsed_ms %lld\n", count, (long long)((now_ns() - start) / 1000000));
    } else {
        unsigned short *seen = calloc(count, sizeof(*seen));
        check(seen != NULL, "calloc");
        struct pollfd ready = {.fd = fd, .events = POLLIN};
        int64_t end = start + (int64_t)(seconds + 35) * 1000000000;
        puts("ready");
        fflush(stdout);
        for (int64_t left; (left = end - now_ns()) > 0;) {
            int result = poll(&ready, 1, (left + 999999) / 1000000);
            if (result < 0 && errno == EINTR) continue;
            check(result >= 0, "poll");
            if (!result) break;
            ssize_t size = recv(fd, frame, sizeof(frame), 0);
            check(size >= 0, "recv");
            if (size < (ssize_t)(offset + 12) || memcmp(frame + offset, "OMCT", 4) ||
                memcmp(frame + offset + 4, &token, sizeof(token))) continue;
            uint32_t sequence;
            memcpy(&sequence, frame + offset + 8, sizeof(sequence));
            sequence = ntohl(sequence);
            if (sequence < (unsigned)count && seen[sequence] != UINT16_MAX) seen[sequence]++;
        }
        for (int i = 0; i < count; i++)
            if (seen[i]) printf("%d %hu\n", i, seen[i]);
        free(seen);
    }
    close(fd);
    return 0;
}
