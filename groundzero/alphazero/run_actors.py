import os
import sys
import time
import torch
import multiprocessing as mp

current_file = os.path.abspath(__file__)
# Path logic: run_actors.py -> alphazero -> groundzero -> [ROOT]
# This ensures groundzero is importable no matter where you run from.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ==============================================================
# 2. IMPORTS (Now using absolute package paths)
# ==============================================================
from groundzero.alphazero.algorithm.model import AlphaNet
from groundzero.alphazero.algorithm.collector import DataCollector
from groundzero.alphazero.algorithm.inference_server import inference_worker

# If you want the dashboard, uncomment and ensure path is correct
# from groundzero.training_dashboard.dashboard_app import run_dashboard_server 

def bootstrap_model(path):
    """Initializes model weights if they don't exist."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        print(f"[*] Initializing new 'brain' at {path}...")
        model = AlphaNet(num_res_blocks=10, channels=128)
        torch.save(model.state_dict(), path)

def worker_task(worker_id, model_path, shared_stats, task_queue, result_dict):
    """Process for generating self-play games."""
    # M1/M2/M3 Mac Optimization: Keep MCTS on CPU, send work to GPU via Queue
    collector = DataCollector(model_path=model_path, device="cpu")
    collector.evaluator.set_batch_mode(task_queue, result_dict)

    print(f"[Worker {worker_id}] Starting batched self-play...")
    
    while True:
        shared_stats[worker_id] = {
            "status": "In Queue", "move_count": 0, "fen": "start", "start_time": time.time()
        }

        start_time = time.time()
        # collect_game handles the actual MCTS and board logic
        game_data = collector.collect_game(worker_id=worker_id, stats=shared_stats)
        
        timestamp = int(time.time() * 1000)
        filename = f"batch_{worker_id}_{timestamp}.npz"
        collector.save_batch(game_data, filename)
        
        # Periodically check for new weight files
        collector.update_model(model_path)

if __name__ == "__main__":
    # REQUIRED for Mac MPS (Metal) and Multi-process safety
    mp.set_start_method('spawn', force=True) 
    
    # Use PROJECT_ROOT to ensure folders go to the very top directory
    MODEL_PATH = os.path.join(PROJECT_ROOT, "models", "best_model.pth")
    DEVICE = "mps" if torch.backends.mps.is_available() else "cpu"
    
    bootstrap_model(MODEL_PATH)
    
    # Manager handles shared memory between workers and the GPU server
    with mp.Manager() as manager:
        shared_stats = manager.dict()
        result_dict = manager.dict() 
        task_queue = mp.Queue(maxsize=256)
        processes = []

        # 1. Start Inference Server (The GPU master)
        inf_p = mp.Process(
            target=inference_worker, 
            args=(MODEL_PATH, DEVICE, task_queue, result_dict)
        )
        inf_p.start()
        processes.append(inf_p)

        # 2. Start Workers (Self-play actors)
        num_workers = 8
        for i in range(num_workers):
            p = mp.Process(
                target=worker_task, 
                args=(i, MODEL_PATH, shared_stats, task_queue, result_dict)
            )
            p.start()
            processes.append(p)

        try:
            print(f"[*] All actors running on {DEVICE}. Press Ctrl+C to stop.")
            for p in processes: p.join()
        except KeyboardInterrupt:
            print("\n[!] Shutting down processes...")
            for p in processes: p.terminate()