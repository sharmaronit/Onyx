# Onyx Startup Guide

## Quick Start

### **Option 1: Demo Only (Recommended)**
```powershell
cd D:\dehradun
.\start.ps1 demo
```
Opens http://localhost:8511 with the Streamlit dashboard (assumes training is already done).

### **Option 2: Full Training (First Time)**
```powershell
cd D:\dehradun
.\start.ps1 train
```
Runs all 8 training stages (~12-14 hours), then starts demo.

### **Option 3: Training + Demo (Full Cycle)**
```powershell
cd D:\dehradun
.\start.ps1 full
```
Same as `train` but keeps Streamlit running after completion.

---

## What Each Mode Does

### **Mode: demo**
- ✓ Activate virtual environment
- ✓ Verify GPU availability
- ✓ Start Streamlit app (port 8511)
- ✗ No training (assumes checkpoints exist)
- **Time:** <1 minute

### **Mode: train**
- ✓ Activate virtual environment
- ✓ Run Stage 1: setup
- ✓ Run Stage 2: data generation (102K transitions)
- ✓ Run Stage 3: GNN training (AUC >0.99)
- ✓ Run Stage 4: Red agent (1M steps)
- ✓ Run Stage 5: Blue agent (1M steps)
- ✓ Run Stage 6: MARL self-play (5 rounds)
- ✓ Run Stage 7: Patch optimization
- ✓ Run Stage 8: Report generation
- ✗ Does NOT start Streamlit
- **Time:** 12-14 hours

### **Mode: full**
- ✓ Run all training stages (see `train` above)
- ✓ Automatically start Streamlit demo after training
- **Time:** 12-14 hours + demo runtime

---

## Troubleshooting

### **Permission Denied Error**
PowerShell execution policy is restricted. Run:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```
Then try again.

### **Virtual Environment Not Found**
The script will auto-create it. If it fails:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### **GPU Not Detected**
The script checks for CUDA availability. If no GPU:
- Training falls back to CPU (will be very slow)
- For inference/demo mode, CPU is fine

### **Streamlit Port Already In Use**
If port 8511 is already taken:
```powershell
# Kill the existing process
Get-Process streamlit | Stop-Process -Force

# Or run on a different port
.\.venv\Scripts\streamlit run demo/app.py --server.port 8502
```

### **Training Crashes Mid-Way**
Resume from where it stopped. Check the last successful stage in logs:
```powershell
cat logs/training.log | tail -20
```
Then run:
```powershell
.\start.ps1 train
# It will warn you, confirm with "yes"
```

---

## What Happens at Startup

1. **Navigate to project root** (`D:\dehradun`)
2. **Check venv exists** (create if missing)
3. **Activate virtual environment**
4. **Verify GPU availability** (print device info)
5. **Based on mode:**
   - `demo`: Start Streamlit immediately
   - `train`: Run 8 sequential stages
   - `full`: Run training, then Streamlit

---

## Streamlit Dashboard (After Startup)

Once the script starts Streamlit, open your browser:
```
http://localhost:8511
```

**4 Tabs:**
- **Tab 1:** Interactive 20-node network graph (pyvis visualization)
- **Tab 2:** CVSS vs Onyx patch ranking (the WOW moment)
- **Tab 3:** Red vs Blue arms-race curves (5-round MARL learning)
- **Tab 4:** Morning security report with top 5 patches

---

## Exiting

- **Streamlit:** Press `Ctrl+C` in terminal
- **Training:** Press `Ctrl+C` (will gracefully stop at current stage end)

---

## File Locations (For Reference)

| Item | Path |
|---|---|
| Project root | `D:\dehradun\` |
| Start script | `D:\dehradun\start.ps1` |
| Virtual env | `D:\dehradun\.venv\` |
| Trained models | `D:\dehradun\checkpoints\` |
| Training data | `D:\dehradun\data\episodes\transitions.h5` |
| Reports | `D:\dehradun\reports\` |
| Demo app | `D:\dehradun\demo\app.py` |

---

## Performance Tips

- **For fastest demo startup:** Use `demo` mode (assumes prior training)
- **For re-training:** Back up checkpoints first (`checkpoints/` folder)
- **For faster training:** Check that CUDA is detected (script verifies this)

---

**Questions?** See `README.md` or check logs in `D:\dehradun\logs\`
