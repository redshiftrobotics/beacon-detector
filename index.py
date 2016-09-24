from enum import Enum
from time import sleep
from os import listdir
from random import shuffle
from functools import reduce

from PIL import Image, ImageFont, ImageDraw


# TODO: The im.pix() api we're using is fairly slow, but it allows us to still use a PIL.Image
# object. For competition, we should switch to im.getdata(). We'd loose our fancy debug view, but it
# would likely be worth it.

IMAGE_SIZE = 1000
THUMBNAIL_SIZE = IMAGE_SIZE // 5
BEACON_VIEW_WIDTH = IMAGE_SIZE // 5
BEACON_VIEW_HEIGHT = BEACON_VIEW_WIDTH // 2
FONT_SIZE = 20

font = ImageFont.truetype('font.ttf', FONT_SIZE)

DEFAULT_OPTIONS = {
  # You might be wondering about this next line. The problem is that beacons don't emit red light.
  # It's actually light pink. This means that there is a large amount of blue in it. Therefore, we
  # need to mostly ignore the blue channel, because it ended up with us actually ignoring a lot of
  # red. Ideally, we'd make the G channel higher too, but then we'd start to get a lot of noise.
  # This might go horribly wrong if the match is played against a purple background.
  'red': [210, 150, 240], # MIN, MAX, MAX
  'blu': [ 85, 255, 200], # MAX, MAX, MIN
  'classify': { 'main': IMAGE_SIZE * .2, 'other': IMAGE_SIZE * .05 }
}

class BeaconState(Enum):
  Blue = 'blue'
  Red = 'red'
  BlueRed = 'bluered'
  RedBlue = 'redblue'


class BeaconDetector:
  def __init__(self, options={}):
    self._options = {**DEFAULT_OPTIONS, **options}

  def _process_pixel(self, x, y, pxl):
    """
    Determine if a pixel is Red, Blue or Black
    :param x: the x-coordinate of the pixel
    :param y: the y-coordinate of the pixel
    :param pxl: the pixel as a (R, G, B) tuple
    :returns: a (R, G, B) value of the color the pixel should be displayed as
    """
    R, G, B = pxl
    if R < self._options['blu'][0] and G < self._options['blu'][1] and B > self._options['blu'][2]:
      self.blus[x] += 1
      return (0, 0, 255)
    if R > self._options['red'][0] and G < self._options['red'][1] and B < self._options['red'][2]:
      self.reds[x] += 1
      return (255, 0, 0)
    return (0, 0, 0)

  def detect(self, im):
    """
    Parse an image and try to detect a beacon.

    :param im: a PIL.Image image object.
    :return BeaconState: the state of the beacon.
    """
    self.im = im
    self.pix = im.load()

    self.reds = [0] * im.size[0]
    self.blus = [0] * im.size[0]

    for x in range(self.im.size[0]):
      for y in range(self.im.size[1]):
        self.pix[x, y] = self._process_pixel(x, y, self.pix[x, y])

    ret = self._classify_image()

    self.im, self.pix, self.reds, self.blus = None, None, None, None

    return ret

  def _find_biggest_streak(self, vals):
    biggest_start  = 0
    biggest_length = 0
    current_start  = -1
    current_length = -1

    for i in range(len(vals)):
      if vals[i] == 0:
        if biggest_length < current_length:
          biggest_start, biggest_length = current_start, current_length
        current_start = -1
        current_length = 0
      else:
        if current_start == -1:
          current_start = i
        current_length += 1

    return (biggest_start, biggest_length)

  def _find_bluered_order(self):
    for i in range(len(self.reds)):
      if self.reds[i] <= self.blus[i]:
        self.reds[i] = 0
      else:
        self.blus[i] = 0

    r_start, r_len = self._find_biggest_streak(self.reds)
    b_start, b_len = self._find_biggest_streak(self.blus)

    if r_start < b_start:
      return BeaconState.RedBlue
    else:
      return BeaconState.BlueRed

  def _classify_image(self):
    num_red = reduce(lambda x, num: num + x, self.reds)
    num_blu = reduce(lambda x, num: num + x, self.blus)
    if num_blu <= self._options['classify']['other'] and num_red > self._options['classify']['main']:
      return BeaconState.Red
    if num_red <= self._options['classify']['other'] and num_blu > self._options['classify']['main']:
      return BeaconState.Blue
    if num_red < self._options['classify']['main']  and num_blu < self._options['classify']['main']:
      return None
    return self._find_bluered_order()

def main():
  num_pass, num_fail = 0, 0
  images = []
  detector = BeaconDetector()

  for state in BeaconState:
    for image in listdir('images/{}'.format(state.value)):
      if image[-4:].lower() == '.jpg':
        images.append((state, 'images/{}/{}'.format(state.value, image)))

  shuffle(images)

  for ex_state, name in images:
    im = Image.open(name)
    thumbnail = im.copy()
    thumbnail.thumbnail((THUMBNAIL_SIZE, THUMBNAIL_SIZE))
    im.thumbnail((IMAGE_SIZE, IMAGE_SIZE))

    state = detector.detect(im)

    _add_helper_views(name, im, state, thumbnail)

    im.show()

    print('{}: Expected: {}, Actual: {}, OK: {}' \
          .format(name, ex_state, state, state is ex_state))

    if state is ex_state:
      num_pass += 1
    else:
      num_fail += 1

  num_total = num_pass + num_fail
  print("Pass: {}/{}. {}%".format(num_pass, num_total, (num_pass/num_total) * 100))



def _add_helper_views(name, im, state, thumbnail):
  draw = ImageDraw.Draw(im)
  im.paste(thumbnail, (im.size[0] - thumbnail.size[0], im.size[1] - thumbnail.size[1]))

  if state is BeaconState.Red or state is BeaconState.Blue:
    color = (255, 0, 0) if state is BeaconState.Red else (0, 0, 255)
    color_im = Image.new('RGB', (BEACON_VIEW_WIDTH, BEACON_VIEW_HEIGHT), color=color)
    im.paste(color_im, (0, im.size[1] - BEACON_VIEW_HEIGHT))
  elif state is BeaconState.BlueRed or state is BeaconState.RedBlue:
    color_1 = (0, 0, 255)
    color_2 = (255, 0, 0)
    if state is BeaconState.RedBlue:
      color_1, color_2 = color_2, color_1
    color_1_im = Image.new('RGB', (BEACON_VIEW_WIDTH // 2, BEACON_VIEW_HEIGHT), color=color_1)
    color_2_im = Image.new('RGB', (BEACON_VIEW_WIDTH // 2, BEACON_VIEW_HEIGHT), color=color_2)
    im.paste(color_1_im, (0, im.size[1] - BEACON_VIEW_HEIGHT))
    im.paste(color_2_im, (BEACON_VIEW_WIDTH // 2, im.size[1] - BEACON_VIEW_HEIGHT))

  draw.text((10, 10), name.lstrip('images/'), font=font)


if __name__ == '__main__':
  main()


