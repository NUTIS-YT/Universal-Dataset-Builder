import 'package:flutter/material.dart';

import '../state/app_controller.dart';

class ExpressiveShell extends StatefulWidget {
  const ExpressiveShell({
    super.key,
    required this.controller,
    required this.pages,
  });

  final AppController controller;
  final List<Widget> pages;

  @override
  State<ExpressiveShell> createState() => _ExpressiveShellState();
}

class _ExpressiveShellState extends State<ExpressiveShell> {
  int _selectedIndex = 0;

  static const _destinations = <({String label, IconData icon, IconData selected})>[
    (label: 'Overview', icon: Icons.dashboard_outlined, selected: Icons.dashboard_rounded),
    (label: 'Dataset', icon: Icons.grid_view_outlined, selected: Icons.grid_view_rounded),
    (label: 'Normalizer', icon: Icons.tune_rounded, selected: Icons.tune_rounded),
    (label: 'Caption generator', icon: Icons.auto_awesome_outlined, selected: Icons.auto_awesome_rounded),
    (label: 'VLM connection', icon: Icons.hub_outlined, selected: Icons.hub_rounded),
    (label: 'Appearance', icon: Icons.palette_outlined, selected: Icons.palette_rounded),
  ];

  @override
  Widget build(BuildContext context) {
    final controller = widget.controller;
    final scheme = Theme.of(context).colorScheme;
    final compact = MediaQuery.sizeOf(context).width < 920;
    final duration = controller.motionDuration(
      430,
      systemReduced: MediaQuery.disableAnimationsOf(context),
    );

    return Scaffold(
      appBar: AppBar(
        toolbarHeight: 76,
        titleSpacing: 22,
        title: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 42,
              height: 42,
              decoration: BoxDecoration(
                color: scheme.secondaryContainer,
                borderRadius: BorderRadius.circular(15),
              ),
              child: Icon(Icons.auto_awesome_rounded, color: scheme.onSecondaryContainer),
            ),
            const SizedBox(width: 13),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  'Universal Dataset Builder',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w800,
                        letterSpacing: -0.3,
                      ),
                ),
                Text(
                  'EXPRESSIVE UI',
                  style: Theme.of(context).textTheme.labelSmall?.copyWith(
                        color: scheme.onSurfaceVariant,
                        letterSpacing: 1.5,
                      ),
                ),
              ],
            ),
          ],
        ),
        actions: [
          _ConnectionPill(online: controller.apiOnline),
          const SizedBox(width: 12),
          if (controller.project != null)
            ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 180),
              child: Tooltip(
                message: controller.project!.databasePath,
                child: Center(
                  child: Text(
                    controller.project!.name,
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.labelLarge,
                  ),
                ),
              ),
            ),
          const SizedBox(width: 18),
        ],
      ),
      body: Row(
        children: [
          if (!compact)
            Padding(
              padding: const EdgeInsets.fromLTRB(12, 8, 8, 12),
              child: NavigationRail(
                selectedIndex: _selectedIndex,
                onDestinationSelected: (index) => setState(() => _selectedIndex = index),
                labelType: NavigationRailLabelType.all,
                groupAlignment: -0.94,
                destinations: [
                  for (final item in _destinations)
                    NavigationRailDestination(
                      icon: Icon(item.icon),
                      selectedIcon: Icon(item.selected),
                      label: Text(item.label),
                    ),
                ],
                trailing: Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: IconButton(
                    tooltip: 'Refresh connection',
                    onPressed: controller.refreshConnection,
                    icon: const Icon(Icons.sync_rounded),
                  ),
                ),
              ),
            ),
          Expanded(
            child: Column(
              children: [
                if (controller.jobActive)
                  Padding(
                    padding: const EdgeInsets.fromLTRB(16, 6, 16, 4),
                    child: _GlobalJobIndicator(controller: controller),
                  ),
                if (controller.lastError != null && !controller.jobActive)
                  Padding(
                    padding: const EdgeInsets.fromLTRB(16, 6, 16, 4),
                    child: Material(
                      color: scheme.errorContainer,
                      borderRadius: BorderRadius.circular(18),
                      child: ListTile(
                        dense: true,
                        leading: Icon(Icons.warning_amber_rounded, color: scheme.onErrorContainer),
                        title: Text(
                          controller.lastError!,
                          style: TextStyle(color: scheme.onErrorContainer),
                        ),
                        trailing: IconButton(
                          onPressed: () {
                            controller.clearError();
                          },
                          icon: Icon(Icons.close_rounded, color: scheme.onErrorContainer),
                        ),
                      ),
                    ),
                  ),
                Expanded(
                  child: Padding(
                    padding: EdgeInsets.fromLTRB(compact ? 14 : 22, 10, compact ? 14 : 22, 18),
                    child: Center(
                      child: ConstrainedBox(
                        constraints: const BoxConstraints(maxWidth: 1480),
                        child: AnimatedSwitcher(
                          duration: duration,
                          reverseDuration: duration,
                          switchInCurve: Curves.easeOutCubic,
                          switchOutCurve: Curves.easeInCubic,
                          transitionBuilder: (child, animation) {
                            final slide = Tween<Offset>(
                              begin: const Offset(0, 0.035),
                              end: Offset.zero,
                            ).animate(
                              CurvedAnimation(
                                parent: animation,
                                curve: Curves.easeOutCubic,
                              ),
                            );
                            return FadeTransition(
                              opacity: animation,
                              child: SlideTransition(position: slide, child: child),
                            );
                          },
                          child: KeyedSubtree(
                            key: ValueKey<int>(_selectedIndex),
                            child: widget.pages[_selectedIndex],
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
      bottomNavigationBar: compact
          ? NavigationBar(
              selectedIndex: _selectedIndex,
              onDestinationSelected: (index) => setState(() => _selectedIndex = index),
              destinations: [
                for (final item in _destinations)
                  NavigationDestination(
                    icon: Icon(item.icon),
                    selectedIcon: Icon(item.selected),
                    label: item.label,
                  ),
              ],
            )
          : null,
    );
  }
}

class _ConnectionPill extends StatelessWidget {
  const _ConnectionPill({required this.online});

  final bool online;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final foreground = online ? scheme.primary : scheme.error;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: foreground.withAlpha(22),
        borderRadius: BorderRadius.circular(30),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.circle, size: 8, color: foreground),
          const SizedBox(width: 8),
          Text(
            online ? 'API online' : 'API offline',
            style: Theme.of(context).textTheme.labelMedium?.copyWith(
                  color: foreground,
                  fontWeight: FontWeight.w700,
                ),
          ),
        ],
      ),
    );
  }
}

class _GlobalJobIndicator extends StatelessWidget {
  const _GlobalJobIndicator({required this.controller});

  final AppController controller;

  @override
  Widget build(BuildContext context) {
    final job = controller.job;
    if (job == null) return const SizedBox.shrink();
    final scheme = Theme.of(context).colorScheme;
    final label = switch (job.kind) {
      'scan' => 'Scanning source images',
      'normalization' => 'Normalizing images',
      'caption_generation' => 'Generating captions',
      _ => 'Working',
    };

    return Card(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(18, 12, 12, 12),
        child: Row(
          children: [
            Icon(Icons.autorenew_rounded, color: scheme.primary),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(label, style: Theme.of(context).textTheme.titleSmall),
                  const SizedBox(height: 7),
                  LinearProgressIndicator(
                    value: job.total > 0 ? job.percent / 100 : null,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    job.total > 0 ? '${job.percent}% · ${job.item}' : job.status,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.labelSmall,
                  ),
                ],
              ),
            ),
            if (job.cancellable)
              IconButton(
                tooltip: 'Cancel task',
                onPressed: controller.cancelCurrentJob,
                icon: const Icon(Icons.close_rounded),
              ),
          ],
        ),
      ),
    );
  }
}
