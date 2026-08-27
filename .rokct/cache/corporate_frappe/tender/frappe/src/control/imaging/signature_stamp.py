# Copyright (c) 2026 RokctAI
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""Deterministic signature/initials background stripping (Pillow only, no AI).

A signature scan arrives as dark ink strokes on a solid background - white
paper is the recommended path, but any solid color works. Stamping that scan
onto a form as-is prints a solid box over the form's own lines, so the SDK
strips the background once at upload:

1. the background color is detected as the per-channel median of the four
   corner pixels (a signature never reaches all four corners of a sensible
   scan);
2. each pixel's distance from the background is the maximum per-channel
   difference;
3. pixels within ``tolerance`` of the background go fully transparent, pixels
   beyond ``2 * tolerance`` stay fully opaque, and the band between ramps
   linearly so anti-aliased stroke edges keep a soft edge.

Everything is pure arithmetic on pixel values - the same input bytes always
produce the same output bytes.
"""

import io

# Pixels this close to the detected background (max per-channel difference,
# 0-255) become fully transparent; full opacity resumes at twice this value.
DEFAULT_TOLERANCE = 60


def detect_background_color(image):
	"""Per-channel median of the four corner pixels of an RGB Pillow image."""
	width, height = image.size
	corners = [
		image.getpixel((0, 0)),
		image.getpixel((width - 1, 0)),
		image.getpixel((0, height - 1)),
		image.getpixel((width - 1, height - 1)),
	]
	channels = []
	for index in range(3):
		values = sorted(corner[index] for corner in corners)
		# median of four = mean of the middle two, floored to an int
		channels.append((values[1] + values[2]) // 2)
	return tuple(channels)


def _alpha_lut(tolerance):
	"""256-entry lookup: background-distance -> alpha (0 / linear ramp / 255)."""
	lut = []
	for distance in range(256):
		if distance <= tolerance:
			lut.append(0)
		elif distance >= 2 * tolerance:
			lut.append(255)
		else:
			lut.append(round((distance - tolerance) * 255.0 / tolerance))
	return lut


def strip_background(image_bytes, tolerance=DEFAULT_TOLERANCE):
	"""Returns the image as transparent-background PNG bytes.

	Ink strokes keep their original color; near-background pixels become
	transparent. Existing transparency in the source is preserved (the
	computed alpha never exceeds the original alpha).
	"""
	from PIL import Image, ImageChops

	source = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
	rgb = source.convert("RGB")

	background = detect_background_color(rgb)
	background_image = Image.new("RGB", rgb.size, background)
	difference = ImageChops.difference(rgb, background_image)
	red, green, blue = difference.split()
	distance = ImageChops.lighter(ImageChops.lighter(red, green), blue)

	alpha = distance.point(_alpha_lut(int(tolerance)))
	original_alpha = source.split()[3]
	alpha = ImageChops.darker(alpha, original_alpha)

	result = Image.merge("RGBA", (*rgb.split(), alpha))
	output = io.BytesIO()
	result.save(output, format="PNG")
	return output.getvalue()
