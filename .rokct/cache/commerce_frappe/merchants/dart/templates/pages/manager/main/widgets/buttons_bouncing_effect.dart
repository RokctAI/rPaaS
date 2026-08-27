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

import 'package:flutter/material.dart';

/// Press-scale feedback wrapper for the add-order FAB, ported from
/// paas_manager `lib/presentation/component/buttons/buttons_bouncing_effect.dart`.
/// base_sdk has no equivalent component; if one lands there later, delete
/// this copy and repoint the import in main_page.dart.
class ButtonsBouncingEffect extends StatefulWidget {
  final bool disabled;
  final Widget child;

  const ButtonsBouncingEffect({
    super.key,
    required this.child,
    this.disabled = true,
  });

  @override
  State createState() => _ButtonsBouncingEffectState();
}

class _ButtonsBouncingEffectState extends State<ButtonsBouncingEffect>
    with TickerProviderStateMixin {
  AnimationController? _controllerA;
  double squareScaleA = 0.95;

  @override
  void initState() {
    _controllerA = AnimationController(
      vsync: this,
      lowerBound: 0.95,
      upperBound: 1.0,
      duration: const Duration(milliseconds: 80),
    );
    _controllerA?.addListener(
      () {
        setState(() {
          squareScaleA = _controllerA!.value;
        });
      },
    );
    _controllerA?.forward(from: 0.0);
    super.initState();
  }

  @override
  void dispose() {
    _controllerA?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return widget.disabled
        ? Listener(
            onPointerDown: (_) {
              _controllerA!.reverse();
            },
            onPointerUp: (_) {
              _controllerA!.forward(from: 1.0);
            },
            child: Transform.scale(
              scale: squareScaleA,
              child: widget.child,
            ),
          )
        : widget.child;
  }
}
