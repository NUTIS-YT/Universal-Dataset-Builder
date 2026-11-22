import 'dart:async';

import 'package:material_ui/material_ui.dart';

import '../data/models.dart';
import '../state/app_controller.dart';
import '../widgets/common.dart';

class DatasetPage extends StatefulWidget {
  const DatasetPage({super.key, required this.controller});

  final AppController controller;

  @override
  State<DatasetPage> createState() => _DatasetPageState();
}

class _DatasetPageState extends State<DatasetPage> {
  final _searchController = TextEditingController();
  String _status = 'All';
  bool _loading = false;

  AppController get controller => widget.controller;

  @override
  void initState() {
    super.initState();
    unawaited(_refresh());
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _refresh() async {
    if (controller.project == null) return;
    setState(() => _loading = true);
    try {
      await controller.refreshImages(
        search: _searchController.text.trim(),
        status: _status,
      );
    } catch (error) {
      _message(error.toString(), error: true);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  void _message(String value, {bool error = false}) {
    if (!mounted) return;
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(
        SnackBar(
          content: Text(value),
          behavior: SnackBarBehavior.floating,
          backgroundColor: error ? Theme.of(context).colorScheme.errorContainer : null,
        ),
      );
  }

  Future<void> _openImage(DatasetImage image) async {
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      showDragHandle: true,
      builder: (context) => _ImageDetailsSheet(
        controller: controller,
        image: image,
        onSaved: _refresh,
        onMessage: _message,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final project = controller.project;
    if (project == null) return buildProjectRequiredState(context);
    final scheme = Theme.of(context).colorScheme;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        PageHeader(
          eyebrow: 'Explore',
          title: 'Dataset browser',
          subtitle: 'Inspect images, review generated captions, and manage image status.',
          trailing: IconButton.filledTonal(
            onPressed: _refresh,
            tooltip: 'Refresh images',
            icon: const Icon(Icons.refresh_rounded),
          ),
        ),
        Row(
          children: [
            Expanded(
              flex: 3,
              child: TextField(
                controller: _searchController,
                onSubmitted: (_) => _refresh(),
                decoration: InputDecoration(
                  hintText: 'Search by filename…',
                  prefixIcon: const Icon(Icons.search_rounded),
                  suffixIcon: IconButton(
                    tooltip: 'Search',
                    onPressed: _refresh,
                    icon: const Icon(Icons.arrow_forward_rounded),
                  ),
                ),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              flex: 2,
              child: DropdownButtonFormField<String>(
                initialValue: _status,
                decoration: const InputDecoration(
                  labelText: 'Status filter',
                  prefixIcon: Icon(Icons.filter_list_rounded),
                ),
                items: const [
                  DropdownMenuItem(value: 'All', child: Text('All statuses')),
                  DropdownMenuItem(value: 'Pending', child: Text('Pending')),
                  DropdownMenuItem(value: 'Normalized', child: Text('Normalized')),
                  DropdownMenuItem(value: 'Captioned', child: Text('Captioned')),
                  DropdownMenuItem(value: 'Reviewed', child: Text('Reviewed')),
                  DropdownMenuItem(value: 'Failed', child: Text('Failed')),
                  DropdownMenuItem(value: 'Excluded', child: Text('Excluded')),
                ],
                onChanged: (value) {
                  if (value == null) return;
                  setState(() => _status = value);
                  _refresh();
                },
              ),
            ),
          ],
        ),
        const SizedBox(height: 16),
        Expanded(
          child: AnimatedBuilder(
            animation: controller,
            builder: (context, _) {
              final images = controller.images;
              if (_loading && images.isEmpty) {
                return const Center(child: CircularProgressIndicator());
              }
              if (images.isEmpty) {
                return EmptyState(
                  icon: Icons.photo_library_outlined,
                  title: 'No images found',
                  message: 'Scan the source folder from Overview or change the search and status filters.',
                  action: FilledButton.tonalIcon(
                    onPressed: _refresh,
                    icon: const Icon(Icons.refresh_rounded),
                    label: const Text('Refresh'),
                  ),
                );
              }

              return Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Padding(
                    padding: const EdgeInsets.only(bottom: 10),
                    child: Row(
                      children: [
                        Text(
                          '${images.length} images loaded',
                          style: Theme.of(context).textTheme.labelLarge?.copyWith(
                                color: scheme.onSurfaceVariant,
                              ),
                        ),
                        const Spacer(),
                        if (_loading)
                          const SizedBox(
                            width: 16,
                            height: 16,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          ),
                      ],
                    ),
                  ),
                  Expanded(
                    child: LayoutBuilder(
                      builder: (context, constraints) {
                        final columns = constraints.maxWidth > 1200
                            ? 5
                            : constraints.maxWidth > 880
                                ? 4
                                : constraints.maxWidth > 570
                                    ? 3
                                    : constraints.maxWidth > 360
                                        ? 2
                                        : 1;
                        return GridView.builder(
                          key: const PageStorageKey('dataset-grid'),
                          gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                            crossAxisCount: columns,
                            crossAxisSpacing: 13,
                            mainAxisSpacing: 13,
                            childAspectRatio: 0.78,
                          ),
                          itemCount: images.length,
                          itemBuilder: (context, index) => _ImageTile(
                            image: images[index],
                            onTap: () => _openImage(images[index]),
                            delay: index * 28,
                          ),
                        );
                      },
                    ),
                  ),
                ],
              );
            },
          ),
        ),
      ],
    );
  }
}

