#!/usr/bin/env python3
"""Check, after a deploy, that the estate is the one the scenario defines.

    python3 benchmarks/agent-env/estate-check.py
    python3 benchmarks/agent-env/estate-check.py --regions us-east-1,us-west-1

The two existing gates ask about the tool. Preflight asks whether the arm can
answer with its own tooling; the audit asks whether it did. Neither asks whether
the thing it answered *about* was intact, and a degraded estate is invisible to
both: the tool runs perfectly and reports what is there.

cdk-m3 is the whole argument. A second Floci on the machine held host port
30000, so this estate's us-west-2 instance could not publish its app ports —
"Bind for 0.0.0.0:30000 failed: port is already allocated" — and went straight
to `terminated`. Five instances deployed where the scenario defines six. The run
completed 24 trials with no exceptions, the audit passed, `cdk` ran in all 24,
and it scored 14/24 against 17-19/24 for the same arm on the same briefing.

Nothing in the harness could tell that from CDK having a bad day. The number was
publishable and wrong, which is the exact failure the other two gates exist to
prevent, arriving through the one door they do not cover.

No ground truth is encoded here. The checks are things that are true of any
freshly wiped and deployed estate, whatever the scenario:

  * nothing is terminated or shutting down. The emulator was wiped minutes ago,
    so every instance in it was created by this deploy, and a deploy does not
    intend to create a terminated instance.
  * the emulator logged no failure to publish an instance's ports. That is the
    collision above, caught at its source rather than through its symptom.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

#: States a deploy never means to produce. Anything here was created and lost.
DEAD = {"terminated", "shutting-down"}

#: The emulator's own report that it could not give an instance its host ports.
PUBLISH_FAILED = "Failed to publish EC2 instance"


def instances(region: str, endpoint: str) -> list[tuple[str, str]]:
    """(id, state) for every instance in one region."""
    out = subprocess.run(
        [
            "aws", "--endpoint-url", endpoint, "--region", region,
            "ec2", "describe-instances", "--output", "json",
        ],
        capture_output=True, text=True,
        env={**os.environ, "AWS_ACCESS_KEY_ID": "test", "AWS_SECRET_ACCESS_KEY": "test"},
    )
    if out.returncode != 0:
        raise SystemExit(f"cannot read {region}: {out.stderr.strip()[:200]}")
    try:
        data = json.loads(out.stdout)
    except ValueError:
        raise SystemExit(f"cannot read {region}: the emulator did not return JSON")
    return [
        (i["InstanceId"], i["State"]["Name"])
        for r in data.get("Reservations", [])
        for i in r.get("Instances", [])
    ]


def publish_failures(container: str) -> list[str]:
    """Lines where the emulator could not publish an instance's ports."""
    out = subprocess.run(
        ["docker", "logs", container], capture_output=True, text=True,
    )
    if out.returncode != 0:
        # Not fatal on its own. The estate check that matters is the state of
        # the instances, and that came from the API.
        return []
    return [
        " ".join(line.split())[:180]
        for line in (out.stdout + out.stderr).splitlines()
        if PUBLISH_FAILED in line
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--endpoint",
        default=f"http://localhost:{os.environ.get('FLOCI_PORT', '4566')}",
        help="the emulator, on the host",
    )
    parser.add_argument(
        "--regions",
        default=os.environ.get("FLOCI_ALLOWED_REGIONS", "us-east-1,us-west-1,us-west-2"),
        help="comma-separated regions the scenario deploys to",
    )
    parser.add_argument("--container", default="floci-floci-1", help="the emulator container")
    args = parser.parse_args()

    regions = [r.strip() for r in args.regions.split(",") if r.strip()]
    problems: list[str] = []
    alive = 0

    for region in regions:
        found = instances(region, args.endpoint)
        living = [(i, s) for i, s in found if s not in DEAD]
        alive += len(living)
        for instance, state in found:
            if state in DEAD:
                problems.append(f"{region}: {instance} is {state}")
        print(f"    {region}: {len(living)} instance(s)" + (f", {len(found) - len(living)} dead" if len(found) != len(living) else ""))

    for line in publish_failures(args.container):
        problems.append(f"emulator could not publish an instance's ports: {line}")

    if not alive:
        problems.append("no instances at all — the deploy did not land")

    if not problems:
        print(f"    estate intact: {alive} instance(s) across {len(regions)} region(s)")
        return 0

    print("", file=sys.stderr)
    print("the estate is not what the scenario defines:", file=sys.stderr)
    for problem in problems:
        print(f"  {problem}", file=sys.stderr)
    print("", file=sys.stderr)
    print(
        "Scoring this would measure a broken estate, not the arm. The usual cause"
        " is another Floci on the machine holding the instance host ports — see"
        " FLOCI_SSH_PORT_START and FLOCI_APP_PORT_START in"
        " benchmarks/floci/docker-compose.yml.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
