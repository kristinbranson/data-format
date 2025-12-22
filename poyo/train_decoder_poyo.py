#!/usr/bin/env python3
"""
CaPOYO Neural Decoder Training Script using torch_brain utilities.

This script follows the torch_brain examples/poyo_plus/train.py pattern
for training a CaPOYO transformer-based decoder.

Usage:
    # Train from scratch
    python train_decoder_poyo.py <data_root> <config_yaml> [options]

    # Finetune from pretrained checkpoint
    python train_decoder_poyo.py <data_root> <config_yaml> --checkpoint <ckpt_path> [options]

    # Resume training (restores full state including epoch, optimizer, scheduler)
    python train_decoder_poyo.py <data_root> <config_yaml> --resume <ckpt_path> [options]

    # Resume with fresh scheduler (loads weights + epoch, reinitializes optimizer/scheduler)
    python train_decoder_poyo.py <data_root> <config_yaml> --resume <ckpt_path> --reset-scheduler [options]

    # Test-only: evaluate a checkpoint on test set
    python train_decoder_poyo.py <data_root> <config_yaml> --test-only <ckpt_path>

Examples:
    # Train from scratch
    python train_decoder_poyo.py ./hdf5_data ./hdf5_data/sosa2024_config.yaml --epochs 100

    # Finetune from pretrained checkpoint (freeze layers for 5 epochs)
    python train_decoder_poyo.py ./hdf5_data ./hdf5_data/sosa2024_config.yaml \\
        --checkpoint ./pretrained.ckpt --freeze-epochs 5 --epochs 50

    # Resume from epoch 17 checkpoint, train to epoch 35 with fresh scheduler
    # (trains 18 more epochs with scheduler configured for those 18 epochs)
    python train_decoder_poyo.py ./hdf5_data ./hdf5_data/sosa2024_config.yaml \\
        --resume ./lightning_logs/version_X/checkpoints/epoch=17-step=27558.ckpt \\
        --reset-scheduler --epochs 35 --lr-decay-start 0
"""

import argparse
import logging
from typing import List, Optional
from tqdm import tqdm

import numpy as np
import torch
import torch.nn as nn
import yaml
import lightning as L
from lightning.pytorch.callbacks import (
    LearningRateMonitor,
    ModelCheckpoint,
    ModelSummary,
)
from torch.utils.data import DataLoader
from collections import defaultdict

# torch_brain imports - following examples/poyo_plus/train.py
from torch_brain.data import Dataset, collate
from torch_brain.data.sampler import RandomFixedWindowSampler, SequentialFixedWindowSampler

# Import accuracy functions from decoder.py
from decoder import accuracy_all_sessions, f1scores_all_sessions
from torch_brain.models import CaPOYO
from torch_brain.optim import SparseLamb
from torch_brain.registry import (
    DataType,
    MODALITY_REGISTRY,
)
from torch_brain.transforms import Compose
import torch_brain

# Import Interval for creating sub-intervals
from temporaldata import Interval

# higher speed on machines with tensor cores
torch.set_float32_matmul_precision("medium")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GradualUnfreezing(L.Callback):
    """A Lightning callback to handle freezing and unfreezing of the model for finetuning.

    When enabled, most model weights are frozen initially. Only unit and session
    embeddings remain trainable. After reaching `unfreeze_at_epoch`, the entire
    model is unfrozen.

    Adapted from torch_brain/examples/poyo_plus/finetune.py
    """

    _has_been_frozen: bool = False
    frozen_params: Optional[List[nn.Parameter]] = None

    def __init__(self, unfreeze_at_epoch: int):
        self.enabled = unfreeze_at_epoch > 0
        self.unfreeze_at_epoch = unfreeze_at_epoch

    @classmethod
    def freeze(cls, model: CaPOYO) -> List[nn.Parameter]:
        """Freeze model weights except for unit and session embeddings."""
        layers_to_freeze = [
            model.enc_atn,
            model.enc_ffn,
            model.proc_layers,
            model.dec_atn,
            model.dec_ffn,
            model.readout,
            model.task_emb,
            model.input_value_map,  # for calcium value map
        ]

        frozen_params = []
        for layer in layers_to_freeze:
            for param in layer.parameters():
                if param.requires_grad:
                    param.requires_grad = False
                    frozen_params.append(param)

        return frozen_params

    def on_train_start(self, trainer, pl_module):
        if self.enabled:
            self.frozen_params = self.freeze(pl_module.model)
            self._has_been_frozen = True
            logger.info(
                f"Model frozen at epoch 0. Will unfreeze at epoch {self.unfreeze_at_epoch}."
            )

    def on_train_epoch_start(self, trainer, pl_module):
        if self.enabled and (trainer.current_epoch == self.unfreeze_at_epoch):
            if not self._has_been_frozen:
                raise RuntimeError("Model has not been frozen yet.")

            for param in self.frozen_params:
                param.requires_grad = True

            self.frozen_params = None
            logger.info(f"Model unfrozen at epoch {trainer.current_epoch}")


def load_model_from_ckpt(model: nn.Module, ckpt_path: str, return_epoch: bool = False):
    """Load pretrained weights from a Lightning checkpoint.

    Args:
        model: The model to load weights into
        ckpt_path: Path to Lightning checkpoint
        return_epoch: If True, also return the epoch number from checkpoint

    Returns:
        If return_epoch=True, returns the epoch number (int). Otherwise None.
    """
    ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=False)
    state_dict = ckpt["state_dict"]
    # Remove "model." prefix added by Lightning wrapper
    state_dict = {
        k.replace("model.", ""): v
        for k, v in state_dict.items()
        if k.startswith("model.")
    }
    model.load_state_dict(state_dict)
    logger.info(f"Loaded pretrained weights from {ckpt_path}")

    if return_epoch:
        epoch = ckpt.get("epoch", 0)
        logger.info(f"Checkpoint was at epoch {epoch}")
        return epoch
    return None


