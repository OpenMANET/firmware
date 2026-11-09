#!/usr/bin/env python3
"""Compile actual patched BCF selection code with synthetic sections and bus stubs.
Usage: python3 tests/regdom.py /path/to/patched/driver
This tests selection/validity, not physical firmware or RF behavior.
"""
import pathlib, subprocess, sys, tempfile
s = (pathlib.Path(sys.argv[1]) / 'firmware.c').read_text()
a = s.index('struct morse_bcf_fallback_entry {')
b = s.index('static int morse_firmware_trigger', a)
code = s[a:b]
pre = r'''
#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <assert.h>
#include <stdio.h>
typedef uint8_t u8;
typedef struct { int e_shnum, e_shstrndx; } morse_elf_ehdr;
typedef struct { unsigned sh_name, sh_offset, sh_size; } morse_elf_shdr;
struct firmware { const u8 *data; unsigned size; };
struct morse { void *dev; struct { int size; } bcf; struct { int count; } regdoms; unsigned long state_flags; char country[3]; bool has_valid_regdom; };
#define MAX_NUM_REGDOMS 20
#define BCF_DEFAULT_SIZE 1024
#define GFP_KERNEL 0
#define MORSE_STATE_FLAG_REGDOM_SET_BY_OTP 0
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define ROUND_BYTES_TO_WORD(a) (((a)+3)&~3)
#define MORSE_ERR(...) ((void)0)
#define MORSE_INFO(...) ((void)0)
#define test_bit(b,p) ((*(p)) & (1UL<<(b)))
#define devm_kmalloc(d,n,f) malloc(n)
#define devm_kfree(d,p) free(p)
static morse_elf_shdr sections[8];
static int nsections;
static int get_file_header(const u8 *d, morse_elf_ehdr *e) { e->e_shnum=nsections; e->e_shstrndx=0; return 0; }
static int get_section_header(const u8 *d, morse_elf_ehdr *e, morse_elf_shdr *s, int i) { *s=sections[i]; return 0; }
static int add_regdom_to_buffer(struct morse *m, char b[][3], const char *c) { return 0; }
static int store_regdom_info(struct morse *m, char b[][3]) { return 0; }
static void morse_claim_bus(struct morse *m) {}
static void morse_release_bus(struct morse *m) {}
static int morse_dm_write(struct morse *m, unsigned a, const u8 *b, int n) { return 0; }
'''
post = r'''
static void check(const char *country, const char *available, bool valid, int expected, bool otp) {
 u8 data[512]={0}; unsigned pos=1;
 sections[0]=(morse_elf_shdr){0,0,0}; nsections=1;
 const char *names[]={".board_config",available};
 for(int i=0;i<2;i++) { if(!names[i]) continue; strcpy((char*)data+pos,names[i]); sections[nsections++]=(morse_elf_shdr){pos,400,4}; pos+=strlen(names[i])+1; }
 struct morse m={.has_valid_regdom=true,.state_flags=otp}; memcpy(m.country,country,3);
 struct firmware fw={data,sizeof(data)};
 int ret=morse_bcf_load(&m,&fw,0);
 assert(ret==expected); assert(m.has_valid_regdom==valid);
}
int main(void) {
 check("US",".regdom_US",true,0,false);
 check("MX",".regdom_US",true,0,false);
 check("AR",".regdom_AU",true,0,false);
 check("CL",".regdom_AU",true,0,false);
 check("CO",".regdom_AU",true,0,false);
 check("ZZ",".regdom_US",false,0,false);
 check("MX",".regdom_AU",false,0,false);
 check("US",NULL,false,-ENOENT,false);
 check("MX",".regdom_US",true,0,true);
 check("ZZ",".regdom_US",false,0,true);
 puts("PASS: 10 actual-code BCF direct/fallback/discovery/OTP cases");
}
'''
with tempfile.TemporaryDirectory() as d:
 c=pathlib.Path(d)/'test.c';c.write_text(pre+code+post)
 subprocess.run(['cc','-std=gnu11','-o',d+'/test',str(c)],check=True)
 subprocess.run([d+'/test'],check=True)
