import serial


class MySerial(serial.Serial):
    # serial.SerialではEOLが\nに設定されており、DS102の規格と異なる
    eol = b'\r'
    leneol = len(eol)

    def __init__(self, port, baudrate, **args):
        super().__init__(port, baudrate, **args)

    def send(self, msg: str):
        msg = msg.encode() + self.eol
        self.write(msg)

    def recv(self):
        line = bytearray()
        while True:
            c = self.read(1)
            if c:
                line += c
                if line[-self.leneol:] == self.eol:
                    break
            else:
                break
        return bytes(line).decode().strip('\r')


def axis2msg(axis: str):
    """
    convert axis to 'AXIs<axis>:'
    :param axis: 'x' or 'y'
    :type axis: str
    :rtype: str
    :return: message string
    """
    if axis not in ['x', 'y']:
        raise ValueError('Axis must be x or y.')
    msg = 'AXIs'
    if axis == 'x':
        msg += '1'
    elif axis == 'y':
        msg += '2'
    msg += ':'
    return msg


class DS102Controller:
    def __init__(self, ser: MySerial):
        """
        initialization
        :param ser: opened port for communication
        :type ser: MySerial
        """
        self.ser = ser
        # 送受信とスピードテーブルの確認
        for axis in ['x', 'y']:
            self.ser.send(axis2msg(axis) +'READY?')
            print(f'{axis} axis: {"READY" if self.ser.recv() == "1" else "NOT READY"}')
            if not self.speed_table_is(axis, 0):
                self.select_speed_table(axis, 0)

    def set_velocity(self, axis: str, vel: int):
        """
        set Fspeed0 vel
        :param axis: 'x' or 'y'
        :param vel: velocity you want to set
        :type axis: str
        :type vel: int
        :return:
        """
        msg = axis2msg(axis) + f'Fspeed0 {vel}'
        self.ser.send(msg)

    def set_velocity_all(self, vel: int):
        """
        set Fspeed0 vel
        :param vel: velocity you want to set
        :type vel: int
        :return:
        """
        for axis in ['x', 'y']:
            self.set_velocity(axis, vel)

    def set_velocity_max_all(self):
        """
        set Fspeed0 vel
        :param vel: velocity you want to set
        :type vel: int
        :return:
        """
        for axis in ['x', 'y']:
            self.set_velocity(axis, 999999)  # TODO: ほんとか？

    def select_speed_table(self, axis: str, speed: int):
        """
        select set of speed from 0~9
        :param axis: 'x' or 'y'
        :param speed: number(0~9) of the set you want to select
        :type axis: str
        :type speed: int
        :return:
        """
        msg = axis2msg(axis) + f'SELectSPeed {speed}'
        self.ser.send(msg)

    def speed_table_is(self, axis: str, speed: int) -> bool:
        """
        check the selected speed
        :param axis: 'x' or 'y'
        :param speed: number(0~9) of the set
        :type axis: str
        :type speed: int
        :rtype: bool
        :return: True or False
        """
        msg = axis2msg(axis) + 'SELectSPeed?'
        self.ser.send(msg)
        msg = self.ser.recv()
        if msg == str(speed):
            return True
        else:
            print('selected speed:', msg)
            return False

    def move_velocity(self, axis: str, vel: int):
        """
        move along selected axis with selected velocity
        :param axis: 'x' or 'y'
        :param vel: velocity
        :type axis: str
        :type vel: int
        :return:
        """
        self.set_velocity(axis, abs(vel))

        msg = axis2msg(axis) + 'GO '
        if vel > 0:
            msg += '5'
        else:
            msg += '6'
        self.ser.send(msg)

    def move_abs(self, axis: str, pos: float):
        """

        :param axis: 'x' or 'y'
        :param pos: absolute position
        :return:
        """
        msg = axis2msg(axis) + f'GOABS {pos}'
        self.ser.send(msg)

    def stop_axis(self, axis: str):
        """
        stop each axis
        Emergency( or Reduction)
        :param axis: 'x' or 'y'
        :type axis: str
        :return:
        """
        msg = axis2msg(axis) + 'STOP Emergency'
        # msg = axis2msg(axis) + 'STOP Reduction'
        self.ser.send(msg)

    def stop(self):
        """
        stop all
        :return:
        """
        msg = 'STOP Emergency'
        # msg = 'STOP Reduction'
        self.ser.send(msg)

    def get_position(self):
        """
        get x and y position
        the unit is mm
        :rtype (int, int)
        :return: x position, y position
        """
        # シリアル通信のエラーで稀に正しい返答が得られないことがある。プログラムが止まらないよう0を入れるようにする。
        pos = []
        for axis in ['x', 'y']:
            msg = axis2msg(axis) + 'POSition?'
            self.ser.send(msg)
            pos_axis = self.ser.recv()
            try:
                pos_axis = int(float(pos_axis) * 1000)
            except ValueError:
                pos_axis = 0
            pos.append(pos_axis)
        return pos
