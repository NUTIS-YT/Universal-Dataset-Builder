import 'package:file_picker/file_picker.dart';
import 'package:material_ui/material_ui.dart';

import '../state/app_controller.dart';
import '../widgets/common.dart';

class DashboardPage extends StatefulWidget {
  const DashboardPage({super.key, required this.controller});

  final AppController controller;

  @override
  State<DashboardPage> createState() => _DashboardPageState();
}

class _DashboardPageState extends State<DashboardPage> {
  AppController get controller => widget.controller;
  bool _dialogBusy = false;

  Future<void> _browseParentDirectory(TextEditingController target) async {
    try {
      final selected = await FilePicker.pickDirectory(
        dialogTitle: 'Choose project parent folder',
      );
      if (selected != null) target.text = selected.toFilePath();
    } catch (error) {
      _showMessage('Could not open the folder picker: $error', error: true);
    }
  }

  Future<void> _browseProjectFile(TextEditingController target) async {
    try {
      final selected = await FilePicker.pickFile(
        dialogTitle: 'Open Universal Dataset Builder project',
        type: FileType.custom,
        allowedExtensions: ['fdb'],
      );
      final selectedPath = selected?.path;
      if (selectedPath != null) target.text = selectedPath;
    } catch (error) {
      _showMessage('Could not open the project picker: $error', error: true);
    }
  }

