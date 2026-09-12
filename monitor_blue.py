import time, os
from pathlib import Path
from tensorboard.backend.event_processing.event_accumulator import EventAccumulator
import numpy as np

def monitor():
    for loop in range(1200):  # 2 hours max
        tb_dir = Path('logs/blue/MaskablePPO_1')
        
        if not tb_dir.exists():
            print(f'\r[0%] Waiting for logs... ({loop*5}s elapsed)', end='', flush=True)
            time.sleep(5)
            continue
        
        events = sorted(tb_dir.glob('events.out.tfevents.*'))
        if not events:
            print(f'\r[0%] Initializing... ({loop*5}s elapsed)', end='', flush=True)
            time.sleep(5)
            continue
        
        try:
            ea = EventAccumulator(str(tb_dir))
            ea.Reload()
            rewards = ea.Scalars('rollout/ep_rew_mean')
            
            if not rewards:
                print(f'\r[0%] No data yet... ({loop*5}s elapsed)', end='', flush=True)
                time.sleep(5)
                continue
            
            steps = rewards[-1].step
            reward = rewards[-1].value
            fps = np.mean([r.value for r in ea.Scalars('time/fps')])
            pct = min(100, (steps / 1_000_000) * 100)
            
            # Draw bar
            filled = int(pct / 2)
            bar = '=' * filled + '-' * (50 - filled)
            
            if steps >= 1_000_000:
                print(f'\n[{bar}] 100.0% - COMPLETE! Reward: {reward:.2f}')
                break
            else:
                remaining_steps = 1_000_000 - steps
                eta_secs = remaining_steps / fps if fps > 0 else 0
                eta_min = int(eta_secs // 60)
                eta_sec = int(eta_secs % 60)
                
                print(f'\r[{bar}] {pct:5.1f}% | Steps: {steps:>8,}/1M | Reward: {reward:6.2f} | FPS: {fps:5.0f} | ETA: {eta_min:3}m {eta_sec:2}s', end='', flush=True)
            
            time.sleep(10)
        except Exception as e:
            print(f'\r[Error] {str(e)[:30]}', end='', flush=True)
            time.sleep(10)
    
    print('\nMonitoring completed.')

if __name__ == '__main__':
    monitor()
