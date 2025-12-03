"""
Visualize preprocessing steps for MAP data conversion.

This script demonstrates how raw neural data is processed into the standardized format:
1. Raw spike times from NWB file
2. Temporal binning (50ms bins)
3. Trial alignment (to go cue)
4. Final formatted output

Author: Claude Code
Date: 2025-12-02
"""

import numpy as np
import matplotlib.pyplot as plt
from pynwb import NWBHDF5IO
from pathlib import Path
import json


def show_processing(nwb_path, trial_idx=0, n_units_to_show=10):
    """
    Visualize preprocessing steps for a single trial.

    Parameters
    ----------
    nwb_path : str
        Path to NWB file
    trial_idx : int
        Which trial to visualize
    n_units_to_show : int
        Number of units to display
    """

    print(f"Loading: {Path(nwb_path).name}")
    print(f"Trial: {trial_idx}")

    # Processing parameters (matching convert_map_data_fast.py)
    time_window = (-2.5, 1.5)
    bin_size = 0.05
    time_bins = np.arange(time_window[0], time_window[1], bin_size)
    n_time_bins = len(time_bins)

    # Load NWB file
    io = NWBHDF5IO(nwb_path, 'r')
    nwbfile = io.read()

    try:
        # Get trial info
        trials = nwbfile.trials
        trial_start = trials['start_time'][trial_idx]
        trial_stop = trials['stop_time'][trial_idx]
        trial_instruction = trials['trial_instruction'][trial_idx]
        trial_outcome = trials['outcome'][trial_idx]

        # Get go cue time (alignment point)
        go_times = nwbfile.acquisition['BehavioralEvents'].time_series['go_start_times'].timestamps[:]
        go_cue_time = go_times[trial_idx]

        # Get event times
        sample_start = nwbfile.acquisition['BehavioralEvents'].time_series['sample_start_times'].timestamps[trial_idx]
        delay_start = nwbfile.acquisition['BehavioralEvents'].time_series['delay_start_times'].timestamps[trial_idx]

        print(f"\nTrial Info:")
        print(f"  Instruction: {trial_instruction}")
        print(f"  Outcome: {trial_outcome}")
        print(f"  Trial duration: {trial_stop - trial_start:.2f}s")
        print(f"  Sample start: {sample_start - go_cue_time:.2f}s relative to go cue")
        print(f"  Delay start: {delay_start - go_cue_time:.2f}s relative to go cue")
        print(f"  Go cue: 0.0s (alignment point)")

        # Get units
        units = nwbfile.units
        n_units = len(units)
        n_units_to_show = min(n_units_to_show, n_units)

        # Get brain regions
        brain_regions = []
        for unit_idx in range(n_units_to_show):
            eg = units['electrode_group'][unit_idx]
            if hasattr(eg, 'location'):
                try:
                    loc_dict = json.loads(eg.location)
                    region = loc_dict.get('brain_regions', 'unknown')
                except:
                    region = 'unknown'
            else:
                region = 'unknown'
            brain_regions.append(region)

        # Create figure with extra rows for inputs and outputs
        n_rows = n_units_to_show + 3  # neurons + 2 input rows + 1 output row
        fig = plt.figure(figsize=(20, 2*n_units_to_show + 6))  # Extra space for input/output rows

        # Create gridspec with variable row heights
        height_ratios = [2] * n_units_to_show + [1.5, 1.5, 2.5]  # Neurons, 2 inputs, outputs
        gs = fig.add_gridspec(n_rows, 4, hspace=0.5, wspace=0.3, height_ratios=height_ratios)

        # Process each unit
        for unit_idx in range(n_units_to_show):
            # Get spike times for this unit
            spike_times = units['spike_times'][unit_idx]

            # === COLUMN 1: Raw spike times (full trial) ===
            ax = fig.add_subplot(gs[unit_idx, 0])

            # Filter spikes to trial period
            trial_spikes = spike_times[(spike_times >= trial_start) & (spike_times <= trial_stop)]
            trial_spikes_rel = trial_spikes - trial_start  # Relative to trial start

            if len(trial_spikes) > 0:
                ax.vlines(trial_spikes_rel, 0, 1, colors='k', linewidth=0.5)

            # Mark events
            ax.axvline(sample_start - trial_start, color='blue', linestyle='--', alpha=0.5, label='Sample')
            ax.axvline(delay_start - trial_start, color='orange', linestyle='--', alpha=0.5, label='Delay')
            ax.axvline(go_cue_time - trial_start, color='red', linestyle='--', alpha=0.5, linewidth=2, label='Go cue')

            ax.set_xlim(0, trial_stop - trial_start)
            ax.set_ylim(0, 1)
            ax.set_yticks([])
            if unit_idx == 0:
                ax.set_title('1. Raw Spike Times\n(full trial)', fontsize=10)
                ax.legend(loc='upper right', fontsize=6)
            if unit_idx == n_units_to_show - 1:
                ax.set_xlabel('Time from trial start (s)', fontsize=8)
            ax.set_ylabel(f'Unit {unit_idx}\n{brain_regions[unit_idx]}', fontsize=8)
            ax.text(0.02, 0.95, f'n={len(trial_spikes)} spikes', transform=ax.transAxes,
                   fontsize=7, va='top')

            # === COLUMN 2: Spikes aligned to go cue ===
            ax = fig.add_subplot(gs[unit_idx, 1])

            # Filter spikes to analysis window relative to go cue
            window_start = go_cue_time + time_window[0]
            window_end = go_cue_time + time_window[1]
            window_spikes = spike_times[(spike_times >= window_start) & (spike_times <= window_end)]
            window_spikes_rel = window_spikes - go_cue_time  # Relative to go cue

            if len(window_spikes) > 0:
                ax.vlines(window_spikes_rel, 0, 1, colors='k', linewidth=0.5)

            # Mark epochs
            ax.axvspan(sample_start - go_cue_time, delay_start - go_cue_time,
                      alpha=0.2, color='blue', label='Sample')
            ax.axvspan(delay_start - go_cue_time, 0,
                      alpha=0.2, color='orange', label='Delay')
            ax.axvspan(0, time_window[1],
                      alpha=0.2, color='green', label='Response')
            ax.axvline(0, color='red', linestyle='--', linewidth=2, label='Go cue')

            ax.set_xlim(time_window)
            ax.set_ylim(0, 1)
            ax.set_yticks([])
            if unit_idx == 0:
                ax.set_title('2. Aligned to Go Cue\n(analysis window)', fontsize=10)
            if unit_idx == n_units_to_show - 1:
                ax.set_xlabel('Time from go cue (s)', fontsize=8)
            ax.text(0.02, 0.95, f'n={len(window_spikes)} spikes', transform=ax.transAxes,
                   fontsize=7, va='top')

            # === COLUMN 3: Binned firing rates ===
            ax = fig.add_subplot(gs[unit_idx, 2])

            # Compute firing rates for each bin
            firing_rates = np.zeros(n_time_bins)
            for bin_idx in range(n_time_bins):
                bin_start = go_cue_time + time_bins[bin_idx]
                bin_end = bin_start + bin_size
                n_spikes = np.sum((spike_times >= bin_start) & (spike_times < bin_end))
                firing_rates[bin_idx] = n_spikes / bin_size

            # Plot as step function
            ax.step(time_bins, firing_rates, where='post', color='black', linewidth=1)
            ax.fill_between(time_bins, firing_rates, step='post', alpha=0.3, color='gray')

            # Mark epochs
            ax.axvspan(sample_start - go_cue_time, delay_start - go_cue_time,
                      alpha=0.1, color='blue')
            ax.axvspan(delay_start - go_cue_time, 0,
                      alpha=0.1, color='orange')
            ax.axvspan(0, time_window[1],
                      alpha=0.1, color='green')
            ax.axvline(0, color='red', linestyle='--', linewidth=2)

            ax.set_xlim(time_window)
            ax.set_ylim(bottom=0)
            if unit_idx == 0:
                ax.set_title(f'3. Binned Firing Rates\n({int(bin_size*1000)}ms bins)', fontsize=10)
            if unit_idx == n_units_to_show - 1:
                ax.set_xlabel('Time from go cue (s)', fontsize=8)
            ax.set_ylabel('FR (Hz)', fontsize=8)
            ax.text(0.02, 0.95, f'mean={np.mean(firing_rates):.1f} Hz', transform=ax.transAxes,
                   fontsize=7, va='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

            # === COLUMN 4: Final formatted data (heatmap style) ===
            ax = fig.add_subplot(gs[unit_idx, 3])

            # Show as heatmap
            ax.imshow(firing_rates.reshape(1, -1), aspect='auto', cmap='hot',
                     extent=[time_window[0], time_window[1], 0, 1], interpolation='nearest')

            # Mark epochs
            ax.axvline(0, color='cyan', linestyle='--', linewidth=2)

            ax.set_xlim(time_window)
            ax.set_ylim(0, 1)
            ax.set_yticks([])
            if unit_idx == 0:
                ax.set_title('4. Final Format\n(standardized)', fontsize=10)
            if unit_idx == n_units_to_show - 1:
                ax.set_xlabel('Time from go cue (s)', fontsize=8)
            ax.text(0.02, 0.5, f'Shape: ({n_time_bins},)', transform=ax.transAxes,
                   fontsize=7, ha='left', va='center', color='white',
                   bbox=dict(boxstyle='round', facecolor='black', alpha=0.7))

        # === INPUT VARIABLES (2 dimensions) ===
        input_row_start = n_units_to_show

        # Input 0: Time from go cue
        ax = fig.add_subplot(gs[input_row_start, :])
        time_values = time_bins
        ax.plot(time_values, time_values, 'b-', linewidth=2, label='Time from go cue')
        ax.axhline(0, color='red', linestyle='--', linewidth=2, alpha=0.5, label='Go cue (t=0)')
        ax.axvspan(sample_start - go_cue_time, delay_start - go_cue_time, alpha=0.1, color='blue', label='Sample')
        ax.axvspan(delay_start - go_cue_time, 0, alpha=0.1, color='orange', label='Delay')
        ax.axvspan(0, time_window[1], alpha=0.1, color='green', label='Response')
        ax.set_xlim(time_window)
        ax.set_ylabel('Time (s)', fontsize=10)
        ax.set_title('INPUT 0: Time from Go Cue (continuous variable, same for all trials)',
                    fontsize=10, fontweight='bold', loc='left')
        ax.legend(loc='upper right', ncol=5, fontsize=7)
        ax.grid(True, alpha=0.3)
        ax.text(0.02, 0.95, 'Shape: (1, 80)\nRange: [-2.5, 1.45]s',
               transform=ax.transAxes, fontsize=8, va='top',
               bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

        # Input 1: Photostimulation status
        ax = fig.add_subplot(gs[input_row_start + 1, :])
        photostim_onset = trials['photostim_onset'][trial_idx]
        photostim_status = 0 if photostim_onset == 'N/A' else 1
        photostim_values = np.full(n_time_bins, photostim_status)

        if photostim_status == 1:
            # Show photostim period if present
            ax.fill_between(time_bins, 0, 1, where=(time_bins >= -0.5) & (time_bins <= 0),
                          color='purple', alpha=0.5, label='Photostim period')
            ax.axvline(0, color='red', linestyle='--', linewidth=2)
            status_text = 'ALM SILENCING TRIAL'
            color = 'purple'
        else:
            ax.fill_between(time_bins, 0, 1, color='gray', alpha=0.3, label='Control (no photostim)')
            status_text = 'CONTROL TRIAL'
            color = 'gray'

        ax.set_xlim(time_window)
        ax.set_ylim(-0.1, 1.1)
        ax.set_ylabel('Photostim', fontsize=10)
        ax.set_yticks([0, 1])
        ax.set_yticklabels(['Control', 'Photostim'])
        ax.set_title(f'INPUT 1: Photostimulation Status (binary variable, trial-specific) - {status_text}',
                    fontsize=10, fontweight='bold', loc='left', color=color)
        ax.grid(True, alpha=0.3, axis='x')
        ax.text(0.02, 0.95, f'Shape: (1, 80)\nValue: {photostim_status}',
               transform=ax.transAxes, fontsize=8, va='top',
               bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

        # === OUTPUT VARIABLES (3 dimensions, all scalar) ===
        output_row = n_units_to_show + 2

        ax = fig.add_subplot(gs[output_row, :])
        ax.axis('off')

        # Compute outputs (matching convert_map_data_fast.py logic)
        instruction = trials['trial_instruction'][trial_idx]
        outcome = trials['outcome'][trial_idx]
        early_lick = trials['early_lick'][trial_idx]

        # Determine lick direction
        if outcome == 'hit':
            lick_direction = instruction
        elif outcome == 'miss':
            lick_direction = 'right' if instruction == 'left' else 'left'
        else:
            lick_direction = 'none'

        # Map to class indices
        lick_mapping = {'left': 0, 'right': 1, 'none': 2}
        outcome_mapping = {'hit': 0, 'miss': 1, 'ignore': 2}
        early_lick_mapping = {'no early': 0, 'early': 1}

        lick_idx = lick_mapping[lick_direction]
        outcome_idx = outcome_mapping[outcome]
        early_idx = early_lick_mapping[early_lick]

        # Display as text in a more compact format
        output_text = f"""OUTPUT VARIABLES (scalar per trial) - Final shape: (3,) = [{lick_idx}, {outcome_idx}, {early_idx}]

  Output 0 - Lick Direction: {lick_idx} ({lick_direction})
    Computed: instruction='{instruction}' + outcome='{outcome}' → lick='{lick_direction}' → class={lick_idx}
    Logic: hit→instruction | miss→opposite | ignore→none  |  Classes: 0=left, 1=right, 2=none

  Output 1 - Outcome: {outcome_idx} ({outcome})
    Source: trials['outcome'][{trial_idx}] → class={outcome_idx}  |  Classes: 0=hit, 1=miss, 2=ignore

  Output 2 - Early Lick: {early_idx} ({early_lick})
    Source: trials['early_lick'][{trial_idx}] → class={early_idx}  |  Classes: 0=no early, 1=early"""

        ax.text(0.5, 0.5, output_text, transform=ax.transAxes,
               fontsize=9, va='center', ha='center', family='monospace',
               bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.95, pad=1.5))
        ax.set_title('OUTPUTS: Behavioral Variables to Decode (categorical, scalar per trial)',
                    fontsize=11, fontweight='bold', loc='center', pad=10)

        # Add overall title
        fig.suptitle(f'Complete Preprocessing Pipeline: Neural Data + Inputs + Outputs\n'
                    f'Session: {Path(nwb_path).stem} | Trial {trial_idx} | '
                    f'Instruction: {trial_instruction} | Outcome: {trial_outcome}',
                    fontsize=14, fontweight='bold', y=0.995)

        # Adjust layout without tight_layout (which conflicts with gridspec)
        plt.subplots_adjust(top=0.96, bottom=0.02, left=0.05, right=0.98)

        # Save figure
        output_name = f'preprocessing_demo_{Path(nwb_path).stem.split("_ses-")[1]}_trial{trial_idx}.png'
        fig.savefig(output_name, dpi=150, bbox_inches='tight')
        print(f"\nSaved: {output_name}")

        return fig

    finally:
        io.close()


def main():
    """Run preprocessing visualization on sample sessions."""
    import glob

    # Get a few example sessions
    nwb_files = sorted(glob.glob('data/sub-440956/*.nwb'))[:1]  # Just do one for demo

    if not nwb_files:
        print("No NWB files found in data/sub-440956/")
        return

    for nwb_file in nwb_files:
        # Show first trial that has good outcome
        io = NWBHDF5IO(nwb_file, 'r')
        nwbfile = io.read()

        # Find a trial with hit outcome
        outcomes = nwbfile.trials['outcome'][:]
        trial_idx = None
        for i, outcome in enumerate(outcomes[:50]):  # Check first 50 trials
            if outcome == 'hit':
                trial_idx = i
                break

        io.close()

        if trial_idx is None:
            print(f"No hit trials found in first 50 trials of {nwb_file}")
            continue

        print("\n" + "="*80)
        show_processing(nwb_file, trial_idx=trial_idx, n_units_to_show=8)
        print("="*80)


if __name__ == '__main__':
    main()
