import os
import time
import torch
import multiprocessing as mp
import sys

# Setup paths
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
if root_dir not in sys.path:
    sys.path.append(root_dir)

from algorithm.model import AlphaNet
from algorithm.collector import DataCollector
# Note: We import a helper to start the app so we can pass the shared dict
from training_dashboard.dashboard_app import run_dashboard_server

def bootstrap_model(path):
    """Initializes a model with random weights if it doesn't exist."""
    if not os.path.exists(path):
        print(f"[*] No model found at {path}. Initializing new 'brain'...")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        model = AlphaNet(num_res_blocks=10, channels=128)
        
        def init_weights(m):
            if isinstance(m, torch.nn.Conv2d) or isinstance(m, torch.nn.Linear):
                torch.nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
        
        model.apply(init_weights)
        torch.save(model.state_dict(), path)
        print(f"[+] Bootstrap complete. Weights saved to {path}")

def worker_task(worker_id, model_path, shared_stats):
    """
    Worker process that performs self-play.
    shared_stats is a multiprocessing.Manager.dict()
    """
    collector = DataCollector(model_path=model_path, device="cpu")
    print(f"[Worker {worker_id}] Starting self-play loop...")
    
    while True:
        # 1. Update shared state to 'Starting'
        shared_stats[worker_id] = {
            "status": "Thinking",
            "move_count": 0,
            "last_depth": 0,
            "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            "start_time": time.time()
        }

        start_time = time.time()
        
        game_data = collector.collect_game(worker_id=worker_id, stats=shared_stats)
        
        duration = time.time() - start_time
        
        # 2. Save result
        timestamp = int(time.time() * 1000)
        filename = f"batch_{worker_id}_{timestamp}.npz"
        collector.save_batch(game_data, filename)
        
        # 3. Update shared state for the 'break' between games
        shared_stats[worker_id] = {
            "status": "Saving/Updating",
            "move_count": len(game_data),
            "last_depth": "-",
            "fen": "-",
            "start_time": start_time
        }
        
        print(f"[Worker {worker_id}] Game finished ({duration:.1f}s). Buffer: {len(game_data)} states.")
        collector.update_model(model_path)

if __name__ == "__main__":
    MODEL_PATH = "models/best_model.pth"
    BUFFER_DIR = "data/replay_buffer"
    
    os.makedirs(BUFFER_DIR, exist_ok=True)
    bootstrap_model(MODEL_PATH)
    
    # Manager handles the shared state between separate processes
    with mp.Manager() as manager:
        shared_stats = manager.dict()
        processes = []

        # 1. Start the Dashboard Process
        # We pass the shared_stats dict so the Flask API can read it
        dashboard_p = mp.Process(
            target=run_dashboard_server, 
            args=(shared_stats,)
        )
        dashboard_p.start()
        processes.append(dashboard_p)

        # 2. Spawn Actor Workers
        num_workers = min(4, os.cpu_count()) 
        print(f"[*] Spawning {num_workers} workers...")
        
        for i in range(num_workers):
            p = mp.Process(target=worker_task, args=(i, MODEL_PATH, shared_stats))
            p.start()
            processes.append(p)

        try:
            for p in processes:
                p.join()
        except KeyboardInterrupt:
            print("\n[*] Terminating all processes...")
            for p in processes:
                p.terminate()