def register_output_modalities(config_yaml: str) -> None:
    """Register custom modalities from config YAML using torch_brain.register_modality().

    This follows the torch_brain pattern where modalities are registered globally
    and assigned sequential IDs (20+, after built-in modalities).
    """
    with open(config_yaml, 'r') as f:
        config = yaml.safe_load(f)

    readout_configs = config[0]['config']['multitask_readout']

    for rc in readout_configs:
        modality_name = rc['readout_id']
        num_classes = rc['metrics'][0]['metric']['num_classes']

        # Skip if already registered (e.g., built-in modalities)
        if modality_name in MODALITY_REGISTRY:
            logger.info(f"Modality {modality_name} already registered with ID {MODALITY_REGISTRY[modality_name].id}")
            continue

        # Register using torch_brain's register_modality (assigns ID automatically)
        modality_id = torch_brain.register_modality(
            modality_name,
            dim=num_classes,
            type=DataType.MULTINOMIAL,
            timestamp_key=rc['timestamp_key'],
            value_key=rc['value_key'],
            loss_fn=torch_brain.nn.loss.CrossEntropyLoss(),
        )
        logger.info(f"Registered {modality_name} with ID {modality_id}")

    # Register a dummy modality to work around torch_brain's off-by-one bug
    # (task_emb is sized to len(registry) but IDs are 1-indexed)
    if "_dummy" not in MODALITY_REGISTRY:
        torch_brain.register_modality(
            "_dummy",
            dim=1,
            type=DataType.MULTINOMIAL,
            timestamp_key="dummy",
            value_key="dummy",
            loss_fn=torch_brain.nn.loss.CrossEntropyLoss(),
        )


class TrainWrapper(L.LightningModule):
    """Lightning wrapper for CaPOYO training.

    This follows the pattern from torch_brain/examples/poyo_plus/train.py
    """

    def __init__(
        self,
        model: CaPOYO,
        base_lr: float = 1e-4,
        weight_decay: float = 1e-4,
        batch_size: int = 64,
        lr_decay_start: float = 0.2,
        starting_epoch: int = 0,
        balanced_loss: bool = False,
        class_weights: Optional[dict] = None,
    ):
        super().__init__()
        self.model = model
        self.base_lr = base_lr
        self.weight_decay = weight_decay
        self.batch_size = batch_size
        self.lr_decay_start = lr_decay_start
        self.starting_epoch = starting_epoch  # For reset-scheduler mode
        self.balanced_loss = balanced_loss
        self.class_weights = class_weights  # Dict: readout_id -> tensor of class weights

    def configure_optimizers(self):
        """Configure SparseLamb optimizer with OneCycleLR scheduler.

        Follows torch_brain/examples/poyo_plus/train.py:
        - Linear LR scaling rule: max_lr = base_lr * batch_size
        - Separate parameter groups for sparse embeddings vs other params
        - OneCycleLR scheduler with warmup and cosine decay
        """
        max_lr = self.base_lr * self.batch_size

        # Separate embedding parameters (sparse) from other parameters
        special_emb_params = (
            list(self.model.unit_emb.parameters())
            + list(self.model.session_emb.parameters())
            + list(self.model.readout.parameters())
        )

        remaining_params = [
            p
            for n, p in self.model.named_parameters()
            if "unit_emb" not in n and "session_emb" not in n and "readout" not in n
        ]

        optimizer = SparseLamb(
            [
                {"params": special_emb_params, "sparse": True},
                {"params": remaining_params},
            ],
            lr=max_lr,
            weight_decay=self.weight_decay,
        )

        # Calculate total_steps for full training schedule
        total_steps = self.trainer.estimated_stepping_batches
        steps_per_epoch = total_steps // self.trainer.max_epochs

        scheduler = torch.optim.lr_scheduler.OneCycleLR(
            optimizer,
            max_lr=max_lr,
            total_steps=total_steps,
            pct_start=self.lr_decay_start,
            anneal_strategy="cos",
            div_factor=1,
        )

        # For reset-scheduler mode: step scheduler forward to the appropriate position
        if self.starting_epoch > 0:
            target_step = self.starting_epoch * steps_per_epoch
            logger.info(f"Scheduler configured for {self.trainer.max_epochs} epochs, "
                       f"advancing to epoch {self.starting_epoch} (step {target_step}/{total_steps})")
            for _ in range(target_step):
                scheduler.step()

        return {
            "optimizer": optimizer,
            "lr_scheduler": {
                "scheduler": scheduler,
                "interval": "step",
            },
        }

    def training_step(self, batch, batch_idx):
        # Forward pass (same as torch_brain's TrainWrapper)
        output_values = self.model(**batch["model_inputs"], unpack_output=False)

        # Compute loss (same as torch_brain's TrainWrapper)
        target_values = batch["target_values"]
        target_weights = batch["target_weights"]
        loss = torch.tensor(0, device=self.device, dtype=torch.float32)
        taskwise_loss = {}

        for readout_id in output_values.keys():
            output = output_values[readout_id]
            target = target_values[readout_id]
            spec = self.model.readout.readout_specs[readout_id]

            weights = 1.0
            if readout_id in target_weights and target_weights[readout_id] is not None:
                weights = target_weights[readout_id]

            # Apply class-balanced weights if enabled
            if self.balanced_loss and self.class_weights is not None and readout_id in self.class_weights:
                # Get per-sample weights based on target class
                class_wts = self.class_weights[readout_id].to(self.device)
                sample_weights = class_wts[target.long()]
                # Combine with existing weights if any
                if isinstance(weights, torch.Tensor):
                    weights = weights * sample_weights
                else:
                    weights = sample_weights

            taskwise_loss[readout_id] = spec.loss_fn(output, target, weights)

            # Count sequences with this task (following torch_brain pattern)
            num_sequences_with_current_task = torch.any(
                batch["model_inputs"]["output_decoder_index"]
                == MODALITY_REGISTRY[readout_id].id,
                dim=1,
            ).sum()
            loss = loss + taskwise_loss[readout_id] * num_sequences_with_current_task

        batch_size = batch["model_inputs"]["input_unit_index"].shape[0]
        loss = loss / batch_size

        # Log losses
        self.log("train_loss", loss, prog_bar=True, batch_size=batch_size)
        self.log_dict({f"losses/{k}": v for k, v in taskwise_loss.items()}, batch_size=batch_size)

        # Log batch statistics (following example code)
        unit_index = batch["model_inputs"]["input_unit_index"].float()
        self.log("inputs/mean_unit_index", unit_index.mean())
        self.log("inputs/std_unit_index", unit_index.std())

        return loss

    def _eval_step(self, batch, prefix: str):
        """Shared evaluation logic for validation and test steps.

        Uses unpack_output=True to avoid padding mismatch issues in partial batches.
        """
        output_values_list = self.model(**batch["model_inputs"], unpack_output=True)

        batch_size = len(output_values_list)
        loss = torch.tensor(0, device=self.device, dtype=torch.float32)
        total_correct = 0
        total_samples = 0

        # Accumulate outputs per readout across all samples
        all_outputs = {}
        for sample_outputs in output_values_list:
            for readout_id, output in sample_outputs.items():
                if readout_id not in all_outputs:
                    all_outputs[readout_id] = []
                all_outputs[readout_id].append(output)

        target_values = batch["target_values"]
        target_weights = batch["target_weights"]

        for readout_id in all_outputs.keys():
            if readout_id not in target_values:
                continue

            output = torch.cat(all_outputs[readout_id], dim=0)
            target = target_values[readout_id]
            spec = self.model.readout.readout_specs[readout_id]

            weights = 1.0
            if readout_id in target_weights and target_weights[readout_id] is not None:
                weights = target_weights[readout_id]

            task_loss = spec.loss_fn(output, target, weights)
            loss = loss + task_loss

            if output.dim() > 1 and output.shape[-1] > 1:
                preds = output.argmax(dim=-1)
                correct = (preds == target).sum().item()
                total_correct += correct
                total_samples += target.numel()
                task_acc = correct / max(target.numel(), 1)
                self.log(f"{prefix}_acc/{readout_id}", task_acc, batch_size=target.numel(), prog_bar=False)

        self.log(f"{prefix}_loss", loss, prog_bar=(prefix == "val"), batch_size=batch_size)

        if total_samples > 0:
            overall_acc = total_correct / total_samples
            self.log(f"{prefix}_acc", overall_acc, prog_bar=(prefix == "val"), batch_size=batch_size)

    def validation_step(self, batch, batch_idx):
        self._eval_step(batch, "val")

    def test_step(self, batch, batch_idx):
        self._eval_step(batch, "test")


