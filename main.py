import os
import sys
import time
import copy
import threading
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from DS102Controller import MySerial, DS102Controller
from PulseLaserController import PulseLaserController
from CustomTkObject import MovableOval
from ConfigLoader import ConfigLoader


WIDTH_BUTTON = 7
SIZE_CANVAS = 320
SIZE_CONT = 15
FONT = ('游ゴシック', 16)


def get_color_by_float(value: float):
    codes = ['#222', '#333', '#444', '#555', '#666', '#777', '#888', '#999', '#aaa', '#bbb', '#ccc',
             '#ddd', '#eee', '#fff']
    value *= len(codes)
    for i, color in enumerate(codes):
        if value < i:
            return color


class Application(tk.Frame):
    def __init__(self, master=None, config='./config.json'):
        super().__init__(master)
        self.master.title('Stage Controller')

        # フォントサイズの調整
        self.style = ttk.Style()
        if os.name == 'nt':
            self.style.theme_use('winnative')  # windowsにしかないテーマ
        self.style.configure('.', font=FONT)
        self.style.configure("stop.TButton", activeforeground='red', foreground='red')

        self.cl = ConfigLoader(config)

        self.open_port()

        self.create_widgets()

        self.rank_pre = 0
        self.direction_pre = [0, 0]

        self.create_thread()

        self.update()

    def open_port(self):
        if self.cl.mode == 'RELEASE':
            self.ser_stage = MySerial(self.cl.port_stage, self.cl.baudrate_stage, write_timeout=0)
            self.stage = DS102Controller(self.ser_stage)
            self.ser_laser = MySerial(self.cl.port_laser, self.cl.baudrate_laser, write_timeout=0)
            self.laser = PulseLaserController(self.ser_laser)
        elif self.cl.mode == 'DEBUG':
            self.stage = self.laser = None
        else:
            raise ValueError('Wrong format in config.json. Mode must be DEBUG or RELEASE.')

    def create_widgets(self):
        # 親フレーム
        self.frame_stage = ttk.LabelFrame(self.master, text='STAGE')
        self.frame_laser = ttk.LabelFrame(self.master, text='PULSE LASER')
        self.button_quit = ttk.Button(self.master, text='QUIT', command=self.quit, style='stop.TButton')
        self.label_quit = ttk.Label(self.master, text='必ずQUITボタンからプログラムを終了')
        self.frame_stage.grid(row=0, column=0, pady=10)
        self.frame_laser.grid(row=1, column=0, pady=10)
        self.button_quit.grid(row=2, columnspan=2, pady=10)
        self.label_quit.grid(row=3, columnspan=2)
        # 子フレーム
        self.frame_controller_canvas = ttk.Frame(self.frame_stage)
        self.frame_controller_buttons = ttk.Frame(self.frame_stage)
        self.frame_controller_position = ttk.Frame(self.frame_stage)
        self.frame_controller_command = ttk.Frame(self.frame_stage)
        self.button_controller_stop = ttk.Button(self.frame_stage, text='STOP ALL STAGES', command=self.stop_stage, style='stop.TButton')
        self.frame_controller_canvas.grid(row=0, column=0)
        self.frame_controller_buttons.grid(row=1, column=0)
        self.frame_controller_position.grid(row=2, column=0)
        self.frame_controller_command.grid(row=3, column=0)
        self.button_controller_stop.grid(row=4, column=0)
        # ウィジェット canvas
        self.canvas_controller = tk.Canvas(self.frame_controller_canvas, width=SIZE_CANVAS, height=SIZE_CANVAS)
        center = SIZE_CANVAS/2
        r_list = [SIZE_CONT*9, SIZE_CONT*7, SIZE_CONT*5, SIZE_CONT*3, SIZE_CONT*1]
        for i, r in enumerate(r_list):
            color = get_color_by_float(i / len(r_list))
            self.canvas_controller.create_oval(center - r, center - r, center + r, center + r, fill=color)
        MovableOval.canvas = self.canvas_controller
        MovableOval.thres_list = r_list
        self.oval = MovableOval(center - SIZE_CONT, center - SIZE_CONT, center + SIZE_CONT, center + SIZE_CONT, fill='lightblue')
        self.canvas_controller.pack()
        # ウィジェット buttons
        self.vel = tk.IntVar(value=100)
        self.combobox_xy = ttk.Combobox(self.frame_controller_buttons, values=self.cl.vel_list[1:], textvariable=self.vel, justify='center', width=WIDTH_BUTTON)
        self.button_top = ttk.Button(self.frame_controller_buttons, width=WIDTH_BUTTON, text='↑')
        self.button_left = ttk.Button(self.frame_controller_buttons, width=WIDTH_BUTTON, text='←')
        self.button_right = ttk.Button(self.frame_controller_buttons, width=WIDTH_BUTTON, text='→')
        self.button_bottom = ttk.Button(self.frame_controller_buttons, width=WIDTH_BUTTON, text='↓')
        self.button_top.bind('<Button-1>', self.move_top)
        self.button_top.bind('<ButtonRelease-1>', self.stop_stage)
        self.button_left.bind('<Button-1>', self.move_left)
        self.button_left.bind('<ButtonRelease-1>', self.stop_stage)
        self.button_right.bind('<Button-1>', self.move_right)
        self.button_right.bind('<ButtonRelease-1>', self.stop_stage)
        self.button_bottom.bind('<Button-1>', self.move_bottom)
        self.button_bottom.bind('<ButtonRelease-1>', self.stop_stage)
        self.button_top.grid(row=0, column=1)
        self.button_left.grid(row=1, column=0)
        self.combobox_xy.grid(row=1, column=1)
        self.button_right.grid(row=1, column=2)
        self.button_bottom.grid(row=2, column=1)
        # ウィジェット position
        self.x_cur = tk.DoubleVar(value=0)
        self.y_cur = tk.DoubleVar(value=0)
        self.label_x = ttk.Label(self.frame_controller_position, text='X [\u03bcm]')
        self.label_y = ttk.Label(self.frame_controller_position, text='Y [\u03bcm]')
        self.label_x_cur = ttk.Label(self.frame_controller_position, textvariable=self.x_cur)
        self.label_y_cur = ttk.Label(self.frame_controller_position, textvariable=self.y_cur)
        self.label_x.grid(row=0, column=0)
        self.label_x_cur.grid(row=0, column=1)
        self.label_y.grid(row=1, column=0)
        self.label_y_cur.grid(row=1, column=1)
        # ウィジェット command
        self.command = tk.StringVar(value='rectangle, 10, 10')
        self.entry_command = ttk.Entry(self.frame_controller_command, textvariable=self.command)
        self.button_exec = ttk.Button(self.frame_controller_command, command=self.exec_command, text='EXEC')
        self.entry_command.grid(row=0, column=0)
        self.button_exec.grid(row=0, column=1)

        # laser
        self.frq = tk.IntVar(value=30)
        self.entry_frq = ttk.Entry(self.frame_laser, textvariable=self.frq, width=5, justify=tk.CENTER)
        self.label_hz = ttk.Label(self.frame_laser, text='Hz')
        self.button_emit_laser = ttk.Button(self.frame_laser, text='EMIT', command=self.emit)
        self.button_stop_laser = ttk.Button(self.frame_laser, text='STOP', command=self.stop_laser, style='stop.TButton')
        self.msg_laser = tk.StringVar(value='Now: 0 Hz (available range: 16~10000 Hz)')
        self.label_msg_frq = ttk.Label(self.frame_laser, textvariable=self.msg_laser)
        self.is_auto_emission = tk.BooleanVar(value=False)
        self.check_auto_emission = tk.Checkbutton(self.frame_laser, text="Auto Emission", command=self.change_auto_emission, variable=self.is_auto_emission)
        self.entry_frq.grid(row=0, column=0)
        self.label_hz.grid(row=0, column=1)
        self.button_emit_laser.grid(row=0, column=2)
        self.button_stop_laser.grid(row=0, column=3)
        self.label_msg_frq.grid(row=1, column=0, columnspan=4)
        self.check_auto_emission.grid(row=2, column=0, columnspan=4)

    def create_thread(self):
        # update_positionの受信待ちで画面がフリーズしないようthreadを立てる
        self.thread = threading.Thread(target=self.update_position)
        self.thread.daemon = True
        self.thread.start()

    def quit(self):
        if self.cl.mode == 'RELEASE':
            self.ser_stage.close()
            self.ser_laser.close()
        self.master.destroy()
        sys.exit()  # デーモン化してあるスレッドはここで死ぬ

    def update(self):
        # 動く or 止まる
        self.check_and_move()
        self.check_and_stop()
        # previous変数を更新
        self.rank_pre = self.oval.get_rank()
        self.direction_pre = copy.copy(self.oval.get_direction())

        self.master.after(self.cl.dt, self.update)

    def check_and_move(self):
        # 図形から操作された場合を検知
        # XY方向
        if self.rank_pre != self.oval.get_rank() or self.direction_pre != self.oval.get_direction():
            # バグで方向が転換できないことがあるので、一度止めるようにする
            if self.direction_pre != self.oval.get_direction():
                self.stop_stage()
            if self.oval.direction[0] > 0:
                self.move_right()
            elif self.oval.direction[0] < 0:
                self.move_left()
            if self.oval.direction[1] > 0:
                self.move_top()
            elif self.oval.direction[1] < 0:
                self.move_bottom()

    def check_and_stop(self):
        # 前回までは動く命令、今回止まる命令が出ていればstopを呼び出す
        if self.rank_pre != 0 and self.oval.get_rank() == 0:
            self.stop_stage()

    def move_right(self, event=None):
        # event is None: 図形操作から呼ばれた
        if event is None:
            vel = self.cl.vel_list[self.oval.get_rank()]
        else:
            vel = self.vel.get()

        if vel == 0:
            return

        if self.cl.mode == 'DEBUG':
            print(f'move right by {vel} \u03bcm/s')
        else:
            if self.is_auto_emission.get():  # 自動照射モード
                self.emit()
            self.stage.move_velocity('x', vel)

    def move_left(self, event=None):
        # event is None: 図形操作から呼ばれた
        if event is None:
            vel = -self.cl.vel_list[self.oval.get_rank()]
        else:
            vel = -self.vel.get()

        if vel == 0:
            return

        if self.cl.mode == 'DEBUG':
            print(f'move left by {vel} \u03bcm/s')
        else:
            if self.is_auto_emission.get():  # 自動照射モード
                self.emit()
            self.stage.move_velocity('x', vel)

    def move_top(self, event=None):
        # pulse laserではy軸の向きが下向き
        # event is None: 図形操作から呼ばれた
        if event is None:
            vel = -self.cl.vel_list[self.oval.get_rank()]
        else:
            vel = -self.vel.get()

        if vel == 0:
            return

        if self.cl.mode == 'DEBUG':
            print(f'move top by {vel} \u03bcm/s')
        else:
            if self.is_auto_emission.get():  # 自動照射モード
                self.emit()
            self.stage.move_velocity('y', vel)

    def move_bottom(self, event=None):
        # pulse laserではy軸の向きが下向き
        # event is None: 図形操作から呼ばれた
        if event is None:
            vel = self.cl.vel_list[self.oval.get_rank()]
        else:
            vel = self.vel.get()

        if vel == 0:
            return

        if self.cl.mode == 'DEBUG':
            print(f'move bottom by {vel} \u03bcm/s')
        else:
            if self.is_auto_emission.get():  # 自動照射モード
                self.emit()
            self.stage.move_velocity('y', vel)

    def stop_stage(self, event=None):
        # xy方向に停止命令を出す
        if self.cl.mode == 'DEBUG':
            print('stop xy')
        else:
            if self.is_auto_emission.get():  # 自動照射モード
                self.stop_laser()
            self.stage.stop()

    def update_position(self):
        # 現在位置を更新
        # シリアル通信で受信する必要があるため，mainloopとは別threadで処理する．
        while True:
            if self.cl.mode == 'DEBUG':
                self.x_cur.set(round(self.x_cur.get() + 0.015, 3))
                self.y_cur.set(round(self.y_cur.get() + 0.015, 3))
            else:
                x, y = self.stage.get_position()
                self.x_cur.set(round(x * 1000, 3))  # umに変換
                self.y_cur.set(round(y * 1000, 3))  # umに変換
            time.sleep(self.cl.dt * 0.001)

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

        x0, y0 = self.x_cur.get(), self.y_cur.get()
        self.stage.set_velocity_all(vel)

        if shape == 'line':
            points = [[x0 + x, y0 - y]]  # この系のy軸は下向きが正
            delays = [max(abs(x), abs(y)) / vel]
        elif shape == 'rectangle':
            points = [[x0 + x, y0],
                      [x0 + x, y0 - y],  # この系のy軸は下向きが正
                      [x0, y0 - y],  # この系のy軸は下向きが正
                      [x0, y0]]
            delays = [max(abs(x), abs(y)) / vel]
        else:
            return

        if self.is_auto_emission.get():  # 自動照射モード
            self.emit()

        for (x, y), delay in zip(points, delays):
            self.stage.move_line(x * 0.001, y * 0.001)
            time.sleep(delay + 0.3)

        if self.is_auto_emission.get():  # 自動照射モード
            self.stop_laser()

    def emit(self):
        frq = self.frq.get()
        if not 16 <= frq <= 10000:
            self.msg_laser.set('Frequency must be 16~10000 Hz.')
            return
        if self.cl.mode == 'RELEASE':
            self.laser.set_frq(frq)
        elif self.cl.mode == 'DEBUG':
            print('Emit')
        self.msg_laser.set(f'Now: {frq} Hz (available range: 16~10000 Hz)')

    def stop_laser(self):
        if self.cl.mode == 'RELEASE':
            self.laser.stop()
        elif self.cl.mode == 'DEBUG':
            print('Stop laser')
        self.msg_laser.set('Now: 0 Hz (available range: 16~10000 Hz)')

    def change_auto_emission(self):
        if self.is_auto_emission.get():
            self.button_emit_laser.config(state=tk.DISABLED)
            self.button_stop_laser.config(state=tk.DISABLED)
        else:
            self.button_emit_laser.config(state=tk.ACTIVE)
            self.button_stop_laser.config(state=tk.ACTIVE)


def main():
    root = tk.Tk()
    root.option_add("*font", FONT)  # こうしないとコンボボックスのフォントが変わらない
    root.protocol('WM_DELETE_WINDOW', (lambda: 'pass')())  # QUITボタン以外の終了操作を許可しない
    app = Application(master=root, config='./config.json')
    app.mainloop()

    print('Successfully finished the controller program.')


if __name__ == '__main__':
    main()
