from os import listdir
from time import sleep
from random import shuffle

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

def _classify_image(red, blue):
  if blue <= CLASSIFICATION_OTHER_THRESHOLD and red > CLASSIFICATION_THRESHOLD:
    return 'red'
  elif red <= CLASSIFICATION_OTHER_THRESHOLD and blue > CLASSIFICATION_THRESHOLD:
    return 'blue'
  elif red < CLASSIFICATION_THRESHOLD and blue < CLASSIFICATION_THRESHOLD:
    return None
  else:
    return 'bluered'

def process_image(image):
  global num_pass, num_fail
  state, name = image
  im = Image.open(name)
  thumbnail = im.copy()
  thumbnail.thumbnail((THUMBNAIL_SIZE, THUMBNAIL_SIZE))
  im.thumbnail((IMAGE_SIZE, IMAGE_SIZE))

  draw = ImageDraw.Draw(im)

  pix = im.load()

  num_red = 0
  num_blue = 0

  def _process_pixel(pxl):
    nonlocal num_red, num_blue
    R, G, B = pxl
    if R < BLU_R and G < BLU_G and B > BLU_B:
      num_blue = num_blue + 1
      return (0, 0, 255)
    if R > RED_R and G < RED_G and B < RED_B:
      num_red = num_red + 1
      return (255, 0, 0)
    return (0, 0, 0)

  for i in range(im.size[0]):
    for j in range(im.size[1]):
      pix[i, j] = _process_pixel(pix[i, j])

  im.paste(thumbnail, (im.size[0] - thumbnail.size[0], im.size[1] - thumbnail.size[1]))

  actual_state = _classify_image(num_red, num_blue)
  if actual_state == 'red' or actual_state == 'blue':
    color = (255, 0, 0) if actual_state == 'red' else (0, 0, 255)
    color_im = Image.new('RGB', (BEACON_VIEW_WIDTH, BEACON_VIEW_HEIGHT), color=color)
    im.paste(color_im, (0, im.size[1] - BEACON_VIEW_HEIGHT))
  elif actual_state == 'bluered' or actual_state =='redblue':
    color_1 = (0, 0, 255)
    color_2 = (255, 0, 0)
    if actual_state == 'redblue':
      color_1, color_2 = color_2, color_1
    color_1_im = Image.new('RGB', (BEACON_VIEW_WIDTH // 2, BEACON_VIEW_HEIGHT), color=color_1)
    color_2_im = Image.new('RGB', (BEACON_VIEW_WIDTH // 2, BEACON_VIEW_HEIGHT), color=color_2)
    im.paste(color_1_im, (0, im.size[1] - BEACON_VIEW_HEIGHT))
    im.paste(color_2_im, (BEACON_VIEW_WIDTH // 2, im.size[1] - BEACON_VIEW_HEIGHT))

  draw.text((10, 10), name.lstrip('images/'), font=font)

  im.show('test')

  print('{}: Red: {}, Blue: {}, Expected: {}, Actual: {}, OK: {}' \
        .format(name, num_red, num_blue, state, actual_state, state == actual_state))
  if state == actual_state:
    num_pass = num_pass + 1
  else:
    num_fail = num_fail + 1
    im.show()


images = []

for state in ['blue', 'red', 'bluered']:
  for image in listdir('images/{}'.format(state)):
    if image[-4:].lower() == '.jpg':
      images.append((state, 'images/{}/{}'.format(state, image)))


shuffle(images)

for image in images:
  process_image(image)

num_total = num_pass + num_fail

print("Pass: {}/{}. {}%".format(num_pass, num_total, (num_pass/num_total) * 100))
