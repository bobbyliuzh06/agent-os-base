#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os,sys,argparse
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
ap=argparse.ArgumentParser(); ap.add_argument("--root",default=os.environ.get("AGENT_OS_ROOT",""))
ap.add_argument("task"); ap.add_argument("--dry",action="store_true")
ns=ap.parse_args()
if ns.root: os.environ["AGENT_OS_ROOT"]=ns.root
from task_engine import run_once
sys.exit(run_once(ns.task, dry=True))  # run 原型默认 dry，不写业务代码、不合并
