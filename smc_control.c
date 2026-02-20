#include <stdio.h>
#include <stdlib.h>
#include <sys/io.h>
#include <unistd.h>

#define APPLESMC_DATA_PORT 0x300
#define APPLESMC_CMD_PORT  0x304
#define SMC_CMD_WRITE      0x11

// 等待 SMC 状态
void smc_wait() {
    while (inb(APPLESMC_CMD_PORT) & 0x01) usleep(10);
}

// 向 SMC 写入一个字节
void smc_write_key(const char* key, unsigned char val) {
    if (ioperm(APPLESMC_DATA_PORT, 0x07, 1)) {
        perror("ioperm 失败 (请用 sudo)");
        exit(1);
    }

    // 发送写指令
    outb(SMC_CMD_WRITE, APPLESMC_CMD_PORT);
    smc_wait();

    // 发送 Key 名称 (BCLM)
    for (int i = 0; i < 4; i++) {
        outb(key[i], APPLESMC_DATA_PORT);
        smc_wait();
    }

    // 发送数据长度 (1 字节)
    outb(1, APPLESMC_DATA_PORT);
    smc_wait();

    // 发送具体的限制数值
    outb(val, APPLESMC_DATA_PORT);
    smc_wait();

    printf("成功向 SMC 写入 Key: %s, Value: %d\n", key, val);
}

int main(int argc, char *argv[]) {
    if (argc < 2) {
        printf("用法: sudo ./smc_control <限制值(10-100)>\n");
        return 1;
    }
    int limit = atoi(argv[1]);
    smc_write_key("BCLM", (unsigned char)limit);
    return 0;
}
