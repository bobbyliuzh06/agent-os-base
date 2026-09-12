#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os,sys,argparse
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
ap=argparse.ArgumentParser(); ap.add_argument("--root",default=os.environ.get("AGENT_OS_ROOT",""))
ap.add_argument("task"); ap.add_argument("--iterations",type=int,default=3)
ns=ap.parse_args()
if ns.root: os.environ["AGENT_OS_ROOT"]=ns.root
from task_engine import evolve
sys.exit(evolve(ns.task, ns.iterations, dry=True))  # evolve 原型仅 dry/观察，不自动合并
