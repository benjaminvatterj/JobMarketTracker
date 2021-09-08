#!/bin/python3

import argparse
from textwrap import dedent
import logging



def launch_gui(args=None):
    """Launch the system's gui"""
    from JMTracker import Tracker
    tracker = Tracker()
    tracker.main_gui()
    return



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=dedent("""
    ====== Job Market Application Tracker =====
    A simple tool to keep track of new postings, those I'm interested
    in and the deadlines.

    -----------------
    UPDATING METHODS
    -----------------
    - Update the current local collection of job postings from
      econjobmarket.org and aeaweb.org.

      ./main.py update

    """), formatter_class=argparse.RawTextHelpFormatter)

    available_actions = {
        'gui': launch_gui,
    }

    parser.add_argument("--action", type=str, choices=available_actions.keys(),
                        help="action to execute", default='gui')
    parser.add_argument("--debug", action="store_true",
                        help="Debug log level")

    args = parser.parse_args()
    action = args.action
    if action not in available_actions.keys():
        raise ValueError(f"Argument option for action {action} not accepted")

    # process debug
    logging_level = logging.DEBUG if args.debug else logging.INFO
    FORMAT = "[%(filename)s:%(lineno)s][%(levelname)s]\t %(message)s"
    logging.basicConfig(format=FORMAT, level=logging_level)

    # Process
    available_actions[action](args)

    print("Done")

