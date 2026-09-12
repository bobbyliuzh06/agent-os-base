#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""任务单实例锁：Windows 用 os.open O_CREAT|O_EXCL；异常即退出。也可改 filelock。"""
import os, sys, time

class TaskLock:
    def __init__(self, lock_path, timeout=0, interval=0.5):
        self.lock_path = lock_path
        self.timeout = timeout
        self.interval = interval
        self.fd = None
    def acquire(self):
        deadline = time.time()+self.timeout
        while True:
            try:
                self.fd = os.open(self.lock_path, os.O_CREAT|os.O_EXCL|os.O_RDWR)
                os.write(self.fd, str(os.getpid()).encode("utf-8"))
                return True
            except FileExistsError:
                # 读取旧 pid，Windows 下仅做存在性判断；超时则放弃
                if self.timeout<=0:
                    return False
                if time.time()>=deadline:
                    return False
                time.sleep(self.interval)
            except OSError:
                return False
    def release(self):
        try:
            if self.fd is not None: os.close(self.fd)
        except Exception: pass
        try:
            if os.path.exists(self.lock_path): os.unlink(self.lock_path)
        except Exception: pass
    def __enter__(self):
        if not self.acquire():
            raise RuntimeError("TASK_LOCKED:"+self.lock_path)
        return self
    def __exit__(self, *a):
        self.release()
