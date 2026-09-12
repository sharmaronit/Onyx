"""
train_gnn.py — Training script for the GNN world model.

Pipeline:
  1. Generate 50K episodes from rule-based simulator (or load existing HDF5)
  2. Split 80/10/10 into train/val/test
  3. Train GraphSAGE with Adam + CosineAnnealingLR for 50 epochs
  4. Log AUC, accuracy, loss to TensorBoard
  5. Save best checkpoint by val AUC

Usage:
    python -m src.training.train_gnn \
        --topologies_dir data/topologies \
        --cve_path data/cve/cve_dataset.json \
        --output checkpoints/gnn_world_model.pt \
        --episodes 50000 \
        --epochs 50

Target: val AUC > 0.87
"""

from __future__ import annotations
import argparse
import os
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, random_split
from torch.utils.tensorboard import SummaryWriter
from sklearn.metrics import roc_auc_score, accuracy_score
from tqdm import tqdm

from src.simulator.episode_generator import generate_dataset, EpisodeDataset
from src.models.gnn_world_model import GNNWorldModel, GATWorldModel, GCNWorldModel


# ---------------------------------------------------------------------------
# Collate function: handle variable-sized graphs in a batch
# ---------------------------------------------------------------------------

def collate_fn(batch):
    """
    Batch items are (x, ct1, n, edge_index) where x is (n, 12), ct1 is (n,), edge_index is (2, E).
    We pad to max n in the batch.
    """
    xs, ct1s, ns, eis = zip(*batch)
    max_n = max(n for n in ns)

    x_batch = torch.zeros(len(batch), max_n, xs[0].shape[-1])
    ct1_batch = torch.zeros(len(batch), max_n)
    n_tensor = torch.tensor(ns, dtype=torch.long)

    for i, (x, ct1, n, _) in enumerate(zip(xs, ct1s, ns, eis)):
        x_batch[i, :n] = x
        ct1_batch[i, :n] = ct1

    return x_batch, ct1_batch, n_tensor, eis


# ---------------------------------------------------------------------------
# Training loop
# ---------------------------------------------------------------------------

def train_epoch(model, loader, optimizer, device):
    model.train()
    total_loss = 0.0
    n_batches = 0

    criterion = nn.BCELoss(reduction="none")

    for x_batch, ct1_batch, n_batch, ei_batch in loader:
        x_batch = x_batch.to(device)    # [B, max_n, 12]
        ct1_batch = ct1_batch.to(device)  # [B, max_n]

        optimizer.zero_grad()
        batch_loss = 0.0

        for b in range(x_batch.shape[0]):
            n = int(n_batch[b])
            x = x_batch[b, :n, :]         # [n, 12]
            target = ct1_batch[b, :n]      # [n]

            # Use actual edge_index from the topology
            edge_index = ei_batch[b].to(device)  # [2, E]

            pred = model(x, edge_index).squeeze(-1)   # [n]
            loss = criterion(pred, target).mean()
            batch_loss += loss

        batch_loss = batch_loss / x_batch.shape[0]
        batch_loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()

        total_loss += batch_loss.item()
        n_batches += 1

    return total_loss / max(n_batches, 1)


