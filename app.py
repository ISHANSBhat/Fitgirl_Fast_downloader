import tkinter as tk
from tkinter import messagebox
import subprocess
from urllib import response
import requests
from bs4 import BeautifulSoup
import os
import re
from urllib.parse import urlparse
from tqdm import tqdm
import threading
import time

WINRAR_PATH = r"C:\Program Files\WinRAR\WinRAR.exe"
INPUT_FILE = "input.txt"
MAX_RETRIES = 5


# ===== GET LINKS =====
def get_links():
    url = url_entry.get().strip()

    if not url:
        messagebox.showerror("Error", "Enter a URL")
        return

    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
    except Exception as e:
        messagebox.showerror("Error", f"Request failed:\n{e}")
        return

    soup = BeautifulSoup(r.text, "html.parser")

    links = [
        a["href"]
        for dlinks_div in soup.find_all("div", class_="dlinks")
        for a in dlinks_div.find_all("a", href=True)
        if a["href"].startswith("https://fuckingfast.co/")
    ]

    if not links:
        messagebox.showerror("Error", "No links found")
        return

    with open(INPUT_FILE, "w") as f:
        f.write("\n".join(links))

    subprocess.Popen(["notepad.exe", INPUT_FILE])

    messagebox.showinfo(
        "Links Ready",
        f"{len(links)} links opened in Notepad.\nEdit and click Start Download."
    )


# ===== DOWNLOAD FILE =====
def download_file(download_url, output_path, file_name):
    try:
        response = requests.get(download_url, stream=True, timeout=60)

        if response.status_code != 200:
            return False

        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        block_size = 8192

        with open(output_path, 'wb') as f:
            with tqdm(total=total_size, unit='B', unit_scale=True, desc=file_name) as pbar:
                for data in response.iter_content(block_size):
                    if not data:
                        continue
                    f.write(data)
                    downloaded += len(data)
                    pbar.update(len(data))

        
        if total_size > 0 and downloaded < total_size:
            print("Incomplete download:", file_name)
            return False

        return True

    except Exception as e:
        print("Download error:", e)
        return False

# ===== credits =====

def show_credits():
    credits_window = tk.Toplevel(root)
    credits_window.title("About")
    credits_window.geometry("350x250")
    credits_window.resizable(False, False)

    tk.Label(
        credits_window,
        text="FitGirl Downloader fking fast",
        font=("Arial", 14, "bold")
    ).pack(pady=10)

    tk.Label(
        credits_window,
        text="Version 1.0",
        font=("Arial", 10)
    ).pack()

    tk.Label(
        credits_window,
        text="\nDeveloped by:\nIshan S Bhat",
        font=("Arial", 10)
    ).pack()


    tk.Label(
        credits_window,
        text="\nExtraction powered by WinRAR",
        font=("Arial", 9)
    ).pack()

    tk.Button(
        credits_window,
        text="Close",
        command=credits_window.destroy
    ).pack(pady=10)

# ===== HELPER_REMOVE_LINK =====
def remove_link_from_file(link):
    try:
        with open(INPUT_FILE, "r") as f:
            lines = [line.strip() for line in f if line.strip()]

        lines = [l for l in lines if l != link]

        with open(INPUT_FILE, "w") as f:
            f.write("\n".join(lines))

    except Exception as e:
        print("Error updating input.txt:", e)

