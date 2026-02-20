import torch
import glob
import numpy as np
import time
import os
from flask import Flask, jsonify
from threading import Thread
from groundzero.alphazero.algorithm.model import AlphaNet

# --- TELEMETRY SERVER ---
telemetry_data = {"loss": 0, "value_loss": 0, "policy_loss": 0, "games_processed": 0}
app = Flask(__name__)

@app.route("/metrics")
def metrics():
    return jsonify(telemetry_data)

def start_telemetry():
    app.run(host="0.0.0.0", port=5002) # Watch this IP from your Mac

# --- LEARNER ---
def train_loop():
    device = "cuda"
    model = AlphaNet(num_res_blocks=10, channels=128).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    
    while True:
        files = glob.glob("data/replay_buffer/*.npz")
        if len(files) < 20:
            time.sleep(10); continue
            
        states, pis, zs = [], [], []
        for f in files[:100]:
            data = np.load(f, allow_pickle=True)['data']
            for s in data:
                states.append(s['state'])
                pis.append(s['pi'])
                zs.append(s['z'])
            os.remove(f)

        # PyTorch Tensors
        s_tensor = torch.tensor(np.array(states)).to(device)
        p_target = torch.tensor(np.array(pis)).to(device)
        v_target = torch.tensor(np.array(zs)).to(device).unsqueeze(1)

        # Forward + Loss
        p_pred, v_pred = model(s_tensor)
        v_loss = torch.nn.functional.mse_loss(v_pred, v_target)
        # Cross-entropy for Policy (AlphaZero style)
        p_loss = -torch.mean(torch.sum(p_target * torch.log(torch.softmax(p_pred, dim=1) + 1e-8), dim=1))
        
        total_loss = v_loss + p_loss
        optimizer.zero_grad()
        total_loss.backward()
        optimizer.step()

        # Update Telemetry
        telemetry_data.update({
            "loss": float(total_loss),
            "value_loss": float(v_loss),
            "policy_loss": float(p_loss),
            "games_processed": telemetry_data["games_processed"] + len(files)
        })
        
        torch.save(model.state_dict(), "models/latest.pth")

if __name__ == "__main__":
    Thread(target=start_telemetry).start()
    train_loop()