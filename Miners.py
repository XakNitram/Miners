import pyglet


class Simulation:
    width = 800
    height = 640

    def __init__(self):
        self.window = pyglet.window.Window(
            width=self.width, height=self.height,
            vsync=True,
        )

    def update(self, dt: float):
        pass

    def on_draw(self):
        self.window.clear()

    def setup(self):
        pyglet.clock.schedule_interval(
            self.update, 1. / 60.
        )

    def run(self):
        self.setup()
        pyglet.app.run()


if __name__ == '__main__':
    sim = Simulation()
    sim.run()
