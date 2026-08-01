# -*- coding: utf-8 -*-
"""trinity_demo.py — GA + Paladin + OpenWorker 集成演示（真实执行）"""

import sys; sys.path.insert(0, "H:/GA/GenericAgent/paladin")

def run_pipeline(tasks: list) -> None:
    from paladin_adapter import PaladinAdapter
    from trinity_bus import get_bus
    from openworker_executor import execute as ow_execute, get_available_actions

    bus = get_bus()
    adapter = PaladinAdapter()
    actions = get_available_actions()

    for task_desc, risk in tasks:
        trace = bus.new_trace()
        print(f"\n[T-{trace}] ====== 任务: {task_desc} (risk={risk}) =====")

        ga_plan = {"task": task_desc, "risk": risk, "agent": "executor"}
        bus.publish("pre_gate", {"task": task_desc, "risk": risk}, trace)

        decision = adapter.gate_assess(task_desc, risk)
        bus.publish("post_gate", {"allow": decision.get("allow"), "zone": decision.get("zone"),
                                   "risk_level": decision.get("risk_level", "?")}, trace)

        if not decision.get("allow", True):
            print(f"  [GATE] {decision.get('risk_level','?'):6s} -> 拒绝 ({decision.get('reason','?')[:60]})")
            continue

        action = "write_file" if "文件" in task_desc else "list_dir"
        params = {"path": "H:/GA/GenericAgent/temp/paladin_log.txt",
                  "content": f"task={task_desc}\nrisk={risk}\n"}
        bus.publish("exec_start", {"action": action, "params": params}, trace)
        result = ow_execute(action, params)
        bus.publish("exec_done", {"status": result["status"], "output": result.get("output","")}, trace)

        from trace import get_trace
        get_trace().inject()
        print(f"  [OW] {action}: {result['status']}")

    print(f"\n闭环: {len(bus.get_events())} 事件")