  Future<void> _showCreateProject() async {
    final directoryPath = TextEditingController();
    final name = TextEditingController();
    final result = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Create a project'),
        content: SizedBox(
          width: 440,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: name,
                autofocus: true,
                decoration: const InputDecoration(
                  labelText: 'Project name',
                  hintText: 'My character dataset',
                  prefixIcon: Icon(Icons.drive_file_rename_outline_rounded),
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: directoryPath,
                decoration: InputDecoration(
                  labelText: 'Parent folder',
                  hintText: '/home/user/Datasets',
                  prefixIcon: const Icon(Icons.folder_outlined),
                  suffixIcon: IconButton(
                    tooltip: 'Browse for folder',
                    onPressed: () => _browseParentDirectory(directoryPath),
                    icon: const Icon(Icons.folder_open_rounded),
                  ),
                  helperText: 'The project folder will be created inside this directory.',
                ),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(dialogContext, true),
            child: const Text('Create project'),
          ),
        ],
      ),
    );
    if (result != true) {
      directoryPath.dispose();
      name.dispose();
      return;
    }

    if (directoryPath.text.trim().isEmpty || name.text.trim().isEmpty) {
      _showMessage('Choose a parent folder and enter a project name.', error: true);
      directoryPath.dispose();
      name.dispose();
      return;
    }

    setState(() => _dialogBusy = true);
    try {
      await controller.createProject(directoryPath.text.trim(), name.text.trim());
      _showMessage('Project created.');
    } catch (error) {
      _showMessage(error.toString(), error: true);
    } finally {
      directoryPath.dispose();
      name.dispose();
      if (mounted) setState(() => _dialogBusy = false);
    }
  }

  Future<void> _showOpenProject() async {
    final projectPath = TextEditingController();
    final result = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Open a project'),
        content: SizedBox(
          width: 440,
          child: TextField(
            controller: projectPath,
            autofocus: true,
            decoration: InputDecoration(
              labelText: 'Path to project.fdb',
              hintText: '/home/user/Datasets/MyDataset/project.fdb',
              prefixIcon: const Icon(Icons.folder_open_rounded),
              suffixIcon: IconButton(
                tooltip: 'Browse for project file',
                onPressed: () => _browseProjectFile(projectPath),
                icon: const Icon(Icons.folder_open_rounded),
              ),
            ),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(dialogContext, true),
            child: const Text('Open project'),
          ),
        ],
      ),
    );
    if (result != true) {
      projectPath.dispose();
      return;
    }
    if (projectPath.text.trim().isEmpty) {
      _showMessage('Choose a project file to open.', error: true);
      projectPath.dispose();
      return;
    }

    setState(() => _dialogBusy = true);
    try {
      await controller.openProject(projectPath.text);
      _showMessage('Project opened.');
    } catch (error) {
      _showMessage(error.toString(), error: true);
    } finally {
      projectPath.dispose();
      if (mounted) setState(() => _dialogBusy = false);
    }
  }

  Future<void> _closeProject() async {
    try {
      await controller.closeProject();
      _showMessage('Project closed.');
    } catch (error) {
      _showMessage(error.toString(), error: true);
    }
  }

  Future<void> _scan() async {
    try {
      await controller.startScan();
      _showMessage('Source scan started.');
    } catch (error) {
      _showMessage(error.toString(), error: true);
    }
  }

  void _showMessage(String message, {bool error = false}) {
    if (!mounted) return;
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(
        SnackBar(
          content: Text(message),
          behavior: SnackBarBehavior.floating,
          backgroundColor: error ? Theme.of(context).colorScheme.errorContainer : null,
        ),
      );
  }

  @override
  Widget build(BuildContext context) {
    final project = controller.project;
    final scheme = Theme.of(context).colorScheme;
    final stats = project?.statistics ?? const <String, int>{};
    final isConnected = controller.apiOnline;

    return SingleChildScrollView(
      key: const PageStorageKey('dashboard-scroll'),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          PageHeader(
            eyebrow: 'Workspace',
            title: 'Your dataset space',
            subtitle: 'Prepare images, keep captions consistent, and build training-ready metadata.',
            trailing: IconButton.filledTonal(
              tooltip: 'Refresh',
              onPressed: controller.refreshConnection,
              icon: const Icon(Icons.refresh_rounded),
            ),
          ),
          if (!isConnected)
            SectionCard(
              title: 'Local API is not reachable',
              subtitle: 'Start the UDB API server, then check the connection again.',
              child: Row(
                children: [
                  const Icon(Icons.link_off_rounded),
                  const SizedBox(width: 12),
                  Expanded(child: Text(controller.apiBaseUrl)),
                  FilledButton.tonal(
                    onPressed: controller.refreshConnection,
                    child: const Text('Reconnect'),
                  ),
                ],
              ),
            )
          else if (project == null)
            _WelcomeCard(
              onCreate: _showCreateProject,
              onOpen: _showOpenProject,
            )
          else ...[
            _ProjectHero(
              projectName: project.name,
              projectPath: project.rootPath,
              metadataPath: project.metadataPath,
              onScan: _scan,
              onClose: _closeProject,
              busy: _dialogBusy || controller.jobActive,
            ),
            const SizedBox(height: 18),
            LayoutBuilder(
              builder: (context, constraints) {
                final columns = constraints.maxWidth > 1050
                    ? 4
                    : constraints.maxWidth > 650
                        ? 2
                        : 1;
                final width = (constraints.maxWidth - (columns - 1) * 12) / columns;
                return Wrap(
                  spacing: 12,
                  runSpacing: 12,
                  children: [
                    SizedBox(
                      width: width,
                      child: MetricCard(
                        label: 'Indexed images',
                        value: stats['images'] ?? 0,
                        icon: Icons.photo_library_outlined,
                        tint: scheme.primary,
                        delay: 0,
                      ),
                    ),
                    SizedBox(
                      width: width,
                      child: MetricCard(
                        label: 'Captions',
                        value: stats['captions'] ?? 0,
                        icon: Icons.notes_rounded,
                        tint: scheme.tertiary,
                        delay: 65,
                      ),
                    ),
                    SizedBox(
                      width: width,
                      child: MetricCard(
                        label: 'Reviewed',
                        value: stats['reviewed'] ?? 0,
                        icon: Icons.verified_outlined,
                        tint: scheme.secondary,
                        delay: 130,
                      ),
                    ),
                    SizedBox(
                      width: width,
                      child: MetricCard(
                        label: 'Failed',
                        value: stats['failed'] ?? 0,
                        icon: Icons.error_outline_rounded,
                        tint: scheme.error,
                        delay: 195,
                      ),
                    ),
                  ],
                );
              },
            ),
            const SizedBox(height: 18),
            JobProgressCard(controller: controller),
            if (!controller.jobActive && controller.images.isEmpty)
              const SectionCard(
                title: 'Ready for the first scan?',
                subtitle: 'Your source folder is empty in the index. Scan it to discover images.',
                child: Row(
                  children: [
                    Icon(Icons.tips_and_updates_outlined),
                    SizedBox(width: 12),
                    Expanded(
                      child: Text('Original images stay in source/. Normalized outputs are written to dataset/.'),
                    ),
                  ],
                ),
              ),
            const SizedBox(height: 18),
            SectionCard(
              title: 'Project structure',
              subtitle: 'The same project file is used by Legacy and Expressive interfaces.',
              child: Column(
                children: [
                  _PathRow(icon: Icons.storage_rounded, label: 'Project database', value: project.databasePath),
                  const Divider(height: 22),
                  _PathRow(icon: Icons.photo_library_outlined, label: 'Original images', value: project.sourcePath),
                  const Divider(height: 22),
                  _PathRow(icon: Icons.folder_copy_outlined, label: 'Normalized dataset', value: project.datasetPath),
                  const Divider(height: 22),
                  _PathRow(icon: Icons.data_object_rounded, label: 'Training manifest', value: project.metadataPath),
                ],
              ),
            ),
          ],
          if (_dialogBusy) const LinearProgressIndicator(),
          const SizedBox(height: 26),
        ],
      ),
    );
  }
}

class _WelcomeCard extends StatelessWidget {
  const _WelcomeCard({required this.onCreate, required this.onOpen});