class _ImageTile extends StatelessWidget {
  const _ImageTile({
    required this.image,
    required this.onTap,
    required this.delay,
  });

  final DatasetImage image;
  final VoidCallback onTap;
  final int delay;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final controller = AppControllerScope.of(context);
    final duration = controller.motionDuration(
      350 + delay.clamp(0, 260).toInt(),
      systemReduced: MediaQuery.disableAnimationsOf(context),
    );

    return TweenAnimationBuilder<double>(
      tween: Tween(begin: 0.96, end: 1),
      duration: duration,
      curve: Curves.easeOutCubic,
      builder: (context, scale, child) => Transform.scale(scale: scale, child: child),
      child: Card(
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          onTap: onTap,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Stack(
                  fit: StackFit.expand,
                  children: [
                    Container(
                      color: scheme.surfaceContainerHighest,
                      child: Image.network(
                        controller.api.imageUri(image.fileUrl).toString(),
                        fit: BoxFit.cover,
                        errorBuilder: (context, error, stackTrace) => Center(
                          child: Icon(
                            Icons.broken_image_outlined,
                            size: 38,
                            color: scheme.onSurfaceVariant,
                          ),
                        ),
                        loadingBuilder: (context, child, progress) {
                          if (progress == null) return child;
                          return Center(
                            child: CircularProgressIndicator(
                              value: progress.expectedTotalBytes == null
                                  ? null
                                  : progress.cumulativeBytesLoaded /
                                      progress.expectedTotalBytes!,
                              strokeWidth: 2,
                            ),
                          );
                        },
                      ),
                    ),
                    Positioned(
                      left: 9,
                      top: 9,
                      child: _StatusPill(status: image.status),
                    ),
                    Positioned(
                      right: 9,
                      top: 9,
                      child: Container(
                        decoration: BoxDecoration(
                          color: scheme.surface.withAlpha(220),
                          borderRadius: BorderRadius.circular(30),
                        ),
                        child: IconButton(
                          visualDensity: VisualDensity.compact,
                          onPressed: onTap,
                          icon: const Icon(Icons.open_in_full_rounded, size: 17),
                          tooltip: 'Open image',
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              Padding(
                padding: const EdgeInsets.fromLTRB(13, 11, 13, 13),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      image.filename,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.titleSmall?.copyWith(
                            fontWeight: FontWeight.w700,
                          ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      image.caption.isEmpty ? 'No caption yet' : image.caption,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
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

class _StatusPill extends StatelessWidget {
  const _StatusPill({required this.status});

  final String status;

  @override
  Widget build(BuildContext context) {
    final color = statusColor(context, status);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface.withAlpha(232),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Text(
        formatStatus(status),
        style: Theme.of(context).textTheme.labelSmall?.copyWith(
              color: color,
              fontWeight: FontWeight.w800,
            ),
      ),
    );
  }
}

class _ImageDetailsSheet extends StatefulWidget {
  const _ImageDetailsSheet({
    required this.controller,
    required this.image,
    required this.onSaved,
    required this.onMessage,
  });

  final AppController controller;
  final DatasetImage image;
  final VoidCallback onSaved;
  final void Function(String, {bool error}) onMessage;

  @override
  State<_ImageDetailsSheet> createState() => _ImageDetailsSheetState();
}

class _ImageDetailsSheetState extends State<_ImageDetailsSheet> {
  late final TextEditingController _captionController;
  late String _status;
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    _captionController = TextEditingController(text: widget.image.caption);
    _status = widget.image.status;
  }

  @override
  void dispose() {
    _captionController.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    setState(() => _saving = true);
    try {
      final caption = _captionController.text.trim();
      if (caption.isNotEmpty) {
        await widget.controller.updateImageCaption(widget.image.id, caption);
      }
      if (_status != widget.image.status) {
        await widget.controller.updateImageStatus(widget.image.id, _status);
      }
      widget.onSaved();
      if (mounted) Navigator.pop(context);
      widget.onMessage('Image changes saved.');
    } catch (error) {
      widget.onMessage(error.toString(), error: true);
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final image = widget.image;
    final scheme = Theme.of(context).colorScheme;
    return SingleChildScrollView(
      padding: EdgeInsets.fromLTRB(
        22,
        8,
        22,
        MediaQuery.viewInsetsOf(context).bottom + 24,
      ),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 900),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      image.filename,
                      style: Theme.of(context).textTheme.titleLarge?.copyWith(
                            fontWeight: FontWeight.w800,
                          ),
                    ),
                  ),
                  _StatusPill(status: _status),
                ],
              ),
              const SizedBox(height: 16),
              ClipRRect(
                borderRadius: BorderRadius.circular(24),
                child: Container(
                  constraints: const BoxConstraints(maxHeight: 420),
                  width: double.infinity,
                  color: scheme.surfaceContainerHighest,
                  child: Image.network(
                    widget.controller.api.imageUri(image.fileUrl).toString(),
                    fit: BoxFit.contain,
                    errorBuilder: (context, error, stackTrace) => const SizedBox(
                      height: 220,
                      child: Center(child: Icon(Icons.broken_image_outlined, size: 44)),
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 18),
              Text('Caption', style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 8),
              TextField(
                controller: _captionController,
                minLines: 3,
                maxLines: 7,
                decoration: const InputDecoration(
                  hintText: 'Enter or edit the caption for this image…',
                ),
              ),
              const SizedBox(height: 16),
              DropdownButtonFormField<String>(
                initialValue: _status,
                decoration: const InputDecoration(
                  labelText: 'Image status',
                  prefixIcon: Icon(Icons.flag_outlined),
                ),
                items: const [
                  DropdownMenuItem(value: 'Pending', child: Text('Pending')),
                  DropdownMenuItem(value: 'Normalized', child: Text('Normalized')),
                  DropdownMenuItem(value: 'Captioned', child: Text('Captioned')),
                  DropdownMenuItem(value: 'Reviewed', child: Text('Reviewed')),
                  DropdownMenuItem(value: 'Failed', child: Text('Failed')),
                  DropdownMenuItem(value: 'Excluded', child: Text('Excluded')),
                ],
                onChanged: (value) {
                  if (value != null) setState(() => _status = value);
                },
              ),
              const SizedBox(height: 10),
              Text(
                '— × — · Unknown format · Original: undefined',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: scheme.onSurfaceVariant,
                    ),
              ),
              const SizedBox(height: 20),
              Align(
                alignment: Alignment.centerRight,
                child: FilledButton.icon(
                  onPressed: _saving ? null : _save,
                  icon: _saving
                      ? const SizedBox(
                          width: 17,
                          height: 17,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.save_rounded),
                  label: Text(_saving ? 'Saving…' : 'Save changes'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