class DataModule(L.LightningDataModule):
    """Lightning DataModule for CaPOYO with train/val/test splits.

    Splits sessions into 60% train, 10% val, 30% test.
    """

    def __init__(
        self,
        data_root: str,
        config_yaml: str,
        model: CaPOYO,
        batch_size: int = 32,
        seed: int = 42,
        finetune: bool = False,
        resume_from_weights: bool = False,
        train_frac: float = 0.6,
        val_frac: float = 0.1,
        test_frac: float = 0.3,
        num_workers: int = 8,
        balanced_loss: bool = False,
    ):
        super().__init__()
        self.data_root = data_root
        self.config_yaml = config_yaml
        self.model = model
        self.batch_size = batch_size
        self.seed = seed
        self.finetune = finetune
        self.resume_from_weights = resume_from_weights  # True when reset-scheduler loads weights
        self.train_frac = train_frac
        self.val_frac = val_frac
        self.test_frac = test_frac
        self.num_workers = num_workers
        self.balanced_loss = balanced_loss
        self.class_weights = None  # Will be computed in setup() if balanced_loss=True
        self._is_setup = False

    def setup(self, stage=None):
        # Guard against double initialization (called manually + by Lightning)
        if self._is_setup:
            return
        self._is_setup = True

        # Create dataset with tokenizer transform
        self.dataset = Dataset(
            root=self.data_root,
            config=self.config_yaml,
            transform=Compose([self.model.tokenize]),
        )
        self.dataset.disable_data_leakage_check()

        # Get all sampling intervals (dict: session_id -> Interval)
        # Each Interval has arrays of trial start/end times (multi-valued)
        all_intervals = self.dataset.get_sampling_intervals()

        rng = np.random.RandomState(self.seed)

        self.train_intervals = {}
        self.val_intervals = {}
        self.test_intervals = {}

        total_train_trials = 0
        total_val_trials = 0
        total_test_trials = 0

        for session_id, interval in all_intervals.items():
            # Get trial boundaries from the multi-valued Interval
            trial_starts = np.asarray(interval.start)
            trial_ends = np.asarray(interval.end)
            n_trials = len(trial_starts)

            if n_trials < 3:
                # Session has too few trials, put all in train
                self.train_intervals[session_id] = interval
                total_train_trials += n_trials
                continue

            # Randomly assign entire trials to train/val/test splits
            trial_indices = list(range(n_trials))
            rng.shuffle(trial_indices)

            n_train = int(n_trials * self.train_frac)
            n_val = int(n_trials * self.val_frac)

            train_indices = sorted(trial_indices[:n_train])
            val_indices = sorted(trial_indices[n_train:n_train + n_val])
            test_indices = sorted(trial_indices[n_train + n_val:])

            # Create multi-valued Interval for each split (one interval per trial)
            if train_indices:
                self.train_intervals[session_id] = Interval(
                    start=trial_starts[train_indices],
                    end=trial_ends[train_indices]
                )
            if val_indices:
                self.val_intervals[session_id] = Interval(
                    start=trial_starts[val_indices],
                    end=trial_ends[val_indices]
                )
            if test_indices:
                self.test_intervals[session_id] = Interval(
                    start=trial_starts[test_indices],
                    end=trial_ends[test_indices]
                )

            total_train_trials += len(train_indices)
            total_val_trials += len(val_indices)
            total_test_trials += len(test_indices)

        logger.info(f"Sessions: {len(all_intervals)} total")
        logger.info(f"Split (random trials per session): {self.train_frac*100:.0f}% train, {self.val_frac*100:.0f}% val, {self.test_frac*100:.0f}% test")
        logger.info(f"Total trials: {total_train_trials} train, {total_val_trials} val, {total_test_trials} test")

        # Initialize model vocabularies using ALL units/sessions
        unit_ids = self.dataset.get_unit_ids()
        session_ids_all = self.dataset.get_session_ids()
        logger.info(f"Dataset: {len(unit_ids)} units, {len(session_ids_all)} sessions total")

        if self.finetune or self.resume_from_weights:
            # Vocab already initialized from loaded weights, extend/subset as needed
            self.model.unit_emb.extend_vocab(unit_ids, exist_ok=True)
            self.model.unit_emb.subset_vocab(unit_ids)
            self.model.session_emb.extend_vocab(session_ids_all, exist_ok=True)
            self.model.session_emb.subset_vocab(session_ids_all)
            mode = "finetuning" if self.finetune else "reset-scheduler resume"
            logger.info(f"Extended vocabulary for {mode}")
        else:
            self.model.unit_emb.initialize_vocab(unit_ids)
            self.model.session_emb.initialize_vocab(session_ids_all)

        # Compute class weights for balanced loss if enabled
        if self.balanced_loss:
            self.class_weights = self._compute_class_weights()

    def _compute_class_weights(self) -> dict:
        """Compute class weights from training data for balanced loss.

        Returns dict mapping readout_id -> tensor of class weights (normalized to sum to 1).
        """
        # Get readout configs from YAML
        with open(self.config_yaml, 'r') as f:
            config = yaml.safe_load(f)
        readout_configs = config[0]['config']['multitask_readout']

        # Initialize class counts for each readout
        class_counts = {}
        num_classes = {}
        for rc in readout_configs:
            readout_id = rc['readout_id']
            nc = rc['metrics'][0]['metric']['num_classes']
            num_classes[readout_id] = nc
            class_counts[readout_id] = np.zeros(nc, dtype=np.float64)

        # Iterate through training intervals to count class occurrences
        logger.info("Computing class weights from training data...")
        for session_id, interval in self.train_intervals.items():
            # Load session data
            session_data = self.dataset.get_recording_data(session_id)

            # Get trial boundaries
            trial_starts = np.asarray(interval.start)
            trial_ends = np.asarray(interval.end)

            for rc in readout_configs:
                readout_id = rc['readout_id']
                value_key = rc['value_key']  # e.g., 'outputs.speed'

                # Navigate to the value in session_data
                keys = value_key.split('.')
                values = session_data
                for k in keys:
                    values = getattr(values, k, None) if hasattr(values, k) else values.get(k, None)
                    if values is None:
                        break

                if values is None:
                    continue

                # Get timestamps for this output
                ts_key = rc['timestamp_key']  # e.g., 'outputs.timestamps'
                ts_keys = ts_key.split('.')
                timestamps = session_data
                for k in ts_keys:
                    timestamps = getattr(timestamps, k, None) if hasattr(timestamps, k) else timestamps.get(k, None)
                    if timestamps is None:
                        break

                if timestamps is None:
                    continue

                timestamps = np.asarray(timestamps)
                values = np.asarray(values)

                # Count occurrences within training intervals
                for t_start, t_end in zip(trial_starts, trial_ends):
                    mask = (timestamps >= t_start) & (timestamps < t_end)
                    trial_values = values[mask]
                    for c in range(num_classes[readout_id]):
                        class_counts[readout_id][c] += np.sum(trial_values == c)

        # Compute weights as inverse frequency, normalized to sum to 1
        class_weights = {}
        for readout_id, counts in class_counts.items():
            total = np.sum(counts)
            if total == 0:
                # No data, use uniform weights
                weights = np.ones(num_classes[readout_id]) / num_classes[readout_id]
            else:
                # Inverse frequency with smoothing
                weights = total / (num_classes[readout_id] * np.maximum(counts, 1))
                # Normalize to sum to 1
                weights = weights / np.sum(weights)
            class_weights[readout_id] = torch.tensor(weights, dtype=torch.float32)
            logger.info(f"  {readout_id}: {weights}")

        return class_weights

    def train_dataloader(self):
        sampler = RandomFixedWindowSampler(
            sampling_intervals=self.train_intervals,
            window_length=self.model.sequence_length,
            generator=torch.Generator().manual_seed(self.seed),
        )
        logger.info(f"Training on {len(sampler)} samples per epoch")

        return DataLoader(
            self.dataset,
            sampler=sampler,
            collate_fn=collate,
            batch_size=self.batch_size,
            num_workers=self.num_workers,
            drop_last=True,
            pin_memory=True,
            persistent_workers=True if self.num_workers > 0 else False,
            prefetch_factor=2 if self.num_workers > 0 else None,
        )

    def val_dataloader(self):
        sampler = RandomFixedWindowSampler(
            sampling_intervals=self.val_intervals,
            window_length=self.model.sequence_length,
            generator=torch.Generator().manual_seed(self.seed + 1),
        )
        logger.info(f"Validation on {len(sampler)} samples")

        return DataLoader(
            self.dataset,
            sampler=sampler,
            collate_fn=collate,
            batch_size=self.batch_size,
            num_workers=self.num_workers,
            drop_last=False,
            pin_memory=True,
            persistent_workers=True if self.num_workers > 0 else False,
            prefetch_factor=2 if self.num_workers > 0 else None,
        )

    def test_dataloader(self):
        sampler = RandomFixedWindowSampler(
            sampling_intervals=self.test_intervals,
            window_length=self.model.sequence_length,
            generator=torch.Generator().manual_seed(self.seed + 2),
        )
        logger.info(f"Test on {len(sampler)} samples")

        return DataLoader(
            self.dataset,
            sampler=sampler,
            collate_fn=collate,
            batch_size=self.batch_size,
            num_workers=self.num_workers,
            drop_last=False,
            pin_memory=True,
            persistent_workers=True if self.num_workers > 0 else False,
            prefetch_factor=2 if self.num_workers > 0 else None,
        )


