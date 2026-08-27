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

import 'package:base_sdk/src/services/location_service.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:geolocator/geolocator.dart';
import 'package:hardware_sdk/hardware_sdk.dart';
import 'package:image/image.dart' as img;

/// A camera stand-in for the capture flow — no physical device required.
class _FakeCamera implements CameraCaptureService {
  final Uint8List bytes;
  bool _initialized = false;
  int captureCount = 0;
  int disposeCount = 0;

  _FakeCamera(this.bytes);

  @override
  Future<void> initialize() async => _initialized = true;

  @override
  bool get isInitialized => _initialized;

  @override
  Future<Uint8List> capture() async {
    captureCount++;
    return bytes;
  }

  @override
  Future<void> dispose() async {
    disposeCount++;
    _initialized = false;
  }
}

/// Subclass of base_sdk's real [LocationService] that returns a canned
/// position, proving the facade integrates with (and reuses) it rather than
/// duplicating location logic.
class _FakeLocationService extends LocationService {
  final Position? position;
  int calls = 0;

  _FakeLocationService(this.position);

  @override
  Future<Position?> determinePosition(BuildContext context) async {
    calls++;
    return position;
  }
}

Uint8List _solidImage(int width, int height) {
  final image = img.Image(width: width, height: height);
  img.fill(image, color: img.ColorRgb8(20, 140, 90));
  return Uint8List.fromList(img.encodePng(image));
}

Position _position(double lat, double lng) => Position(
      latitude: lat,
      longitude: lng,
      timestamp: DateTime.now(),
      accuracy: 1,
      altitude: 0,
      altitudeAccuracy: 0,
      heading: 0,
      headingAccuracy: 0,
      speed: 0,
      speedAccuracy: 0,
    );

Future<BuildContext> _pumpContext(WidgetTester tester) async {
  late BuildContext context;
  await tester.pumpWidget(
    MaterialApp(
      home: Builder(
        builder: (ctx) {
          context = ctx;
          return const SizedBox.shrink();
        },
      ),
    ),
  );
  return context;
}

void main() {
  const pngOptions = StampOptions(format: StampImageFormat.png);

  group('CameraCaptureService (mockable capture flow)', () {
    test('fake camera initializes and yields bytes', () async {
      final camera = _FakeCamera(Uint8List.fromList(const [1, 2, 3]));
      expect(camera.isInitialized, isFalse);
      await camera.initialize();
      expect(camera.isInitialized, isTrue);

      final bytes = await camera.capture();
      expect(bytes, isNotEmpty);
      expect(camera.captureCount, 1);
    });
  });

  group('CameraStampService', () {
    testWidgets('captures, resolves location, and burns both in',
        (tester) async {
      final source = _solidImage(320, 240);
      final camera = _FakeCamera(source);
      final location = _FakeLocationService(_position(1.234567, 2.345678));
      final service =
          CameraStampService(camera: camera, locationService: location);

      final context = await _pumpContext(tester);
      final result =
          await service.captureAndStamp(context: context, options: pngOptions);

      expect(camera.captureCount, 1);
      expect(location.calls, 1, reason: 'must call base_sdk LocationService');
      expect(result.hasLocation, isTrue);
      expect(result.position!.latitude, 1.234567);
      expect(result.stampedLines.any((l) => l.contains('Lat')), isTrue);

      // Stamped output must genuinely differ from the raw capture.
      expect(result.bytes, isNot(equals(result.originalBytes)));
      expect(img.decodeImage(result.bytes), isNotNull);
    });

    testWidgets('includeLocation:false skips the LocationService',
        (tester) async {
      final camera = _FakeCamera(_solidImage(200, 200));
      final location = _FakeLocationService(_position(0, 0));
      final service =
          CameraStampService(camera: camera, locationService: location);

      final context = await _pumpContext(tester);
      final result = await service.captureAndStamp(
        context: context,
        includeLocation: false,
        options: pngOptions,
      );

      expect(location.calls, 0);
      expect(result.position, isNull);
      expect(result.hasLocation, isFalse);
      expect(result.stampedLines.length, 1); // timestamp only
    });

    testWidgets('honors a caller-provided content builder', (tester) async {
      final camera = _FakeCamera(_solidImage(200, 200));
      final service = CameraStampService(
        camera: camera,
        locationService: _FakeLocationService(null),
      );

      final context = await _pumpContext(tester);
      final result = await service.captureAndStamp(
        context: context,
        includeLocation: false,
        contentBuilder: (ctx) => const ['ORDER-42', 'custom line'],
        options: pngOptions,
      );

      expect(result.stampedLines, const ['ORDER-42', 'custom line']);
      expect(result.bytes, isNot(equals(result.originalBytes)));
    });

    testWidgets('a null location still stamps the timestamp', (tester) async {
      final camera = _FakeCamera(_solidImage(200, 200));
      final location = _FakeLocationService(null); // e.g. permission denied
      final service =
          CameraStampService(camera: camera, locationService: location);

      final context = await _pumpContext(tester);
      final result =
          await service.captureAndStamp(context: context, options: pngOptions);

      expect(location.calls, 1);
      expect(result.position, isNull);
      expect(result.stampedLines.length, 1);
    });

    test('dispose delegates to the camera', () async {
      final camera = _FakeCamera(_solidImage(10, 10));
      final service = CameraStampService(
        camera: camera,
        locationService: _FakeLocationService(null),
      );
      await service.dispose();
      expect(camera.disposeCount, 1);
    });
  });
}
