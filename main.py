import os
import sys
import time
import copy
import threading
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import serial
from DS102Controller import MySerial, DS102Controller
from PulseLaserController import PulseLaserController
from CustomTkObject import MovableOval
from ConfigLoader import ConfigLoader
from CommandWindow import CommandWindow


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

        self.is_limit = [False, False]

        self.create_thread_pos()

        self.update()

    def open_port(self):
        if self.cl.mode == 'RELEASE':
            self.ser_stage = MySerial(self.cl.port_stage, self.cl.baudrate_stage, write_timeout=0)
            self.stage = DS102Controller(self.ser_stage)
            self.ser_laser = serial.Serial(self.cl.port_laser, self.cl.baudrate_laser, write_timeout=0)
            self.laser = PulseLaserController(self.ser_laser)
        elif self.cl.mode == 'DEBUG':
            self.stage = self.laser = None
        else:
            raise ValueError('Wrong format in config.json. Mode must be DEBUG or RELEASE.')

    def create_widgets(self):
        # 親フレーム
        frame_stage = ttk.LabelFrame(self.master, text='STAGE')
        frame_laser = ttk.LabelFrame(self.master, text='PULSE LASER')
        button_quit = ttk.Button(self.master, text='QUIT', command=self.quit, style='stop.TButton')
        label_quit = ttk.Label(self.master, text='必ずQUITボタンからプログラムを終了')
        frame_stage.grid(row=0, column=0, pady=10)
        frame_laser.grid(row=1, column=0, pady=10)
        button_quit.grid(row=2, columnspan=2, pady=10)
        label_quit.grid(row=3, columnspan=2)
        # 子フレーム
        frame_controller_canvas = ttk.Frame(frame_stage)
        frame_controller_buttons = ttk.Frame(frame_stage)
        frame_controller_position = ttk.Frame(frame_stage)
        frame_controller_command = ttk.Frame(frame_stage)
        button_controller_stop = ttk.Button(frame_stage, text='STOP ALL STAGES', command=self.stop_stage, style='stop.TButton')
        frame_controller_canvas.grid(row=0, column=0)
        frame_controller_buttons.grid(row=1, column=0)
        frame_controller_position.grid(row=2, column=0)
        frame_controller_command.grid(row=3, column=0)
        button_controller_stop.grid(row=4, column=0)
        # ウィジェット canvas
        canvas_controller = tk.Canvas(frame_controller_canvas, width=SIZE_CANVAS, height=SIZE_CANVAS)
        center = SIZE_CANVAS/2
        r_list = [SIZE_CONT*9, SIZE_CONT*7, SIZE_CONT*5, SIZE_CONT*3, SIZE_CONT*1]
        for i, r in enumerate(r_list):
            color = get_color_by_float(i / len(r_list))
            canvas_controller.create_oval(center - r, center - r, center + r, center + r, fill=color)
        MovableOval.canvas = canvas_controller
        MovableOval.thres_list = r_list
        self.oval = MovableOval(center - SIZE_CONT, center - SIZE_CONT, center + SIZE_CONT, center + SIZE_CONT, fill='lightblue')
        canvas_controller.pack()
        # ウィジェット buttons
        self.vel = tk.IntVar(value=100)
        combobox_xy = ttk.Combobox(frame_controller_buttons, values=self.cl.vel_list[1:], textvariable=self.vel, justify='center', width=WIDTH_BUTTON)
        button_top = ttk.Button(frame_controller_buttons, width=WIDTH_BUTTON, text='↑')
        button_left = ttk.Button(frame_controller_buttons, width=WIDTH_BUTTON, text='←')
        button_right = ttk.Button(frame_controller_buttons, width=WIDTH_BUTTON, text='→')
        button_bottom = ttk.Button(frame_controller_buttons, width=WIDTH_BUTTON, text='↓')
        button_top.bind('<Button-1>', self.move_top)
        button_top.bind('<ButtonRelease-1>', self.stop_stage)
        button_left.bind('<Button-1>', self.move_left)
        button_left.bind('<ButtonRelease-1>', self.stop_stage)
        button_right.bind('<Button-1>', self.move_right)
        button_right.bind('<ButtonRelease-1>', self.stop_stage)
        button_bottom.bind('<Button-1>', self.move_bottom)
        button_bottom.bind('<ButtonRelease-1>', self.stop_stage)
        button_top.grid(row=0, column=1)
        button_left.grid(row=1, column=0)
        combobox_xy.grid(row=1, column=1)
        button_right.grid(row=1, column=2)
        button_bottom.grid(row=2, column=1)
        # ウィジェット position
        self.x_cur = tk.IntVar(value=0)
        self.y_cur = tk.IntVar(value=0)
        label_x = ttk.Label(frame_controller_position, text='X [\u03bcm]')
        label_y = ttk.Label(frame_controller_position, text='Y [\u03bcm]')
        label_x_cur = ttk.Label(frame_controller_position, textvariable=self.x_cur)
        label_y_cur = ttk.Label(frame_controller_position, textvariable=self.y_cur)
        button_set_origin = ttk.Button(frame_controller_position, text='SET ORG', command=self.set_origin)
        label_x.grid(row=0, column=0)
        label_x_cur.grid(row=0, column=1)
        label_y.grid(row=1, column=0)
        label_y_cur.grid(row=1, column=1)
        button_set_origin.grid(row=0, column=2, rowspan=2)

        # laser
        self.frq = tk.IntVar(value=100)
        entry_frq = ttk.Entry(frame_laser, textvariable=self.frq, width=5, justify=tk.CENTER)
        label_hz = ttk.Label(frame_laser, text='Hz')
        self.button_emit_laser = ttk.Button(frame_laser, text='EMIT', command=self.emit)
        self.button_stop_laser = ttk.Button(frame_laser, text='STOP', command=self.stop_laser, style='stop.TButton')
        self.msg_laser = tk.StringVar(value='Now: 0 Hz (available: 16~10000 Hz)')
        label_msg_frq = ttk.Label(frame_laser, textvariable=self.msg_laser)
        self.is_auto_emission = tk.BooleanVar(value=False)
        check_auto_emission = tk.Checkbutton(frame_laser, text="Auto Emission", command=self.change_auto_emission, variable=self.is_auto_emission)
        entry_frq.grid(row=0, column=0)
        label_hz.grid(row=0, column=1)
        self.button_emit_laser.grid(row=0, column=2)
        self.button_stop_laser.grid(row=0, column=3)
        label_msg_frq.grid(row=1, column=0, columnspan=4)
        check_auto_emission.grid(row=2, column=0, columnspan=4)

        # menu bar
        menu_bar = tk.Menu(self.master, tearoff=False)
        self.master.config(menu=menu_bar)

        menu_setting = tk.Menu(menu_bar, tearoff=False)
        menu_bar.add_cascade(label='Setting', menu=menu_setting)
        menu_setting.add_command(label='Open Config File', command=lambda: print('IMPLEMENT ME'))

        menu_tool = tk.Menu(menu_bar, tearoff=False)
        menu_bar.add_cascade(label='Tool', menu=menu_tool)
        menu_tool.add_command(label='Command Mode', command=self.open_command_window)
        menu_tool.add_command(label='Reset Origin', command=self.create_thread_reset)

        menu_help = tk.Menu(menu_bar, tearoff=False)
        menu_bar.add_cascade(label='Help', menu=menu_help)
        menu_help.add_command(label='Manual', command=lambda: print('IMPLEMENT ME'))

    def create_thread_pos(self):
        # update_positionの受信待ちで画面がフリーズしないようthreadを立てる
        thread_pos = threading.Thread(target=self.update_position)
        thread_pos.daemon = True
        thread_pos.start()

    def create_thread_reset(self):
        if messagebox.askyesno('確認', '機械原点を(0, 0)にしますか？'):
            thread_reset = threading.Thread(target=self.reset_origin)
            thread_reset.daemon = True
            thread_reset.start()

    def quit(self):
        if self.cl.mode == 'RELEASE':
            self.stop_stage()
            self.stop_laser()
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

    def get_velocity(self):
        # entryに何も入っていないとエラーになってしまうので例外処理
        try:
            vel = self.vel.get()
        except tk.TclError:
            self.vel.set(1)
            vel = 1
        if vel <= 0:
            self.vel.set(1)
            vel = 1
        elif vel > 25000:
            self.vel.set(25000)
            vel = 25000
        return vel

    def move_right(self, event=None):
        self.move('x', 1, event)

    def move_left(self, event=None):
        self.move('x', -1, event)

    def move_top(self, event=None):
        # pulse laserではy軸の向きが下向き
        self.move('y', -1, event)

    def move_bottom(self, event=None):
        # pulse laserではy軸の向きが下向き
        self.move('y', 1, event)

    def move(self, axis: str, direction: int, event = None):
        # event is None: 図形操作から呼ばれた
        if event is None:
            vel = self.cl.vel_list[self.oval.get_rank()]
        else:
            vel = self.get_velocity()

        vel *= direction  # direction is 1 or -1

        if vel == 0:
            return

        if self.cl.mode == 'DEBUG':
            print(f'move {axis} by {vel} \u03bcm/s')
        else:
            if self.is_auto_emission.get():  # 自動照射モード
                self.emit()
            self.stage.move_velocity(axis, vel)

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
                self.x_cur.set(int(self.x_cur.get() + 15))
                self.y_cur.set(int(self.y_cur.get() + 15))
            else:
                x, y = self.stage.get_position()
                self.x_cur.set(int(x * 1000))  # umに変換
                self.y_cur.set(-int(y * 1000))  # umに変換, yは下向きだが、ユーザーは気にせず動かせるようにする
                self.is_limit = self.stage.check_limit_all()  # 現在位置が機械限界か判定する
            time.sleep(self.cl.dt * 0.001)

    def set_origin(self):
        if self.cl.mode == 'DEBUG':
            print('set origin')
        elif self.cl.mode == 'RELEASE':
            for axis in ['x', 'y']:
                self.stage.set_position(axis, 0)

    def reset_origin(self):
        if self.cl.mode == 'DEBUG':
            print('reset origin')
        elif self.cl.mode == 'RELEASE':
            for i, axis in enumerate(['x', 'y']):
                self.stage.move_velocity(axis, 25000)
                while not self.is_limit[i]:  # limitの判定はupdate_position内で取得している
                    time.sleep(self.cl.dt * 0.001)
                self.stage.set_position(axis, 7.35)  # 大体14.7mmが駆動範囲
                self.stage.move_abs(axis, 0)  # 原点に戻す
                time.sleep(3)

    def emit(self):
        frq = self.frq.get()
        if not 16 <= frq <= 10000:
            self.msg_laser.set('Frequency must be 16~10000 Hz.')
            return
        if self.cl.mode == 'RELEASE':
            self.laser.set_frq(frq)
        elif self.cl.mode == 'DEBUG':
            print('Emit')
        self.msg_laser.set(f'Now: {frq} Hz (available: 16~10000 Hz)')

    def stop_laser(self):
        if self.cl.mode == 'RELEASE':
            self.laser.stop()
        elif self.cl.mode == 'DEBUG':
            print('Stop laser')
        self.msg_laser.set('Now: 0 Hz (available: 16~10000 Hz)')

    def change_auto_emission(self):
        self.stop_laser()
        if self.is_auto_emission.get():
            self.button_emit_laser.config(state=tk.DISABLED)
            self.button_stop_laser.config(state=tk.DISABLED)
        else:
            self.button_emit_laser.config(state=tk.ACTIVE)
            self.button_stop_laser.config(state=tk.ACTIVE)

    def open_command_window(self):
        CommandWindow(self, self.cl, self.stage, self.laser)


def main():
    root = tk.Tk()
    root.option_add("*font", FONT)  # こうしないとコンボボックスのフォントが変わらない
    root.protocol('WM_DELETE_WINDOW', (lambda: 'pass')())  # QUITボタン以外の終了操作を許可しない
    app = Application(master=root, config='./config.json')
    app.mainloop()


if __name__ == '__main__':
    main()