def evaluate_full_trials(
    model: CaPOYO,
    dataset: Dataset,
    intervals: dict,
    readout_ids: List[str],
    config_yaml: str,
    device: torch.device,
    window_length: float = 1.0,
    batch_size: int = 32,
) -> tuple:
    """Evaluate model on full trials and convert to decoder.py format.

    Args:
        model: Trained CaPOYO model
        dataset: torch_brain Dataset
        intervals: Dict mapping session_id -> Interval with trial boundaries
        readout_ids: List of readout IDs (output names)
        config_yaml: Path to config YAML (for getting output info)
        device: Device to run inference on
        window_length: Window length for sequential sampling
        batch_size: Batch size for inference

    Returns:
        predictions: List of sessions, each is list of trials, each is (doutput, T) array
        outputs: Same format for ground truth
        readout_ids: List of readout names (output_names for decoder.py)
    """
    model.to(device)
    model.eval()

    # Get readout configs for output ordering
    with open(config_yaml, 'r') as f:
        config = yaml.safe_load(f)
    readout_configs = config[0]['config']['multitask_readout']

    # Build ordered list of readout_ids and their info
    readout_info = []
    for rc in readout_configs:
        readout_info.append({
            'readout_id': rc['readout_id'],
            'value_key': rc['value_key'],
            'timestamp_key': rc['timestamp_key'],
            'num_classes': rc['metrics'][0]['metric']['num_classes'],
        })

    doutput = len(readout_info)
    ordered_readout_ids = [ri['readout_id'] for ri in readout_info]

    # Create sequential sampler for deterministic full coverage
    sampler = SequentialFixedWindowSampler(
        sampling_intervals=intervals,
        window_length=window_length,
        step=window_length,  # Non-overlapping
        drop_short=True,  # Skip trials shorter than window
    )

    dataloader = DataLoader(
        dataset,
        sampler=sampler,
        collate_fn=collate,
        batch_size=batch_size,
        num_workers=0,  # Use single worker for deterministic order
        drop_last=False,
    )

    # Collect predictions and targets per session per trial
    # Structure: session_predictions[session_id][trial_idx] = {readout_id: [(timestamps, preds), ...]}
    session_predictions = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    session_targets = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

    # Track trial boundaries for each session
    # intervals[session_id] has .start and .end arrays
    session_trial_boundaries = {}
    for session_id, interval in intervals.items():
        starts = np.asarray(interval.start)
        ends = np.asarray(interval.end)
        session_trial_boundaries[session_id] = list(zip(starts, ends))

    logger.info(f"Running full trial evaluation on {len(sampler)} windows...")

    # Collect window metadata from sampler (session_id, start, end) in order
    window_metadata = list(sampler)

    # Reset sampler for dataloader iteration
    sampler = SequentialFixedWindowSampler(
        sampling_intervals=intervals,
        window_length=window_length,
        step=window_length,
        drop_short=True,
    )
    dataloader = DataLoader(
        dataset,
        sampler=sampler,
        collate_fn=collate,
        batch_size=batch_size,
        num_workers=0,
        drop_last=False,
    )

    window_idx = 0
    n_batches = (len(window_metadata) + batch_size - 1) // batch_size
    with torch.no_grad():
        for batch_idx, batch in enumerate(tqdm(dataloader, total=n_batches, desc="Evaluating")):
            # Move batch to device
            model_inputs = {k: v.to(device) if isinstance(v, torch.Tensor) else v
                          for k, v in batch["model_inputs"].items()}

            # Forward pass
            output_values_list = model(**model_inputs, unpack_output=True)

            # Process each sample in the batch
            for sample_idx, sample_outputs in enumerate(output_values_list):
                if window_idx >= len(window_metadata):
                    break

                idx = window_metadata[window_idx]
                session_id, start_time, end_time = idx.recording_id, idx.start, idx.end
                window_idx += 1

                # Find which trial this window belongs to
                trial_idx = None
                for t_idx, (t_start, t_end) in enumerate(session_trial_boundaries.get(session_id, [])):
                    if t_start <= start_time < t_end:
                        trial_idx = t_idx
                        break

                if trial_idx is None:
                    continue

                # Collect predictions for each readout
                for readout_id in ordered_readout_ids:
                    if readout_id in sample_outputs:
                        preds = sample_outputs[readout_id].cpu().numpy()
                        pred_classes = preds.argmax(axis=-1)  # Convert logits to class predictions
                        session_predictions[session_id][trial_idx][readout_id].append(pred_classes)

    # Get ground truth by iterating through sessions/trials directly
    logger.info("Collecting ground truth outputs...")
    for session_id, trial_bounds in session_trial_boundaries.items():
        session_data = dataset.get_recording_data(session_id)

        for trial_idx, (t_start, t_end) in enumerate(trial_bounds):
            for ri in readout_info:
                readout_id = ri['readout_id']
                value_key = ri['value_key']
                ts_key = ri['timestamp_key']

                # Get timestamps
                ts_keys = ts_key.split('.')
                timestamps = session_data
                for k in ts_keys:
                    timestamps = getattr(timestamps, k, None) if hasattr(timestamps, k) else timestamps.get(k, None)
                    if timestamps is None:
                        break
                if timestamps is None:
                    continue
                timestamps = np.asarray(timestamps)

                # Get values
                keys = value_key.split('.')
                values = session_data
                for k in keys:
                    values = getattr(values, k, None) if hasattr(values, k) else values.get(k, None)
                    if values is None:
                        break
                if values is None:
                    continue
                values = np.asarray(values)

                # Filter to trial time range
                mask = (timestamps >= t_start) & (timestamps < t_end)
                trial_values = values[mask]
                session_targets[session_id][trial_idx][readout_id] = trial_values

    # Convert to decoder.py format: list of sessions, each is list of trials, each is (doutput, T)
    # First, get ordered session list
    session_ids_ordered = sorted(session_predictions.keys())

    predictions_decoder = []
    outputs_decoder = []

    for session_id in session_ids_ordered:
        n_trials = len(session_trial_boundaries[session_id])
        session_preds = []
        session_outs = []

        for trial_idx in range(n_trials):
            # Stack predictions from all windows for this trial
            trial_pred_arrays = []
            trial_out_arrays = []

            for readout_id in ordered_readout_ids:
                # Concatenate predictions from all windows
                if session_predictions[session_id][trial_idx][readout_id]:
                    pred_concat = np.concatenate(session_predictions[session_id][trial_idx][readout_id])
                else:
                    pred_concat = np.array([])

                # Get ground truth
                if readout_id in session_targets[session_id][trial_idx]:
                    out_concat = session_targets[session_id][trial_idx][readout_id]
                else:
                    out_concat = np.array([])

                trial_pred_arrays.append(pred_concat)
                trial_out_arrays.append(out_concat)

            # Find minimum length (in case of slight misalignment)
            if trial_pred_arrays and len(trial_pred_arrays[0]) > 0:
                min_len = min(len(p) for p in trial_pred_arrays if len(p) > 0)
                min_len = min(min_len, min(len(o) for o in trial_out_arrays if len(o) > 0))

                # Truncate and stack into (doutput, T)
                trial_preds_stacked = np.stack([p[:min_len] for p in trial_pred_arrays], axis=0)
                trial_outs_stacked = np.stack([o[:min_len] for o in trial_out_arrays], axis=0)
            else:
                # Empty trial
                trial_preds_stacked = np.zeros((doutput, 0))
                trial_outs_stacked = np.zeros((doutput, 0))

            session_preds.append(trial_preds_stacked)
            session_outs.append(trial_outs_stacked)

        predictions_decoder.append(session_preds)
        outputs_decoder.append(session_outs)

    return predictions_decoder, outputs_decoder, ordered_readout_ids

