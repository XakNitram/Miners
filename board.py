from collections import deque
from dataclasses import dataclass
from random import random, randrange
from typing import Optional, Tuple, List, Deque, Set, Union

from math import atan2, tau
from pyglet.graphics import OrderedGroup, Batch
from pyglet.graphics.vertexdomain import VertexList

from camera import Camera
from common import global_timer, GRID_SIZE
from intersections import Rectangle
from shapes import line_quad, quad


BLOCKS = OrderedGroup(0)
MINERS = OrderedGroup(1)
BORDER = OrderedGroup(2)


@dataclass
class Block:
    broken: bool = False
    value: int = 0


class Chunk:
    BLOCK_SHAPE = quad
    # BLOCK_SHAPE = line_quad

    def __init__(self, name: int, offset: Tuple[float, float]):
        self.blocks: List[Block] = [Block(value=randrange(3)) for _ in range(256)]
        self.vbos: List[Optional[VertexList]] = [None for _ in range(256)]
        self.name = name
        self.offset = offset
        self.visible = False

        self.bound = None

        self.show_queue: Deque[Tuple[int, int]] = deque(maxlen=16)

    def __repr__(self):
        x, y = self.offset
        return f"Chunk({self.name:d}, ({x:f}, {y:f}))"

    def hide(self):
        # print(f"disabling the chunk {self.name}")

        if not self.visible:
            for i in range(256):
                vbo = self.vbos[i]
                if vbo is not None:
                    self.vbos[i].delete()
                    self.vbos[i] = None

            self.show_queue.clear()

            if self.bound is not None:
                self.bound.delete()
                self.bound = None

    def show(self, batch: Batch, view_box: Rectangle):
        # print(f"enabling the chunk {self.name}")

        if self.visible:
            ox, oy = self.offset
            self.show_queue.clear()

            # angle-based loading
            bound_box = self.rectangle
            vbcx, vbcy = view_box.center
            bbcx, bbcy = bound_box.center

            eighth = tau / 8
            sixteenth = tau / 16

            # % tau converts negative angles to standard angles
            angle = (atan2(vbcy - bbcy, vbcx - bbcx) % tau)

            # this only works for a camera zoom showing a 3x3 grid.
            # load_order: List[Tuple[int, int]] = [None] * 16
            if 7 * eighth - sixteenth < angle or angle <= sixteenth:
                for i in range(3, -1, -1):
                    for j in range(4):
                        self.show_queue.append((i, j))
            elif sixteenth < angle <= 2 * eighth - sixteenth:
                for p in range(1, -1, -1):
                    for q in range(1, -1, -1):
                        for i in range(1, -1, -1):
                            for j in range(1, -1, -1):
                                self.show_queue.append((p * 2 + i, q * 2 + j))
            elif 2 * eighth - sixteenth < angle <= 3 * eighth - sixteenth:
                for j in range(3, -1, -1):
                    for i in range(4):
                        self.show_queue.append((i, j))
            elif 3 * eighth - sixteenth < angle <= 4 * eighth - sixteenth:
                for p in range(2):
                    for q in range(1, -1, -1):
                        for i in range(2):
                            for j in range(1, -1, -1):
                                self.show_queue.append((p * 2 + i, q * 2 + j))
            elif 4 * eighth - sixteenth < angle <= 5 * eighth - sixteenth:
                for i in range(4):
                    for j in range(4):
                        self.show_queue.append((i, j))
            elif 5 * eighth - sixteenth < angle <= 6 * eighth - sixteenth:
                for p in range(2):
                    for q in range(2):
                        for i in range(2):
                            for j in range(2):
                                self.show_queue.append((p * 2 + i, q * 2 + j))
            elif 6 * eighth - sixteenth < angle <= 7 * eighth - sixteenth:
                for j in range(4):
                    for i in range(4):
                        self.show_queue.append((i, j))
            else:
                for p in range(1, -1, -1):
                    for q in range(2):
                        for i in range(1, -1, -1):
                            for j in range(2):
                                self.show_queue.append((p * 2 + i, q * 2 + j))

            # for j in range(4):
            #     for i in range(4):
            #         self.show_queue.append((i, j))
            # shuffle(self.show_queue)

            self.bound = line_quad.add_to_batch(
                batch, BORDER, (
                    'v4f', line_quad.transform_no_rotate(
                        ox, oy, 16 * GRID_SIZE, 16 * GRID_SIZE
                    ).flatten()
                )
            )

    def process(self, batch: Batch) -> bool:
        if not len(self.show_queue):
            return True

        scale = GRID_SIZE
        ox, oy = self.offset
        for _ in range(4):
            i, j = self.show_queue.popleft()
            for n in range(4):
                for m in range(4):
                    index = (j * 64) + (i * 16) + (n * 4) + m
                    # value = self.blocks[index].value
                    group = BLOCKS
                    # group = GROUPS[value]
                    self.vbos[index] = self.BLOCK_SHAPE.add_to_batch(
                        batch, group, (
                            'v4f/static', self.BLOCK_SHAPE.transform_no_rotate(
                                (i * 4 + m) * scale + ox,
                                (j * 4 + n) * scale + oy,
                                scale, scale
                            ).flatten()),
                        ('c3B/static', [0x3e, 0x41, 0x4e] * 4)
                        # ("t3f", TEXTURES[value].tex_coords)
                    )

        return False

    @property
    def rectangle(self) -> Rectangle:
        ox, oy = self.offset
        scale = 16 * GRID_SIZE
        return Rectangle(ox, oy, scale, scale)


class ChunkGrid:
    """Construct to handle chunk loading and unloading."""

    @dataclass
    class Loadable:
        chunk: int
        finished: bool = False

    def __init__(self, initial_width, initial_height):
        self.chunks: List[Chunk] = []

        w2 = initial_width / 2
        h2 = initial_height / 2
        cx = cy = 16 * GRID_SIZE
        xr = yr = 5

        # self.chunks = [
        #     Chunk(0, (offset_x0, offset_y0)),
        #     Chunk(1, (offset_x1, offset_y1)),
        #     Chunk(2, (offset_x2, offset_y2)),
        #         ...,
        #     Chunk(n, (w2 + cx * (n - xr / 2, h2 + cy * (n - xr / 2))
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
            set()   # cache data
        ]

        self.current: int = -1

    def __getitem__(self, item: Union[int, slice]) -> Chunk:
        return self.chunks[item]

    def process_graphics(self, batch: Batch, view_box: Rectangle):
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

        self.chunks: ChunkGrid = ChunkGrid(init_width, init_height)

    @global_timer.timed
    def update(self, dt):
        # the scale added will depend on the camera's movement speed.
        # view_box = self.camera.rectangle.scale(-200., -200.)
        # view_box = self.camera.rectangle.scale(200., 200.)
        view_box = self.camera.rectangle
        self.chunks.process_graphics(self.batch, view_box)