# ===== CORE LOGIC  =====
def run_download():
    try:
        if not os.path.exists(INPUT_FILE):
            messagebox.showerror("Error", "Run 'Get Links' first")
            return

        parsed = urlparse(url_entry.get().strip())

        user_folder = folder_entry.get().strip()

        game_name = (
            user_folder or
            parsed.fragment.split("--")[0].strip("_") or
            "downloaded_game"
        )

        if not game_name:
            root.after(0, lambda: messagebox.showwarning(
                "Warning",
                "Could not detect game name from URL.\nFiles will be saved in 'downloads/game/'."
            ))
            game_name = "game"

        downloads_folder = os.path.join("downloads", game_name)
        os.makedirs(downloads_folder, exist_ok=True)

        round_num = 1

        exhausted = True

        while round_num <= MAX_RETRIES:

            with open(INPUT_FILE, "r") as f:
                links = [line.strip() for line in f if line.strip()]

            if not links:
                print("All downloads completed!")
                exhausted = False
                break

            print(f"\n--- Retry Round {round_num} ---")
            round_num += 1

            for link in links:
                try:
                    response = requests.get(link, timeout=30)
                    soup = BeautifulSoup(response.text, 'html.parser')
                    meta_title = soup.find('meta', attrs={'name': 'title'})
                    file_name = meta_title['content'] if meta_title else "file"

                    script_tags = soup.find_all('script')
                    download_function = None

                    for script in script_tags:
                        if 'function download' in script.text:
                            download_function = script.text
                            break

                    if download_function:
                        match = re.search(
                            r'window\.open\(["\'](https?://[^\s"\'\)]+)',
                            download_function
                        )

                        if match:
                            download_url = match.group(1)
                            output_path = os.path.join(downloads_folder, file_name)
                            print("Download URL:", download_url)
                            print("Expected size (bytes):", response.headers.get("content-length"))

                            print("Downloading:", file_name)

                            success = download_file(download_url, output_path, file_name)

                            if success:
                                remove_link_from_file(link)
                            else:
                                print("Will retry:", file_name)

                                if os.path.exists(output_path):
                                    os.remove(output_path)

                except Exception as e:
                    print("Error:", e)

            if links:
                time.sleep(3)   

        if exhausted:
            root.after(0, lambda: messagebox.showwarning(
                "Stopped",
                "Max retries reached. Some files may not have downloaded."
            ))
        else:
            root.after(0, lambda: ask_extract(downloads_folder))

    except Exception as e:
        root.after(0, lambda err=e: messagebox.showerror("Fatal Error", str(err)))

# ===== START THREAD =====
def start_download():
    threading.Thread(
        target=run_download,
        daemon=True
    ).start()

# ===== ASK EXTRACTION THREAD =====
def ask_extract(folder):
    do_extract = messagebox.askyesno(
        "Extraction",
        "All downloads completed.\nDo you want to extract?"
    )

    if do_extract:
        threading.Thread(
            target=run_extraction,
            args=(folder,),
            daemon=True
        ).start()
    else:
        messagebox.showinfo("Done", "Download complete (no extraction).")

# ==== RUN EXTRACTION THREAD =====
def run_extraction(folder):
    print("Starting extraction...")

    rar_file = None

    for file in sorted(os.listdir(folder)):
        if re.search(r'part0*1\.rar$', file.lower()):
            rar_file = os.path.join(folder, file)
            break

    if not rar_file:
        for file in sorted(os.listdir(folder)):
            if file.lower().endswith(".rar"):
                rar_file = os.path.join(folder, file)
                break

    if not rar_file:
        print("No archive found")
        return

    proc = subprocess.Popen([
        WINRAR_PATH,
        "x",
        "-y",
        "-o+",
        rar_file,
        folder
    ])

    proc.wait()

    print("Extraction completed")

    # 🔥 Ask delete AFTER extraction
    root.after(0, lambda: ask_delete(folder))

# ===== ASK DELETE THREAD =====
def ask_delete(folder):
    do_delete = messagebox.askyesno(
        "Cleanup",
        "Extraction completed.\nDelete .rar files?"
    )

    if do_delete:
        delete_archives(folder)

    messagebox.showinfo("Done", "Process complete.")

# ==== DELETE ARCHIVES =====
def delete_archives(folder):
    print("Deleting archive files...")

    for file in os.listdir(folder):
        if file.lower().endswith(".rar"):
            try:
                os.remove(os.path.join(folder, file))
            except Exception as e:
                print("Delete error:", e)

# ===== UI =====
root = tk.Tk()
root.title("FitGirl Fking Fast Downloader ~ Ishxt Bhat")
root.geometry("420x330")

tk.Label(root, text="Enter FitGirl URL:").pack(pady=10)

url_entry = tk.Entry(root, width=50)
url_entry.pack(pady=5)

tk.Label(root, text="Save folder name (optional):").pack(pady=5)

folder_entry = tk.Entry(root, width=50)
folder_entry.pack(pady=5)

tk.Button(root, text="Get Links", command=get_links).pack(pady=10)
tk.Button(root, text="Start Download", command=start_download).pack(pady=10)
tk.Button(root, text="About / Credits", command=show_credits).pack(pady=5)

root.mainloop()
