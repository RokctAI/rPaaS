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


import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:base_sdk/src/presentation/pages/profile/profile_section.dart';
import 'package:base_sdk/src/presentation/pages/profile/profile_section_registry.dart';

/// Contract under test — the installer marker-block semantics ported to a
/// runtime registry:
///
///   * duplicate section id: first registration wins, the duplicate is
///     dropped;
///   * sections sort by order, ties broken by id, deterministically.
void main() {
  ProfileSection section(String id, int order) =>
      ProfileSection(id: id, order: order, builder: (_) => const SizedBox());

  setUp(() => ProfileSectionRegistry.I.reset());

  test('duplicate id keeps the first registration', () {
    final first = section('wallet', 10);
    ProfileSectionRegistry.I.register(first);
    ProfileSectionRegistry.I.register(section('wallet', 99));

    expect(ProfileSectionRegistry.I.sections, hasLength(1));
    expect(ProfileSectionRegistry.I.sections.single, same(first));
  });

  test('sections sort by order with id tie-break', () {
    ProfileSectionRegistry.I.register(section('zeta', 10));
    ProfileSectionRegistry.I.register(section('alpha', 10));
    ProfileSectionRegistry.I.register(section('omega', 5));

    expect(
      ProfileSectionRegistry.I.sections.map((s) => s.id).toList(),
      ['omega', 'alpha', 'zeta'],
    );
  });

  test('host actions default to unset (affordances hidden)', () {
    expect(ProfileSectionRegistry.I.onEditProfile, isNull);
    expect(ProfileSectionRegistry.I.onLogout, isNull);
  });
}
