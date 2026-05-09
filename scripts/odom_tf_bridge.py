#!/usr/bin/env python3

from pathlib import Path
import sys


PACKAGE_SRC = Path(__file__).resolve().parents[1] / "src"
if str(PACKAGE_SRC) not in sys.path:
    sys.path.insert(0, str(PACKAGE_SRC))

import rospy

from rexrov_single_oberon7_fm_dp.odom_tf_bridge import (
    OdomTfBridge,
    config_from_ros_params,
)


def main() -> int:
    rospy.init_node("dp_fm_odom_tf_bridge")
    try:
        OdomTfBridge(config_from_ros_params()).run()
    except Exception as exc:
        rospy.logerr("Odom TF bridge failed: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
