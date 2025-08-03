import tkinter as tk
from tkinter import filedialog, messagebox
import os
import csv
import requests
import subprocess
import shutil
import threading
import sys

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def download_and_concat(base_url, final_output, segment_dir="segments_temp", status_callback=print):
    os.makedirs(segment_dir, exist_ok=True)
    list_file_path = os.path.join(segment_dir, "list.txt")
    index = 0

    with open(list_file_path, "w") as list_f:
        while True:
            ts_url = f"{base_url}{index}.ts"
            filename = f"seg_{index:04}.ts"
            full_path = os.path.join(segment_dir, filename)

            try:
                response = requests.get(ts_url, timeout=10)
            except requests.RequestException as e:
                status_callback(f"❌ Error downloading: {e}")
                break

            if response.status_code == 200:
                with open(full_path, "wb") as f:
                    f.write(response.content)
                list_f.write(f"file '{filename}'\n")
                status_callback(f"✅ Downloaded: {ts_url}")
                index += 1
            else:
                status_callback(f"❌ {ts_url} not found (end of list).")
                break

    if index == 0:
        status_callback(f"⚠️ No segments found for {base_url}")
        return False

    ffmpeg_path = resource_path("ffmpeg.exe")

    os.chdir(segment_dir)
    result = subprocess.run([
        ffmpeg_path, "-f", "concat", "-safe", "0",
        "-i", "list.txt", "-c", "copy", os.path.basename(final_output)
    ])
    os.chdir("..")

    if result.returncode == 0:
        os.makedirs(os.path.dirname(final_output), exist_ok=True)
        shutil.move(os.path.join(segment_dir, os.path.basename(final_output)), final_output)
        status_callback(f"🎉 Final video saved at: {final_output}")
    else:
        status_callback(f"❌ Error concatenating video: {final_output}")
        return False

    shutil.rmtree(segment_dir)
    return True

class VideoDownloaderApp:
    def __init__(self, master):
        self.master = master
        master.title("HLS Video Downloader")

        self.url_label = tk.Label(master, text="Video Base URL:")
        self.url_label.grid(row=0, column=0, sticky='e')

        self.url_entry = tk.Entry(master, width=60)
        self.url_entry.grid(row=0, column=1, padx=10, pady=5)

        self.output_label = tk.Label(master, text="Output Filename:")
        self.output_label.grid(row=1, column=0, sticky='e')

        self.output_entry = tk.Entry(master, width=60)
        self.output_entry.grid(row=1, column=1, padx=10, pady=5)
        self.output_entry.insert(0, "video_final.mp4")

        self.download_button = tk.Button(master, text="Download Single Video", command=self.download_single)
        self.download_button.grid(row=2, column=1, pady=10, sticky="w")

        self.csv_button = tk.Button(master, text="Download from CSV", command=self.download_from_csv)
        self.csv_button.grid(row=2, column=1, pady=10, sticky="e")

        self.text_output = tk.Text(master, height=18, width=90)
        self.text_output.grid(row=3, column=0, columnspan=2, padx=10, pady=10)

    def log(self, msg):
        self.text_output.insert(tk.END, msg + "\n")
        self.text_output.see(tk.END)
        self.master.update()

    def download_single(self):
        url = self.url_entry.get().strip().rstrip('/')
        output_name = self.output_entry.get().strip()
        if not url:
            messagebox.showwarning("Missing URL", "Please enter a base URL.")
            return
        output_path = os.path.join("output", output_name)
        threading.Thread(target=self._thread_download_single, args=(url, output_path)).start()

    def _thread_download_single(self, url, output_path):
        self.log(f"🔽 Starting single video download: {url}")
        success = download_and_concat(url, output_path, status_callback=self.log)
        if not success:
            self.log("⚠️ Download failed.")

    def download_from_csv(self):
        csv_path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if not csv_path:
            return
        threading.Thread(target=self._thread_download_csv, args=(csv_path,)).start()

    def _thread_download_csv(self, csv_path):
        self.log(f"📄 Loading CSV: {csv_path}")
        try:
            with open(csv_path, newline='', encoding="utf-8") as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    course_name = row["course_name"].strip()
                    module_name = row["module_name"].strip()
                    video_num = row["video_num"].strip()
                    video_name = row["video_name"].strip()
                    base_url = row["base_url"].strip().rstrip('/')

                    final_filename = f"{video_num}_{video_name}.mp4"
                    output_path = os.path.join("output", course_name, module_name, final_filename)

                    self.log(f"\n🔽 Starting download: {final_filename}")
                    self.log(f"📚 Course: {course_name} | 📦 Module: {module_name} | 🌐 Base URL: {base_url}")
                    success = download_and_concat(base_url, output_path, status_callback=self.log)

                    if not success:
                        self.log(f"⚠️ Failed to process: {video_name}")
        except Exception as e:
            self.log(f"❌ Error reading CSV: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = VideoDownloaderApp(root)
    root.mainloop()

