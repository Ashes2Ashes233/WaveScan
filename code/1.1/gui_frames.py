#gui_frames.py

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import webbrowser
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk


class ConnectionFrame(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.columnconfigure(0, weight=1);
        self.columnconfigure(2, weight=1)
        self.rowconfigure(0, weight=1);
        self.rowconfigure(8, weight=1)
        center_frame = ttk.Frame(self)
        center_frame.grid(row=1, column=1, rowspan=7)
        ttk.Label(center_frame, text="Instrument IP Address:", font=("Helvetica", 12)).pack(pady=(20, 5))
        self.ip_entry = ttk.Entry(center_frame, width=30, justify='center')
        self.ip_entry.insert(0, "127.0.0.1")
        self.ip_entry.pack(pady=5, ipady=4)
        ttk.Label(center_frame, text="Port:", font=("Helvetica", 12)).pack(pady=(5, 5))
        self.port_entry = ttk.Entry(center_frame, width=10, justify='center')
        self.port_entry.insert(0, "5023")
        self.port_entry.pack(pady=5)
        button_frame = ttk.Frame(center_frame)
        button_frame.pack(pady=10)
        self.connect_button = ttk.Button(button_frame, text="Connect", command=self.connect_device)
        self.connect_button.pack(side="left", padx=5)
        self.disconnect_button = ttk.Button(button_frame, text="Disconnect", command=self.disconnect_device,
                                            state="disabled")
        self.disconnect_button.pack(side="left", padx=5)
        self.status_label = ttk.Label(center_frame, text="Status: Not Connected", foreground="red",
                                      font=("Helvetica", 10))
        self.status_label.pack(pady=5)
        self.device_id_label = ttk.Label(center_frame, text="Instrument: N/A", font=("Helvetica", 9))
        self.device_id_label.pack(pady=5)
        self.next_button = ttk.Button(center_frame, text="Continue to Test", state="disabled",
                                      command=lambda: controller.show_frame("RunningFrame"))
        self.next_button.pack(pady=20)
        about_button = ttk.Button(center_frame, text="About",
                                  command=lambda: webbrowser.open_new("https://github.com/Ashes2Ashes233/WaveScan"))
        about_button.pack(pady=10)

    def connect_device(self):
        ip, port = self.ip_entry.get(), self.port_entry.get()
        if not ip or not port:
            messagebox.showerror("Error", "IP Address and Port cannot be empty.")
            return
        if self.controller.connect_instrument(ip, port):
            self.status_label.config(text="Status: Connected", foreground="green")
            self.device_id_label.config(text=f"Instrument: {self.controller.get_device_id()}")
            self.connect_button.config(state="disabled");
            self.disconnect_button.config(state="normal");
            self.next_button.config(state="normal")
        else:
            messagebox.showerror("Connection Failed",
                                 f"Cannot connect to {ip}:{port}.\nPlease check IP/Port or use Fake Analyzer.")

    def disconnect_device(self):
        self.controller.disconnect_instrument()
        self.status_label.config(text="Status: Not Connected", foreground="red")
        self.device_id_label.config(text="Instrument: N/A")
        self.connect_button.config(state="normal");
        self.disconnect_button.config(state="disabled");
        self.next_button.config(state="disabled")


class SettingsFrame(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.entries = {}
        ttk.Label(self, text="Report Configuration", font=("Helvetica", 16, "bold")).pack(pady=10)
        frame = ttk.LabelFrame(self, text="Report Metadata")
        frame.pack(pady=10, padx=20)
        fields = [("Test name", ""), ("Test type", "Normal"), ("Sample number", ""), ("Model number", ""),
                  ("Lab request", ""), ("Tester", ""), ("Equipment", "Keysight X-Series")]
        for i, (label_text, default_value) in enumerate(fields):
            label = ttk.Label(frame, text=label_text + ":")
            label.grid(row=i, column=0, sticky="e", padx=5, pady=5)
            widget = ttk.Entry(frame, width=40)
            widget.insert(0, default_value)
            widget.grid(row=i, column=1, sticky="ew", padx=5, pady=5)
            self.entries[label_text] = widget
        button_frame = ttk.Frame(self)
        button_frame.pack(pady=20)
        ttk.Button(button_frame, text="Generate Report", command=self.confirm_and_generate_report).pack(side="left",
                                                                                                        padx=10)
        ttk.Button(button_frame, text="Back to Test", command=lambda: self.controller.show_frame("RunningFrame")).pack(
            side="left", padx=10)

    def confirm_and_generate_report(self):
        self.controller.settings = {key: widget.get() for key, widget in self.entries.items()}
        self.controller.generate_final_report()


class RunningFrame(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        main_pane = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_pane.pack(fill=tk.BOTH, expand=True)
        left_frame = ttk.Frame(main_pane)
        main_pane.add(left_frame, weight=1)

        # Live Test Control
        live_control_frame = ttk.LabelFrame(left_frame, text="Live Test Control")
        live_control_frame.pack(fill=tk.X, pady=5, padx=5)
        self.start_button = ttk.Button(live_control_frame, text="Start", command=self.start_test)
        self.start_button.pack(side="left", padx=5)
        self.stop_button = ttk.Button(live_control_frame, text="Stop", command=self.stop_test, state="disabled")
        self.stop_button.pack(side="left", padx=5)
        ttk.Label(live_control_frame, text="Time (min):").pack(side="left", padx=(10, 5))
        self.test_time_entry = ttk.Entry(live_control_frame, width=6)
        self.test_time_entry.insert(0, "1")
        self.test_time_entry.pack(side="left", padx=5)
        self.rate_label = ttk.Label(live_control_frame, text="Rate: 0.0 Hz")
        self.rate_label.pack(side="left", padx=(10, 5))

        # Top Frequencies Table
        table_frame = ttk.LabelFrame(left_frame, text="Top Frequencies")
        table_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        cols = ("Rank", "Frequency (MHz)", "Hits")
        self.tree = ttk.Treeview(table_frame, columns=cols, show='headings', height=8)
        for col in cols:
            self.tree.heading(col, text=col);
            self.tree.column(col, width=80, anchor='center')
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Post-Test Analysis Panel
        self.analysis_frame = ttk.LabelFrame(left_frame, text="Post-Test Analysis")
        self.analysis_frame.pack(fill=tk.X, padx=5, pady=(10, 5))
        ttk.Label(self.analysis_frame, text="Start (s):").grid(row=0, column=0, padx=5, pady=5)
        self.start_entry = ttk.Entry(self.analysis_frame, width=8)
        self.start_entry.grid(row=0, column=1)
        ttk.Label(self.analysis_frame, text="End (s):").grid(row=0, column=2, padx=5, pady=5)
        self.end_entry = ttk.Entry(self.analysis_frame, width=8)
        self.end_entry.grid(row=0, column=3)
        self.show_range_button = ttk.Button(self.analysis_frame, text="Show Range", command=self.show_ranged_view)
        self.show_range_button.grid(row=0, column=4, padx=5)
        self.show_overall_button = ttk.Button(self.analysis_frame, text="Show Overall", command=self.show_overall_view)
        self.show_overall_button.grid(row=0, column=5, padx=5)

        # Right Panel
        right_frame = ttk.Frame(main_pane)
        main_pane.add(right_frame, weight=2)
        plot_frame = ttk.LabelFrame(right_frame, text="Frequency Distribution")
        plot_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.fig = Figure(figsize=(8, 6), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_frame)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.toolbar = NavigationToolbar2Tk(self.canvas, plot_frame);
        self.toolbar.update()
        report_frame = ttk.LabelFrame(right_frame, text="Report Notes")
        report_frame.pack(fill=tk.X, padx=5, pady=5)
        self.observations_text = scrolledtext.ScrolledText(report_frame, height=4)
        self.observations_text.pack(fill=tk.X, expand=True, padx=5, pady=5)
        self.create_report_button = ttk.Button(right_frame, text="Generate Report", command=self.proceed_to_report)
        self.create_report_button.pack(pady=10)
        self.toggle_analysis_controls(False)

    def start_test(self):
        try:
            test_time = int(self.test_time_entry.get())
            if test_time <= 0: raise ValueError()
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a valid positive number for test time (minutes).")
            return
        self.toggle_analysis_controls(False)
        self.create_report_button.config(state="disabled")
        self.controller.start_data_acquisition(duration_minutes=test_time)
        self.start_button.config(state="disabled");
        self.stop_button.config(state="normal");
        self.test_time_entry.config(state="disabled")
        self.rate_label.config(text="Rate: ... Hz")

    def stop_test(self):
        self.controller.stop_data_acquisition()
        self.start_button.config(state="normal");
        self.stop_button.config(state="disabled");
        self.test_time_entry.config(state="normal")
        self.rate_label.config(text="Rate: 0.0 Hz")

    def toggle_analysis_controls(self, enable=False):
        state = "normal" if enable else "disabled"
        for child in self.analysis_frame.winfo_children():
            child.configure(state=state)

    def show_ranged_view(self):
        try:
            start_s = float(self.start_entry.get())
            end_s = float(self.end_entry.get())
            if start_s < 0 or end_s <= start_s: raise ValueError()
            self.controller.display_ranged_stats(start_s, end_s)
        except (ValueError, TypeError):
            messagebox.showerror("Invalid Input", "Please enter a valid numerical time range where End > Start.")

    def show_overall_view(self):
        self.controller.display_overall_stats()

    def update_live_stats(self, rate):
        self.rate_label.config(text=f"Rate: {rate:.1f} Hz")

    def on_test_finished(self):
        self.create_report_button.config(state="normal")
        self.toggle_analysis_controls(True)
        # Display final overall stats
        self.controller.display_overall_stats()

    def proceed_to_report(self):
        self.controller.prepare_for_report(self.observations_text.get("1.0", tk.END).strip())
        self.controller.show_frame("SettingsFrame")