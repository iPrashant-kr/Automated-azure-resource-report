<<<<<<< HEAD
# Azure Resource Provisioning Delta Report

This project provides a **local Python script** to fetch details of all Azure resources provisioned in the last 30 days and compare them with the previous 30 days.  
Outputs are CSV files suitable for Excel analysis.

## 1. Create Project Directory & Git Repo
```bash
mkdir azure-resource-report
cd azure-resource-report
git init
```

## 2. Prerequisites
- Python **3.10+** installed
- Azure CLI installed and logged in:
  ```bash
  az login
  ```
- GitHub/GitLab account (optional, if pushing repo remotely)

## 3. Setup Environment
```bash
# Create virtual environment
python -m venv .venv

# Activate environment
source .venv/bin/activate   # Linux/macOS
.venv\Scripts\activate    # Windows

# Place main.py and requirements.txt in this repo

# Install dependencies
pip install -r requirements.txt
```

## 4. Run the Script
```bash
python main.py --outdir reports --days 30
```
- `--outdir` → folder where CSVs are written (default: `reports`)
- `--days` → number of days for each comparison window (default: 30)

## 5. Outputs
The script generates the following inside the output folder:
- `current_inventory.csv` → snapshot of all resources
- `created_last_30d.csv` → resources created in last 30 days
- `created_prev_30d.csv` → resources created in previous 30-day window
- `deleted_last_30d.csv` → resources deleted in last 30 days
- `summary.csv` → comparative counts & net deltas per subscription/resourceType

## 6. Push to GitHub (optional)
```bash
git add .
git commit -m "Initial commit: Azure provisioning delta report"
git branch -M main
git remote add origin https://github.com/<your-username>/azure-resource-report.git
git push -u origin main
```

---

## Notes
- Ensure Activity Logs retention is >= 60 days (default is 90).
- If your tenant has custom resource providers, review raw events to fine-tune classification.
=======
# Automated-azure-resource-report
Automation to fetch Resouces created within a duration.

