"""
A slight change to MinerTest, we want this version to have an infinite world
the viewer can pan around.

We'll make the chunk size 16x16.
To start, we will not have depth.

We will start by just drawing quads.

How do we handle an infinite world with batch rendering?
I think we do a check over all loaded blocks to see
if they fall within the viewport. If not, we do VertexList.delete,
else, we add to the batch.
"""

import pyglet

from board import Board
from camera import Camera
from common import global_timer
from graph import Graph


class Simulation:
    def __init__(self, width, height, framerate):
        self.width = width
        self.height = height
        self.framerate = framerate

        self.window = pyglet.window.Window(
            width=self.width, height=self.height,
            vsync=True,
        )
        # self.fps = pyglet.window.FPSDisplay(self.window)
        self.fps = Graph(0, height - 100, 200, 100, 2, 2, 60, 60.)

        self.keys = pyglet.window.key.KeyStateHandler()
        self.window.push_handlers(self.keys)
        self.window.push_handlers(self.on_draw)

        self.batch = pyglet.graphics.Batch()
        self.camera = Camera(10)
        self.gui_camera = Camera(10)
        self.position_label = pyglet.text.Label(
            "x=0, y=0", font_name="consolas",
            x=2, y=self.height - 118
        )

        self.board = Board(self.batch, self.camera, self.width, self.height)

    def update(self, dt: float):
        dx = self.keys[pyglet.window.key.D] - self.keys[pyglet.window.key.A]
        dy = self.keys[pyglet.window.key.W] - self.keys[pyglet.window.key.S]
        self.camera.move(dx, dy)
        x, y = self.camera.position
        self.position_label.text = f"x={x}, y={y}"

        self.board.update(dt)
        self.fps.push(1/dt)
        self.fps.update(dt)

    def on_draw(self):
        self.window.clear()
        with self.camera:
            self.batch.draw()

        with self.gui_camera:
            self.position_label.draw()
            self.gui_camera.rectangle.scale(-200., -200.).draw()
            self.fps.draw()

    def setup(self):
        pyglet.clock.schedule_interval(
            self.update, 1. / self.framerate
        )

    def run(self):
        self.setup()
        pyglet.app.run()


if __name__ == '__main__':
    sim = Simulation(800, 640, 60.)
    sim.run()