def main():
    parser = argparse.ArgumentParser(description="Train CaPOYO decoder")
    parser.add_argument("data_root", help="Root directory with HDF5 files")
    parser.add_argument("config_yaml", help="Path to dataset config YAML")
    # Paper defaults from POYO+ (Azabou et al. ICLR 2025)
    # Note: paper used batch_size=4800 with 8 H100s; scale down for single GPU
    parser.add_argument("--epochs", type=int, default=300,
                        help="Paper: 300 epochs")
    parser.add_argument("--batch-size", type=int, default=64,
                        help="Paper: 4800 global (600/GPU with 8 H100s)")
    parser.add_argument("--base-lr", type=float, default=3.125e-5,
                        help="Base learning rate (scaled by batch_size: max_lr = base_lr * batch_size)")
    parser.add_argument("--lr-decay-start", type=float, default=0.5,
                        help="Fraction of training before LR decay starts (config default: 0.5)")
    parser.add_argument("--sequence-length", type=float, default=1.0)
    parser.add_argument("--latent-step", type=float, default=0.125,
                        help="Paper: 128 total latents / 1.0s = 8 steps")
    parser.add_argument("--num-latents", type=int, default=16,
                        help="Latents per step (16 * 8 steps = 128 total, matching paper)")
    parser.add_argument("--dim", type=int, default=128,
                        help="Paper: 128")
    parser.add_argument("--depth", type=int, default=8,
                        help="Paper: 8 blocks (2 cross-atn + 6 self-atn)")
    parser.add_argument("--dim-head", type=int, default=64)
    parser.add_argument("--cross-heads", type=int, default=2,
                        help="Paper: 2 heads for cross-attention")
    parser.add_argument("--self-heads", type=int, default=8,
                        help="Paper: 8 heads for self-attention")
    parser.add_argument("--ffn-dropout", type=float, default=0.2,
                        help="Paper: 0.2")
    parser.add_argument("--lin-dropout", type=float, default=0.4,
                        help="Linear layer dropout (config default: 0.4)")
    parser.add_argument("--atn-dropout", type=float, default=0.2,
                        help="Paper: 0.2")
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--val-every", type=int, default=5,
                        help="Run validation every N epochs")
    parser.add_argument("--num-workers", type=int, default=8,
                        help="Number of DataLoader workers")
    parser.add_argument("--precision", type=str, default="32",
                        choices=["16", "bf16", "32"],
                        help="Training precision (16=fp16, bf16=bfloat16, 32=fp32)")
    parser.add_argument("--cpu", action="store_true")
    parser.add_argument("--seed", type=int, default=42)
    # Finetuning arguments
    parser.add_argument("--checkpoint", type=str, default=None,
                        help="Path to pretrained checkpoint for finetuning")
    parser.add_argument("--freeze-epochs", type=int, default=5,
                        help="Number of epochs to freeze most layers (only train embeddings)")
    parser.add_argument("--resume", type=str, default=None,
                        help="Path to checkpoint to resume training from (restores full state)")
    parser.add_argument("--reset-scheduler", action="store_true",
                        help="When resuming, reinitialize optimizer/scheduler for remaining epochs "
                             "(loads model weights + epoch number, fresh optimizer/scheduler)")
    parser.add_argument("--test-only", type=str, default=None,
                        help="Path to checkpoint for test evaluation only (no training)")
    parser.add_argument("--balanced-loss", action="store_true",
                        help="Use class-balanced loss (inverse frequency weighting)")
    args = parser.parse_args()

    finetune = args.checkpoint is not None

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    # Register custom modalities (adds to global MODALITY_REGISTRY with IDs 20+)
    logger.info("Registering output modalities...")
    register_output_modalities(args.config_yaml)
    logger.info(f"Total modalities in registry: {len(MODALITY_REGISTRY)}")

    # Create model with full MODALITY_REGISTRY
    # This ensures task_emb is large enough for all modality IDs
    logger.info("Creating CaPOYO model...")
    model = CaPOYO(
        sequence_length=args.sequence_length,
        readout_specs=MODALITY_REGISTRY,  # Pass full registry
        latent_step=args.latent_step,
        num_latents_per_step=args.num_latents,
        dim=args.dim,
        depth=args.depth,
        dim_head=args.dim_head,
        cross_heads=args.cross_heads,
        self_heads=args.self_heads,
        ffn_dropout=args.ffn_dropout,
        lin_dropout=args.lin_dropout,
        atn_dropout=args.atn_dropout,
    )

    # Load pretrained weights if finetuning
    if finetune:
        load_model_from_ckpt(model, args.checkpoint)

    # Load checkpoint for test-only mode (must be before setup for vocab handling)
    if args.test_only:
        logger.info(f"Test-only mode: loading checkpoint from {args.test_only}")
        load_model_from_ckpt(model, args.test_only)

    # Check if we'll be loading weights (for vocab handling in DataModule)
    resume_from_weights = (args.resume is not None and args.reset_scheduler) or (args.test_only is not None)

    # Create DataModule first (need to call setup to compute class weights if balanced_loss)
    data_module = DataModule(
        data_root=args.data_root,
        config_yaml=args.config_yaml,
        model=model,
        batch_size=args.batch_size,
        seed=args.seed,
        finetune=finetune,
        resume_from_weights=resume_from_weights,
        num_workers=args.num_workers,
        balanced_loss=args.balanced_loss,
    )

    # Call setup manually to compute class weights before creating TrainWrapper
    data_module.setup()

    # Create Lightning wrapper with class weights if balanced loss is enabled
    wrapper = TrainWrapper(
        model=model,
        base_lr=args.base_lr,
        weight_decay=args.weight_decay,
        batch_size=args.batch_size,
        lr_decay_start=args.lr_decay_start,
        balanced_loss=args.balanced_loss,
        class_weights=data_module.class_weights,
    )

    # Setup callbacks (following example code)
    callbacks = [
        LearningRateMonitor(logging_interval="step"),
        ModelSummary(max_depth=2),  # Display parameter count
        ModelCheckpoint(
            save_last=True,
            monitor="val_loss",
            mode="min",
            save_on_train_epoch_end=False,
            every_n_epochs=args.val_every,
        ),
    ]
    if finetune:
        callbacks.append(GradualUnfreezing(unfreeze_at_epoch=args.freeze_epochs))
        logger.info(f"Finetuning mode: will freeze layers for {args.freeze_epochs} epochs")

    # Create trainer
    trainer = L.Trainer(
        max_epochs=args.epochs,
        accelerator="cpu" if args.cpu else "auto",
        devices=1,
        precision=args.precision,
        log_every_n_steps=1,  # Match example code
        check_val_every_n_epoch=args.val_every,
        enable_checkpointing=True,
        logger=True,
        callbacks=callbacks,
    )

    # Handle test-only mode vs training mode
    if not args.test_only:
        
        resume_ckpt_path = args.resume
        starting_epoch = 0

        if args.resume and args.reset_scheduler:

            # Handle resume with reset-scheduler: load model weights and epoch, fresh optimizer/scheduler

            logger.info(f"Loading model weights from {args.resume} (reset-scheduler mode)")
            checkpoint_epoch = load_model_from_ckpt(model, args.resume, return_epoch=True)
            starting_epoch = checkpoint_epoch + 1  # Resume from next epoch
            remaining_epochs = args.epochs - starting_epoch
            if remaining_epochs <= 0:
                raise ValueError(
                    f"Checkpoint is at epoch {checkpoint_epoch}, but --epochs is {args.epochs}. "
                    f"Need --epochs > {checkpoint_epoch} to continue training."
                )
            logger.info(f"Will train from epoch {starting_epoch} to {args.epochs - 1} ({remaining_epochs} epochs)")
            logger.info(f"Optimizer/scheduler reinitialized, scheduler starts at epoch {starting_epoch}")
            resume_ckpt_path = None  # Don't pass to trainer.fit, we'll set epoch manually

            # Update wrapper with starting_epoch for scheduler calculation
            wrapper.starting_epoch = starting_epoch

        # Train
        if finetune:
            mode = "finetuning"
        elif args.resume and args.reset_scheduler:
            mode = "resuming with reset scheduler"
        else:
            mode = "training from scratch"
        max_lr = args.base_lr * args.batch_size
        logger.info(f"Optimizer: SparseLamb with OneCycleLR scheduler")
        logger.info(f"LR config: base_lr={args.base_lr}, batch_size={args.batch_size}, max_lr={max_lr}")
        logger.info(f"LR warmup: {args.lr_decay_start*100:.0f}% of training, then cosine decay")
        logger.info(f"Precision: {args.precision}")
        if args.balanced_loss:
            logger.info(f"Balanced loss: enabled (inverse frequency class weighting)")
        logger.info(f"Starting {mode} for {args.epochs} epochs...")
        logger.info(f"Validation every {args.val_every} epochs")
        if resume_ckpt_path:
            logger.info(f"Resuming full state from checkpoint: {resume_ckpt_path}")

        # Set starting epoch for reset-scheduler mode
        if args.resume and args.reset_scheduler:
            trainer.fit_loop.epoch_progress.current.completed = starting_epoch
            trainer.fit_loop.epoch_progress.current.processed = starting_epoch

        trainer.fit(wrapper, data_module, ckpt_path=resume_ckpt_path)
        logger.info("Training complete!")

    # # Run final test evaluation (Lightning's built-in)
    # logger.info("Running test evaluation...")
    # test_results = trainer.test(wrapper, data_module)
    # logger.info(f"Test results: {test_results}")

    # Run full trial evaluation with decoder.py format for balanced accuracy
    logger.info("\n" + "="*60)
    logger.info("Running full trial evaluation (decoder.py format)...")
    device = torch.device("cuda" if torch.cuda.is_available() and not args.cpu else "cpu")

    # Evaluate on test set
    test_predictions, test_outputs, output_names = evaluate_full_trials(
        model=model,
        dataset=data_module.dataset,
        intervals=data_module.test_intervals,
        readout_ids=list(MODALITY_REGISTRY.keys()),
        config_yaml=args.config_yaml,
        device=device,
        window_length=args.sequence_length,
        batch_size=args.batch_size,
    )

    test_balanced_accuracy = accuracy_all_sessions(test_predictions, test_outputs, balanced=True)

    # Also evaluate on training set
    logger.info("Evaluating on training set...")
    train_predictions, train_outputs, _ = evaluate_full_trials(
        model=model,
        dataset=data_module.dataset,
        intervals=data_module.train_intervals,
        readout_ids=list(MODALITY_REGISTRY.keys()),
        config_yaml=args.config_yaml,
        device=device,
        window_length=args.sequence_length,
        batch_size=args.batch_size,
    )
    
    train_balanced_accuracy = accuracy_all_sessions(train_predictions, train_outputs, balanced=True)

    # Get num_classes for each output dimension
    num_classes = []
    for readout_id in output_names:
        spec = MODALITY_REGISTRY[readout_id]
        num_classes.append(spec.dim)

    logger.info("\nTraining Balanced Accuracy Scores (chance = 1/num_classes):")
    for out_dim, name in enumerate(output_names):
        logger.info(f"  {out_dim} ({name}): {train_balanced_accuracy[out_dim]:.4f}  (chance: {1.0 / num_classes[out_dim]:.4f})")

    logger.info("\nTest Balanced Accuracy Scores (chance = 1/num_classes):")
    for out_dim, name in enumerate(output_names):
        logger.info(f"  {out_dim} ({name}): {test_balanced_accuracy[out_dim]:.4f}  (chance: {1.0 / num_classes[out_dim]:.4f})")

    logger.info("="*60)