  final VoidCallback onCreate;
  final VoidCallback onOpen;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final duration = context.readMotionDuration(700);
    return TweenAnimationBuilder<double>(
      tween: Tween(begin: 0.94, end: 1),
      duration: duration,
      curve: Curves.easeOutBack,
      builder: (context, scale, child) => Transform.scale(scale: scale, child: child),
      child: Card(
        clipBehavior: Clip.antiAlias,
        child: Container(
          width: double.infinity,
          padding: const EdgeInsets.all(30),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [
                scheme.primaryContainer,
                scheme.secondaryContainer,
              ],
            ),
          ),
          child: LayoutBuilder(
            builder: (context, constraints) {
              final compact = constraints.maxWidth < 630;
              final copy = Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(Icons.auto_awesome_rounded, size: 36, color: scheme.onPrimaryContainer),
                  const SizedBox(height: 18),
                  Text(
                    'Build better datasets.',
                    style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                          color: scheme.onPrimaryContainer,
                          fontWeight: FontWeight.w900,
                          letterSpacing: -1,
                        ),
                  ),
                  const SizedBox(height: 10),
                  Text(
                    'Create a workspace or open an existing UDB project. Your data remains local and both interfaces share the same backend.',
                    style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                          color: scheme.onPrimaryContainer.withAlpha(220),
                        ),
                  ),
                  const SizedBox(height: 24),
                  Wrap(
                    spacing: 10,
                    runSpacing: 10,
                    children: [
                      FilledButton.icon(
                        onPressed: onCreate,
                        icon: const Icon(Icons.add_rounded),
                        label: const Text('Create project'),
                      ),
                      OutlinedButton.icon(
                        onPressed: onOpen,
                        icon: const Icon(Icons.folder_open_rounded),
                        label: const Text('Open project'),
                        style: OutlinedButton.styleFrom(
                          foregroundColor: scheme.onPrimaryContainer,
                          side: BorderSide(color: scheme.onPrimaryContainer.withAlpha(100)),
                        ),
                      ),
                    ],
                  ),
                ],
              );
              if (compact) return copy;
              return Row(
                children: [
                  Expanded(flex: 7, child: copy),
                  const SizedBox(width: 20),
                  Expanded(
                    flex: 4,
                    child: Icon(
                      Icons.dataset_rounded,
                      size: 155,
                      color: scheme.onPrimaryContainer.withAlpha(55),
                    ),
                  ),
                ],
              );
            },
          ),
        ),
      ),
    );
  }
}

class _ProjectHero extends StatelessWidget {
  const _ProjectHero({
    required this.projectName,
    required this.projectPath,
    required this.metadataPath,
    required this.onScan,
    required this.onClose,
    required this.busy,
  });

  final String projectName;
  final String projectPath;
  final String metadataPath;
  final VoidCallback onScan;
  final VoidCallback onClose;
  final bool busy;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: LayoutBuilder(
          builder: (context, constraints) {
            final compact = constraints.maxWidth < 690;
            final details = Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: scheme.primaryContainer,
                        borderRadius: BorderRadius.circular(18),
                      ),
                      child: Icon(Icons.folder_special_rounded, color: scheme.onPrimaryContainer, size: 26),
                    ),
                    const SizedBox(width: 14),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(projectName, style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800)),
                          Text('Active project', style: Theme.of(context).textTheme.labelMedium?.copyWith(color: scheme.primary)),
                        ],
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 14),
                Text(projectPath, maxLines: 2, overflow: TextOverflow.ellipsis, style: Theme.of(context).textTheme.bodySmall?.copyWith(color: scheme.onSurfaceVariant)),
                const SizedBox(height: 7),
                Text('Manifest · $metadataPath', maxLines: 1, overflow: TextOverflow.ellipsis, style: Theme.of(context).textTheme.labelSmall?.copyWith(color: scheme.onSurfaceVariant)),
              ],
            );
            final actions = Wrap(
              spacing: 10,
              runSpacing: 10,
              children: [
                FilledButton.icon(
                  onPressed: busy ? null : onScan,
                  icon: const Icon(Icons.manage_search_rounded),
                  label: const Text('Scan source'),
                ),
                OutlinedButton.icon(
                  onPressed: busy ? null : onClose,
                  icon: const Icon(Icons.folder_off_outlined),
                  label: const Text('Close'),
                ),
              ],
            );
            if (compact) {
              return Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [details, const SizedBox(height: 18), actions],
              );
            }
            return Row(
              children: [
                Expanded(child: details),
                const SizedBox(width: 18),
                actions,
              ],
            );
          },
        ),
      ),
    );
  }
}

class _PathRow extends StatelessWidget {
  const _PathRow({required this.icon, required this.label, required this.value});

  final IconData icon;
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Row(
      children: [
        Icon(icon, color: scheme.primary),
        const SizedBox(width: 14),
        SizedBox(
          width: 150,
          child: Text(label, style: Theme.of(context).textTheme.labelLarge),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: SelectableText(
            value,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(color: scheme.onSurfaceVariant),
          ),
        ),
      ],
    );
  }
}
