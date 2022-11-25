import time
import tkinter as tk
from tkinter import ttk, messagebox
import threading


class CommandWindow(tk.Toplevel):
    def __init__(self, main_window, cl, stage, laser):
        super().__init__()
        self.main_window = main_window
        self.cl = cl
        self.stage = stage
        self.laser = laser

        self.create_widgets()

    def create_widgets(self):
        label_shape = tk.Label(self, text="図形")

        self.command = tk.StringVar(value='rectangle, 10, 20, 100')
        entry_command = ttk.Entry(self, textvariable=self.command, justify=tk.CENTER)
        button_exec = ttk.Button(self, command=self.exec_command, text='EXEC')

        label_shape.grid(row=0, column=0)
        entry_command.grid(row=0, column=1)
        button_exec.grid(row=0, column=2)

    def exec_command(self):
        command_is_ok, command = self.check_command()
        if not command_is_ok:
            messagebox.showerror('エラー', '無効なコマンドです')
            return

        shape, x, y, vel = command
        msg = f'x: {x} um, y: {y} um の {shape}を速度 {vel} um/s で描きます。'
        ok = messagebox.askyesno('確認', msg)

        if ok:
            thread = threading.Thread(target=self.move_shape, args=tuple(command))
            thread.daemon = True
            thread.start()

    def check_command(self):
        command = self.command.get().split(',')
        command = list(map(lambda s: s.strip(), command))
        command_is_ok = True
        x, y = 0, 0
        vel = 10
        # 形から違う
        if command[0] not in ['line', 'rectangle'] or len(command) < 3 or 4 < len(command):
            command_is_ok = False
        else:
            # 値が無効
            # 座標
            try:
                x = float(command[1])
                y = float(command[2])
            except ValueError:
                command_is_ok = False
            # 速度
            if len(command) == 4:
                try:
                    vel = int(command[3])
                except ValueError:
                    command_is_ok = False
                if vel < 1 or 100000 < vel:
                    command_is_ok = False

        if command_is_ok:
            return True, [command[0], x, y, vel]
        else:
            return False, None

    def move_shape(self, shape, x, y, vel):
        if self.cl.mode == 'DEBUG':
            print(shape, x, y, vel)
            return

        x0, y0 = self.main_window.x_cur.get(), - self.main_window.y_cur.get()
        self.stage.set_velocity_all(vel)

        if shape == 'line':
            points = [[x0 + x, y0 - y]]  # この系のy軸は下向きが正
            delays = [max(abs(x), abs(y)) / vel]
        elif shape == 'rectangle':
            points = [[x0 + x, y0],
                      [x0 + x, y0 - y],  # この系のy軸は下向きが正
                      [x0, y0 - y],  # この系のy軸は下向きが正
                      [x0, y0]]
            delays = [abs(x) / vel, abs(y) / vel, abs(x) / vel, abs(y) / vel]
        else:
            return

        if self.main_window.is_auto_emission.get():  # 自動照射モード
            self.main_window.emit()

        for (x, y), delay in zip(points, delays):
            self.stage.move_line(x * 0.001, y * 0.001)
            time.sleep(delay + 0.3)

        if self.main_window.is_auto_emission.get():  # 自動照射モード
            self.main_window.stop_laser()
