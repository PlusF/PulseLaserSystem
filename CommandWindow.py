import time
import tkinter as tk
from tkinter import ttk
import threading


WIDTH = 300
HEIGHT = 300
WIDTH_ENTRY = 5


class CommandWindow(tk.Toplevel):
    def __init__(self, main_window, cl, stage, laser):
        super().__init__()
        self.main_window = main_window
        self.cl = cl
        self.stage = stage
        self.laser = laser

        self.create_widgets()

        self.update_canvas()
        self.bind('<Key>', self.update_canvas)

    def create_widgets(self):
        frame_setting = ttk.LabelFrame(self)
        self.canvas = tk.Canvas(self, width=WIDTH, height=HEIGHT, background='white')
        frame_setting.grid(row=0, column=0)
        self.canvas.grid(row=1, column=0)

        self.shape = tk.IntVar(value=0)
        radio_line = ttk.Radiobutton(frame_setting, text="Line", command=self.update, variable=self.shape, value=0)
        radio_rect = ttk.Radiobutton(frame_setting, text="Rectangle", command=self.update, variable=self.shape, value=1)
        label_x = ttk.Label(frame_setting, text='X [\u03bcm]')
        label_y = ttk.Label(frame_setting, text='Y [\u03bcm]')
        self.x = tk.IntVar(value=100)
        self.y = tk.IntVar(value=100)
        entry_x = ttk.Entry(frame_setting, textvariable=self.x, width=WIDTH_ENTRY, justify=tk.RIGHT)
        entry_y = ttk.Entry(frame_setting, textvariable=self.y, width=WIDTH_ENTRY, justify=tk.RIGHT)
        label_vel = ttk.Label(frame_setting, text='Vel [\u03bcm/s]')
        self.vel = tk.IntVar(value=100)
        entry_vel = ttk.Entry(frame_setting, textvariable=self.vel, width=WIDTH_ENTRY, justify=tk.RIGHT)
        self.is_filled = tk.BooleanVar(value=False)
        self.check_fill = ttk.Checkbutton(frame_setting, text="Fill", command=self.update, variable=self.is_filled, state=tk.DISABLED)
        self.interval = tk.IntVar(value=5)
        self.entry_interval = ttk.Entry(frame_setting, textvariable=self.interval, width=WIDTH_ENTRY, state=tk.DISABLED, justify=tk.RIGHT)
        self.label_interval = ttk.Label(frame_setting, text='\u03bcm毎', state=tk.DISABLED)
        self.direction = tk.IntVar(value=0)
        self.radio_vertical = ttk.Radiobutton(frame_setting, text="縦", command=self.update, variable=self.direction, value=0, state=tk.DISABLED)
        self.radio_horizontal = ttk.Radiobutton(frame_setting, text="横", command=self.update, variable=self.direction, value=1, state=tk.DISABLED)
        button_exec = ttk.Button(frame_setting, text='EXEC', command=self.exec_command)
        radio_line.grid(row=0, column=1, sticky='W')
        radio_rect.grid(row=1, column=1, sticky='W')
        label_x.grid(row=0, column=2, sticky='W')
        label_y.grid(row=1, column=2, sticky='W')
        entry_x.grid(row=0, column=3, sticky='W')
        entry_y.grid(row=1, column=3, sticky='W')
        label_vel.grid(row=2, column=2, sticky='W')
        entry_vel.grid(row=2, column=3, sticky='W')
        self.check_fill.grid(row=0, column=4, sticky='W')
        self.entry_interval.grid(row=0, column=5, sticky='W')
        self.label_interval.grid(row=0, column=6, sticky='W')
        self.radio_vertical.grid(row=1, column=5, sticky='E')
        self.radio_horizontal.grid(row=1, column=6, sticky='W')
        button_exec.grid(row=2, column=4, columnspan=3)

    def update(self):
        if self.shape.get() == 0:
            self.is_filled.set(False)
            self.check_fill.config(state=tk.DISABLED)
        elif self.shape.get() == 1:
            self.check_fill.config(state=tk.ACTIVE)

        if self.is_filled.get():
            self.entry_interval.config(state=tk.ACTIVE)
            self.label_interval.config(state=tk.ACTIVE)
            self.radio_vertical.config(state=tk.ACTIVE)
            self.radio_horizontal.config(state=tk.ACTIVE)
        else:
            self.entry_interval.config(state=tk.DISABLED)
            self.label_interval.config(state=tk.DISABLED)
            self.radio_vertical.config(state=tk.DISABLED)
            self.radio_horizontal.config(state=tk.DISABLED)

        self.update_canvas()

    def update_canvas(self, event=None):
        self.canvas.delete("all")

        points, _, lasers = self.get_points()
        points = points + [[0, 0]]

        max_x = max([abs(p[0]) for p in points] + [1])
        max_y = max([abs(p[1]) for p in points] + [1])
        amplitude = min(WIDTH / max_x, HEIGHT / max_y) / 2
        start_x = WIDTH / 2 - max_x / 2 * amplitude
        start_y = HEIGHT / 2 + max_y / 2 * amplitude

        # START POSITION
        r = 3
        self.canvas.create_oval(start_x - r, start_y - r, start_x + r, start_y + r, fill='red', width=0)

        for i in range(len(lasers)):
            x0, y0 = points[i - 1]
            x1, y1 = points[i]
            x0 = start_x + x0 * amplitude
            x1 = start_x + x1 * amplitude
            y0 = start_y + y0 * amplitude
            y1 = start_y + y1 * amplitude
            if lasers[i]:
                self.canvas.create_line(x0, y0, x1, y1, fill='green', width=1)
            else:
                self.canvas.create_line(x0, y0, x1, y1, fill='green', width=1, dash=(1, 1))

    def exec_command(self):
        thread = threading.Thread(target=self.move_shape)
        thread.daemon = True
        thread.start()

    def get_points(self):
        try:
            shape, x, y, vel, d = self.shape.get(), self.x.get(), self.y.get(), self.vel.get(), self.interval.get()
        except tk.TclError:
            return [], [], []
        if d <= 0:
            return [], [], []

        if shape == 0:  # Line
            points = [[x, -y]]  # この系のy軸は下向きが正
            delays = [max(abs(x), abs(y)) / vel]
        elif shape == 1:  # Rectangle
            points = [[x, 0],
                      [x, -y],  # この系のy軸は下向きが正
                      [0, -y],  # この系のy軸は下向きが正
                      [0, 0]]
            delays = [abs(x) / vel, abs(y) / vel, abs(x) / vel, abs(y) / vel]
        else:
            return

        if self.is_filled.get():
            if self.direction.get() == 0:  # 縦
                n = (abs(x) // d + 1) * 2
                points = [
                    [d * (i // 2), -y * (1 if i%4 in [1, 2] else 0)] for i in range(1, n)
                ]
            elif self.direction.get() == 1:  # 横
                n = (abs(y) // d + 1) * 2
                points = [
                    [x * (1 if i%4 in [1, 2] else 0), -d * (i // 2)] for i in range(1, n)
                ]
            lasers = [False if i%2 else True for i in range(n - 1)]
            delays = [d / vel if i%2 else abs(y) / vel for i in range(n - 1)]
        else:
            lasers = [True] * len(points)

        return points, delays, lasers

    def move_shape(self):
        x0, y0 = self.main_window.x_cur.get(), - self.main_window.y_cur.get()
        points, delays, lasers = self.get_points()

        if self.cl.mode == 'DEBUG':
            print('move shape')
            return

        self.stage.set_velocity_all(self.vel.get())

        for (x, y), delay, laser in zip(points, delays, lasers):
            if self.main_window.is_auto_emission.get():  # 自動照射モード
                if laser:
                    self.main_window.emit()
                else:
                    self.main_window.stop_laser()
            self.stage.move_line((x0 + x) * 0.001, (y0 + y) * 0.001)
            time.sleep(delay + 0.3)

        if self.main_window.is_auto_emission.get():  # 自動照射モード
            self.main_window.stop_laser()
