import 'package:flutter/material.dart';

import '../state/app_controller.dart';

class PageHeader extends StatelessWidget {
  const PageHeader({
    super.key,
    required this.title,
    required this.subtitle,
    this.eyebrow,
    this.trailing,
  });

  final String title;
  final String subtitle;
  final String? eyebrow;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final scheme = theme.colorScheme;
    return Padding(
      padding: const EdgeInsets.only(bottom: 22),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (eyebrow != null) ...[
                  Text(
                    eyebrow!.toUpperCase(),
                    style: theme.textTheme.labelMedium?.copyWith(
                      color: scheme.primary,
                      letterSpacing: 1.8,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  const SizedBox(height: 7),
                ],
                Text(
                  title,
                  style: theme.textTheme.headlineMedium?.copyWith(
                    fontWeight: FontWeight.w800,
                    letterSpacing: -1,
                  ),
                ),
                const SizedBox(height: 7),
                Text(
                  subtitle,
                  style: theme.textTheme.bodyLarge?.copyWith(
                    color: scheme.onSurfaceVariant,
                  ),
                ),
              ],
            ),
          ),
          if (trailing != null) ...[
            const SizedBox(width: 16),
            trailing!,
          ],
        ],
      ),
    );
  }
}

class SectionCard extends StatelessWidget {
  const SectionCard({
    super.key,
    required this.child,
    this.title,
    this.subtitle,
    this.trailing,
    this.padding = const EdgeInsets.all(22),
  });

  final Widget child;
  final String? title;
  final String? subtitle;
  final Widget? trailing;
  final EdgeInsetsGeometry padding;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: padding,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (title != null || trailing != null)
              Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        if (title != null)
                          Text(title!, style: Theme.of(context).textTheme.titleLarge),
                        if (subtitle != null) ...[
                          const SizedBox(height: 4),
                          Text(
                            subtitle!,
                            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                                ),
                          ),
                        ],
                      ],
                    ),
                  ),
                  if (trailing != null) trailing!,
                ],
              ),
            if (title != null || trailing != null) const SizedBox(height: 18),
            child,
          ],
        ),
      ),
    );
  }
}

class MetricCard extends StatelessWidget {
  const MetricCard({
    super.key,
    required this.label,
    required this.value,
    required this.icon,
    required this.tint,
    this.delay = 0,
  });

  final String label;
  final int value;
  final IconData icon;
  final Color tint;
  final int delay;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final duration = context.readMotionDuration(500 + delay);
    return TweenAnimationBuilder<double>(
      key: ValueKey('$label-$value'),
      tween: Tween(begin: 0, end: 1),
      duration: duration,
      curve: Curves.easeOutCubic,
      builder: (context, progress, child) => Opacity(
        opacity: progress,
        child: Transform.translate(
          offset: Offset(0, (1 - progress) * 14),
          child: child,
        ),
      ),
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Row(
            children: [
              Container(
                width: 48,
                height: 48,
                decoration: BoxDecoration(
                  color: tint.withAlpha(30),
                  borderRadius: BorderRadius.circular(17),
                ),
                child: Icon(icon, color: tint),
              ),
              const SizedBox(width: 15),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    TweenAnimationBuilder<double>(
                      tween: Tween(begin: 0, end: value.toDouble()),
                      duration: duration,
                      builder: (context, count, _) => Text(
                        count.round().toString(),
                        style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                              fontWeight: FontWeight.w800,
                              letterSpacing: -1,
                            ),
                      ),
                    ),
                    Text(
                      label,
                      style: Theme.of(context).textTheme.labelLarge?.copyWith(
                            color: scheme.onSurfaceVariant,
                          ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class EmptyState extends StatelessWidget {
  const EmptyState({
    super.key,
    required this.icon,
    required this.title,
    required this.message,
    this.action,
  });

  final IconData icon;
  final String title;
  final String message;
  final Widget? action;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 48),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 76,
              height: 76,
              decoration: BoxDecoration(
                color: scheme.secondaryContainer,
                borderRadius: BorderRadius.circular(28),
              ),
              child: Icon(icon, size: 36, color: scheme.onSecondaryContainer),
            ),
            const SizedBox(height: 20),
            Text(title, style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 8),
            ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 420),
              child: Text(
                message,
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: scheme.onSurfaceVariant,
                    ),
              ),
            ),
            if (action != null) ...[
              const SizedBox(height: 22),
              action!,
            ],
          ],
        ),
      ),
    );
  }
}

