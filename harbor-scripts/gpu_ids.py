#!/usr/bin/env python3
"""Map cgroup-relative GPU indices to physical (node-wide) indices using PCI bus IDs.

Why this translation is needed, and why it cannot be arithmetic:

LSF grants a job one card and renumbers it from the job's own point of view, so
`nvidia-smi` inside the job calls it index 0 whichever card it is; the physical index is
left in CUDA_VISIBLE_DEVICES_ORIG. CDI, which is how podman addresses a GPU, names devices
by physical index. Asking for index 0 from a job allocated another card therefore hands the
container a device it has no permission to use: under the default exclusive-process mode
torch reports no GPU and trains on the CPU, holding an idle card for the length of the run.

The indices cannot be computed from each other, because device minors are not in PCI order.
On one l4 node PCI b5:00.0 is /dev/nvidia6 while ca:00.0 is /dev/nvidia5. Matching by PCI
address, as below, is the only reliable route.

Each task's environment/docker-compose.yaml names its card with
`device_ids: ["${HARBOR_GPU_ID:-0}"]`, which run_harbor.sh fills from this script. It has to
be expressed there rather than in a compose override, because podman-compose APPENDS
reservation device lists across -f files rather than replacing them: a task's own
`count: 1` cannot be retracted, and the container would end up holding both the card it
owns and the one it does not. Unset, the variable resolves to 0, which is correct wherever
the job has the node's only GPU -- the case every gpu_l4_large sweep runs in.
"""

import subprocess
import sys
import yaml


def normalize_pci(pci: str) -> str:
    """Normalize PCI address to 'bus:dev.fn' (e.g. '3f:00.0'), stripping any domain prefix."""
    parts = pci.strip().lower().split(":")
    # Keep only last two colon-separated parts: bus:dev.fn
    return ":".join(parts[-2:])


def get_physical_gpu_ids(relative_ids: list[int]) -> list[int]:
    result = subprocess.run(
        ["nvidia-smi", "--query-gpu=index,gpu_bus_id", "--format=csv,noheader,nounits"],
        capture_output=True, text=True, check=True,
    )
    visible_pci = {}
    for line in result.stdout.strip().splitlines():
        idx, pci = line.split(", ")
        visible_pci[int(idx)] = normalize_pci(pci)

    with open("/etc/cdi/nvidia.yaml") as f:
        spec = yaml.safe_load(f)

    pci_to_physical = {}
    for dev in spec["devices"]:
        name = dev["name"]
        if not name.isdigit():
            continue
        for hook in dev.get("containerEdits", {}).get("hooks", []):
            for arg in hook.get("args", []):
                if "pci-" in arg:
                    raw = arg.split("pci-")[1].split("-")[0]
                    pci_to_physical.setdefault(normalize_pci(raw), int(name))

    physical_ids = []
    for rel_id in relative_ids:
        pci = visible_pci[rel_id]
        physical_ids.append(pci_to_physical[pci])

    return physical_ids


if __name__ == "__main__":
    relative = [int(x) for x in sys.argv[1:]]
    physical = get_physical_gpu_ids(relative)
    print(physical)
