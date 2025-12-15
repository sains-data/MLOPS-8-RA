import schedule
import time
import subprocess
import os
import datetime

def job():
    print(f"\n[Scheduler] Starting weekly job at {datetime.datetime.now()}")
    
    # 1. Run Scraper
    print("[Scheduler] Running Scraper...")
    try:
        # Assumes running from root
        subprocess.run(["python", "scripts/scraper.py"], check=True)
        print("[Scheduler] Scraper finished successfully.")
    except subprocess.CalledProcessError as e:
        print(f"[Scheduler] Scraper failed! Error: {e}")
        return # Do not retrain if scraping failed

    # 2. Run Training
    print("[Scheduler] Running Retraining...")
    try:
        subprocess.run(["python", "scripts/train.py"], check=True)
        print("[Scheduler] Retraining finished successfully. Models updated.")
    except subprocess.CalledProcessError as e:
        print(f"[Scheduler] Retraining failed! Error: {e}")

def main():
    print("--- 🕒 Automatic Weekly Scheduler Started ---")
    print("Schedule: Every Sunday at 02:00 AM")
    
    # Schedule the job every Sunday at 02:00 AM
    schedule.every().sunday.at("02:00").do(job)
    
    # For testing purposes (uncomment to run immediately)
    # job() 
    
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    # Check if schedule library is installed
    try:
        import schedule
        main()
    except ImportError:
        print("Library 'schedule' not found. Installing...")
        os.system("pip install schedule")
        import schedule
        main()
