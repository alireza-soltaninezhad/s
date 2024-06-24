from flask import Flask, request, render_template, send_from_directory, Response
import os
import threading
import psutil
import time
import matplotlib.pyplot as plt
import subprocess
import re
from moviepy.editor import VideoFileClip

app = Flask(__name__)

VIDEO_FOLDER = 'VIDEO_FOLDER'  # Path to your video folder
OUTPUT_FOLDER = 'OUTPUT_FOLDER'  # Path where outputs are saved


@app.route('/', methods=['GET', 'POST'])
def index3():
    videos = os.listdir(VIDEO_FOLDER)
    if request.method == 'POST':
        video_name = request.form['video']
        count = int(request.form['count'])
        video_path = os.path.join(VIDEO_FOLDER, video_name)
        video_duration = get_video_duration_moviepy(
            video_path) or 300  # Default to 300 seconds if no duration is fetched

        stats = []
        monitor_thread = threading.Thread(target=monitor_performance, args=(stats, video_duration, video_name))
        monitor_thread.start()

        print(f"Started playing {count} instances of {video_name}.")
        return render_template('play_videos.html', video_name=video_name, count=count)

    return render_template('index3.html', videos=videos)


@app.route('/video/<filename>')
def stream_video(filename):
    return send_file_with_range(os.path.join(VIDEO_FOLDER, filename))


def send_file_with_range(path):
    range_header = request.headers.get('Range', None)
    if not range_header:
        return send_from_directory(VIDEO_FOLDER, os.path.basename(path))

    size = os.path.getsize(path)
    byte1, byte2 = 0, None

    m = re.search(r'bytes=(\d+)-(\d*)', range_header)
    if m:
        byte1, byte2 = map(lambda x: int(x) if x else None, m.groups())

    byte2 = byte2 or size - 1
    length = byte2 - byte1 + 1
    data = None
    with open(path, 'rb') as f:
        f.seek(byte1)
        data = f.read(length)

    rv = Response(data, 206, mimetype="video/mp4", content_type="video/mp4", direct_passthrough=True)
    rv.headers.add('Content-Range', f'bytes {byte1}-{byte2}/{size}')
    rv.headers.add('Accept-Ranges', 'bytes')
    return rv


def get_video_duration_moviepy(video_path):
    """ Get video duration using moviepy. """
    try:
        with VideoFileClip(video_path) as video:
            duration = video.duration
            print(f"Video duration for {video_path}: {duration} seconds")
            return duration
    except Exception as e:
        print(f"Error obtaining duration from video {video_path}: {e}")
        return None


def monitor_performance(stats, duration, filename):
    print("Monitoring started.")
    start_time = time.time()
    while time.time() - start_time < duration:
        cpu = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory().percent
        net = psutil.net_io_counters()
        stats.append((cpu, memory, net.bytes_sent / (1024 ** 3), net.bytes_recv / (1024 ** 3)))  # Convert bytes to GB
        print(
            f"Monitoring: CPU {cpu}%, Memory {memory}%, Net Sent {net.bytes_sent / (1024 ** 3)} GB, Net Received {net.bytes_recv / (1024 ** 3)} GB")
    save_and_plot(stats, filename)


def save_and_plot(stats, filename):
    cpus, memories, sent, recv = zip(*stats)
    avg_cpu = sum(cpus) / len(cpus)
    avg_memory = sum(memories) / len(memories)
    avg_sent = sum(sent) / len(sent)
    avg_recv = sum(recv) / len(recv)

    text_file_path = os.path.join(OUTPUT_FOLDER, f'{filename}_averages.txt')
    with open(text_file_path, 'w') as f:
        f.write(f'Average CPU: {avg_cpu}%\n')
        f.write(f'Average Memory: {avg_memory}%\n')
        f.write(f'Average Sent: {avg_sent:.6f} GB\n')
        f.write(f'Average Received: {avg_recv:.6f} GB\n')
    print(f"Monitoring data saved to {text_file_path}")

    plot_file_path = os.path.join(OUTPUT_FOLDER, f'{filename}_performance.png')
    plt.figure(figsize=(10, 15))

    plt.subplot(3, 1, 1)
    plt.plot(cpus, label='CPU Usage (%)')
    plt.xlabel('Time (seconds)')
    plt.ylabel('CPU Usage (%)')
    plt.legend(loc='upper right')

    plt.subplot(3, 1, 2)
    plt.plot(memories, label='Memory Usage (%)')
    plt.xlabel('Time (seconds)')
    plt.ylabel('Memory Usage (%)')
    plt.legend(loc='upper right')

    plt.subplot(3, 1, 3)
    plt.plot(sent, label='Network Sent (GB)')
    plt.plot(recv, label='Network Received (GB)')
    plt.xlabel('Time (seconds)')
    plt.ylabel('Network (GB)')
    plt.legend(loc='upper right')

    plt.tight_layout()
    plt.savefig(plot_file_path)
    plt.close()
    print(f"Performance plot saved to {plot_file_path}.")


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
