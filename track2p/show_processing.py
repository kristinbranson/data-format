"""
Visualize preprocessing steps for Track2p data conversion

This function demonstrates each preprocessing step for a selected trial:
1. Raw neural data (spikes) - full session
2. Binned into 2-minute trials
3. Time input generation
4. Output variable computation and discretization
"""
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from convert_data import (
    load_subject_data,
    segment_into_trials,
    discretize_motion_energy,
    create_time_input,
    map_session_to_age_category,
    TRIAL_TIMEPOINTS,
    SAMPLING_RATE,
    MOTION_SMOOTHING_WINDOW
)

def show_processing(subject_id='jm031', session_idx=0, trial_idx=0, neuron_idx=0):
    """
    Visualize preprocessing steps for a specific trial

    Args:
        subject_id: Subject identifier (e.g., 'jm031')
        session_idx: Session index (0-based)
        trial_idx: Trial index within session (0-based, 0-9 or 0-14 depending on session)
        neuron_idx: Which neuron to show (0-based)
    """
    # Load subject data
    data_dir = Path('data')
    subject_dir = data_dir / subject_id

    print(f"Loading data for {subject_id}...")
    sessions_spks, sessions_motion, session_names, n_neurons = load_subject_data(subject_dir)
    n_sessions = len(sessions_spks)

    print(f"  Sessions: {n_sessions}, Neurons: {n_neurons}")
    print(f"  Visualizing session {session_idx+1}/{n_sessions}: {session_names[session_idx]}")

    # Get data for selected session
    spks_session = sessions_spks[session_idx]  # (n_neurons, n_timepoints)
    motion_session = sessions_motion[session_idx]  # (n_timepoints,)

    # Session duration
    n_timepoints = spks_session.shape[1]
    time_session = np.arange(n_timepoints) / SAMPLING_RATE  # seconds

    print(f"  Session duration: {n_timepoints} timepoints = {n_timepoints/SAMPLING_RATE:.1f} seconds")

    # Segment into trials
    spks_trials = segment_into_trials(spks_session, TRIAL_TIMEPOINTS)
    motion_trials = segment_into_trials(motion_session, TRIAL_TIMEPOINTS)
    n_trials = len(spks_trials)

    print(f"  Number of trials: {n_trials}")

    # Get selected trial
    spks_trial = spks_trials[trial_idx]  # (n_neurons, 3600)
    motion_trial = motion_trials[trial_idx]  # (3600,)

    # Create time input
    time_input = create_time_input(TRIAL_TIMEPOINTS, SAMPLING_RATE)  # (1, 3600)

    # Compute outputs (motion energy is now time-varying, binary categorization)
    motion_categories = discretize_motion_energy(motion_trials, method='binary', smoothing_window=MOTION_SMOOTHING_WINDOW)
    age_category = map_session_to_age_category(session_idx, n_sessions)
    session_number = session_idx

    motion_cat_timeseries = motion_categories[trial_idx]  # Now an array of shape (n_timepoints,)

    # Compute distribution of categories in this trial
    unique_cats, counts = np.unique(motion_cat_timeseries, return_counts=True)
    cat_dist = {int(c): counts[i]/len(motion_cat_timeseries)*100 for i, c in enumerate(unique_cats)}

    print(f"\nTrial {trial_idx+1}/{n_trials}:")
    print(f"  Motion energy categories (time-varying, binary):")
    for cat in sorted(cat_dist.keys()):
        cat_name = 'Low' if cat==0 else 'High'
        print(f"    {cat_name} ({cat}): {cat_dist[cat]:.1f}% of timepoints")
    print(f"  Age category: {age_category} ({'Early' if age_category==0 else 'Mid' if age_category==1 else 'Late'})")
    print(f"  Session number: {session_number}")

    # Create visualization
    fig = plt.figure(figsize=(20, 12))
    gs = fig.add_gridspec(4, 2, hspace=0.3, wspace=0.3)

    # 1. Raw neural data - full session
    ax1 = fig.add_subplot(gs[0, :])
    # Show a few neurons for visualization
    n_show = min(10, n_neurons)
    for i in range(n_show):
        ax1.plot(time_session, spks_session[i] + i*5, 'k-', alpha=0.6, linewidth=0.5)

    # Highlight the selected trial
    trial_start_time = trial_idx * (TRIAL_TIMEPOINTS / SAMPLING_RATE)
    trial_end_time = (trial_idx + 1) * (TRIAL_TIMEPOINTS / SAMPLING_RATE)
    ax1.axvspan(trial_start_time, trial_end_time, alpha=0.3, color='red', label=f'Trial {trial_idx+1}')

    ax1.set_xlabel('Time (s)', fontsize=12)
    ax1.set_ylabel(f'Neurons (showing {n_show}/{n_neurons})', fontsize=12)
    ax1.set_title(f'Step 1: Raw Neural Data - Full Session ({session_names[session_idx]})', fontsize=14, fontweight='bold')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # 2. Full session motion energy
    ax2 = fig.add_subplot(gs[1, :], sharex=ax1)
    ax2.plot(time_session, motion_session, 'b-', linewidth=1)
    ax2.axvspan(trial_start_time, trial_end_time, alpha=0.3, color='red', label=f'Trial {trial_idx+1}')
    ax2.set_xlabel('Time (s)', fontsize=12)
    ax2.set_ylabel('Motion Energy', fontsize=12)
    ax2.set_title('Step 2: Full Session Motion Energy', fontsize=14, fontweight='bold')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # 3. Trial neural data (selected trial)
    ax3 = fig.add_subplot(gs[2, 0])
    time_trial = time_input.flatten()

    # Show the selected neuron
    ax3.plot(time_trial, spks_trial[neuron_idx], 'g-', linewidth=1, label=f'Neuron {neuron_idx}')
    ax3.set_xlabel('Time within trial (s)', fontsize=12)
    ax3.set_ylabel('Spike activity', fontsize=12)
    ax3.set_title(f'Step 3: Trial {trial_idx+1} - Single Neuron Activity', fontsize=14, fontweight='bold')
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    # 4. Trial motion energy
    ax4 = fig.add_subplot(gs[2, 1])
    ax4.plot(time_trial, motion_trial, 'b-', linewidth=1)
    ax4.axhline(np.mean(motion_trial), color='r', linestyle='--', linewidth=2,
                label=f'Mean = {np.mean(motion_trial):.0f}')
    ax4.set_xlabel('Time within trial (s)', fontsize=12)
    ax4.set_ylabel('Motion Energy', fontsize=12)
    ax4.set_title(f'Step 4: Trial {trial_idx+1} - Motion Energy', fontsize=14, fontweight='bold')
    ax4.legend()
    ax4.grid(True, alpha=0.3)

    # 5. Input representation
    ax5 = fig.add_subplot(gs[3, 0])
    ax5.plot(time_trial, time_input.flatten(), 'purple', linewidth=2)
    ax5.set_xlabel('Timepoint index', fontsize=12)
    ax5.set_ylabel('Time (s)', fontsize=12)
    ax5.set_title('Step 5: Input - Time within Trial', fontsize=14, fontweight='bold')
    ax5.grid(True, alpha=0.3)

    # 6. Output variables - now time-varying motion energy (binary)
    ax6 = fig.add_subplot(gs[3, 1])

    # Plot motion energy categories over time
    ax6.plot(time_trial, motion_cat_timeseries, 'b-', linewidth=2, label='Motion Category')
    ax6.fill_between(time_trial, 0, motion_cat_timeseries, alpha=0.3)
    ax6.set_xlabel('Time within trial (s)', fontsize=12)
    ax6.set_ylabel('Motion Energy Category', fontsize=12)
    ax6.set_yticks([0, 1])
    ax6.set_yticklabels(['Low', 'High'])
    ax6.set_title('Step 6: Output - Time-Varying Motion Energy (Binary)', fontsize=14, fontweight='bold')
    ax6.grid(True, alpha=0.3)
    ax6.legend()

    # Add text annotation
    unique_cats, counts = np.unique(motion_cat_timeseries, return_counts=True)
    cat_text = ', '.join([f"{int(c)}: {counts[i]/len(motion_cat_timeseries)*100:.1f}%"
                          for i, c in enumerate(unique_cats)])
    ax6.text(0.02, 0.98, f'Distribution: {cat_text}\nAge: {"Early" if age_category==0 else "Mid" if age_category==1 else "Late"}, Session: {session_number}',
             transform=ax6.transAxes, fontsize=10, verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    # Overall title
    fig.suptitle(f'Track2p Data Preprocessing Pipeline\nSubject: {subject_id}, Session: {session_names[session_idx]}, Trial: {trial_idx+1}',
                 fontsize=16, fontweight='bold')

    # Save figure
    output_name = f'preprocessing_demo_{subject_id}_ses{session_idx+1:02d}.png'
    plt.savefig(output_name, dpi=150, bbox_inches='tight')
    print(f"\nSaved visualization to: {output_name}")
    plt.close()

    return fig

if __name__ == '__main__':
    import sys

    # Default parameters
    subject_id = 'jm031'
    session_idx = 0
    trial_idx = 0
    neuron_idx = 0

    # Parse command line arguments if provided
    if len(sys.argv) > 1:
        subject_id = sys.argv[1]
    if len(sys.argv) > 2:
        session_idx = int(sys.argv[2])
    if len(sys.argv) > 3:
        trial_idx = int(sys.argv[3])
    if len(sys.argv) > 4:
        neuron_idx = int(sys.argv[4])

    print("=" * 80)
    print("TRACK2P PREPROCESSING VISUALIZATION")
    print("=" * 80)

    # Show processing for specified trial
    show_processing(subject_id, session_idx, trial_idx, neuron_idx)

    print("\n" + "=" * 80)
    print("COMPLETE")
    print("=" * 80)
