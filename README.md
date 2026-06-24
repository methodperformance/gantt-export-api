# Gantt Export API

Serverless Python function that generates Excel files from dashboard JSON data.

## Files
- `api/export.py` — main function
- `gantt_template.xlsx` — Excel template with full styling
- `requirements.txt` — Python dependencies
- `vercel.json` — Vercel config

## Deploy to Vercel
1. Upload this folder to GitHub
2. Connect to Vercel
3. Deploy

## API
POST /api/export
Body: { name, plant, leader, actions: [{name, owner, start, end, percent, update}] }
Returns: .xlsx file
