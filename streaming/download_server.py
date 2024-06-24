from flask import Flask, Response, send_from_directory
import os
import psutil
import time
import threading
import matplotlib.pyplot as plt
from moviepy.editor import VideoFileClip

app = Flask(__name__)

VIDEO_FOLDER = 'VIDEO_FOLDER'  # Update this path to your video folder
OUTPUT_FOLDER = 'OUTPUT_FOLDER'  # Ensure this directory exists and is writable

@app.route('/')
def index():
    videos = os.listdir(VIDEO_FOLDER)
    links = [f'<li><a href="/video/{video}">{video}</a></li>' for video in videos]
    return f'<h1>Videos</h1><ul>{"".join(links)}</ul>'

def get_video_duration(video_path):
    try:
        with VideoFileClip(video_path) as video:
            return video.duration
    except Exception as e:
        print(f"Error reading video file {video_path}: {e}")
        return None  # Return None if there's an error

def monitor_performance(filename, interval=1):
    try:
        video_path = os.path.join(VIDEO_FOLDER, filename)
        video_duration = get_video_duration(video_path)
        if video_duration is None:  # Check if duration could not be determined
            return
        stats = []
        start_time = time.time()

        while time.time() - start_time < video_duration:
            cpu = psutil.cpu_percent(interval=interval)
            memory = psutil.virtual_memory().percent
            stats.append((time.time() - start_time, cpu, memory))
            time.sleep(interval)
            save_incremental(stats[-1], filename)  # Save data incrementally

        save_and_plot(stats, filename)
    except Exception as e:
        print(f"Error during monitoring: {e}")

def save_incremental(stat, filename):
    text_file_path = os.path.join(OUTPUT_FOLDER, f'{filename}_usage.txt')
    with open(text_file_path, 'a') as f:
        timestamp, cpu, memory = stat
        f.write(f'{timestamp:.2f}, {cpu}, {memory}\n')

    print(f"Appended data to {text_file_path} at {timestamp:.2f} seconds")

def save_and_plot(stats, filename):
    text_file_path = os.path.join(OUTPUT_FOLDER, f'{filename}_usage.txt')
    plot_file_path = os.path.join(OUTPUT_FOLDER, f'{filename}_plot.png')

    # Calculate average CPU and Memory usage
    if stats:
        avg_cpu = sum(cpu for _, cpu, _ in stats) / len(stats)
        avg_memory = sum(memory for _, _, memory in stats) / len(stats)

    # Write all data and averages to the text file
    with open(text_file_path, 'w') as f:  # Using 'w' to write from the beginning
        for timestamp, cpu, memory in stats:
            f.write(f'{timestamp:.2f}, {cpu}, {memory}\n')
        # Append averages at the end
        f.write(f'\nAverage CPU Usage: {avg_cpu:.2f}%\n')
        f.write(f'Average Memory Usage: {avg_memory:.2f}%\n')

    print(f"Saved monitoring data to {text_file_path}")
    print(f"Average CPU Usage: {avg_cpu:.2f}%, Average Memory Usage: {avg_memory:.2f}%")

    # Plotting
    times, cpus, memories = zip(*stats)
    plt.figure(figsize=(10, 5))
    plt.plot(times, cpus, label='CPU Usage (%)')
    plt.plot(times, memories, label='Memory Usage (%)')
    plt.xlabel('Time (seconds)')
    plt.ylabel('Usage (%)')
    plt.title('CPU and Memory Usage Over Time')
    plt.legend()
    plt.savefig(plot_file_path)
    print(f"Saved usage plot to {plot_file_path}")

@app.route('/video/<filename>')
def stream_video(filename):
    monitor_thread = threading.Thread(target=monitor_performance, args=(filename,))
    monitor_thread.start()

    return send_from_directory(VIDEO_FOLDER, filename)

if __name__ == '__main__':
    app.run(debug=True, threaded=True, host='0.0.0.0')
