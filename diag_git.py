import subprocess
import os

def run_git(args):
    try:
        print(f"\n--- COMMAND: git {' '.join(args)} ---")
        res = subprocess.run(["git"] + args, capture_output=True, text=True)
        print("STDOUT:", res.stdout)
        print("STDERR:", res.stderr)
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    print(f"CWD: {os.getcwd()}")
    run_git(["status"])
    run_git(["remote", "-v"])
    run_git(["log", "-1"])
