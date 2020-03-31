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
from collections import deque
from random import random
from typing import List, Tuple, Optional

import pyglet
from pyglet.graphics.vertexdomain import VertexList

from graph import Graph
from intersections import Rectangle
from shapes import line_quad
from timer import Timer

global_timer = Timer()


class Camera:
    """
    A simple 2D camera that contains the speed and offset.
    Extended from the pyglet example camera
    """

    def __init__(self, scroll_speed=1, min_zoom=1, max_zoom=4):
        assert min_zoom <= max_zoom, "Minimum zoom must not be greater than maximum zoom"
        self.scroll_speed = scroll_speed
        self.max_zoom = max_zoom
        self.min_zoom = min_zoom
        self.offset_x = 0
        self.offset_y = 0
        self._zoom = max(min(1, self.max_zoom), self.min_zoom)

    @property
    def zoom(self):
        return self._zoom

    @zoom.setter
    def zoom(self, value):
        """ Here we set zoom, clamp time_data to minimum of min_zoom and max of max_zoom."""
        self._zoom = max(min(value, self.max_zoom), self.min_zoom)

    @property
    def position(self):
        """Query the current offset."""
        return self.offset_x, self.offset_y

    @position.setter
    def position(self, value):
        """Set the scroll offset directly."""
        self.offset_x, self.offset_y = value

    def move(self, axis_x, axis_y):
        """ Move axis direction with scroll_speed.
            Example: Move left -> move(-1, 0)
         """
        self.offset_x += self.scroll_speed * axis_x
        self.offset_y += self.scroll_speed * axis_y

    def begin(self):
        # Set the current camera offset so you can draw your scene.
        # Translate using the zoom and the offset.
        pyglet.gl.glTranslatef(-self.offset_x * self._zoom, -self.offset_y * self._zoom, 0)

        # Scale by zoom level.
        pyglet.gl.glScalef(self._zoom, self._zoom, 1)

    def end(self):
        # Since this is a matrix, you will need to reverse the translate after rendering otherwise
        # it will multiply the current offset every draw update pushing it further and further away.

        # Reverse scale, since that was the last transform.
        pyglet.gl.glScalef(1 / self._zoom, 1 / self._zoom, 1)

        # Reverse translate.
        pyglet.gl.glTranslatef(self.offset_x * self._zoom, self.offset_y * self._zoom, 0)

    def __enter__(self):
        self.begin()

    def __exit__(self, exception_type, exception_value, traceback):
        self.end()

    @property
    def rectangle(self) -> Rectangle:
        return Rectangle(self.offset_x, self.offset_y, 800, 640)


class Block:
    __slots__ = ["broken", "vbo"]
    shape = line_quad
    size = 32

    def __init__(self):
        self.vbo: Optional[VertexList] = None
        self.broken = False

    def update(self, x: float, y: float):
        self.vbo.vertices = self.shape.transform_no_rotate(
            x, y, self.size, self.size
        ).flatten()


class Chunk:
    def __init__(self, name: int, offset: Tuple[float, float]):
        self.data: List[Block] = [Block() for i in range(256)]
        self.name = name
        self.offset = offset
        self.disabled = True

        # self.text = None
        self.bound = None

    def disable(self):
        """Disable the chunk. Will be later converted to asynchronous code."""
        # print(f"disabling the chunk {self.name}")

        if not self.disabled:
            for i in range(256):
                self.data[i].vbo.delete()
                self.data[i].vbo = None
            # self.text.delete()
            self.bound.delete()
            self.bound = None

            self.disabled = True

    def enable(self, batch):
        """Enable the chunk. Will be later converted to asynchronous code."""
        # print(f"enabling the chunk {self.name}")

        if self.disabled:
            ox, oy = self.offset
            # self.text = pyglet.text.Label(
            #     str(self.name), align='center',
            #     x=ox + 504, y=ox + 504, width=512, height=512,
            #     batch=batch
            # )

            for i in range(16):
                for j in range(16):
                    block = self.data[i * 16 + j]
                    block.vbo = block.shape.add_to_batch(
                        batch, None, 'v4f/stream',
                        ('c3f/static', [1., 0., 0.] * 4)
                    )
                    block.update(
                        float((i & 0xFF) * block.size + ox),
                        float((j & 0xFF) * block.size + oy)
                    )

            self.bound = line_quad.add_to_batch(
                batch, None, ('v4f', line_quad.transform_no_rotate(ox, oy, 16 * Block.size, 16 * Block.size).flatten())
            )
            self.disabled = False

    @property
    def rectangle(self) -> Rectangle:
        ox, oy = self.offset
        scale = 16 * Block.size
        return Rectangle(ox, oy, scale, scale)


class Board:
    """Collection of chunks."""
    def __init__(self, batch, camera, width, height):
        self.batch = batch
        self.camera = camera

        # We only need to load 9 chunks at any time,
        # but we'd need to find some way to cache
        # the already loaded chunks that are out of view.
        w2 = width / 2
        h2 = height / 2
        cx = cy = 16 * Block.size
        self.chunks = [
            Chunk(0, (w2 - cx * 1.5, h2 - cy * 1.5)),
            Chunk(1, (w2 - cy * 0.5, h2 - cy * 1.5)),
            Chunk(2, (w2 + cy * 0.5, h2 - cy * 1.5)),
            Chunk(3, (w2 - cx * 1.5, h2 - cy * 0.5)),
            Chunk(4, (w2 - cy * 0.5, h2 - cy * 0.5)),
            Chunk(5, (w2 + cy * 0.5, h2 - cy * 0.5)),
            Chunk(6, (w2 - cx * 1.5, h2 + cy * 0.5)),
            Chunk(7, (w2 - cy * 0.5, h2 + cy * 0.5)),
            Chunk(8, (w2 + cy * 0.5, h2 + cy * 0.5))
        ]

        # for chunk in self.chunks:
        #     chunk.enable(batch)

        self.queues = [
            deque(),  # load
            deque()   # unload
        ]

    def update(self, dt):
        # the scale added will depend on the camera's movement speed.
        camera_rect = self.camera.rectangle.scale(-200., -200.)
        for chunk in self.chunks:
            if chunk.disabled and camera_rect.intersects(chunk.rectangle):
                self.queues[0].append(chunk)
            elif not chunk.disabled and not camera_rect.intersects(chunk.rectangle):
                self.queues[1].append(chunk)

        # For now just load one chunk per frame.
        loads = len(self.queues[0])
        unloads = len(self.queues[1])
        if loads and (unloads == 0 or random() > 0.5):
            chunk = self.queues[0].pop()
            chunk.enable(self.batch)
        elif unloads and (loads == 0 or random() < 0.5):
            chunk = self.queues[1].pop()
            chunk.disable()


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

        self.board = Board(self.batch, self.camera, self.width, self.height)

    def update(self, dt: float):
        dx = self.keys[pyglet.window.key.D] - self.keys[pyglet.window.key.A]
        dy = self.keys[pyglet.window.key.W] - self.keys[pyglet.window.key.S]
        self.camera.move(dx, dy)

        self.board.update(dt)
        self.fps.push(1/dt)
        self.fps.update(dt)

    def on_draw(self):
        self.window.clear()
        with self.camera:
            self.batch.draw()

        with self.gui_camera:
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
