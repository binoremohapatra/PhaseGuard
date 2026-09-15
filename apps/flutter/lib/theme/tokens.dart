import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// Exact tokens from index.html `:root` and component CSS.
class PgColors {
  // Existing base (some updated per Step 0 requirements)
  static const bgPrimary = Color(0xFF0D0D12);      // The new deep dark background
  static const bgSecondary = Color(0xFF14141C);    // slightly lighter than bgPrimary
  static const accentBlue = Color(0xFF5483B3);
  static const mediumBlue = Color(0xFF7DA0CA);
  static const lightBlue = Color(0xFFC1E8FF);
  
  static const safe = Color(0xFF00E5A0);           // signature safe-green
  static const safeGlow = Color(0x4000E5A0);       // 25% opacity for box-shadow
  
  static const warn = Color(0xFFF4C95D);
  static const uncertain = Color(0xFFFFB020);      // amber
  static const uncertainGlow = Color(0x40FFB020);  // 25% opacity
  
  static const crit = Color(0xFFFF5D6C);
  static const criticalGlow = Color(0x40FF5D6C);   // pairs with existing `crit` (25% opacity)
  
  static const limited = Color(0xFF6B7280);        // muted grey, deliberately no glow
  
  static const dspAccent = Color(0xFF9D5CFF);      // purple, "AI/experimental" signal
  
  static const white = Colors.white;
  static const screenBottom = Color(0xFF010A18);

  // ADD — surface layers (for glassmorphism card depth)
  static const surfaceGlass = Color(0x1AFFFFFF);   // 10% white, for frosted cards
  static const borderSubtle = Color(0x1AFFFFFF);   // hairline borders on glass cards

  static const glassBg = Color.fromRGBO(193, 232, 255, 0.05);
  static const glassBgStrong = Color.fromRGBO(193, 232, 255, 0.08);
  static const glassBorder = Color.fromRGBO(193, 232, 255, 0.14);

  static const screenGradient = [
    Color(0xFF5483B3),
    Color(0xFF052659),
    Color(0xFF021024),
    Color(0xFF010A18),
  ];

  static const primaryBtn = [Color(0xFFFF6B78), Color(0xFFFF4457)];
}

class PgType {
  // Display font: Poppins (already used in PgTheme.display) — headings, banners, buttons
  // Body font: Inter (already used in PgTheme.body) — paragraphs, labels
  // ADD a THIRD font role for technical readouts:
  static TextStyle mono({double size = 13, Color color = PgColors.lightBlue, FontWeight weight = FontWeight.w500}) =>
      GoogleFonts.jetBrainsMono(fontSize: size, color: color, fontWeight: weight);
  // Use PgType.mono() for: PDI scores, SHA-256 hashes, timestamps, phone numbers — anything numeric/technical.
}

class PgSpacing {
  static const xs = 4.0, sm = 8.0, md = 16.0, lg = 24.0, xl = 32.0, xxl = 48.0;
}

class PgRadius {
  static const card = 20.0, button = 14.0, chip = 100.0, bar = 8.0; // pill-shaped chips/badges + bar for pills
}

// Keeping old ones so app_theme.dart doesn't break if they were used elsewhere
class PgRadii {
  static const glass = 22.0;
  static const pill = 999.0;
  static const nav = 26.0;
  static const icon = 10.0;
  static const bar = 4.0;
}

class PgSpace {
  static const screenH = 20.0;
  static const section = 28.0;
  static const titleGap = 14.0;
  static const navBottom = 120.0;
}