@torch.no_grad()
def eval_epoch(model, loader, device):
    model.eval()
    all_preds, all_targets = [], []
    total_loss = 0.0
    n_batches = 0
    criterion = nn.BCELoss()

    for x_batch, ct1_batch, n_batch, ei_batch in loader:
        x_batch = x_batch.to(device)
        ct1_batch = ct1_batch.to(device)

        for b in range(x_batch.shape[0]):
            n = int(n_batch[b])
            x = x_batch[b, :n, :]
            target = ct1_batch[b, :n]
            edge_index = ei_batch[b].to(device)

            pred = model(x, edge_index).squeeze(-1)
            loss = criterion(pred, target)
            total_loss += loss.item()
            n_batches += 1

            all_preds.extend(pred.cpu().numpy().tolist())
            all_targets.extend(target.cpu().numpy().tolist())

    all_preds = np.array(all_preds)
    all_targets = np.array(all_targets)

    # AUC (only if both classes present)
    if len(np.unique(all_targets)) > 1:
        auc = roc_auc_score(all_targets, all_preds)
    else:
        auc = 0.5

    acc = accuracy_score(all_targets, (all_preds > 0.5).astype(int))
    avg_loss = total_loss / max(n_batches, 1)

    return avg_loss, auc, acc


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(args):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    # ---- Generate or load dataset ----
    hdf5_path = Path(args.hdf5_cache)
    if args.regenerate or not hdf5_path.exists():
        print("Generating episode dataset...")
        stats = generate_dataset(
            topologies_dir=args.topologies_dir,
            cve_path=args.cve_path,
            output_path=str(hdf5_path),
            episodes_per_topology=args.episodes // 3,  # 3 topologies
            max_steps=50,
            seed=42,
            verbose=True,
        )
        print(f"Generated: {stats['total_transitions']:,} transitions")
    else:
        print(f"Loading cached dataset from {hdf5_path}")

    # ---- Dataset splits ----
    full_dataset = EpisodeDataset(str(hdf5_path))()
    n_total = len(full_dataset)
    n_train = int(0.80 * n_total)
    n_val = int(0.10 * n_total)
    n_test = n_total - n_train - n_val

    train_ds, val_ds, test_ds = random_split(
        full_dataset, [n_train, n_val, n_test],
        generator=torch.Generator().manual_seed(42)
    )
    print(f"Dataset splits: train={n_train:,}  val={n_val:,}  test={n_test:,}")

    train_loader = DataLoader(train_ds, batch_size=args.batch_size,
                              shuffle=True, collate_fn=collate_fn, num_workers=0, pin_memory=True)
    val_loader   = DataLoader(val_ds,   batch_size=args.batch_size,
                              shuffle=False, collate_fn=collate_fn, num_workers=0)
    test_loader  = DataLoader(test_ds,  batch_size=args.batch_size,
                              shuffle=False, collate_fn=collate_fn, num_workers=0)

    # ---- Model ----
    model_cls = {
        "sage": GNNWorldModel,
        "gat":  GATWorldModel,
        "gcn":  GCNWorldModel,
    }[args.arch]

    model = model_cls(hidden_channels=args.hidden_dim).to(device)
    n_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"Model: {args.arch.upper()}  params={n_params:,}")

    # ---- Optimizer + scheduler ----
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr, weight_decay=1e-5)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)

    # ---- TensorBoard ----
    log_dir = Path(args.log_dir) / args.arch
    writer = SummaryWriter(log_dir=str(log_dir))
    print(f"TensorBoard logs: {log_dir}")

    # ---- Training ----
    best_val_auc = 0.0
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    for epoch in range(1, args.epochs + 1):
        train_loss = train_epoch(model, train_loader, optimizer, device)
        val_loss, val_auc, val_acc = eval_epoch(model, val_loader, device)
        scheduler.step()

        writer.add_scalar("loss/train", train_loss, epoch)
        writer.add_scalar("loss/val",   val_loss,   epoch)
        writer.add_scalar("auc/val",    val_auc,    epoch)
        writer.add_scalar("acc/val",    val_acc,    epoch)
        writer.add_scalar("lr",         scheduler.get_last_lr()[0], epoch)

        if val_auc > best_val_auc:
            best_val_auc = val_auc
            torch.save(model.state_dict(), output_path)
            print(f"Epoch {epoch:3d}  train_loss={train_loss:.4f}  val_loss={val_loss:.4f}"
                  f"  val_auc={val_auc:.4f}  val_acc={val_acc:.4f}  *** SAVED ***")
        else:
            if epoch % 5 == 0:
                print(f"Epoch {epoch:3d}  train_loss={train_loss:.4f}  val_loss={val_loss:.4f}"
                      f"  val_auc={val_auc:.4f}  val_acc={val_acc:.4f}")

    # ---- Final test evaluation ----
    model.load_state_dict(torch.load(output_path, map_location=device, weights_only=True))
    test_loss, test_auc, test_acc = eval_epoch(model, test_loader, device)
    print(f"\nTest results: loss={test_loss:.4f}  AUC={test_auc:.4f}  ACC={test_acc:.4f}")
    print(f"Best val AUC: {best_val_auc:.4f}")

    if test_auc < 0.87:
        print("WARNING: Test AUC below target 0.87. Consider more data or longer training.")
    else:
        print("Target AUC 0.87 achieved.")

    writer.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train GNN World Model")
    parser.add_argument("--topologies_dir", default="data/topologies")
    parser.add_argument("--cve_path",       default="data/cve/cve_dataset.json")
    parser.add_argument("--hdf5_cache",     default="data/episodes/transitions.h5")
    parser.add_argument("--output",         default="checkpoints/gnn_world_model.pt")
    parser.add_argument("--log_dir",        default="logs/gnn")
    parser.add_argument("--arch",           default="sage", choices=["sage", "gat", "gcn"])
    parser.add_argument("--episodes",       default=50000, type=int)
    parser.add_argument("--epochs",         default=50,    type=int)
    parser.add_argument("--batch_size",     default=128,   type=int)
    parser.add_argument("--hidden_dim",     default=64,    type=int)
    parser.add_argument("--lr",             default=3e-4,  type=float)
    parser.add_argument("--regenerate",     action="store_true")
    args = parser.parse_args()
    main(args)
