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
import logging
from torch.utils.data import Dataset, DataLoader

# ==============================================================
# 1. SILENCE EXTERNAL NOISE
# ==============================================================
logging.getLogger('werkzeug').disabled = True
logging.getLogger('requests').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)

# --- Path Fix ---
current_file = os.path.abspath(__file__)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from groundzero.alphazero.algorithm.model import AlphaNet

class ChessDataset(Dataset):
    def __init__(self, buffer_path, max_samples=100000):
        self.buffer_path = os.path.abspath(buffer_path)
        self.max_samples = max_samples
        self.states, self.pis, self.zs = [], [], []
        self.refresh_files()

    def refresh_files(self):
        if not os.path.exists(self.buffer_path): return
        all_files = sorted(glob.glob(os.path.join(self.buffer_path, "*.npz")), 
                          key=os.path.getmtime, reverse=True)
        self.file_list = all_files[:1000]
        t_s, t_p, t_z = [], [], []
        total = 0
        for f in self.file_list:
            try:
                with np.load(f) as data:
                    t_s.append(data['states']); t_p.append(data['pis']); t_z.append(data['zs'])
                    total += len(data['zs'])
                if total >= self.max_samples: break
            except: continue
        if t_s:
            self.states = np.concatenate(t_s)
            self.pis = np.concatenate(t_p)
            self.zs = np.concatenate(t_z)
        else:
            self.states, self.pis, self.zs = [], [], []

    def __len__(self): return len(self.zs) if len(self.zs) > 0 else 0
    def __getitem__(self, idx):
        return torch.from_numpy(self.states[idx]).float(), \
               torch.from_numpy(self.pis[idx]).float(), \
               torch.tensor(self.zs[idx]).float()

class AlphaTrainer:
    def __init__(self, model_path, buffer_path, device="cpu", dashboard_url="http://localhost:5005"):
        self.model_path, self.buffer_path = model_path, buffer_path
        self.device, self.dashboard_url = device, dashboard_url
        self.dataset = ChessDataset(self.buffer_path)
        
        self.model = AlphaNet(num_res_blocks=10, channels=128).to(self.device)
        if os.path.exists(self.model_path):
            self.model.load_state_dict(torch.load(self.model_path, map_location=self.device, weights_only=True))
        
        # AdamW with specific weight decay helps prevent the "Zero Value Loss" lazy learning
        self.optimizer = optim.AdamW(self.model.parameters(), lr=0.001, weight_decay=1e-4)
        self.mse_loss, self.ce_loss = nn.MSELoss(), nn.CrossEntropyLoss()

    def train_step(self, batch_size=512, epochs=3):
        self.dataset.refresh_files()
        if len(self.dataset) < 2000:
            print(f"\r [!] Buffer: {len(self.dataset)}/2000 | Awaiting data...", end="")
            return False

        loader = DataLoader(self.dataset, batch_size=batch_size, shuffle=True)
        print(f"\n{'-'*60}\n ENGINE UPDATE | Samples: {len(self.dataset)} | Device: {self.device}\n{'-'*60}")
        
        self.model.train()
        for epoch in range(epochs):
            p_ls, v_ls = [], []
            t0 = time.time()
            for i, (s, p, z) in enumerate(loader):
                s, p, z = s.to(self.device), p.to(self.device), z.to(self.device)
                
                self.optimizer.zero_grad()
                p_logits, v = self.model(s)
                
                # Standard AlphaZero Loss: (z - v)^2 - pi * log(p)
                loss_v = self.mse_loss(v.view(-1), z)
                loss_p = self.ce_loss(p_logits, p)
                
                (loss_v + loss_p).backward()
                self.optimizer.step()
                
                p_ls.append(loss_p.item()); v_ls.append(loss_v.item())

                if i % 10 == 0:
                    prog = (i / len(loader)) * 100
                    print(f"\r  > Epoch {epoch+1} | {prog:4.1f}% | P-Loss: {loss_p.item():.4f} | V-Loss: {loss_v.item():.4f}", end="")

            avg_p, avg_v = np.mean(p_ls), np.mean(v_ls)
            print(f"\n [+] Epoch {epoch+1} | Avg P: {avg_p:.4f} | Avg V: {avg_v:.4f} | {time.time()-t0:.1f}s")
            
            try: requests.post(f"{self.dashboard_url}/api/update", 
                               json={"p_loss": float(avg_p), "v_loss": float(avg_v), "lr": 0.001, "buffer_size": len(self.dataset)}, 
                               timeout=0.1)
            except: pass
        
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        torch.save(self.model.state_dict(), self.model_path)
        print(f"[*] Weights Synchronized.\n")
        return True

if __name__ == "__main__":
    B_PATH = os.path.join(PROJECT_ROOT, "groundzero", "data", "replay_buffer")
    M_PATH = os.path.join(PROJECT_ROOT, "groundzero", "models", "best_model.pth")
    D_SCRIPT = os.path.join(PROJECT_ROOT, "groundzero", "network_dashboard", "app.py")
    DEV = "mps" if torch.backends.mps.is_available() else "cpu"

    print(f"[*] Starting Silent AlphaZero Stack...")
    db_p = subprocess.Popen([sys.executable, D_SCRIPT], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    try:
        tr = AlphaTrainer(M_PATH, B_PATH, DEV)
        while True:
            if tr.train_step(batch_size=512): time.sleep(30)
            else: time.sleep(10)
    except KeyboardInterrupt:
        db_p.terminate()