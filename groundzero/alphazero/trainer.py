import os
import glob
import time
import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import requests
import subprocess
import sys
from torch.utils.data import Dataset, DataLoader
from algorithm.model import AlphaNet

class ChessDataset(Dataset):
    def __init__(self, buffer_path, max_samples=100000):
        self.buffer_path = os.path.abspath(buffer_path)
        self.max_samples = max_samples
        self.file_list = []
        self.refresh_files()

    def refresh_files(self):
        if not os.path.exists(self.buffer_path):
            return
        all_files = sorted(glob.glob(os.path.join(self.buffer_path, "*.npz")), 
                          key=os.path.getmtime, reverse=True)
        
        self.file_list = all_files[:200]
        
        self.states, self.pis, self.zs = [], [], []
        total_samples = 0
        for f in self.file_list:
            try:
                with np.load(f) as data:
                    self.states.append(data['states'])
                    self.pis.append(data['pis'])
                    self.zs.append(data['zs'])
                    total_samples += len(data['zs'])
                if total_samples >= self.max_samples: break
            except: continue
            
        if self.states:
            self.states = np.concatenate(self.states, axis=0)
            self.pis = np.concatenate(self.pis, axis=0)
            self.zs = np.concatenate(self.zs, axis=0)

    def __len__(self):
        return len(self.zs) if hasattr(self, 'zs') else 0

    def __getitem__(self, idx):
        return (
            torch.from_numpy(self.states[idx]).float(),
            torch.from_numpy(self.pis[idx]).float(),
            torch.tensor(self.zs[idx]).float()
        )

class AlphaTrainer:
    def __init__(self, model_path, buffer_path, device="cpu", dashboard_url="http://localhost:5005"):
        self.model_path = os.path.abspath(model_path)
        self.buffer_path = buffer_path
        self.device = device
        self.dashboard_url = dashboard_url
        self.dataset = ChessDataset(self.buffer_path)
        
        self.model = AlphaNet(num_res_blocks=10, channels=128).to(self.device)
        if os.path.exists(self.model_path):
            print(f"[*] Reloading Weights: {os.path.basename(self.model_path)}")
            self.model.load_state_dict(torch.load(self.model_path, map_location=self.device))
        
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
        except:
            pass 

    def train_step(self, batch_size=1024, epochs=3):
        start_load = time.time()
        self.dataset.refresh_files()
        
        if len(self.dataset) < 2000:
            print(f" [!] Buffer: {len(self.dataset)}/2000 | Awaiting data...")
            return False

        loader = DataLoader(
            self.dataset, 
            batch_size=batch_size, 
            shuffle=True, 
            num_workers=0, 
            pin_memory=True if self.device != "cpu" else False
        )
        
        print(f"\n{'-'*50}\n ENGINE UPDATE | Samples: {len(self.dataset)} | Load Time: {time.time()-start_load:.2f}s")
        self.model.train()

        for epoch in range(epochs):
            p_losses, v_losses = [], []
            epoch_start = time.time()
            
            for states, pis, zs in loader:
                states, pis, zs = states.to(self.device), pis.to(self.device), zs.to(self.device)
                
                self.optimizer.zero_grad()
                p_logits, v = self.model(states)
                v = v.view(-1)
                
                loss_v = self.mse_loss(v, zs)
                loss_p = self.ce_loss(p_logits, pis)
                
                (loss_v + loss_p).backward()
                self.optimizer.step()
                
                p_losses.append(loss_p.item())
                v_losses.append(loss_v.item())

            avg_p, avg_v = np.mean(p_losses), np.mean(v_losses)
            print(f" > Epoch {epoch+1}/{epochs} | Policy: {avg_p:.4f} | Value: {avg_v:.4f} | {time.time()-epoch_start:.1f}s")
            self.report_metrics(avg_p, avg_v)
        
        torch.save(self.model.state_dict(), self.model_path)
        print(f"[*] Weights Synchronized. {'-'*31}")
        return True

if __name__ == "__main__":
    # Resolve Paths based on your screenshot structure
    script_dir = os.path.dirname(os.path.abspath(__file__)) # groundzero/alphazero/
    project_root = os.path.dirname(os.path.dirname(script_dir)) # GROUNDZERO/
    
    MODEL_PATH = os.path.join(project_root, "models", "best_model.pth")
    BUFFER_PATH = os.path.join(project_root, "data", "replay_buffer")
    DASHBOARD_SCRIPT = os.path.join(project_root, "groundzero", "network_dashboard", "app.py")

    DEVICE = "mps" if torch.backends.mps.is_available() else "cpu"

    # Launch Dashboard Process
    print(f"[*] Starting Dashboard from: {DASHBOARD_SCRIPT}")
    dashboard_proc = subprocess.Popen([sys.executable, DASHBOARD_SCRIPT])

    try:
        trainer = AlphaTrainer(MODEL_PATH, BUFFER_PATH, DEVICE)
        print(f"[*] AlphaZero Trainer Active [{DEVICE}]")

        while True:
            if trainer.train_step():
                time.sleep(30)
            else:
                time.sleep(10)
    except KeyboardInterrupt:
        print("\n[*] Shutting down Trainer and Dashboard...")
        dashboard_proc.terminate()