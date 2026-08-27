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
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:map_launcher/map_launcher.dart';
import 'package:base_sdk/src/presentation/theme/app_style.dart';

import 'buttons/buttons_bouncing_effect.dart';

class MapsList extends StatefulWidget {
  final Coords location;
  final String title;

  const MapsList({super.key, required this.location, required this.title});

  @override
  State<MapsList> createState() => _MapsListState();
}

class _MapsListState extends State<MapsList> {
  List<AvailableMap> availableMaps = [];

  @override
  void initState() {
    installedMaps();
    super.initState();
  }

  installedMaps() async {
    availableMaps = await MapLauncher.installedMaps;
    setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    return ListView.builder(
        shrinkWrap: true,
        itemCount: availableMaps.length,
        itemBuilder: (context, index) {
          return ButtonsBouncingEffect(
            child: Container(
              margin: EdgeInsets.symmetric(horizontal: 24.w, vertical: 8.h),
              decoration: BoxDecoration(
                  color: AppStyle.white, borderRadius: BorderRadius.circular(16)),
              child: ListTile(
                onTap: () => availableMaps[index].showMarker(
                  coords: widget.location,
                  title: widget.title,
                ),
                title: Text(availableMaps[index].mapName),
                leading: ClipRRect(
                  borderRadius: BorderRadius.circular(16.r),
                  child: SvgPicture.asset(
                    availableMaps[index].icon,
                    height: 30.0,
                    width: 30.0,
                  ),
                ),
              ),
            ),
          );
        });
  }
}
