#!/usr/bin/env python3

from pathlib import Path
import sys


PACKAGE_SRC = Path(__file__).resolve().parents[1] / "src"
if str(PACKAGE_SRC) not in sys.path:
    sys.path.insert(0, str(PACKAGE_SRC))

import rospy

from rexrov_single_oberon7_fm_dp.recorder import EpisodeRecorder


def main() -> int:
    rospy.init_node("dp_fm_episode_recorder")
    try:
        path = EpisodeRecorder().run()
    except Exception as exc:
        rospy.logerr("Episode recording failed: %s", exc)
        return 1
    rospy.loginfo("Episode recording complete: %s", path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
