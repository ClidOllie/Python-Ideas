"""CalcPhoto.ipynb

This code is meant to run in Google Colab

Original file is located at
    https://colab.research.google.com/drive/1X0pgwkin_0j1ga6dNPejFMLU0Dv4lmL5
"""

import os
import matplotlib.pyplot as plt
from PIL import Image, ImageEnhance
import numpy as np



### Input folder name here
z = input("What is the home folder called on your computer? (eg. johndoe)\n")
y = input("Where is the file? EG: Desktop, Documents, Downloads, ETC\n")
v = input("Is the image in a folder? If not, press enter\n")
x = input("Type in the full name of the image (Including image type).\n")
### Input image name here
img = Image.open(f'/Users/{z}/{y}/{v}/{x}')

# Calculate the new aspect ratio (width:height)
target_aspect_ratio = 95 / 63

# Get the current image size
img_width, img_height = img.size

# Calculate the aspect ratio of the current image
current_aspect_ratio = img_width / img_height

# Check if the current aspect ratio is wider than the target aspect ratio
if current_aspect_ratio > target_aspect_ratio:
    # Calculate the new width to maintain the target aspect ratio
    new_width = int(img_height * target_aspect_ratio)

    # Calculate the x-coordinate for cropping from the center
    left = (img_width - new_width) // 2
    right = left + new_width

    # Crop the image
    img_cropped = img.crop((left, 0, right, img_height))
else:
    # Calculate the new height to maintain the target aspect ratio
    new_height = int(img_width / target_aspect_ratio)

    # Calculate the y-coordinate for cropping from the center
    upper = (img_height - new_height) // 2
    lower = upper + new_height

    # Crop the image
    img_cropped = img.crop((0, upper, img_width, lower))

# Resize the cropped image to 95x63
new_size = (190, 126)
img_resized = img_cropped.resize(new_size)

for i in range(10,25,1):
  print(round((i/10-1)*100), "percent increased contrast:")
  # Increase the contrast of the image by 50%
  contrast_enhancer = ImageEnhance.Contrast(img_resized)
  img_contrast_enhanced = contrast_enhancer.enhance(i/10)  # 1.0 means no change, values > 1 increase contrast

  # Increase the image exposure by 50%
  exposure_enhancer = ImageEnhance.Brightness(img_contrast_enhanced)
  img_exposure_enhanced = exposure_enhancer.enhance(1.1)  # 1.0 means no change, values > 1 increase exposure

  # Convert the exposure-enhanced image to grayscale
  img_gray = img_exposure_enhanced.convert('L')

  # Apply Floyd-Steinberg dithering to create a binary representation
  img_binary = img_gray.convert('1', dither=Image.FLOYDSTEINBERG)

  # Display the binary image
  plt.imshow(img_binary, cmap='gray')
  plt.axis('on')  # Turn off axis to remove ticks
  plt.show()

  # Convert the binary image to a NumPy array and then to a binary string
  binary_array = np.array(img_binary)
  binary_string = ''.join('1' if val else '0' for val in binary_array.flatten())

  # Add a comma after the first digit, then after every 8 digits in the binary string
  binary_string_with_commas = binary_string[0] + ',' + ','.join(binary_string[i:i+8] for i in range(1, len(binary_string), 8))

  print("Binary String with Commas:")
  print(binary_string_with_commas)
  print("---------------------------")
  print("")