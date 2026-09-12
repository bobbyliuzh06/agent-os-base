#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sandbox_sitecustomize：沙箱子进程的网络守卫模块。
- 主程序 import 本模块不会自动生效；必须显式调用 enable_sandbox_netguard()。
- enable_sandbox_netguard() 后：
  1) socket.socket / socket.create_connection 替换为抛 SandboxNetworkViolation 的 stub；
  2) 通过 sys.meta_path 懒补丁，在 urllib.request / requests / httpx / ftplib /
     smtplib / websocket 首次 import 完成后替换其网络入口；
  3) 已 import 的模块立即替换。
- 仅依赖标准库（meta_path + importlib），不引入第三方包。
"""
import builtins
import importlib
import importlib.abc
import importlib.machinery
import sys


class SandboxNetworkViolation(Exception):
    """沙箱网络访问违规。"""


_PATCH_TARGETS = {
    "urllib.request": ["urlopen", "urlretrieve"],
    "requests.api": ["request"],
    "requests": ["request", "get", "post", "put", "delete", "head", "patch"],
    "httpx": ["Client"],
    "ftplib": ["FTP"],
    "smtplib": ["SMTP", "SMTP_SSL"],
    "websocket": ["create_connection", "WebSocket"],
    "paramiko": ["SSHClient"],
}


def _blocker(*a, **k):
    raise SandboxNetworkViolation("network access blocked by sandbox netguard")


class _BlockedSocket:
    """类形 stub：保证 ssl 等模块 `class SSLSocket(socket)` 的继承不崩，实例化即违规。"""

    def __new__(cls, *a, **k):
        raise SandboxNetworkViolation("socket blocked by sandbox netguard")


def _patch_module(mod_name):
    targets = _PATCH_TARGETS.get(mod_name)
    if not targets:
        return
    mod = sys.modules.get(mod_name)
    if mod is None:
        return
    for attr in targets:
        if hasattr(mod, attr):
            setattr(mod, attr, _blocker)


class _NetGuardLoader(importlib.abc.Loader):
    def __init__(self, inner):
        self._inner = inner

    def create_module(self, spec):
        if hasattr(self._inner, "create_module"):
            return self._inner.create_module(spec)
        return None

    def exec_module(self, module):
        if hasattr(self._inner, "exec_module"):
            self._inner.exec_module(module)
        _patch_module(module.__name__)


class _NetGuardFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname not in _PATCH_TARGETS:
            return None
        spec = importlib.machinery.PathFinder.find_spec(fullname, path)
        if spec and spec.loader is not None:
            spec.loader = _NetGuardLoader(spec.loader)
        return spec


def _install_finder():
    for f in list(sys.meta_path):
        if isinstance(f, _NetGuardFinder):
            return
    sys.meta_path.insert(0, _NetGuardFinder())


def enable_sandbox_netguard():
    """显式开启网络守卫。调用前不生效。"""
    import socket
    socket.socket = _BlockedSocket
    socket.create_connection = _blocker
    socket.getaddrinfo = _blocker
    _install_finder()
    for name in _PATCH_TARGETS:
        if name in sys.modules:
            _patch_module(name)
    return True
