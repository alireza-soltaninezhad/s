from flask import Flask, request, render_template, send_from_directory
import os
import psutil
import time
import threading
import matplotlib.pyplot as plt
from moviepy.editor import VideoFileClip

app = Flask(__name__)

VIDEO_FOLDER = 'VIDEO_FOLDER'  # Update this path to your video folder
OUTPUT_FOLDER = 'OUTPUT_FOLDER'  # Ensure this directory exists and is writable


@app.route('/', methods=['GET', 'POST'])
def index2():
    videos = os.listdir(VIDEO_FOLDER)
    if request.method == 'POST':
        video_name = request.form['video']
        count = int(request.form['count'])
        threads = []
        for i in range(count):
            print(f"Starting thread {i + 1} for video {video_name}")
            t = threading.Thread(target=monitor_performance, args=(video_name,))
            t.start()
            threads.append(t)

        for i, t in enumerate(threads):
            t.join()
            print(f"Thread {i + 1} has completed.")

        return render_template('index2.html', videos=videos,
                               message=f'Successfully monitored {count} instances of {video_name}.')
    return render_template('index2.html', videos=videos)


def get_video_duration(video_path):
    try:
        with VideoFileClip(video_path) as video:
            duration = video.duration
        print(f"Video duration for {video_path}: {duration} seconds")
        return duration
    except Exception as e:
        print(f"Error reading video file {video_path}: {e}")
        return None  # Return None if there's an error


def monitor_performance(filename, interval=1):
    video_path = os.path.join(VIDEO_FOLDER, filename)
    video_duration = get_video_duration(video_path)
    if video_duration is None:  # Check if duration could not be determined
        print("Video duration could not be determined, monitoring skipped.")
        return
    stats = []
    start_time = time.time()

    while time.time() - start_time < video_duration:
        cpu = psutil.cpu_percent(interval=interval)
        memory = psutil.virtual_memory().percent
        stats.append((time.time() - start_time, cpu, memory))
        print(f"Time: {time.time() - start_time:.2f} s, CPU: {cpu}%, Memory: {memory}%")
        time.sleep(interval)

    save_and_plot(stats, filename)


def save_and_plot(stats, filename):
    text_file_path = os.path.join(OUTPUT_FOLDER, f'{filename}_usage.txt')
    plot_file_path = os.path.join(OUTPUT_FOLDER, f'{filename}_plot.png')

    # Calculate average CPU and Memory usage
    if stats:
        avg_cpu = sum(cpu for _, cpu, _ in stats) / len(stats)
        avg_memory = sum(memory for _, _, memory in stats) / len(stats)

    # Write all data and averages to the text file
    with open(text_file_path, 'w') as f:
        for timestamp, cpu, memory in stats:
            f.write(f'{timestamp:.2f}, {cpu}, {memory}\n')
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
    plt.title(f'CPU and Memory Usage Over Time for {filename}')
    plt.legend()
    plt.savefig(plot_file_path)
    print(f"Saved usage plot to {plot_file_path}")


if __name__ == '__main__':
    app.run(debug=True, threaded=True, host='0.0.0.0')
