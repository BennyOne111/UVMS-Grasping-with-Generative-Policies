#!/usr/bin/env python3

import argparse
import json
from pathlib import Path
import time
from typing import Dict

import rospy
from gazebo_msgs.msg import ModelStates
from gazebo_msgs.srv import DeleteModel, GetModelState


def _model_present(model_states_topic: str, model_name: str, timeout_sec: float) -> bool:
    try:
        msg = rospy.wait_for_message(model_states_topic, ModelStates, timeout=timeout_sec)
    except Exception:
        return False
    return model_name in msg.name


def _wait_for_absent(model_states_topic: str, model_name: str, timeout_sec: float) -> bool:
    deadline = time.monotonic() + max(0.0, timeout_sec)
    while not rospy.is_shutdown() and time.monotonic() <= deadline:
        if not _model_present(model_states_topic, model_name, timeout_sec=1.0):
            return True
        rospy.sleep(0.1)
    return not _model_present(model_states_topic, model_name, timeout_sec=1.0)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Delete the B8 target gate probe model from Gazebo. "
            "This resets only the target marker; it sends no arm or gripper commands."
        )
    )
    parser.add_argument("--target-model-name", default="cylinder_target_gate_probe")
    parser.add_argument("--model-states-topic", default="/gazebo/model_states")
    parser.add_argument("--get-model-state-service", default="/gazebo/get_model_state")
    parser.add_argument("--delete-model-service", default="/gazebo/delete_model")
    parser.add_argument("--wait-timeout-sec", type=float, default=5.0)
    parser.add_argument("--ignore-missing", action="store_true")
    parser.add_argument("--output-json", default="")
    args = parser.parse_args()

    rospy.init_node("b8_reset_target_gate_probe", anonymous=True)

    rospy.wait_for_service(args.get_model_state_service, timeout=args.wait_timeout_sec)
    rospy.wait_for_service(args.delete_model_service, timeout=args.wait_timeout_sec)
    get_model_state = rospy.ServiceProxy(args.get_model_state_service, GetModelState)
    delete_model = rospy.ServiceProxy(args.delete_model_service, DeleteModel)

    before_present = bool(_model_present(args.model_states_topic, args.target_model_name, timeout_sec=1.0))
    get_response = get_model_state(args.target_model_name, "world")
    get_model_success = bool(get_response.success)

    delete_attempted = False
    delete_success = False
    delete_status = ""
    if before_present or get_model_success:
        delete_attempted = True
        response = delete_model(args.target_model_name)
        delete_success = bool(response.success)
        delete_status = str(response.status_message)
    elif args.ignore_missing:
        delete_success = True
        delete_status = "model already absent"
    else:
        delete_status = "model not present before delete"

    absent_after_delete = _wait_for_absent(
        args.model_states_topic,
        args.target_model_name,
        timeout_sec=args.wait_timeout_sec,
    )

    report: Dict[str, object] = {
        "tool": "reset_b8_target_gate_probe",
        "target_model_name": args.target_model_name,
        "before_present_in_model_states": before_present,
        "get_model_state_success": get_model_success,
        "delete_attempted": delete_attempted,
        "delete_success": delete_success,
        "delete_status": delete_status,
        "absent_after_delete": absent_after_delete,
        "control_commands_sent": False,
        "gripper_commands_sent": False,
    }
    passed = bool(delete_success and absent_after_delete)
    report["passed"] = passed

    text = json.dumps(report, indent=2, sort_keys=True)
    print(text)
    if args.output_json:
        output_path = Path(args.output_json).expanduser()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text + "\n", encoding="utf-8")
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
