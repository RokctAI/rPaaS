// Copyright (c) 2026 RokctAI
//
// Permission is hereby granted, free of charge, to any person obtaining a copy
// of this software and associated documentation files (the "Software"), to deal
// in the Software without restriction, including without limitation the rights
// to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
// copies of the Software, and to permit persons to whom the Software is
// furnished to do so, subject to the following conditions:
//
// The above copyright notice and this permission notice shall be included in all
// copies or substantial portions of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
// OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
// SOFTWARE.

import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:hardware_sdk/hardware_sdk.dart';
import 'package:image/image.dart' as img;

/// Builds a solid-color PNG to use as a source frame.
Uint8List _solidImage(int width, int height,
    {int r = 10, int g = 120, int b = 200}) {
  final image = img.Image(width: width, height: height);
  img.fill(image, color: img.ColorRgb8(r, g, b));
  return Uint8List.fromList(img.encodePng(image));
}

/// Counts pixels that differ between two decoded images within a y-range.
int _differingPixels(img.Image a, img.Image b, int yStart, int yEnd) {
  var changed = 0;
  for (var y = yStart; y < yEnd; y++) {
    for (var x = 0; x < a.width; x++) {
      final pa = a.getPixel(x, y);
      final pb = b.getPixel(x, y);
      if (pa.r != pb.r || pa.g != pb.g || pa.b != pb.b) {
        changed++;
      }
    }
  }
  return changed;
}

void main() {
  group('ImageStamper', () {
    const stamper = ImageStamper();

    test('burns text into the actual pixels (not a no-op)', () {
      final source = _solidImage(400, 300);
      final stamped = stamper.stamp(
        source,
        const ['2026-07-19 12:00:00', 'Lat 1.234567, Lng 2.345678'],
        options: const StampOptions(format: StampImageFormat.png),
      );

      // The encoded bytes must actually change.
      expect(stamped, isNot(equals(source)));

      final original = img.decodeImage(source)!;
      final result = img.decodeImage(stamped)!;

      // Dimensions are preserved.
      expect(result.width, original.width);
      expect(result.height, original.height);

      // The bottom stamp band must contain modified pixels.
      final changed = _differingPixels(result, original, 260, 300);
      expect(
        changed,
        greaterThan(0),
        reason: 'stamp band must differ from the source image',
      );
    });

    test('top-left position stamps the top band, not the bottom', () {
      final source = _solidImage(400, 300);
      final stamped = stamper.stamp(
        source,
        const ['top stamp'],
        options: const StampOptions(
          position: StampPosition.topLeft,
          format: StampImageFormat.png,
        ),
      );

      final original = img.decodeImage(source)!;
      final result = img.decodeImage(stamped)!;

      final topChanged = _differingPixels(result, original, 0, 40);
      final bottomChanged = _differingPixels(result, original, 260, 300);
      expect(topChanged, greaterThan(0));
      expect(bottomChanged, equals(0));
    });

    test('whitespace-only lines still return a valid re-encoded image', () {
      final source = _solidImage(60, 60);
      final stamped = stamper.stamp(source, const ['', '   ']);
      expect(img.decodeImage(stamped), isNotNull);
    });

    test('throws ImageStampException on undecodable bytes', () {
      expect(
        () => stamper.stamp(Uint8List.fromList(const [1, 2, 3, 4]), const ['x']),
        throwsA(isA<ImageStampException>()),
      );
    });

    test('encodes JPEG when requested', () {
      final source = _solidImage(120, 120);
      final stamped = stamper.stamp(
        source,
        const ['jpg'],
        options: const StampOptions(format: StampImageFormat.jpg),
      );
      // JPEG magic bytes.
      expect(stamped[0], 0xFF);
      expect(stamped[1], 0xD8);
    });
  });
}
