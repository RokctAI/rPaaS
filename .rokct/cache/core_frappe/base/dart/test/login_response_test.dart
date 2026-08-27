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


import 'package:flutter_test/flutter_test.dart';

import 'package:base_sdk/src/models/response/login_response.dart';

void main() {
  group('LoginResponse / UserData parsing', () {
    test('parses the full login contract incl. refresh_token/expires_at',
        () {
      final response = LoginResponse.fromJson({
        'timestamp': '2026-08-14 09:00:00',
        'status': true,
        'message': 'Logged In',
        'data': {
          'access_token': 'apikey:apisecret',
          'refresh_token': 'refresh-32-chars',
          'expires_at': '2026-08-15 09:00:00',
          'token_type': 'Bearer',
        },
      });
      expect(response.status, isTrue);
      expect(response.data?.accessToken, 'apikey:apisecret');
      expect(response.data?.refreshToken, 'refresh-32-chars');
      expect(response.data?.expiresAt, '2026-08-15 09:00:00');
      expect(response.data?.tokenType, 'Bearer');
    });

    test('tolerates responses without a refresh contract (Google/OTP)', () {
      final data = UserData.fromJson({
        'access_token': 'apikey:apisecret',
        'token_type': 'Bearer',
      });
      expect(data.accessToken, 'apikey:apisecret');
      expect(data.refreshToken, isNull);
      expect(data.expiresAt, isNull);
    });

    test('round-trips through toJson', () {
      final data = UserData.fromJson({
        'access_token': 'a:b',
        'refresh_token': 'r',
        'expires_at': '2026-08-15 09:00:00',
        'token_type': 'Bearer',
      });
      final json = data.toJson();
      expect(json['refresh_token'], 'r');
      expect(json['expires_at'], '2026-08-15 09:00:00');
    });

    test('failure shape (status:false) parses with null data', () {
      final response = LoginResponse.fromJson({
        'status': false,
        'message': 'Invalid refresh token',
      });
      expect(response.status, isFalse);
      expect(response.data, isNull);
    });
  });
}
