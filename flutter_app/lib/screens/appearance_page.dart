import 'package:material_ui/material_ui.dart';

import '../state/app_controller.dart';
import '../widgets/common.dart';

class AppearancePage extends StatefulWidget {
  const AppearancePage({super.key, required this.controller});

  final AppController controller;

  @override
  State<AppearancePage> createState() => _AppearancePageState();
}

class _AppearancePageState extends State<AppearancePage> {
  bool _previewExpanded = false;

  @override
  Widget build(BuildContext context) {
    final controller = widget.controller;
    final scheme = Theme.of(context).colorScheme;
    final duration = controller.motionDuration(
      620,
      systemReduced: MediaQuery.disableAnimationsOf(context),
    );

    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          PageHeader(
            eyebrow: 'Personalize',
            title: 'Appearance & motion',
            subtitle: 'Shape the look and feel of Expressive UI. Motion effects are optional.',
            trailing: Icon(Icons.palette_rounded, size: 36, color: scheme.primary),
          ),
          LayoutBuilder(
            builder: (context, constraints) {
              final compact = constraints.maxWidth < 820;
              final appearance = SectionCard(
                title: 'Color theme',
                subtitle: 'Choose a theme for the entire Expressive interface.',
                child: RadioGroup<String>(
                  groupValue: controller.themeMode,
                  onChanged: (value) {
                    if (value != null) controller.setThemeMode(value);
                  },
                  child: const Column(
                    children: [
                      RadioListTile<String>(
                        contentPadding: EdgeInsets.zero,
                        value: 'dark',
                        title: const Text('Dark'),
                        secondary: const Icon(Icons.dark_mode_outlined),
                      ),
                      RadioListTile<String>(
                        contentPadding: EdgeInsets.zero,
                        value: 'light',
                        title: const Text('Light'),
                        secondary: const Icon(Icons.light_mode_outlined),
                      ),
                      RadioListTile<String>(
                        contentPadding: EdgeInsets.zero,
                        value: 'system',
                        title: const Text('Follow system'),
                        secondary: const Icon(Icons.brightness_auto_outlined),
                      ),
                    ],
                  ),
                ),
              );
              final motion = SectionCard(
                title: 'Motion controls',
                subtitle: 'These options affect page transitions, cards, expanding sections, and progress details.',
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    SwitchListTile(
                      contentPadding: EdgeInsets.zero,
                      title: const Text('Enable animations'),
                      subtitle: const Text('Turn off to use instant, static transitions throughout Expressive UI.'),
                      value: controller.animationsEnabled,
                      onChanged: controller.setAnimationsEnabled,
                    ),
                    const Divider(height: 20),
                    DropdownButtonFormField<MotionPreset>(
                      initialValue: controller.motionPreset,
                      decoration: const InputDecoration(
                        labelText: 'Animation style',
                        prefixIcon: Icon(Icons.animation_rounded),
                      ),
                      items: const [
                        DropdownMenuItem(
                          value: MotionPreset.gentle,
                          child: Text('Gentle · reduced motion'),
                        ),
                        DropdownMenuItem(
                          value: MotionPreset.expressive,
                          child: Text('Expressive · full motion'),
                        ),
                      ],
                      onChanged: controller.animationsEnabled
                          ? (value) {
                              if (value != null) controller.setMotionPreset(value);
                            }
                          : null,
                    ),
                    const SizedBox(height: 12),
                    Text(
                      controller.animationsEnabled
                          ? controller.motionPreset == MotionPreset.expressive
                              ? 'Full transitions: fade, slide, scale, expanding panels, and animated counters.'
                              : 'Subtle transitions: shorter fades and small movement, with less visual activity.'
                          : 'All optional motion effects are disabled.',
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(color: scheme.onSurfaceVariant),
                    ),
                  ],
                ),
              );
              if (compact) {
                return Column(children: [appearance, const SizedBox(height: 14), motion]);
              }
              return Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(child: appearance),
                  const SizedBox(width: 14),
                  Expanded(child: motion),
                ],
              );
            },
          ),
          const SizedBox(height: 16),
          SectionCard(
            title: 'Motion preview',
            subtitle: 'Try the current animation profile. Changes are saved automatically.',
            trailing: OutlinedButton.icon(
              onPressed: () => setState(() => _previewExpanded = !_previewExpanded),
              icon: const Icon(Icons.play_arrow_rounded),
              label: const Text('Replay'),
            ),
            child: AnimatedContainer(
              duration: duration,
              curve: Curves.easeInOutBack,
              width: double.infinity,
              height: _previewExpanded ? 188 : 108,
              padding: const EdgeInsets.all(18),
              decoration: BoxDecoration(
                color: scheme.secondaryContainer,
                borderRadius: BorderRadius.circular(_previewExpanded ? 30 : 20),
              ),
              child: Row(
                children: [
                  AnimatedRotation(
                    turns: _previewExpanded ? 0.5 : 0,
                    duration: duration,
                    curve: Curves.easeInOutCubic,
                    child: Icon(
                      Icons.auto_awesome_rounded,
                      size: _previewExpanded ? 52 : 38,
                      color: scheme.onSecondaryContainer,
                    ),
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: AnimatedSwitcher(
                      duration: duration,
                      child: Text(
                        _previewExpanded ? 'Expressive motion is active.' : 'A little motion goes a long way.',
                        key: ValueKey(_previewExpanded),
                        style: Theme.of(context).textTheme.titleMedium?.copyWith(
                              color: scheme.onSecondaryContainer,
                              fontWeight: FontWeight.w700,
                            ),
                      ),
                    ),
                  ),
                  AnimatedScale(
                    scale: _previewExpanded ? 1.18 : 1,
                    duration: duration,
                    curve: Curves.easeOutBack,
                    child: Icon(Icons.bubble_chart_rounded, size: 36, color: scheme.onSecondaryContainer),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 24),
        ],
      ),
    );
  }
}
