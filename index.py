from os import listdir
from time import sleep
from random import shuffle
from functools import reduce

from PIL import Image, ImageFont, ImageDraw

RED_R = 210  # MIN
RED_G = 150  # MAX
# You might be wondering about this next line. The problem is that beacons don't emit red light.
# It's actually light pink. This means that there is a large amount of blue in it. Therefore, we
# need to mostly ignore the blue channel, because it ended up with us actually ignoring a lot of
# red. Ideally, we'd make the G channel higher too, but then we'd start to get a lot of noise.
# This might go horribly wrong if the match is played against a purple background.
RED_B = 240  # MAX

BLU_R =  85  # MAX
BLU_G = 255  # MAX
BLU_B = 200  # MIN

IMAGE_SIZE = 1000
THUMBNAIL_SIZE = IMAGE_SIZE // 5
BEACON_VIEW_WIDTH = IMAGE_SIZE // 5
BEACON_VIEW_HEIGHT = BEACON_VIEW_WIDTH // 2
FONT_SIZE = 20

CLASSIFICATION_THRESHOLD = IMAGE_SIZE * .2
CLASSIFICATION_OTHER_THRESHOLD = IMAGE_SIZE * .05

num_pass = 0
num_fail = 0

font = ImageFont.truetype('font.ttf', FONT_SIZE)

def _find_biggest_streak(vals):
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


def _find_bluered_order(reds, blues):
  for i in range(len(reds)):
    if reds[i] <= blues[i]:
      reds[i] = 0
    else:
      blues[i] = 0

  r_start, r_len = _find_biggest_streak(reds)
  b_start, b_len = _find_biggest_streak(blues)

  if r_start < b_start:
    return 'redblue'
  else:
    return 'bluered'


def _classify_image(reds, blues):
  num_red = reduce(lambda x, num: num + x, reds)
  num_blue = reduce(lambda x, num: num + x, blues)
  if num_blue <= CLASSIFICATION_OTHER_THRESHOLD and num_red > CLASSIFICATION_THRESHOLD:
    return 'red'
  elif num_red <= CLASSIFICATION_OTHER_THRESHOLD and num_blue > CLASSIFICATION_THRESHOLD:
    return 'blue'
  elif num_red < CLASSIFICATION_THRESHOLD and num_blue < CLASSIFICATION_THRESHOLD:
    return None
  else:
    return _find_bluered_order(reds, blues)


def _get_image(name):
  im = Image.open(name)
  thumbnail = im.copy()
  thumbnail.thumbnail((THUMBNAIL_SIZE, THUMBNAIL_SIZE))
  im.thumbnail((IMAGE_SIZE, IMAGE_SIZE))

  pix = im.load()

  return im, thumbnail, pix


def _add_helper_views(name, im, state, thumbnail):
  draw = ImageDraw.Draw(im)
  im.paste(thumbnail, (im.size[0] - thumbnail.size[0], im.size[1] - thumbnail.size[1]))

  if state == 'red' or state == 'blue':
    color = (255, 0, 0) if state == 'red' else (0, 0, 255)
    color_im = Image.new('RGB', (BEACON_VIEW_WIDTH, BEACON_VIEW_HEIGHT), color=color)
    im.paste(color_im, (0, im.size[1] - BEACON_VIEW_HEIGHT))
  elif state == 'bluered' or state =='redblue':
    color_1 = (0, 0, 255)
    color_2 = (255, 0, 0)
    if state == 'redblue':
      color_1, color_2 = color_2, color_1
    color_1_im = Image.new('RGB', (BEACON_VIEW_WIDTH // 2, BEACON_VIEW_HEIGHT), color=color_1)
    color_2_im = Image.new('RGB', (BEACON_VIEW_WIDTH // 2, BEACON_VIEW_HEIGHT), color=color_2)
    im.paste(color_1_im, (0, im.size[1] - BEACON_VIEW_HEIGHT))
    im.paste(color_2_im, (BEACON_VIEW_WIDTH // 2, im.size[1] - BEACON_VIEW_HEIGHT))

  draw.text((10, 10), name.lstrip('images/'), font=font)


def process_image(image):
  global num_pass, num_fail
  state, name = image
  im, thumbnail, pix = _get_image(name)

  reds =  [0] * im.size[0]
  blues = [0] * im.size[0]

  def _process_pixel(x, y, pxl):
    R, G, B = pxl
    if R < BLU_R and G < BLU_G and B > BLU_B:
      blues[x] += 1
      return (0, 0, 255)
    if R > RED_R and G < RED_G and B < RED_B:
      reds[x] += 1
      return (255, 0, 0)
    return (0, 0, 0)

  for x in range(im.size[0]):
    for y in range(im.size[1]):
      pix[x, y] = _process_pixel(x, y, pix[x, y])


  actual_state = _classify_image(reds, blues)
  _add_helper_views(name, im, actual_state, thumbnail)

  im.show()

  print('{}: Red: {}, Blue: {}, Expected: {}, Actual: {}, OK: {}' \
        .format(name, sum(reds), sum(blues), state, actual_state, state == actual_state))
  if state == actual_state:
    num_pass = num_pass + 1
  else:
    num_fail = num_fail + 1


images = []

for state in ['blue', 'red', 'bluered', 'redblue']:
  for image in listdir('images/{}'.format(state)):
    if image[-4:].lower() == '.jpg':
      images.append((state, 'images/{}/{}'.format(state, image)))


shuffle(images)

for image in images:
  process_image(image)

num_total = num_pass + num_fail

print("Pass: {}/{}. {}%".format(num_pass, num_total, (num_pass/num_total) * 100))