if __name__ == "__main__":
    main()

"""
Balanced:

lightning_logs/version_62/

Training Balanced Accuracy Scores (chance = 1/num_classes):
INFO:__main__:  0 (output_dist_to_reward_zone): 0.3440  (chance: 0.1429)
INFO:__main__:  1 (output_absolute_position): 0.4307  (chance: 0.2000)
INFO:__main__:  2 (output_speed): 0.4528  (chance: 0.2000)
INFO:__main__:  3 (output_lick): 0.6246  (chance: 0.5000)
INFO:__main__:  4 (output_reward_zone): 0.8646  (chance: 0.3333)
INFO:__main__:  5 (output_reward_outcome): 0.6597  (chance: 0.5000)
INFO:__main__:
Test Balanced Accuracy Scores (chance = 1/num_classes):
INFO:__main__:  0 (output_dist_to_reward_zone): 0.2889  (chance: 0.1429)
INFO:__main__:  1 (output_absolute_position): 0.3939  (chance: 0.2000)
INFO:__main__:  2 (output_speed): 0.4111  (chance: 0.2000)
INFO:__main__:  3 (output_lick): 0.5986  (chance: 0.5000)
INFO:__main__:  4 (output_reward_zone): 0.8296  (chance: 0.3333)
INFO:__main__:  5 (output_reward_outcome): 0.5476  (chance: 0.5000)
INFO:__main__:============================================================



Not balanced:

Test results on sosa2024_config.yaml after 36 epochs of training from scratch

Training Balanced Accuracy Scores (chance = 1/num_classes):
INFO:__main__:  0 (output_dist_to_reward_zone): 0.2688  (chance: 0.1429)
INFO:__main__:  1 (output_absolute_position): 0.4022  (chance: 0.2000)
INFO:__main__:  2 (output_speed): 0.3863  (chance: 0.2000)
INFO:__main__:  3 (output_lick): 0.5000  (chance: 0.5000)
INFO:__main__:  4 (output_reward_zone): 0.8532  (chance: 0.3333)
INFO:__main__:  5 (output_reward_outcome): 0.5156  (chance: 0.5000)
INFO:__main__:
Test Balanced Accuracy Scores (chance = 1/num_classes):
INFO:__main__:  0 (output_dist_to_reward_zone): 0.2482  (chance: 0.1429)
INFO:__main__:  1 (output_absolute_position): 0.3875  (chance: 0.2000)
INFO:__main__:  2 (output_speed): 0.3651  (chance: 0.2000)
INFO:__main__:  3 (output_lick): 0.5000  (chance: 0.5000)
INFO:__main__:  4 (output_reward_zone): 0.8220  (chance: 0.3333)
INFO:__main__:  5 (output_reward_outcome): 0.4963  (chance: 0.5000)
INFO:__main__:============================================================

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃             Test metric             ┃            DataLoader 0             ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│              test_acc               │         0.6359245181083679          │
│  test_acc/output_absolute_position  │         0.4014490246772766          │
│ test_acc/output_dist_to_reward_zone │         0.40656641125679016         │
│        test_acc/output_lick         │         0.8487386703491211          │
│   test_acc/output_reward_outcome    │         0.8389236330986023          │
│     test_acc/output_reward_zone     │         0.8342021107673645          │
│        test_acc/output_speed        │         0.4856613874435425          │
│              test_loss              │          5.572466850280762          │
└─────────────────────────────────────┴─────────────────────────────────────┘
Testing ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 762/762 0:01:20 • 0:00:00 9.40it/s  
INFO:__main__:Test results: [{'test_acc/output_dist_to_reward_zone': 0.40656641125679016, 'test_acc/output_absolute_position': 0.4014490246772766, 'test_acc/output_speed': 0.4856613874435425, 'test_acc/output_lick': 0.8487386703491211, 'test_acc/output_reward_zone': 0.8342021107673645, 'test_acc/output_reward_outcome': 0.8389236330986023, 'test_loss': 5.572466850280762, 'test_acc': 0.6359245181083679}]

Val best, 20 epochs
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃             Test metric             ┃            DataLoader 0             ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│              test_acc               │          0.628080427646637          │
│  test_acc/output_absolute_position  │          0.393827885389328          │
│ test_acc/output_dist_to_reward_zone │         0.3936888575553894          │
│        test_acc/output_lick         │         0.8488591313362122          │
│   test_acc/output_reward_outcome    │         0.8401920199394226          │
│     test_acc/output_reward_zone     │         0.8229570984840393          │
│        test_acc/output_speed        │         0.4689388871192932          │
│              test_loss              │          5.502614974975586          │
└─────────────────────────────────────┴─────────────────────────────────────┘
Testing ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 762/762 0:01:29 • 0:00:00 8.77it/s  
INFO:__main__:Test results: [{'test_acc/output_dist_to_reward_zone': 0.3936888575553894, 'test_acc/output_absolute_position': 0.393827885389328, 'test_acc/output_speed': 0.4689388871192932, 'test_acc/output_lick': 0.8488591313362122, 'test_acc/output_reward_zone': 0.8229570984840393, 'test_acc/output_reward_outcome': 0.8401920199394226, 'test_loss': 5.502614974975586, 'test_acc': 0.628080427646637}]

After 70 something epochs without reducing the LR
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃             Test metric             ┃            DataLoader 0             ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│              test_acc               │         0.6259605884552002          │
│  test_acc/output_absolute_position  │         0.38903093338012695         │
│ test_acc/output_dist_to_reward_zone │         0.3909017741680145          │
│        test_acc/output_lick         │         0.8488591313362122          │
│   test_acc/output_reward_outcome    │         0.8457582592964172          │
│     test_acc/output_reward_zone     │         0.8156762719154358          │
│        test_acc/output_speed        │         0.4655281901359558          │
│              test_loss              │          5.507855415344238          │
└─────────────────────────────────────┴─────────────────────────────────────┘
Testing ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 762/762 0:01:24 • 0:00:00 9.03it/s  
INFO:__main__:Test results: [{'test_acc/output_dist_to_reward_zone': 0.3909017741680145, 'test_acc/output_absolute_position': 0.38903093338012695, 'test_acc/output_speed': 0.4655281901359558, 'test_acc/output_lick': 0.8488591313362122, 'test_acc/output_reward_zone': 0.8156762719154358, 'test_acc/output_reward_outcome': 0.8457582592964172, 'test_loss': 5.507855415344238, 'test_acc': 0.6259605884552002}]
"""