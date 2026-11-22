import 'dart:async';

import 'package:flutter/material.dart';

import 'screens/appearance_page.dart';
import 'screens/caption_generator_page.dart';
import 'screens/connection_page.dart';
import 'screens/dashboard_page.dart';
import 'screens/dataset_page.dart';
import 'screens/normalizer_page.dart';
import 'state/app_controller.dart';
import 'widgets/common.dart';
import 'widgets/expressive_shell.dart';

class UdbExpressiveApp extends StatefulWidget {
  const UdbExpressiveApp({super.key, required this.controller});

  final AppController controller;

  @override
  State<UdbExpressiveApp> createState() => _UdbExpressiveAppState();
}

class _UdbExpressiveAppState extends State<UdbExpressiveApp> {
  @override
  void initState() {
    super.initState();
    unawaited(widget.controller.initialize());
  }

  ThemeData _theme(Brightness brightness) {
    final scheme = ColorScheme.fromSeed(
      seedColor: const Color(0xFF82AFFF),
      brightness: brightness,
    );
    return ThemeData(
      useMaterial3: true,
      colorScheme: scheme,
      brightness: brightness,
      scaffoldBackgroundColor: scheme.surface,
      visualDensity: VisualDensity.standard,
      appBarTheme: AppBarTheme(
        backgroundColor: scheme.surface,
        foregroundColor: scheme.onSurface,
        centerTitle: false,
        elevation: 0,
      ),
      cardTheme: CardThemeData(
        color: scheme.surfaceContainerLow,
        elevation: 0,
        margin: EdgeInsets.zero,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(28),
          side: BorderSide(color: scheme.outlineVariant.withAlpha(100)),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: scheme.surfaceContainerHighest.withAlpha(125),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(18),
          borderSide: BorderSide.none,
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(18),
          borderSide: BorderSide(color: scheme.outlineVariant.withAlpha(100)),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(18),
          borderSide: BorderSide(color: scheme.primary, width: 1.6),
        ),
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          minimumSize: const Size(48, 48),
          shape: const StadiumBorder(),
          padding: const EdgeInsets.symmetric(horizontal: 22, vertical: 14),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          minimumSize: const Size(46, 46),
          shape: const StadiumBorder(),
          side: BorderSide(color: scheme.outlineVariant),
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 13),
        ),
      ),
      chipTheme: ChipThemeData(
        shape: const StadiumBorder(),
        side: BorderSide(color: scheme.outlineVariant.withAlpha(100)),
        padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 4),
      ),
      navigationRailTheme: NavigationRailThemeData(
        backgroundColor: scheme.surface,
        indicatorColor: scheme.secondaryContainer,
        selectedIconTheme: IconThemeData(color: scheme.onSecondaryContainer),
        unselectedIconTheme: IconThemeData(color: scheme.onSurfaceVariant),
        selectedLabelTextStyle: TextStyle(
          color: scheme.onSurface,
          fontWeight: FontWeight.w700,
        ),
        unselectedLabelTextStyle: TextStyle(color: scheme.onSurfaceVariant),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: widget.controller,
      builder: (context, _) {
        final controller = widget.controller;
        final themeMode = controller.themeMode == 'system'
            ? ThemeMode.system
            : controller.themeMode == 'light'
                ? ThemeMode.light
                : ThemeMode.dark;
        return MaterialApp(
          title: 'Universal Dataset Builder',
          debugShowCheckedModeBanner: false,
          themeMode: themeMode,
          theme: _theme(Brightness.light),
          darkTheme: _theme(Brightness.dark),
          home: controller.initialized
              ? AppControllerScope(
                  controller: controller,
                  child: ExpressiveShell(
                    controller: controller,
                    pages: [
                      DashboardPage(controller: controller),
                      DatasetPage(controller: controller),
                      NormalizerPage(controller: controller),
                      CaptionGeneratorPage(controller: controller),
                      ConnectionPage(controller: controller),
                      AppearancePage(controller: controller),
                    ],
                  ),
                )
              : const _StartingScreen(),
        );
      },
    );
  }
}

class _StartingScreen extends StatelessWidget {
  const _StartingScreen();

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Scaffold(
      body: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.auto_awesome_rounded, size: 48, color: scheme.primary),
            const SizedBox(height: 18),
            Text(
              'Universal Dataset Builder',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 16),
            const SizedBox(width: 170, child: LinearProgressIndicator()),
          ],
        ),
      ),
    );
  }
}
