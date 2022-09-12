import time
import ulab
import busio
import board
import displayio
import digitalio
import terminalio
import adafruit_tsl2591
import collections
import gamepadshift
import adafruit_itertools as itertools
from adafruit_display_text import label
from adafruit_bitmap_font import bitmap_font


class LightSensorDisplay:

    LOOP_DT = 0.1
    GAIN_BUTTON = 2
    IWIN_BUTTON = 1
    BUTTON_DEADTIME = 1.0
    DEFAULT_GAIN = 'HIGH'
    DEFAULT_IWIN = '400MS'

    GAIN_DICT = collections.OrderedDict([ 
        ('LOW'  , adafruit_tsl2591.GAIN_LOW  ), 
        ('MED'  , adafruit_tsl2591.GAIN_MED  ), 
        ('HIGH' , adafruit_tsl2591.GAIN_HIGH ), 
        ('MAX'  , adafruit_tsl2591.GAIN_MAX  ), 
        ])

    IWIN_DICT = collections.OrderedDict([ 
        ('100MS'  , adafruit_tsl2591.INTEGRATIONTIME_100MS), 
        ('200MS'  , adafruit_tsl2591.INTEGRATIONTIME_200MS), 
        ('300MS'  , adafruit_tsl2591.INTEGRATIONTIME_300MS), 
        ('400MS'  , adafruit_tsl2591.INTEGRATIONTIME_400MS), 
        ('500MS'  , adafruit_tsl2591.INTEGRATIONTIME_500MS), 
        ('600MS'  , adafruit_tsl2591.INTEGRATIONTIME_600MS), 
        ])

    def __init__(self):

        # Gain cycle
        self.gain_cycle = itertools.cycle(self.GAIN_DICT)
        self.gain_name = ''
        while self.gain_name != self.DEFAULT_GAIN:
            self.gain_name = next(self.gain_cycle)

        # Integration time cycle
        self.iwin_cycle = itertools.cycle(self.IWIN_DICT)
        self.iwin_name = ''
        while self.iwin_name != self.DEFAULT_IWIN:
            self.iwin_name = next(self.iwin_cycle)

        self.last_button_press = time.monotonic()

        # Set up color palette
        self.color_to_rgb = collections.OrderedDict([
                ('black' , 0x000000), 
                ('gray'  , 0x9f9f9f), 
                ('red'   , 0xff0000), 
                ('green' , 0x00ff00),
                ('blue'  , 0x0000ff),
                ('white' , 0xffffff),
                ])
        self.color_to_index = {k:i for (i,k) in enumerate(self.color_to_rgb)}
        self.palette = displayio.Palette(len(self.color_to_rgb))
        for i, palette_tuple in enumerate(self.color_to_rgb.items()):
            self.palette[i] = palette_tuple[1]   

        # Create tile grid
        self.bitmap = displayio.Bitmap( 
                board.DISPLAY.width, 
                board.DISPLAY.height, 
                len(self.color_to_rgb)
                )
        self.bitmap.fill(self.color_to_index['black'])
        self.tile_grid = displayio.TileGrid(self.bitmap,pixel_shader=self.palette)
        self.font = terminalio.FONT

        # Create header text label
        header_str = 'LUX'
        text_color = self.color_to_rgb['green']
        self.header_label = label.Label(self.font, text=header_str, color=text_color, scale=2)
        bbox = self.header_label.bounding_box
        self.header_label.x = board.DISPLAY.width//2 - 2*bbox[2]//2
        self.header_label.y = bbox[3] + 10 

        # Create value text label
        value_str = f'__.___'
        text_color = self.color_to_rgb['green']
        self.value_label = label.Label(self.font, text=value_str, color=text_color, scale=2)
        bbox = self.value_label.bounding_box
        self.value_label.x = board.DISPLAY.width//2 - 2*bbox[2]//2
        self.value_label.y = self.header_label.y + bbox[3] + 20 

        # Create text label for gain info
        gain_str = f'GAIN (A) = {self.gain_name}' 
        text_color = self.color_to_rgb['blue']
        self.gain_label = label.Label(self.font, text=gain_str, color=text_color, scale=1)
        bbox = self.gain_label.bounding_box
        self.gain_label.x = board.DISPLAY.width//2 - bbox[2]//2 - 5
        self.gain_label.y = self.value_label.y + bbox[3] + 20 

        # Create text label for integration time info
        iwin_str = f'IWIN (B) = {self.iwin_name}' 
        text_color = self.color_to_rgb['blue']
        self.iwin_label = label.Label(self.font, text=iwin_str, color=text_color, scale=1)
        bbox = self.iwin_label.bounding_box
        self.iwin_label.x = self.gain_label.x
        self.iwin_label.y = self.value_label.y + bbox[3] + 32 
        
        # Ceate display group and add items to it
        self.group = displayio.Group()
        self.group.append(self.tile_grid)
        self.group.append(self.header_label)
        self.group.append(self.value_label)
        self.group.append(self.gain_label)
        self.group.append(self.iwin_label)
        board.DISPLAY.show(self.group)

        # Set up light sensor
        i2c = busio.I2C(board.SCL, board.SDA)
        self.sensor = adafruit_tsl2591.TSL2591(i2c)
        self.sensor.integration_time = self.IWIN_DICT[self.iwin_name]
        self.sensor.gain = self.GAIN_DICT[self.gain_name]
        self.channel = 0

        # Get gamepad 
        self.pad = gamepadshift.GamePadShift(
                digitalio.DigitalInOut(board.BUTTON_CLOCK), 
                digitalio.DigitalInOut(board.BUTTON_OUT),
                digitalio.DigitalInOut(board.BUTTON_LATCH),
                )

        board.DISPLAY.show(self.group)

    def read_sensor(self):
        return float(self.sensor.lux)


    def run(self):

        while True:

            buttons = self.pad.get_pressed()
            print(buttons)
            if buttons:
                now = time.monotonic()
                if now - self.last_button_press > self.BUTTON_DEADTIME:
                    if buttons & self.GAIN_BUTTON:
                        self.gain_name = next(self.gain_cycle)
                        self.sensor.gain = self.GAIN_DICT[self.gain_name]
                        self.gain_label.text = f'GAIN (A) = {self.gain_name}'
                    if buttons & self.IWIN_BUTTON:
                        self.iwin_name = next(self.iwin_cycle)
                        self.sensor.integration_time = self.IWIN_DICT[self.iwin_name]
                        self.iwin_label.text = f'IWIN (B) = {self.iwin_name}'
                    self.last_button_press = now

            try:
                value = self.read_sensor()
            except RuntimeError:
                value = None
            if value is not None:
                self.value_label.text = f'{value:1.3f}'
            else:
                self.value_label.text = 'xx.xxx'

            time.sleep(self.LOOP_DT)
            board.DISPLAY.show(self.group)


# -------------------------------------------------------------------------------------------------------

display = LightSensorDisplay()
display.run()


