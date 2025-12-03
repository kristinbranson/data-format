"""
Visualize preprocessing steps for Lee et al. 2025 data conversion.

This script demonstrates each preprocessing step for a selected trial:
- Raw position data
- Discretized spatial bins
- Environment geometry (blocked partitions)
- Neural activity traces
"""

import h5py
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from pathlib import Path


def show_processing(subject_id='QLAK-CA1-08', session_idx=4,
                   data_dir='data', save_fig=True):
    """
    Visualize preprocessing steps for one session.

    Parameters
    ----------
    subject_id : str
        Subject ID (e.g., 'QLAK-CA1-08')
    session_idx : int
        Session index to visualize (0-30)
    data_dir : str
        Directory containing .mat files
    save_fig : bool
        Whether to save the figure
    """
    # Load data
    mat_file = Path(data_dir) / f"{subject_id}.mat"

    with h5py.File(mat_file, 'r') as f:
        # Get environment name
        env_ref = f['envs'][0, session_idx]
        env_name = ''.join([chr(int(c)) for c in f[env_ref][:].flatten()])

        # Get position data
        pos_ref = f['position'][session_idx, 0]
        position = f[pos_ref][:]  # (n_timepoints, 2)

        # Get blocked partitions
        blocked_ref = f['blocked'][0, session_idx]
        blocked = f[blocked_ref][:].flatten()

        # Get neural traces
        trace_ref = f['trace'][session_idx, 0]
        trace = f[trace_ref][:]  # (n_timepoints, n_neurons)

    # Discretize position into bins
    ARENA_SIZE = 75.0
    N_BINS = 3
    BIN_SIZE = ARENA_SIZE / N_BINS

    x, y = position[:, 0], position[:, 1]
    x_bin = np.floor(x / BIN_SIZE).astype(int)
    y_bin = np.floor(y / BIN_SIZE).astype(int)
    x_bin = np.clip(x_bin, 0, N_BINS - 1)
    y_bin = np.clip(y_bin, 0, N_BINS - 1)
    spatial_bins = y_bin * N_BINS + x_bin

    # Create geometry grid
    geometry = np.zeros((3, 3))
    if not (len(blocked) == 1 and blocked[0] == -1):
        for partition_idx in blocked:
            if partition_idx >= 0:
                row = int(partition_idx) // 3
                col = int(partition_idx) % 3
                geometry[row, col] = 1

    # Create figure
    fig = plt.figure(figsize=(20, 12))
    gs = fig.add_gridspec(3, 4, hspace=0.3, wspace=0.3)

    # 1. Environment geometry
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.imshow(geometry, cmap='RdGy', vmin=0, vmax=1, origin='upper')
    ax1.set_title(f'Environment Geometry: {env_name}', fontsize=14, fontweight='bold')
    ax1.set_xlabel('X partition (West → East)')
    ax1.set_ylabel('Y partition (North → South)')

    # Add partition labels
    for i in range(3):
        for j in range(3):
            partition_num = i * 3 + j
            color = 'white' if geometry[i, j] > 0.5 else 'black'
            ax1.text(j, i, str(partition_num), ha='center', va='center',
                    fontsize=16, color=color, fontweight='bold')
    ax1.set_xticks(range(3))
    ax1.set_yticks(range(3))
    ax1.set_xticklabels(['0', '1', '2'])
    ax1.set_yticklabels(['0', '1', '2'])

    # 2. Raw trajectory
    ax2 = fig.add_subplot(gs[0, 1])
    # Show environment boundaries
    for i in range(3):
        for j in range(3):
            if geometry[i, j] > 0.5:
                rect = patches.Rectangle(
                    (j * BIN_SIZE, i * BIN_SIZE), BIN_SIZE, BIN_SIZE,
                    linewidth=0, facecolor='gray', alpha=0.5
                )
                ax2.add_patch(rect)

    # Plot trajectory (subsample for visibility)
    subsample = max(1, len(x) // 5000)
    scatter = ax2.scatter(x[::subsample], y[::subsample], c=np.arange(len(x))[::subsample],
                         cmap='viridis', s=1, alpha=0.5)
    ax2.set_xlim(0, ARENA_SIZE)
    ax2.set_ylim(0, ARENA_SIZE)
    ax2.set_xlabel('X position (cm)')
    ax2.set_ylabel('Y position (cm)')
    ax2.set_title('Raw Trajectory (color = time)', fontsize=14, fontweight='bold')
    ax2.set_aspect('equal')
    ax2.invert_yaxis()  # Match grid orientation

    # Add grid lines
    for i in range(N_BINS + 1):
        ax2.axhline(i * BIN_SIZE, color='red', linestyle='--', alpha=0.3, linewidth=1)
        ax2.axvline(i * BIN_SIZE, color='red', linestyle='--', alpha=0.3, linewidth=1)

    # 3. Discretized spatial bins
    ax3 = fig.add_subplot(gs[0, 2])
    # Count occupancy per bin
    bin_counts = np.zeros((3, 3))
    for b in range(9):
        mask = spatial_bins == b
        bin_counts[b // 3, b % 3] = np.sum(mask)

    im = ax3.imshow(bin_counts, cmap='hot', origin='upper')
    ax3.set_title('Spatial Bin Occupancy', fontsize=14, fontweight='bold')
    ax3.set_xlabel('X bin')
    ax3.set_ylabel('Y bin')

    # Add counts as text
    for i in range(3):
        for j in range(3):
            count = int(bin_counts[i, j])
            pct = 100 * count / len(spatial_bins)
            color = 'white' if bin_counts[i, j] > bin_counts.max() / 2 else 'black'
            ax3.text(j, i, f'{i*3+j}\n{count}\n({pct:.1f}%)',
                    ha='center', va='center', fontsize=10, color=color)
    ax3.set_xticks(range(3))
    ax3.set_yticks(range(3))
    plt.colorbar(im, ax=ax3, label='# timepoints')

    # 4. Output encoding (first 1000 timepoints)
    ax4 = fig.add_subplot(gs[0, 3])
    t_plot = min(1000, len(spatial_bins))
    time_s = np.arange(t_plot) / 30.0  # 30 Hz sampling
    ax4.scatter(time_s, spatial_bins[:t_plot], s=1, alpha=0.5)
    ax4.set_xlabel('Time (s)')
    ax4.set_ylabel('Spatial bin (0-8)')
    ax4.set_title(f'Output: Categorical Position\n(first {t_plot} timepoints)',
                 fontsize=14, fontweight='bold')
    ax4.set_ylim(-0.5, 8.5)
    ax4.set_yticks(range(9))
    ax4.grid(True, alpha=0.3)

    # 5-7. Neural activity (example neurons)
    n_neurons = trace.shape[1]
    neurons_to_plot = [0, n_neurons // 2, n_neurons - 1]  # First, middle, last

    for idx, neuron_idx in enumerate(neurons_to_plot):
        ax = fig.add_subplot(gs[1, idx])

        # Plot neural trace
        t_plot = min(5000, len(trace))
        time_s = np.arange(t_plot) / 30.0
        neural_data = trace[:t_plot, neuron_idx]

        # Replace NaN with 0
        neural_data = np.nan_to_num(neural_data, nan=0.0)

        # Plot as raster
        active_times = time_s[neural_data > 0.5]
        ax.scatter(active_times, np.ones_like(active_times) * neuron_idx,
                  s=5, color='black', marker='|')

        ax.set_xlabel('Time (s)')
        ax.set_ylabel(f'Neuron {neuron_idx}')
        ax.set_title(f'Neural Activity: Neuron {neuron_idx}\n'
                    f'({np.sum(neural_data > 0.5)} events)',
                    fontsize=12, fontweight='bold')
        ax.set_ylim(neuron_idx - 0.5, neuron_idx + 0.5)
        ax.set_xlim(0, time_s[-1])
        ax.set_yticks([])
        ax.grid(True, alpha=0.3, axis='x')

    # 8. Population activity summary
    ax8 = fig.add_subplot(gs[1, 3])
    t_plot = min(5000, len(trace))
    time_s = np.arange(t_plot) / 30.0
    trace_plot = np.nan_to_num(trace[:t_plot, :], nan=0.0)

    # Population firing rate over time
    pop_rate = np.sum(trace_plot, axis=1)  # Total events per timepoint
    ax8.plot(time_s, pop_rate, linewidth=0.5)
    ax8.set_xlabel('Time (s)')
    ax8.set_ylabel('Population activity\n(# active neurons)')
    ax8.set_title(f'Population Activity Summary\n({n_neurons} neurons total)',
                 fontsize=12, fontweight='bold')
    ax8.grid(True, alpha=0.3)

    # 9. Data dimensions summary
    ax9 = fig.add_subplot(gs[2, :])
    ax9.axis('off')

    summary_text = f"""
    PREPROCESSING SUMMARY FOR {subject_id}, SESSION {session_idx} ({env_name})
    ═══════════════════════════════════════════════════════════════════════════

    RAW DATA:
      • Position: {position.shape} = (n_timepoints, [x, y])
      • Neural traces: {trace.shape} = (n_timepoints, n_neurons)
      • Sampling rate: 30 Hz
      • Session duration: {len(position) / 30.0 / 60:.1f} minutes

    PREPROCESSING:
      1. Discretize position (x, y) → spatial bin (0-8) using 3×3 grid (25 cm bins)
      2. Convert blocked partitions → geometry vector (9 dimensions, binary)
      3. Replace NaN values in neural traces with 0

    STANDARDIZED FORMAT:
      • Neural: ({n_neurons}, {len(trace)}) = (n_neurons, n_timepoints)
      • Input: (9,) = geometry vector [constant per session]
      • Output: (1, {len(spatial_bins)}) = categorical position bin [time-varying]

    ENVIRONMENT GEOMETRY:
      • Blocked partitions: {blocked if blocked[0] != -1 else "None (full square)"}
      • Open partitions: {np.sum(geometry == 0):.0f}/9
      • Walled partitions: {np.sum(geometry == 1):.0f}/9

    DATA QUALITY:
      • Non-NaN neural data: {100 * np.sum(~np.isnan(trace)) / trace.size:.1f}%
      • Active neurons (>0 events): {np.sum(np.sum(np.nan_to_num(trace, 0) > 0.5, axis=0) > 0)}/{n_neurons}
      • Mean population activity: {np.mean(np.sum(np.nan_to_num(trace, 0) > 0.5, axis=1)):.2f} neurons/timepoint
    """

    ax9.text(0.05, 0.5, summary_text, transform=ax9.transAxes,
            fontsize=11, verticalalignment='center', family='monospace',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))

    fig.suptitle(f'Data Preprocessing Visualization: {subject_id}, Session {session_idx}',
                fontsize=16, fontweight='bold', y=0.995)

    if save_fig:
        figname = f'preprocessing_demo_{subject_id.lower()}_ses{session_idx:02d}.png'
        fig.savefig(figname, dpi=150, bbox_inches='tight')
        print(f"Saved figure: {figname}")

    plt.show()

    return fig


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Visualize data preprocessing')
    parser.add_argument('--subject', default='QLAK-CA1-08', help='Subject ID')
    parser.add_argument('--session', type=int, default=4, help='Session index (0-30)')
    parser.add_argument('--data-dir', default='data', help='Data directory')

    args = parser.parse_args()

    show_processing(args.subject, args.session, args.data_dir)
