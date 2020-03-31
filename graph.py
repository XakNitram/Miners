from collections import deque
from typing import Deque, Optional

from pyglet.gl import GL_LINES
from pyglet.graphics import vertex_list_indexed
from pyglet.graphics.vertexdomain import IndexedVertexList


class Graph:
    graph: IndexedVertexList

    def __init__(
            self, x: float, y: float,
            width: float, height: float,
            padx: float = 2., pady: float = 2.,
            samples: int = 10,
            maximum: Optional[float] = None
    ):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.padx = padx
        self.pady = pady

        if maximum is None:
            self._maximum = 100.
            self._static_maximum = 100.
            self._maximum_is_set = False
        else:
            self._maximum = maximum
            self._static_maximum = maximum
            self._maximum_is_set = True

        try:
            self._samples = int(samples)
        except ValueError:
            raise ValueError(f"invalid literal for parameter 'samples' with base 10: '{samples}'")

        del samples
        samples = self._samples

        self._data: Deque[float] = deque(maxlen=samples)
        self._count: int = 0

        self.graph = vertex_list_indexed(
            samples, self.indices, 'v2f/stream',
            ('c3f', [0., 1., 0.] * samples)
        )
        space_x = (self.width - self.padx * 2) / (samples - 1)

        base_vertices = [0.0, 0.0] * samples
        for i, j in enumerate(range(0, samples * 2, 2)):
            base_x = self.x + self.padx + (i * space_x)
            base_y = self.y + self.pady

            base_vertices[j:j+2] = base_x, base_y
        self.graph.vertices = base_vertices

        self._invalid = True
        # TODO: implement border

    def invalidate(self):
        self._invalid = True

    @property
    def maximum(self):
        return self._maximum

    @maximum.setter
    def maximum(self, value: Optional[float]):
        if value is not None:
            self._maximum = value
            self._maximum_is_set = True
        else:
            self._maximum = (sum(self._data) / self.samples) * 2
            self._maximum_is_set = False

    @property
    def samples(self):
        return self._samples

    def update_samples(self, samples: int):
        try:
            samples = int(samples)
        except ValueError:
            raise ValueError(f"invalid literal for parameter 'samples' with base 10: '{samples}'")

        old_samples = self.samples
        if samples == old_samples:
            return

        diff = abs(samples - old_samples)
        if samples > old_samples:
            new_data = deque(list(self._data), maxlen=samples)
            old_vertices = list(self.graph.vertices)

            old_vertices += [0.0, self.y + self.pady] * diff
        else:
            new_data = deque(list(self._data)[diff:diff + samples], maxlen=samples)
            old_vertices = list(self.graph.vertices[diff * 2:(diff + samples) * 2])
            print(range(diff, diff+samples))

        space_x = (self.width - self.padx * 2) / (samples - 1)
        for i, j in enumerate(range(0, samples * 2, 2)):
            base_x = self.x + self.padx + (i * space_x)

            old_vertices[j] = base_x

        self._count = 0
        self._samples = samples
        self._data = new_data

        self.graph = vertex_list_indexed(
            samples, self.indices, 'v2f/stream',
            ('c3f', [1., 0., 0.] * samples)
        )
        self.graph.vertices = old_vertices

    @property
    def indices(self):
        # [0, 1, 1, 2, 2, 3, 3, 4, ...]
        samples = self.samples

        indices = [0] * (samples * 2)

        for i, points in zip(
                range(0, samples * 2, 2),
                zip(range(0, samples - 1), range(1, samples))
        ):
            indices[i:i+2] = points
        return indices

    def push(self, value: float):
        self._data.append(value)

        if self._maximum < value:
            self._maximum = value
            self._count = 1
        elif self._count >= self.samples + 1 or not self._count:
            max_in_data = max(self._data)
            if self._maximum_is_set:
                self._maximum = max(
                    self._static_maximum,
                    max_in_data
                )
            else:
                self._maximum = max(
                    (sum(self._data) / self.samples) * 2,
                    max_in_data
                )
            self._count = 1

        self._count += 1
        self.invalidate()

    def update(self, dt: float):
        # TODO: Vertical Graph?
        if self._invalid:
            y_dist = (self.height - self.pady * 2) / self.maximum

            # iterate over the time_data here
            new_positions = list(self.graph.vertices)
            for i, point in zip(range(1, self.samples * 2, 2), self._data):
                new_y = (self.y + self.pady + (point * y_dist))
                new_positions[i] = new_y
            self.graph.vertices = new_positions

    def draw(self):
        self.graph.draw(GL_LINES)
