#main_app.py

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import time
import queue
import numpy as np
from datetime import datetime
from collections import defaultdict
import os

from gui_frames import ConnectionFrame, SettingsFrame, RunningFrame
#from instrument_controller import FakeSignalAnalyzer as InstrumentController
from instrument_controller import SignalAnalyzerController as InstrumentController
from report_generator import generate_pdf_report
from matplotlib.figure import Figure


class SpectrumAnalyzerApp(tk.Tk):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title("WaveScan - Microwave Spectrum Analyzer")
        self.geometry("1200x800")
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # 状态变量
        self.instrument = None
        self.is_running = False
        self.data_queue = queue.Queue(maxsize=20000)
        self.data_thread = None
        self.stop_thread = threading.Event()

        self.test_timer = None
        self.test_start_time = None

        self.historical_data_list = []
        self.historical_data_np = None
        self.analysis_range = None  # None for 'Overall', (start, end) for 'Ranged'

        self.frequency_counts = defaultdict(int)
        self.top_frequencies = []
        self.reads_since_last_update = 0
        self.last_update_time = time.time()

        self.settings = {}
        self.report_observations = ""

        # UI 设置
        container = ttk.Frame(self)
        container.pack(side="top", fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1);
        container.grid_columnconfigure(0, weight=1)
        self.frames = {}
        for F in (ConnectionFrame, RunningFrame, SettingsFrame):
            frame = F(parent=container, controller=self)
            self.frames[F.__name__] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame("ConnectionFrame")
        self.after(250, self.process_queue)  # UI update loop

    def show_frame(self, page_name):
        self.frames[page_name].tkraise()

    def connect_instrument(self, ip, port):
        self.instrument = InstrumentController(ip, port)
        return self.instrument.connect()

    def disconnect_instrument(self):
        if self.instrument: self.instrument.close(); self.instrument = None

    def get_device_id(self):
        if self.instrument and self.instrument.connected:
            # 修正了 SignalAnalyzerController 的判断
            return self.instrument.query("*IDN?") if not isinstance(self.instrument,
                                                                    InstrumentController) else self.instrument.query(
                "*IDN?")
        return "N/A"

    def start_data_acquisition(self, duration_minutes):
        self.is_running = True
        self.stop_thread.clear()
        self.test_start_time = time.time()
        # Reset all data stores
        self.historical_data_list.clear();
        self.historical_data_np = None;
        self.analysis_range = None
        self.frequency_counts.clear();
        self.top_frequencies.clear()
        self.reads_since_last_update = 0;
        self.last_update_time = time.time()
        while not self.data_queue.empty(): self.data_queue.get()

        test_end_time = self.test_start_time + duration_minutes * 60
        self.check_test_time(test_end_time)

        self.data_thread = threading.Thread(target=self._data_acquisition_loop, daemon=True)
        self.data_thread.start()
        # 立即显示一个空的“实时”视图
        self.display_overall_stats()

    def check_test_time(self, end_time):
        if self.is_running and time.time() >= end_time:
            self.frames["RunningFrame"].stop_test()
            messagebox.showinfo("Test Completed", "The specified test duration has been reached.")
        elif self.is_running:
            self.test_timer = self.after(1000, lambda: self.check_test_time(end_time))

    def stop_data_acquisition(self):
        if not self.is_running: return
        self.is_running = False
        self.stop_thread.set()
        if self.test_timer: self.after_cancel(self.test_timer); self.test_timer = None
        if self.data_thread and self.data_thread.is_alive(): self.data_thread.join(timeout=0.5)

        self.process_queue(force_process_all=True)

        if self.historical_data_list:
            self.historical_data_np = np.array(self.historical_data_list)
            self.historical_data_list.clear()

        self.frames["RunningFrame"].on_test_finished()

    def _data_acquisition_loop(self):
        while not self.stop_thread.is_set():
            try:
                peak_freq = self.instrument.read_peak_frequency()
                if peak_freq is not None:
                    timestamp = time.time() - self.test_start_time
                    if not self.data_queue.full():
                        self.data_queue.put((timestamp, round(peak_freq)))
            except Exception as e:
                print(f"Data acquisition error: {e}");
                self.stop_data_acquisition();
                break
        print("Data acquisition thread stopped.")

    def process_queue(self, force_process_all=False):
        reads_this_batch = 0
        while not self.data_queue.empty():
            try:
                timestamp, freq = self.data_queue.get_nowait()
                self.frequency_counts[freq] += 1
                if self.historical_data_np is None: self.historical_data_list.append((timestamp, freq))
                reads_this_batch += 1
            except queue.Empty:
                break

        now = time.time()
        if reads_this_batch > 0: self.reads_since_last_update += reads_this_batch

        elapsed = now - self.last_update_time
        if elapsed > 0.25:  # 更新间隔可以稍长一些
            rate = self.reads_since_last_update / elapsed
            self.frames["RunningFrame"].update_live_stats(rate)
            self.last_update_time = now
            self.reads_since_last_update = 0
            # 如果测试正在运行，则用最新的“全时段”数据更新主显示
            if self.is_running:
                self.display_overall_stats()

        if not force_process_all: self.after(250, self.process_queue)

    def update_main_display(self, counts_to_show, top_5_to_show, title_prefix):
        frame = self.frames["RunningFrame"]
        ax = frame.ax
        # 更新表格
        frame.tree.delete(*frame.tree.get_children())
        for rank, (freq, count) in enumerate(top_5_to_show, 1):
            frame.tree.insert("", "end", values=(rank, f"{freq}", count))

        # 更新图表
        ax.clear()
        if counts_to_show:
            sorted_bins = sorted(counts_to_show.items())
            ax.bar([b[0] for b in sorted_bins], [b[1] for b in sorted_bins], width=0.8, color='steelblue')
            for rank, (freq, count) in enumerate(top_5_to_show, 1):
                ax.annotate(f"#{rank}", (freq, count), textcoords="offset points", xytext=(0, 5), ha='center')

        # 根据是否在运行来决定标题
        final_title_prefix = f"{title_prefix} (Live)" if self.is_running and title_prefix == "Overall" else title_prefix
        ax.set_title(f"{final_title_prefix} Frequency Distribution (2400-2500 MHz)")
        ax.set_xlabel("Frequency (MHz)");
        ax.set_ylabel("Count")
        ax.grid(True, linestyle='--', alpha=0.7);
        ax.set_xlim(2400, 2500)
        frame.canvas.draw()

    def display_ranged_stats(self, start_sec, end_sec):
        self.analysis_range = (start_sec, end_sec)
        counts, top_5 = self.get_stats_for_range(start_sec, end_sec)
        if counts is None or not counts:
            messagebox.showwarning("No Data", f"No data found in the time range {start_sec}s - {end_sec}s.")
            self.analysis_range = None
            return
        self.update_main_display(counts, top_5, f"Range ({start_sec:.1f}s - {end_sec:.1f}s)")

    def display_overall_stats(self):
        self.analysis_range = None
        self.top_frequencies = sorted(self.frequency_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        self.update_main_display(self.frequency_counts, self.top_frequencies, "Overall")

    def get_stats_for_range(self, start_sec, end_sec):
        if self.historical_data_np is None: return None, None
        mask = (self.historical_data_np[:, 0] >= start_sec) & (self.historical_data_np[:, 0] <= end_sec)
        ranged_data = self.historical_data_np[mask]
        if ranged_data.shape[0] == 0: return {}, []
        unique_freqs, counts = np.unique(ranged_data[:, 1], return_counts=True)
        ranged_counts = dict(zip(unique_freqs.astype(int), counts))
        top_5 = sorted(ranged_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        return ranged_counts, top_5

    def generate_ranged_plot(self, start_sec, end_sec):
        counts, top_5 = self.get_stats_for_range(start_sec, end_sec)
        if not counts: return None
        fig = Figure(figsize=(8, 6), dpi=100)
        ax = fig.add_subplot(111)
        sorted_bins = sorted(counts.items())
        ax.bar([b[0] for b in sorted_bins], [b[1] for b in sorted_bins], width=0.8, color='darkgreen')
        for rank, (freq, count) in enumerate(top_5, 1):
            ax.annotate(f"#{rank}", (freq, count), textcoords="offset points", xytext=(0, 5), ha='center')
        ax.set_title(f"Freq. Distribution ({start_sec:.1f}s - {end_sec:.1f}s)")
        ax.set_xlabel("Frequency (MHz)");
        ax.set_ylabel("Count");
        ax.grid(True);
        ax.set_xlim(2400, 2500)
        return fig

    def prepare_for_report(self, observations):
        self.report_observations = observations

    def generate_final_report(self):
        if not self.frequency_counts: messagebox.showwarning("Warning", "No data collected."); return
        self.settings['Start time'] = datetime.fromtimestamp(self.test_start_time).strftime('%Y-%m-%d %H:%M:%S')
        self.settings['Observations'] = self.report_observations
        # Overall Data
        overall_top_5 = sorted(self.frequency_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        self.settings['main_frequency_data'] = [["Rank", "Frequency (MHz)", "Count"]] + [[r + 1, f, c] for r, (f, c) in
                                                                                         enumerate(overall_top_5)]
        # Ranged Data (if applicable)
        ranged_plot_fig, self.settings['ranged_frequency_data'] = None, None
        if self.analysis_range:
            start_s, end_s = self.analysis_range
            ranged_plot_fig = self.generate_ranged_plot(start_s, end_s)
            _, top_5_ranged = self.get_stats_for_range(start_s, end_s)
            if top_5_ranged:
                self.settings['ranged_frequency_data'] = [["Rank", "Frequency (MHz)", "Count"]] + [[r + 1, f, c] for
                                                                                                   r, (f, c) in
                                                                                                   enumerate(
                                                                                                       top_5_ranged)]
        # Plot Handling
        plot_data_list, temp_files = [], []
        # 使用 self.frames["RunningFrame"].fig 会导致报告中的图是最后显示的图，而不是全时段的图
        # 我们需要为报告专门生成一张全时段的图
        overall_fig = Figure(figsize=(8, 6), dpi=100)
        ax = overall_fig.add_subplot(111)
        # 借用 update_main_display 的逻辑来画图
        overall_counts = self.frequency_counts
        if overall_counts:
            sorted_bins = sorted(overall_counts.items())
            ax.bar([b[0] for b in sorted_bins], [b[1] for b in sorted_bins], width=0.8, color='steelblue')
            for rank, (freq, count) in enumerate(overall_top_5, 1):
                ax.annotate(f"#{rank}", (freq, count), textcoords="offset points", xytext=(0, 5), ha='center')
        ax.set_title("Overall Frequency Distribution (2400-2500 MHz)")
        ax.set_xlabel("Frequency (MHz)");
        ax.set_ylabel("Count")
        ax.grid(True, linestyle='--', alpha=0.7);
        ax.set_xlim(2400, 2500)

        path = "temp_main_plot.png";
        temp_files.append(path)
        overall_fig.savefig(path, dpi=150, bbox_inches='tight')
        plot_data_list.append({'title': "Overall Frequency Distribution", 'path': path})

        if ranged_plot_fig:
            path = "temp_ranged_plot.png";
            temp_files.append(path)
            ranged_plot_fig.savefig(path, dpi=150, bbox_inches='tight')
            plot_data_list.append({'title': "Custom Time-Range Analysis", 'path': path})

        filepath = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF Documents", "*.pdf")])
        if filepath:
            if generate_pdf_report(filepath, self.settings, plot_data_list):
                messagebox.showinfo("Success", f"Report saved to:\n{filepath}")
            else:
                messagebox.showerror("Error", "Failed to generate PDF report.")

        for f in temp_files:
            if os.path.exists(f): os.remove(f)

    def on_closing(self):
        self.stop_thread.set()
        if self.data_thread and self.data_thread.is_alive(): self.data_thread.join(timeout=0.2)
        if self.instrument: self.instrument.close()
        self.destroy()


if __name__ == "__main__":
    app = SpectrumAnalyzerApp()
    app.mainloop()