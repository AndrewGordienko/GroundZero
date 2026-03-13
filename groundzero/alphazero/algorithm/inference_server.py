import torch
import multiprocessing as mp
import numpy as np
import time

def inference_worker(model_path, device, task_queue, result_dict):
    """
    The GPU Master process. 
    Optimized for dynamic batching to maximize throughput.
    """
    # Import inside the function to avoid CUDA/MPS initialization issues in the main process
    from .model import AlphaNet
    
    print(f"[Inference] Initializing model on {device}...")
    model = AlphaNet(num_res_blocks=10, channels=128).to(device)
    
    # Load model with weights
    try:
        # Using weights_only=True is a security best practice in newer Torch versions
        model.load_state_dict(torch.load(model_path, map_location=device))
    except Exception as e:
        print(f"[Inference] Warning: Could not load model weights: {e}")
    
    model.eval()

    # Settings for high-throughput
    BATCH_SIZE = 64
    WAIT_TIMEOUT = 0.001 # 1ms window to allow queue to fill up
    
    print(f"[Inference] Server is active. Batch Size: {BATCH_SIZE}")

    while True:
        batch = []
        ids = []
        
        # 1. Block until at least ONE task is available
        try:
            task_id, state = task_queue.get(timeout=1.0)
            batch.append(state)
            ids.append(task_id)
        except:
            continue # No tasks for 1 second, just loop back

        # 2. Dynamic Batching: Try to fill the rest of the batch
        start_wait = time.time()
        while len(batch) < BATCH_SIZE:
            try:
                task_id, state = task_queue.get_nowait()
                batch.append(state)
                ids.append(task_id)
            except:
                if time.time() - start_wait < WAIT_TIMEOUT:
                    time.sleep(0.0001) 
                    continue
                else:
                    break 

        # 3. Batch Inference
        if batch:
            with torch.no_grad():
                # Stack numpy arrays into a single tensor
                tensors = torch.from_numpy(np.stack(batch)).to(device)
                
                logits, values = model(tensors)
                
                # FIX: Flatten values so they are 1D arrays (N,) instead of (N, 1)
                # This prevents the "only 0-dimensional arrays" TypeError
                probs = torch.softmax(logits, dim=1).cpu().numpy()
                vals = values.cpu().numpy().flatten()
                
                # 4. Distribute results back to workers
                # We use a temporary dict and update the shared result_dict once 
                # to minimize Inter-Process Communication (IPC) locking overhead.
                updates = {}
                for i, tid in enumerate(ids):
                    updates[tid] = (probs[i], float(vals[i]))
                
                result_dict.update(updates)