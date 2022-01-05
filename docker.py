import argparse
import os

compose_prod = "docker-compose.prod.yml"
compose_dev = filename = "docker-compose.yml"

parser = argparse.ArgumentParser(description="Runs docker containers.")
parser.add_argument(
    "action",
    type=str,
    help="Specify docker action.",
    choices=["up", "down", "build", "restart", "start", "stop"],
)
parser.add_argument(
    "-p", "--production", action="store_true", help="Run in production mode."
)
parser.add_argument(
    "-d", "--detached", action="store_true", help="Run in detached mode."
)

args = parser.parse_args()
action = args.action

if args.production:
    filename = compose_prod

cmd = "docker-compose -f %s %s" % (filename, action)

if args.detached:
    cmd += " -d"

print("Running: %s\n" % cmd)
os.system(cmd)
