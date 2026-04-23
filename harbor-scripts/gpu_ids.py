#!/usr/bin/env python3
"""Map cgroup-relative GPU indices to physical (node-wide) indices using PCI bus IDs."""

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
