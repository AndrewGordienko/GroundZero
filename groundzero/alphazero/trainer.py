import os
import sys
import glob
import time
import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import requests
import subprocess
from torch.utils.data import Dataset, DataLoader

# ==============================================================
# SMART PATH FIX
# ==============================================================
current_file = os.path.abspath(__file__)
# trainer.py (0) -> alphazero (1) -> groundzero (2) -> ROOT (3)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from groundzero.alphazero.algorithm.model import AlphaNet

class ChessDataset(Dataset):
    def __init__(self, buffer_path, max_samples=100000):
        self.buffer_path = os.path.abspath(buffer_path)
        self.max_samples = max_samples
        self.file_list = []
        self.states, self.pis, self.zs = [], [], []
        self.refresh_files()

    def refresh_files(self):
        if not os.path.exists(self.buffer_path):
            return
            
        all_files = sorted(glob.glob(os.path.join(self.buffer_path, "*.npz")), 
                          key=os.path.getmtime, reverse=True)
        
        self.file_list = all_files[:1000]
        temp_states, temp_pis, temp_zs = [], [], []
        total_samples = 0
        
        for f in self.file_list:
            try:
                with np.load(f) as data:
                    temp_states.append(data['states'])
                    temp_pis.append(data['pis'])
                    temp_zs.append(data['zs'])
                    total_samples += len(data['zs'])
                if total_samples >= self.max_samples: break
            except: continue
            
        if temp_states:
            self.states = np.concatenate(temp_states, axis=0)
            self.pis = np.concatenate(temp_pis, axis=0)
            self.zs = np.concatenate(temp_zs, axis=0)
        else:
            self.states, self.pis, self.zs = [], [], []

    def __len__(self):
        return len(self.zs) if len(self.zs) > 0 else 0

    def __getitem__(self, idx):
        return (
            torch.from_numpy(self.states[idx]).float(),
            torch.from_numpy(self.pis[idx]).float(),
            torch.tensor(self.zs[idx]).float()
        )

class AlphaTrainer:
    def __init__(self, model_path, buffer_path, device="cpu", dashboard_url="http://localhost:5005"):
        self.model_path = model_path
        self.buffer_path = buffer_path
        self.device = device
        self.dashboard_url = dashboard_url
        self.dataset = ChessDataset(self.buffer_path)
        
        self.model = AlphaNet(num_res_blocks=10, channels=128).to(self.device)
        if os.path.exists(self.model_path):
            print(f"[*] Reloading Weights: {os.path.basename(self.model_path)}")
            self.model.load_state_dict(torch.load(self.model_path, map_location=self.device, weights_only=True))
        
        self.optimizer = optim.AdamW(self.model.parameters(), lr=0.001, weight_decay=1e-4)
        self.mse_loss = nn.MSELoss()
        self.ce_loss = nn.CrossEntropyLoss()

    def report_metrics(self, p_loss, v_loss):
        try:
            payload = {
                "p_loss": float(p_loss),
                "v_loss": float(v_loss),
                "lr": self.optimizer.param_groups[0]['lr'],
                "buffer_size": len(self.dataset)
            }
            requests.post(f"{self.dashboard_url}/api/update", json=payload, timeout=0.5)
        except: pass 

    def train_step(self, batch_size=1024, epochs=3):
        self.dataset.refresh_files()
        current_samples = len(self.dataset)
        
        if current_samples < 2000:
            print(f" [!] Buffer: {current_samples}/2000 | Files: {len(self.dataset.file_list)} | Awaiting data...")
            return False

        loader = DataLoader(self.dataset, batch_size=batch_size, shuffle=True)
        print(f"\n ENGINE UPDATE | Samples: {current_samples}")
        self.model.train()

        for epoch in range(epochs):
            p_losses, v_losses = [], []
            for states, pis, zs in loader:
                states, pis, zs = states.to(self.device), pis.to(self.device), zs.to(self.device)
                self.optimizer.zero_grad()
                p_logits, v = self.model(states)
                loss_v = self.mse_loss(v.view(-1), zs)
                loss_p = self.ce_loss(p_logits, pis)
                (loss_v + loss_p).backward()
                self.optimizer.step()
                p_losses.append(loss_p.item()); v_losses.append(loss_v.item())

            print(f" > Epoch {epoch+1}/{epochs} | Policy: {np.mean(p_losses):.4f} | Value: {np.mean(v_losses):.4f}")
            self.report_metrics(np.mean(p_losses), np.mean(v_losses))
        
        torch.save(self.model.state_dict(), self.model_path)
        print(f"[*] Weights Synchronized.")
        return True

if __name__ == "__main__":
    # FIX: Adding 'groundzero' to the path to match your actual folder structure
    BUFFER_PATH = os.path.join(PROJECT_ROOT, "groundzero", "data", "replay_buffer")
    MODEL_PATH = os.path.join(PROJECT_ROOT, "groundzero", "models", "best_model.pth")
    
    DASHBOARD_SCRIPT = os.path.join(PROJECT_ROOT, "groundzero", "network_dashboard", "app.py")
    
    DEVICE = "mps" if torch.backends.mps.is_available() else "cpu"

    print(f"[*] Starting Trainer...")
    print(f"[*] Searching for samples in: {BUFFER_PATH}")

    dashboard_proc = subprocess.Popen([sys.executable, DASHBOARD_SCRIPT])

    try:
        trainer = AlphaTrainer(MODEL_PATH, BUFFER_PATH, DEVICE)
        while True:
            if trainer.train_step(): 
                time.sleep(30)
            else: 
                time.sleep(10)
    except KeyboardInterrupt:
        print("\n[!] Shutting down...")
        dashboard_proc.terminate()