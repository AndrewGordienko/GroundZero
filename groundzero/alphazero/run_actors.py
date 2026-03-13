import os
import sys
import time
import torch
import multiprocessing as mp

# --- Path Fix ---
current_file = os.path.abspath(__file__)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from groundzero.alphazero.algorithm.model import AlphaNet
from groundzero.alphazero.algorithm.collector import DataCollector
from groundzero.alphazero.algorithm.inference_server import inference_worker
# Re-enabling the dashboard import
from groundzero.training_dashboard.dashboard_app import run_dashboard_server 

def bootstrap_model(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        print(f"[*] Initializing new 'brain' at {path}...")
        model = AlphaNet(num_res_blocks=10, channels=128)
        torch.save(model.state_dict(), path)

def worker_task(worker_id, model_path, shared_stats, task_queue, result_dict):
    collector = DataCollector(model_path=model_path, device="cpu")
    collector.evaluator.set_batch_mode(task_queue, result_dict)
    print(f"[Worker {worker_id}] Starting batched self-play...")
    
    while True:
        shared_stats[worker_id] = {"status": "In Queue", "move_count": 0, "fen": "start", "start_time": time.time()}
        game_data = collector.collect_game(worker_id=worker_id, stats=shared_stats)
        filename = f"batch_{worker_id}_{int(time.time() * 1000)}.npz"
        collector.save_batch(game_data, filename)
        collector.update_model(model_path)

if __name__ == "__main__":
    mp.set_start_method('spawn', force=True) 
    MODEL_PATH = os.path.join(PROJECT_ROOT, "models", "best_model.pth")
    DEVICE = "mps" if torch.backends.mps.is_available() else "cpu"
    bootstrap_model(MODEL_PATH)
    
    with mp.Manager() as manager:
        shared_stats = manager.dict()
        result_dict = manager.dict() 
        task_queue = mp.Queue(maxsize=256)
        processes = []

        # 1. Start Inference Server
        inf_p = mp.Process(target=inference_worker, args=(MODEL_PATH, DEVICE, task_queue, result_dict))
        inf_p.start()
        processes.append(inf_p)

        # 2. Start Dashboard (The visual URL part)
        dash_p = mp.Process(target=run_dashboard_server, args=(shared_stats,))
        dash_p.start()
        processes.append(dash_p)

        # 3. Start Workers
        for i in range(8):
            p = mp.Process(target=worker_task, args=(i, MODEL_PATH, shared_stats, task_queue, result_dict))
            p.start()
            processes.append(p)

        try:
            print(f"[*] Engine Online. URL: http://127.0.0.1:5000")
            for p in processes: p.join()
        except KeyboardInterrupt:
            for p in processes: p.terminate()