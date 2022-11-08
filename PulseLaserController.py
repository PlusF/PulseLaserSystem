import time
import serial


class PulseLaserController:
    def __init__(self, ser: serial.Serial):
        """
        initialization
        :param ser: opened port for communication
        :type ser: serial.Serial
        """
        self.ser = ser
        time.sleep(1)

    def set_frq(self, frq: int):
        if 16 <= frq <= 10000:
            self.ser.write(f'{frq}\n'.encode())
        else:
            print('Invalid frequency. It must be 16~10000(integer).')

    def stop(self):
        self.ser.write('-1\n'.encode())


def main():
    ser = serial.Serial('COM6', baudrate=9600, write_timeout=0)
    time.sleep(2)
    ser.write('-1\n'.encode())
    print(ser.readline().decode())


if __name__ == '__main__':
    main()
