/// PhaseGuard Design System
/// All color, typography, and spacing tokens used across the app.
library app_theme;

import 'package:flutter/material.dart';

class AppColors {
  // Primary palette - Blue (matching logo)
  static const primary = Color(0xFF0066FF);
  static const primaryDark = Color(0xFF0044AA);
  static const primaryLight = Color(0xFF3388FF);
  static const onPrimary = Colors.white;
  static const primary10 = Color(0x1A0066FF);
  static const primary20 = Color(0x330066FF);
  static const onPrimary10 = Color(0x1AFFFFFF);

  // Secondary
  static const secondary = Color(0xFF3388FF);
  static const onSecondary = Colors.white;
  static const secondary20 = Color(0x333388FF);

  // Tertiary (danger / decline)
  static const tertiary = Color(0xFFEF4444);

  // Background - Black based
  static const primaryBackground = Color(0xFF000000);
  static const secondaryBackground = Color(0xFF0A0A0A);
  static const surfaceVariant = Color(0xFF141414);
  static const surface30 = Color(0x4D141414);
  static const surface40 = Color(0x66141414);
  static const surface20 = Color(0x33141414);

  // Text
  static const primaryText = Colors.white;
  static const secondaryText = Color(0xFFB0B0B0);
  static const accent3 = Color(0xFF606060);

  // Borders
  static const alternate = Color(0xFF1A1A1A);

  // Semantic
  static const success = Color(0xFF22C55E);
  static const error = Color(0xFFEF4444);
  static const warning = Color(0xFFF59E0B);

  // Utility
  static const onSurface = Colors.white;
  static const fullContrast = Color(0x266C63FF);
  static const onPrimaryContainer = Color(0xFFE0DEFF);
  static const onError = Colors.white;
}

class AppTextStyles {
  static const _fontFamily = 'Roboto';

  static TextStyle titleLarge = const TextStyle(
    fontFamily: _fontFamily,
    fontSize: 24,
    fontWeight: FontWeight.bold,
    color: AppColors.primaryText,
    letterSpacing: 0.3,
    height: 1.3,
  );

  static TextStyle titleMedium = const TextStyle(
    fontFamily: _fontFamily,
    fontSize: 18,
    fontWeight: FontWeight.bold,
    color: AppColors.primaryText,
    letterSpacing: 0.2,
    height: 1.4,
  );

  static TextStyle titleSmall = const TextStyle(
    fontFamily: _fontFamily,
    fontSize: 16,
    fontWeight: FontWeight.bold,
    color: AppColors.primaryText,
    height: 1.4,
  );

  static TextStyle labelMedium = const TextStyle(
    fontFamily: _fontFamily,
    fontSize: 14,
    fontWeight: FontWeight.w600,
    color: AppColors.primaryText,
    letterSpacing: 0.3,
    height: 1.3,
  );

  static TextStyle labelSmall = const TextStyle(
    fontFamily: _fontFamily,
    fontSize: 12,
    fontWeight: FontWeight.w500,
    color: AppColors.secondaryText,
    height: 1.2,
  );

  static TextStyle bodyMedium = const TextStyle(
    fontFamily: _fontFamily,
    fontSize: 14,
    fontWeight: FontWeight.normal,
    color: AppColors.primaryText,
    height: 1.5,
  );

  static TextStyle bodySmall = const TextStyle(
    fontFamily: _fontFamily,
    fontSize: 12,
    fontWeight: FontWeight.normal,
    color: AppColors.secondaryText,
    height: 1.4,
  );

  static TextStyle headlineSmall = const TextStyle(
    fontFamily: _fontFamily,
    fontSize: 22,
    fontWeight: FontWeight.bold,
    color: AppColors.primaryText,
    height: 1.3,
    letterSpacing: 0.5,
  );

  static TextStyle bodyLarge = const TextStyle(
    fontFamily: _fontFamily,
    fontSize: 16,
    fontWeight: FontWeight.normal,
    color: AppColors.primaryText,
    height: 1.6,
  );

  static TextStyle labelLarge = const TextStyle(
    fontFamily: _fontFamily,
    fontSize: 16,
    fontWeight: FontWeight.w600,
    color: AppColors.primaryText,
    letterSpacing: 0.3,
  );
}

class AppRadius {
  static const small = 8.0;
  static const medium = 12.0;
  static const large = 20.0;
  static const full = 9999.0;
}

class AppSpacing {
  static const xs = 4.0;
  static const sm = 8.0;
  static const md = 16.0;
  static const lg = 24.0;
  static const xl = 32.0;
}
