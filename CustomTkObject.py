# tkinterのcanvasに描画する図形をコントローラーに使う
# 範囲内での操作、現在の位置の取得が行える
import math


class MovableObject:
    canvas = None
    thres_list = []

    def __init__(self):
        self.id = None
        self.x0 = None
        self.y0 = None
        self.rank = None
        self.direction = None
        self.disp = None

    def dragging(self, event):
        pass

    def reset(self, event=None):
        self.canvas.moveto(self.id, self.x0, self.y0)
        self.rank = 0
        self.direction = [0, 0, 0]  # (x, y, z)
        self.disp = 0

    def get_rank(self):
        """
        :rtype: int
        :return: rank
        """
        for i, thres in enumerate(self.thres_list):
            if self.disp <= thres:
                self.rank = len(self.thres_list) - i - 1
        return self.rank

    def get_direction(self):
        """
        :rtype: list
        :return: list of direction [x, y, z]
        """
        return self.direction


class MovableOval(MovableObject):
    def __init__(self, x0, y0, x1, y1, **key):
        super().__init__()
        self.id = self.canvas.create_oval(x0, y0, x1, y1, **key)
        self.canvas.tag_bind(self.id, '<Button1-Motion>', self.dragging)
        self.canvas.tag_bind(self.id, '<ButtonRelease>', self.reset)
        x0, y0, x1, y1 = self.canvas.bbox(self.id)
        self.r = (x1 - x0) / 2
        self.x0 = (x0 + x1) / 2 - self.r
        self.y0 = (y0 + y1) / 2 - self.r
        self.reset()

    def dragging(self, event):
        x = event.x - self.r
        y = event.y - self.r
        dx = x - self.x0
        dy = y - self.y0
        r = (dx ** 2 + dy ** 2) ** 0.5
        theta = math.atan2(dy, dx)
        if r > self.thres_list[0]:
            x = self.thres_list[0] * math.cos(theta) * 0.95 + self.x0
            y = self.thres_list[0] * math.sin(theta) * 0.95 + self.y0
        self.canvas.moveto(self.id, x, y)

        # get_rank用
        dx = x - self.x0
        dy = y - self.y0
        r = (dx ** 2 + dy ** 2) ** 0.5
        self.disp = r

        # directionの確認
        if math.pi * -0.75 < theta < math.pi * -0.25:
            self.direction[0] = 0
            self.direction[1] = 1
        elif math.pi * -0.25 < theta < math.pi * 0.25:
            self.direction[0] = 1
            self.direction[1] = 0
        elif math.pi * 0.25 < theta < math.pi * 0.75:
            self.direction[0] = 0
            self.direction[1] = -1
        else:
            self.direction[0] = -1
            self.direction[1] = 0
