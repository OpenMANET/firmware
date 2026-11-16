#!/usr/bin/env python3
"""Exercise actual legacy create/update wrappers against a non-reentrant RRD stub.

Usage: test_collectd_rrd_lock.py PREPARED_COLLECTD_SOURCE
The input must be the original source, before the shared-lock patch. The test
proves the original wrappers overlap and the patched wrappers serialize calls.
"""

import pathlib
import re
import shutil
import subprocess
import sys
import tempfile


def wrapper(source, name):
    legacy = source.split("#else  /* !HAVE_THREADSAFE_LIBRRD */", 1)[1]
    match = re.search(r"static int " + name + r"\([^)]*\)\s*\{", legacy)
    assert match, name
    depth = 1
    end = match.end()
    while depth:
        depth += (legacy[end] == "{") - (legacy[end] == "}")
        end += 1
    return legacy[match.start():end]


HARNESS = r"""
#define _GNU_SOURCE
#include <assert.h>
#include <pthread.h>
#include <stdatomic.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#define ssnprintf snprintf
#define sfree free
#define ERROR(...) ((void)0)
#define P_ERROR(...) ((void)0)
#define WARNING(...) ((void)0)
#define P_WARNING(...) ((void)0)
#define rrd_clear_error() ((void)0)
#define rrd_get_error() "mock RRD error"
static atomic_int active, overlaps;
static pthread_barrier_t start;
static int mock_rrd(int argc, char **argv) {
  (void)argc; (void)argv;
  if (atomic_fetch_add(&active, 1) != 0)
    atomic_fetch_add(&overlaps, 1);
  usleep(100);
  atomic_fetch_sub(&active, 1);
  return 0;
}
#define rrd_create mock_rrd
#define rrd_update mock_rrd
"""

MAIN = r"""
static void *worker(void *arg) {
  const char *values[] = {"DS:value:GAUGE:60:U:U"};
  pthread_barrier_wait(&start);
  for (int i = 0; i < 1000; i++) {
    int status = (uintptr_t)arg
      ? srrd_update("mock.rrd", NULL, 1, values)
      : srrd_create("mock.rrd", 30, 1700000000, 1, values);
    assert(status == 0);
  }
  return NULL;
}
int main(void) {
  pthread_t create, update;
  pthread_barrier_init(&start, NULL, 2);
  pthread_create(&create, NULL, worker, (void *)0);
  pthread_create(&update, NULL, worker, (void *)1);
  pthread_join(create, NULL);
  pthread_join(update, NULL);
  pthread_barrier_destroy(&start);
  printf("overlapping legacy RRD calls: %d\n", atomic_load(&overlaps));
  return atomic_load(&overlaps) ? 1 : 0;
}
"""


def exercise(source, work, patched):
    create = wrapper((source / "src/utils/rrdcreate/rrdcreate.c").read_text(), "srrd_create")
    update = wrapper((source / "src/rrdtool.c").read_text(), "srrd_update")
    if patched:
        lock = "pthread_mutex_t cu_rrd_legacy_lock = PTHREAD_MUTEX_INITIALIZER;\n"
        assert "&cu_rrd_legacy_lock" in create and "&cu_rrd_legacy_lock" in update
    else:
        lock = ("static pthread_mutex_t create_lock = PTHREAD_MUTEX_INITIALIZER;\n"
                "static pthread_mutex_t update_lock = PTHREAD_MUTEX_INITIALIZER;\n")
        create = create.replace("&librrd_lock", "&create_lock")
        update = update.replace("&librrd_lock", "&update_lock")
    cfile = work / ("fixed.c" if patched else "original.c")
    binary = cfile.with_suffix("")
    cfile.write_text(HARNESS + lock + create + "\n" + update + MAIN)
    subprocess.run(["cc", "-std=c11", "-Wall", "-Wextra", "-Werror", "-pthread",
                    str(cfile), "-o", str(binary)], check=True)
    result = subprocess.run([str(binary)], text=True, capture_output=True)
    print(("Patched: " if patched else "Original: ") + result.stdout.strip())
    assert result.returncode == (0 if patched else 1), result.stderr


source = pathlib.Path(sys.argv[1]).resolve()
root = pathlib.Path(__file__).resolve().parents[2]
patch = root / "feeds/packages/utils/collectd/patches/952-share-legacy-librrd-lock.patch"
with tempfile.TemporaryDirectory() as tmp:
    work = pathlib.Path(tmp)
    exercise(source, work, False)
    fixed = work / "source"
    for name in ("src/rrdtool.c", "src/utils/rrdcreate/rrdcreate.c", "src/utils/rrdcreate/rrdcreate.h"):
        dest = fixed / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / name, dest)
    subprocess.run(["patch", "-s", "-d", str(fixed), "-p1", "-i", str(patch)], check=True)
    exercise(fixed, work, True)
print("PASS: legacy RRD creation and updates share one lock")
