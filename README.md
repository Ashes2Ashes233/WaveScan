# WaveScan

WaveScan is a desktop application designed to connect to Keysight's X-Series spectrum analyzers. It uses high-frequency polling to collect peak frequencies of devices within specific frequency bands in real time and performs statistical analysis on this massive amount of data, helping engineers quickly and accurately determine the target device's true operating frequency.
**Key Features**

*Real-time Data Acquisition:*
Connects to a Keysight X-Series spectrum analyzer via Telnet to sample high-frequency peak frequencies.
*High Performance:* 
Utilizing a multi-threaded architecture, it separates time-consuming I/O operations from UI responsiveness, ensuring a smooth and real-time interface.
*Dynamic Visualization:*
Real-time display of the data sampling rate (Hz).Dynamically updated frequency distribution histogram.Real-time display of the top 5 most frequently occurring frequencies and their statistical counts.
*Interactive Post-Analysis:*
After the test, you can specify a time range (in seconds) on the main interface to instantly view the frequency distribution graph and data statistics for that time period.
Supports free switching between the "Full Time" view and the "Custom Range" view.
*Professional PDF Reports:*
Generate PDF reports with one click, including test metadata, observation notes, statistical tables, and analysis charts.
If range analysis is performed, the report automatically includes both the "Full Time" and "Custom Range" charts and tables.
*Developer-Friendly:*
Built-in FakeSignalAnalyzer simulator facilitates development and debugging without physical hardware.
