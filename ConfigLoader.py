import json


class ConfigLoader:
    def __init__(self, filename):
        with open(filename, 'r') as f:
            config = json.load(f)
        self.mode = config['mode']
        self.dt = int(1000 / config['FPS'])
        self.port_stage = f'COM{config["PORT-stage"]}'
        self.port_laser = f'COM{config["PORT-laser"]}'
        self.baudrate_stage = config["BAUDRATE-stage"]
        self.baudrate_laser = config["BAUDRATE-laser"]
        self.vel_list = config["VEL_LIST"]


def main():
    cl = ConfigLoader('./config.json')
    print(cl.mode)


if __name__ == '__main__':
    main()
