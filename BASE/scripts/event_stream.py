# -*- coding: utf-8 -*-
"""event_stream.py —— 统一事件流（BASE 组件：感知总线，哈希链防篡改）。

append-only + 哈希链：每个事件含 prev_hash（上一事件哈希）与自哈希，任何篡改破坏链。
来源：婴儿智能体核心（tasks/project-layer-core-20260913）经 BASE 化沉淀。
schema: {seq, ts, source, signal, subject, payload, world, prev_hash, hash}
旧事件（无 world 字段）按实际键集合校验，兼容历史流。"""
import hashlib, json, pathlib
from datetime import datetime, timezone

class EventStream:
    def __init__(self, path):
        self.path = pathlib.Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _read_all(self):
        if not self.path.exists():
            return []
        return [json.loads(l) for l in self.path.read_text(encoding="utf-8").splitlines() if l.strip()]

    def last_hash(self):
        evts = self._read_all()
        return evts[-1]["hash"] if evts else "GENESIS"

    def append(self, source, signal, subject, payload, world="dev"):
        evts = self._read_all()
        seq = len(evts) + 1
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        prev_hash = self.last_hash()
        body = json.dumps({"seq": seq, "ts": ts, "source": source, "signal": signal,
                           "subject": str(subject), "payload": payload, "world": world,
                           "prev_hash": prev_hash}, ensure_ascii=False, sort_keys=True)
        h = hashlib.sha256(body.encode("utf-8")).hexdigest()
        event = {"seq": seq, "ts": ts, "source": source, "signal": signal,
                 "subject": str(subject), "payload": payload, "world": world,
                 "prev_hash": prev_hash, "hash": h}
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
        return event

    def verify_chain(self):
        evts = self._read_all()
        prev = "GENESIS"
        for e in evts:
            if e["prev_hash"] != prev:
                return False, "chain broken at seq=%s" % e["seq"]
            keys = [k for k in ("seq", "ts", "source", "signal", "subject",
                                "payload", "world", "prev_hash") if k in e]
            body = json.dumps({k: e[k] for k in keys}, ensure_ascii=False, sort_keys=True)
            if hashlib.sha256(body.encode("utf-8")).hexdigest() != e["hash"]:
                return False, "tampered at seq=%s" % e["seq"]
            prev = e["hash"]
        return True, "chain intact (%d events)" % len(evts)

    def since(self, seq):
        return [e for e in self._read_all() if e["seq"] > seq]
