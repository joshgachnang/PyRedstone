#!/usr/bin/env python
try:
    import pyredstone.pyredstone as pyredstone
except Exception as e:
    import pyredstone
import argparse
import os

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="A Minecraft server wrapper for vanilla and CraftBukkit servers.")
    parser.add_argument("command", help="The command to call.")
    parser.add_argument("args", nargs="*", help="Args to pass to the command.")
    parser.add_argument("--config", help="Path to config file.")
    args = parser.parse_args()
    if not os.path.exists(args.config):
        logger.error("Config file %s does not exist." % args.config)
        sys.exit(1)
    rs = pyredstone.RedstoneServer(args.config)
    try:
        method = getattr(rs, args.command)
    except AttributeError as e:
        logger.error("%s is not a recognized command. Please try again." % args.command)
        sys.exit(1)
    print method(*args.args)