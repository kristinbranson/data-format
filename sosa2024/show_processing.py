"""
Visualization of preprocessing steps for Sosa et al. 2024 dataset conversion.

This script demonstrates how raw data is processed into the standardized format.
"""

import numpy as np
import matplotlib.pyplot as plt
import pynwb
from convert_data import (
    calculate_distance_to_reward_zone,
    discretize_distance_to_reward,
    discretize_absolute_position,
    discretize_speed,
    infer_reward_zone,
    load_session_data,
    REWARD_ZONES
)


def show_processing(nwb_file_path: str, trial_id: int = 10, output_file: str = 'preprocessing_demo.png'):
    """
    Visualize preprocessing steps for a single trial.

    Args:
        nwb_file_path: Path to NWB file
        trial_id: Trial number to visualize
        output_file: Output filename for plot
    """
    # Load session data
    print(f"Loading {nwb_file_path}...")
    session_data = load_session_data(nwb_file_path)

    # Infer reward zone
    reward_zone = infer_reward_zone(session_data, session_data['session_id'])
    zone_start, zone_end = REWARD_ZONES[reward_zone]
    print(f"Reward zone: {reward_zone} ({zone_start}-{zone_end} cm)")

    # Extract trial data
    trial_mask = (
        (session_data['trial_num'] == trial_id) &
        (session_data['scanning'] > 0) &
        (session_data['position'] >= 0) &
        (session_data['position'] <= 450)
    )

    if not np.any(trial_mask):
        print(f"No valid data for trial {trial_id}")
        return

    # Raw data
    position_raw = session_data['position'][trial_mask]
    speed_raw = session_data['speed'][trial_mask]
    lick_raw = session_data['lick'][trial_mask]
    neural_raw = session_data['neural_data'][trial_mask, :]  # (n_timepoints, n_neurons)

    # Compute time vector
    sampling_rate = 15.5  # Hz
    time = np.arange(len(position_raw)) / sampling_rate

    # Process: calculate distance to reward
    distance_to_reward = calculate_distance_to_reward_zone(position_raw, reward_zone)

    # Discretize outputs
    distance_bins = discretize_distance_to_reward(distance_to_reward)
    position_bins = discretize_absolute_position(position_raw)
    speed_bins = discretize_speed(speed_raw)
    lick_binary = (lick_raw > 0).astype(int)

    print(f"\nTrial {trial_id} summary:")
    print(f"  Duration: {time[-1]:.2f} seconds ({len(time)} timepoints)")
    print(f"  Position range: {position_raw.min():.1f} - {position_raw.max():.1f} cm")
    print(f"  Speed range: {speed_raw.min():.1f} - {speed_raw.max():.1f} cm/s")
    print(f"  Neurons: {neural_raw.shape[1]}")
    print(f"  Licks: {lick_binary.sum()} frames")

    # Create visualization
    fig, axes = plt.subplots(5, 2, figsize=(16, 14))
    fig.suptitle(f'Preprocessing Steps: Trial {trial_id} (Reward Zone {reward_zone})', fontsize=14)

    # Row 1: Position
    ax = axes[0, 0]
    ax.plot(time, position_raw, 'k-', linewidth=1)
    ax.axhline(zone_start, color='r', linestyle='--', alpha=0.5, label=f'Zone {reward_zone} start')
    ax.axhline(zone_end, color='r', linestyle='--', alpha=0.5, label=f'Zone {reward_zone} end')
    ax.fill_between([0, time[-1]], zone_start, zone_end, color='r', alpha=0.1)
    ax.set_ylabel('Position (cm)')
    ax.set_title('Raw Position Data')
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    ax = axes[0, 1]
    ax.plot(time, position_bins, 'b-', linewidth=2, drawstyle='steps-post')
    ax.set_ylabel('Position Bin')
    ax.set_title('Discretized Absolute Position (5 bins)')
    ax.set_yticks([0, 1, 2, 3, 4])
    ax.set_yticklabels(['0-90cm', '90-180cm', '180-270cm', '270-360cm', '360-450cm'])
    ax.grid(True, alpha=0.3)

    # Row 2: Distance to Reward
    ax = axes[1, 0]
    ax.plot(time, distance_to_reward, 'g-', linewidth=1)
    ax.axhline(0, color='r', linestyle='-', linewidth=2, alpha=0.5, label='In reward zone')
    ax.set_ylabel('Distance (cm)')
    ax.set_title('Distance to Reward Zone')
    ax.legend()
    ax.grid(True, alpha=0.3)

    ax = axes[1, 1]
    ax.plot(time, distance_bins, 'm-', linewidth=2, drawstyle='steps-post')
    ax.set_ylabel('Distance Bin')
    ax.set_title('Discretized Distance to Reward (7 bins)')
    ax.set_yticks([0, 1, 2, 3, 4, 5, 6])
    ax.set_yticklabels(['<-50', '-50:-10', '-10:0', '0\n(in zone)', '0:10', '10:50', '>50'], fontsize=8)
    ax.grid(True, alpha=0.3)

    # Row 3: Speed
    ax = axes[2, 0]
    ax.plot(time, speed_raw, 'c-', linewidth=1)
    ax.axhline(2, color='k', linestyle='--', alpha=0.3, label='Stationary threshold')
    ax.set_ylabel('Speed (cm/s)')
    ax.set_title('Raw Speed Data')
    ax.legend()
    ax.grid(True, alpha=0.3)

    ax = axes[2, 1]
    ax.plot(time, speed_bins, 'c-', linewidth=2, drawstyle='steps-post')
    ax.set_ylabel('Speed Bin')
    ax.set_title('Discretized Speed (5 bins)')
    ax.set_yticks([0, 1, 2, 3, 4])
    ax.set_yticklabels(['<2\n(still)', '2-10\n(slow)', '10-20\n(med)', '20-40\n(fast)', '>40\n(v.fast)'], fontsize=8)
    ax.grid(True, alpha=0.3)

    # Row 4: Licking
    ax = axes[3, 0]
    lick_diff = np.diff(lick_raw, prepend=0)
    lick_times = time[lick_diff > 0]
    ax.eventplot([lick_times], colors='orange', linewidths=2)
    ax.set_ylabel('Lick Events')
    ax.set_title('Raw Lick Detection')
    ax.set_ylim(-0.5, 1.5)
    ax.set_yticks([])
    ax.grid(True, alpha=0.3)

    ax = axes[3, 1]
    ax.plot(time, lick_binary, 'orange', linewidth=2, drawstyle='steps-post')
    ax.set_ylabel('Lick Binary')
    ax.set_title('Binary Licking Indicator')
    ax.set_yticks([0, 1])
    ax.set_yticklabels(['No Lick', 'Lick'])
    ax.set_ylim(-0.1, 1.1)
    ax.grid(True, alpha=0.3)

    # Row 5: Neural Activity
    # Select up to 10 neurons to display
    n_neurons_display = min(10, neural_raw.shape[1])
    neuron_indices = np.linspace(0, neural_raw.shape[1] - 1, n_neurons_display, dtype=int)

    ax = axes[4, 0]
    for i, neuron_idx in enumerate(neuron_indices):
        ax.plot(time, neural_raw[:, neuron_idx] + i * 2, linewidth=0.5, alpha=0.7)
    ax.set_ylabel('Neural Activity\n(offset for visibility)')
    ax.set_xlabel('Time (s)')
    ax.set_title(f'Deconvolved Ca²⁺ Activity ({n_neurons_display}/{neural_raw.shape[1]} neurons)')
    ax.grid(True, alpha=0.3)

    ax = axes[4, 1]
    # Show heatmap of neural activity
    neural_subset = neural_raw[:, neuron_indices].T
    im = ax.imshow(neural_subset, aspect='auto', cmap='viridis', interpolation='nearest')
    ax.set_ylabel('Neuron Index')
    ax.set_xlabel('Time (s)')
    ax.set_title('Neural Activity Heatmap')
    # Set x-ticks to time
    n_ticks = 5
    tick_indices = np.linspace(0, len(time) - 1, n_ticks, dtype=int)
    ax.set_xticks(tick_indices)
    ax.set_xticklabels([f'{time[i]:.1f}' for i in tick_indices])
    plt.colorbar(im, ax=ax, label='Activity')

    fig.tight_layout()
    fig.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"\nSaved visualization to: {output_file}")

    return fig


def main():
    """Run preprocessing visualization on example trials."""
    # Example 1: Trial from sub-m11 session 03
    print("="*60)
    print("Example 1: sub-m11 session 03, trial 10")
    print("="*60)
    show_processing(
        'data/sub-m11/sub-m11_ses-03_behavior+ophys.nwb',
        trial_id=10,
        output_file='preprocessing_demo_m11_ses03.png'
    )

    # Example 2: Trial from sub-m12 session 05
    print("\n" + "="*60)
    print("Example 2: sub-m12 session 05, trial 20")
    print("="*60)
    show_processing(
        'data/sub-m12/sub-m12_ses-05_behavior+ophys.nwb',
        trial_id=20,
        output_file='preprocessing_demo_m12_ses05.png'
    )

    print("\n✓ Preprocessing visualization complete!")


if __name__ == '__main__':
    main()
