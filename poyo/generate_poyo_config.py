#!/usr/bin/env python3
"""
Generate torch_brain config YAML from a converted pickle file.

Usage:
    python generate_poyo_config.py <pickle_file> <brainset_name> [--output <config.yaml>]

Example:
    python generate_poyo_config.py converted_data.pkl sosa2024 --output hdf5_data/sosa2024_config.yaml
"""

import argparse
import pickle
import yaml
from pathlib import Path


def generate_config(pickle_path: str, brainset_name: str, output_path: str = None):
    """Generate torch_brain config YAML from pickle file.

    Args:
        pickle_path: Path to the converted data pickle file
        brainset_name: Name of the brainset (e.g., 'sosa2024')
        output_path: Output path for YAML file (default: <brainset_name>_config.yaml)
    """
    # Load pickle file
    with open(pickle_path, 'rb') as f:
        data = pickle.load(f)

    # Extract info
    n_sessions = len(data['neural'])
    output_names = data['output_names']
    output_values = data['output_values']

    print(f"Loaded pickle file: {pickle_path}")
    print(f"  Sessions: {n_sessions}")
    print(f"  Outputs: {output_names}")

    # Generate session list
    sessions = [f"session_{i:04d}" for i in range(n_sessions)]

    # Generate multitask_readout config
    multitask_readout = []
    for i, (name, values) in enumerate(zip(output_names, output_values)):
        num_classes = len(values)
        readout_config = {
            'readout_id': f'output_{name}',
            'timestamp_key': 'outputs.timestamps',
            'value_key': f'outputs.{name}',
            'metrics': [
                {
                    'metric': {
                        '_target_': 'torchmetrics.Accuracy',
                        'task': 'multiclass',
                        'num_classes': num_classes,
                    }
                }
            ]
        }
        multitask_readout.append(readout_config)
        print(f"  {name}: {num_classes} classes -> {values}")

    # Build full config
    config = [
        {
            'selection': [
                {
                    'brainset': brainset_name,
                    'sessions': sessions,
                }
            ],
            'config': {
                'multitask_readout': multitask_readout,
            }
        }
    ]

    # Determine output path
    if output_path is None:
        output_path = f"{brainset_name}_config.yaml"

    # Write YAML
    with open(output_path, 'w') as f:
        f.write(f"# Dataset config for {brainset_name}\n")
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    print(f"\nConfig written to: {output_path}")

    return config


def main():
    parser = argparse.ArgumentParser(
        description="Generate torch_brain config YAML from converted pickle file"
    )
    parser.add_argument("pickle_file", help="Path to converted data pickle file")
    parser.add_argument("brainset_name", help="Name of the brainset (e.g., 'sosa2024')")
    parser.add_argument("--output", "-o", default=None,
                        help="Output path for YAML file (default: <brainset_name>_config.yaml)")
    args = parser.parse_args()

    generate_config(args.pickle_file, args.brainset_name, args.output)


if __name__ == "__main__":
    main()
