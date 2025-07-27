import csv
import os
import requests
import subprocess
import shutil
import argparse

def download_and_concat(base_url, final_output, segment_dir="segments_temp"):
    os.makedirs(segment_dir, exist_ok=True)
    list_file_path = os.path.join(segment_dir, "list.txt")
    index = 0

    with open(list_file_path, "w") as list_f:
        while True:
            ts_url = f"{base_url}{index}.ts"
            filename = f"seg_{index:04}.ts"
            full_path = os.path.join(segment_dir, filename)

            response = requests.get(ts_url)
            if response.status_code == 200:
                with open(full_path, "wb") as f:
                    f.write(response.content)
                list_f.write(f"file '{filename}'\n")
                print(f"✅ Downloaded: {ts_url}")
                index += 1
            else:
                print(f"❌ {ts_url} not found (end of list).")
                break

    if index == 0:
        print(f"⚠️ No segments found for {base_url}")
        return False

    os.chdir(segment_dir)
    result = subprocess.run([
        "ffmpeg", "-f", "concat", "-safe", "0",
        "-i", "list.txt", "-c", "copy", os.path.basename(final_output)
    ])
    os.chdir("..")

    if result.returncode == 0:
        os.makedirs(os.path.dirname(final_output), exist_ok=True)
        shutil.move(os.path.join(segment_dir, os.path.basename(final_output)), final_output)
        print(f"🎉 Final video saved at: {final_output}")
    else:
        print(f"❌ Error concatenating video: {final_output}")
        return False

    shutil.rmtree(segment_dir)
    return True

# CLI arguments
parser = argparse.ArgumentParser(description="HLS (.ts) video downloader - single or batch mode via CSV")
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument("--url", help="Base URL of the video (excluding the segment number)")
group.add_argument("--csv", help="Path to the CSV file containing video entries")

parser.add_argument("-o", "--output", help="Name of the final output file (for single URL mode). Default: video_final.mp4")
args = parser.parse_args()

if args.url:
    base_url = args.url.rstrip('/')
    output_name = args.output if args.output else "video_final.mp4"
    output_path = os.path.join("output", output_name)
    print(f"\n🔽 Starting single video download: {base_url}")
    download_and_concat(base_url, output_path)

elif args.csv:
    with open(args.csv, newline='', encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            dir_name = row["dir_name"]
            video_num = row["video_num"]
            video_name = row["video_name"]
            base_url = row["base_url"].rstrip('/')

            final_filename = f"{video_num}_{video_name}.mp4"
            output_path = os.path.join("output", dir_name, final_filename)

            print(f"\n🔽 Starting download: {final_filename}")
            print(f"📂 Folder: {dir_name} | 🌐 Base URL: {base_url}")
            success = download_and_concat(base_url, output_path)

            if not success:
                print(f"⚠️ Failed to process: {video_name}")

