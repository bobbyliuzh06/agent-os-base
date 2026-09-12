import os, sys, json
import pytest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent/"BASE"/"scripts"))
os.environ.setdefault("AGENT_OS_ROOT", str(Path(__file__).parent.parent.resolve()))
@pytest.fixture
def root(): return Path(os.environ["AGENT_OS_ROOT"])
@pytest.fixture
def sample_proposal():
    return {
        "summary":"测试提案",
        "scope_in":["tasks/demo/task-evolve"],
        "scope_out":["BASE"],
        "deliverables":["tasks/demo/task-evolve/out/result.md"],
        "steps":["解析","生成"],
        "risks":[],
        "rollback":["删除 out/"],
        "acceptance":["rc=0"],
        "base_change_required":False,
        "tool_calls":[]
    }