class JobProgressCard extends StatelessWidget {
  const JobProgressCard({super.key, required this.controller});

  final AppController controller;

  @override
  Widget build(BuildContext context) {
    final job = controller.job;
    if (job == null) return const SizedBox.shrink();
    final scheme = Theme.of(context).colorScheme;
    final active = job.isActive;
    final title = switch (job.status) {
      'completed' => 'Operation complete',
      'cancelled' => 'Operation cancelled',
      'failed' => 'Operation failed',
      'cancelling' => 'Stopping after current item…',
      _ => 'Working…',
    };
    final subtitle = job.item.isEmpty
        ? (job.error ?? job.status)
        : job.item;
    return SectionCard(
      title: title,
      subtitle: subtitle,
      trailing: active
          ? Text(
              job.total > 0 ? '${job.percent}%' : 'In progress',
              style: Theme.of(context).textTheme.labelLarge?.copyWith(
                    color: scheme.primary,
                    fontWeight: FontWeight.w700,
                  ),
            )
          : Icon(
              job.status == 'completed' ? Icons.check_circle_rounded : Icons.info_rounded,
              color: job.status == 'completed' ? scheme.primary : scheme.onSurfaceVariant,
            ),
      child: Column(
        children: [
          LinearProgressIndicator(
            value: job.total > 0 ? job.percent / 100 : (active ? null : 1),
            borderRadius: BorderRadius.circular(10),
          ),
          if (active && job.cancellable) ...[
            const SizedBox(height: 14),
            Align(
              alignment: Alignment.centerRight,
              child: OutlinedButton.icon(
                onPressed: controller.cancelCurrentJob,
                icon: const Icon(Icons.stop_rounded),
                label: const Text('Cancel after current item'),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

extension MotionContext on BuildContext {
  Duration readMotionDuration(int milliseconds) {
    final controller = AppControllerScope.of(this);
    return controller.motionDuration(
      milliseconds,
      systemReduced: MediaQuery.disableAnimationsOf(this),
    );
  }
}

class AppControllerScope extends InheritedWidget {
  const AppControllerScope({
    super.key,
    required this.controller,
    required super.child,
  });

  final AppController controller;

  static AppController of(BuildContext context) {
    final scope = context.dependOnInheritedWidgetOfExactType<AppControllerScope>();
    assert(scope != null, 'AppControllerScope was not found in the widget tree.');
    return scope!.controller;
  }

  @override
  bool updateShouldNotify(AppControllerScope oldWidget) =>
      controller != oldWidget.controller;
}

Widget buildProjectRequiredState(BuildContext context) => const EmptyState(
      icon: Icons.folder_open_rounded,
      title: 'No project open',
      message: 'Create a new project or open an existing project from Overview.',
    );

String formatStatus(String value) => switch (value) {
      'Pending' => 'Pending',
      'Normalized' => 'Normalized',
      'Captioned' => 'Captioned',
      'Reviewed' => 'Reviewed',
      'Failed' => 'Failed',
      'Excluded' => 'Excluded',
      _ => value,
    };

Color statusColor(BuildContext context, String status) {
  final scheme = Theme.of(context).colorScheme;
  return switch (status) {
    'Reviewed' => scheme.primary,
    'Captioned' => scheme.tertiary,
    'Normalized' => scheme.secondary,
    'Failed' => scheme.error,
    'Excluded' => scheme.outline,
    _ => scheme.onSurfaceVariant,
  };
}
