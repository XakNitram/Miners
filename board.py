from collections import deque
from dataclasses import dataclass
from random import random, shuffle, randrange
from typing import Optional, Tuple, List, Deque, Set, Union

from pyglet import gl
from pyglet.graphics import Group, OrderedGroup, Batch
from pyglet.graphics.vertexdomain import VertexList

from camera import Camera
from common import global_timer
from intersections import Rectangle
from shapes import quad, line_quad


@dataclass
class Position:
    x: float = 0.
    y: float = 0.


@dataclass
class Block:
    # position: Position = Position(0., 0.)  # why did we want this?
    broken: bool = False
    value: int = 0


BLOCKS = OrderedGroup(0)
BORDER = OrderedGroup(1)


class Chunk:
    BLOCK_SHAPE = line_quad
    BLOCK_SIZE = 8

    def __init__(self, name: int, offset: Tuple[float, float]):
        self.blocks: List[Block] = [Block(value=randrange(3)) for _ in range(256)]
        self.vbos: List[Optional[VertexList]] = [None for _ in range(256)]
        self.name = name
        self.offset = offset
        self.visible = False

        # self.text = None
        self.bound = None

        self.show_queue: Deque[Tuple[int, int]] = deque(maxlen=16)

    def __repr__(self):
        x, y = self.offset
        return f"Chunk({self.name:d}, ({x:f}, {y:f}))"

    def hide(self):
        """Disable the chunk. Will be later converted to asynchronous code."""
        # print(f"disabling the chunk {self.name}")

        if not self.visible:
            for i in range(256):
                vbo = self.vbos[i]
                if vbo is not None:
                    self.vbos[i].delete()
                    self.vbos[i] = None

            self.show_queue.clear()
            # self.text.delete()
            # self.bound.delete()
            # self.bound = None

    def show(self, batch, camera):
        """Enable the chunk. Will be later converted to asynchronous code."""
        # print(f"enabling the chunk {self.name}")

        if self.visible:
            ox, oy = self.offset
            # self.text = pyglet.text.Label(
            #     str(self.name), align='center',
            #     x=ox + 504, y=ox + 504, width=512, height=512,
            #     batch=batch
            # )
            self.show_queue.clear()

            # load in 4 x 4 squares
            for j in range(4):
                for i in range(4):
                    self.show_queue.append((i, j))
            shuffle(self.show_queue)

            # self.bound = line_quad.add_to_batch(
            #     batch, BORDER, (
            #         'v4f', line_quad.transform_no_rotate(
            #             ox, oy, 16 * self.BLOCK_SIZE, 16 * self.BLOCK_SIZE
            #         ).flatten()
            #     )
            # )

    def process(self, batch) -> bool:
        if not len(self.show_queue):
            return True

        scale = self.BLOCK_SIZE
        ox, oy = self.offset
        for _ in range(4):
            i, j = self.show_queue.pop()
            for n in range(4):
                for m in range(4):
                    index = (j * 64) + (i * 16) + (n * 4) + m
                    # value = self.blocks[index].value
                    group = BLOCKS
                    self.vbos[index] = self.BLOCK_SHAPE.add_to_batch(
                        batch, group, (
                            'v4f/static', self.BLOCK_SHAPE.transform_no_rotate(
                                (i * 4 + m) * scale + ox,
                                (j * 4 + n) * scale + oy,
                                scale, scale
                            ).flatten()),
                        ('c3f/static', [1., 0., 0.] * 4)
                    )
                    block.update(
                        float((i & 0xFF) * block.size + ox),
                        float((j & 0xFF) * block.size + oy)
                    )

        return False

    @property
    def rectangle(self) -> Rectangle:
        ox, oy = self.offset
        scale = 16 * Chunk.BLOCK_SIZE
        return Rectangle(ox, oy, scale, scale)


class ChunkCollection:
    """Construct to handle chunk loading and unloading."""

    def __init__(self, initial_width, initial_height):
        self.chunks: List[Chunk] = []

        w2 = initial_width / 2
        h2 = initial_height / 2
        cx = cy = 16 * Chunk.BLOCK_SIZE
        xr = yr = 5

        # self.chunks = [
        #     Chunk(0, (offset_x0, offset_y0)),
        #     Chunk(1, (offset_x1, offset_y1)),
        #     Chunk(2, (offset_x2, offset_y2)),
        #         ...,
        #     CHunk(n, (w2 + cx * (n - xr / 2, h2 + cy * (n - xr / 2))
        # ]

        for j in range(yr):
            for i in range(xr):
                index = j * yr + i

                self.chunks.append(Chunk(index, (
                    w2 + cx * (i - xr / 2),
                    h2 + cy * (j - yr / 2)
                )))

        self.loading: List[Set[int]] = [
            set(),  # load vbos
            set(),  # delete vbos
            set(),  # load data
            set()   # save data
        ]

        self.current: int = -1

    def __getitem__(self, item: Union[int, slice]) -> Chunk:
        return self.chunks[item]

    def process(self, batch: Batch, view_box: Rectangle):
        visible, hidden, available, unavailable = self.loading

        for i, chunk in enumerate(self.chunks):
            if not chunk.visible and view_box.intersects(chunk.rectangle):
                visible.add(i)
                chunk.visible = True

                if i in hidden:
                    hidden.discard(i)
            elif chunk.visible and not view_box.intersects(chunk.rectangle):
                hidden.add(i)
                chunk.visible = False

                if i in visible:
                    visible.discard(i)

        showing = len(visible)
        hiding = len(hidden)

        if showing and (hiding == 0 or random() > 0.5) and self.current < 0:
            index = visible.pop()
            chunk = self[index]
            chunk.show(batch, view_box)

            self.current = index

        elif hiding and (showing == 0 or random() > 0.5):
            chunk = self[hidden.pop()]
            chunk.hide()

        if self.current > -1:
            chunk = self[self.current]
            if chunk.process(batch):
                self.current = -1


class Board:
    """Collection of chunks."""
    def __init__(
            self, batch: Batch, camera: Camera,
            init_width: int, init_height: int
    ):
        self.batch = batch
        self.camera = camera

        self.chunks: ChunkCollection = ChunkCollection(init_width, init_height)

    def update(self, dt):
        # the scale added will depend on the camera's movement speed.
        view_box = self.camera.rectangle.scale(-200., -200.)
        # view_box = self.camera.rectangle

        self.chunks.process(self.batch, view_box)
