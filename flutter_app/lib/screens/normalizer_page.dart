import 'package:material_ui/material_ui.dart';

import '../state/app_controller.dart';
import '../widgets/common.dart';

class NormalizerPage extends StatefulWidget {
  const NormalizerPage({super.key, required this.controller});

  final AppController controller;

  @override
  State<NormalizerPage> createState() => _NormalizerPageState();
}

class _NormalizerPageState extends State<NormalizerPage> {
  final _startNumber = TextEditingController(text: '1');
  String _alphaMode = 'preserve';
  String _sortMode = 'filename_asc';
  bool _skipDuplicates = true;
  bool _scanning = false;
  bool _normalizing = false;

  @override
  void dispose() {
    _startNumber.dispose();
    super.dispose();
  }

  Future<void> _scan() async {
    setState(() => _scanning = true);
    try {
      await widget.controller.startScan();
      _showMessage('Source scan started.');
    } catch (error) {
      _showMessage(error.toString(), error: true);
    } finally {
      if (mounted) setState(() => _scanning = false);
    }
  }

  Future<void> _normalize() async {
    final start = int.tryParse(_startNumber.text.trim());
    if (start == null || start < 1) {
      _showMessage('Start number must be a positive integer.', error: true);
      return;
    }
    setState(() => _normalizing = true);
    try {
      await widget.controller.startNormalization(
        startNumber: start,
        alphaMode: _alphaMode,
        skipDuplicates: _skipDuplicates,
        sortMode: _sortMode,
      );
      _showMessage('Normalization started.');
    } catch (error) {
      _showMessage(error.toString(), error: true);
    } finally {
      if (mounted) setState(() => _normalizing = false);
    }
  }

  void _showMessage(String value, {bool error = false}) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(value),
        behavior: SnackBarBehavior.floating,
        backgroundColor: error ? Theme.of(context).colorScheme.errorContainer : null,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (widget.controller.project == null) {
      return buildProjectRequiredState(context);
    }
    final busy = widget.controller.jobActive;
    final scheme = Theme.of(context).colorScheme;

    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          PageHeader(
            eyebrow: 'Prepare',
            title: 'Image normalizer',
            subtitle: 'Create sequential PNG outputs while keeping original source images untouched.',
            trailing: Icon(Icons.transform_rounded, size: 34, color: scheme.primary),
          ),
          LayoutBuilder(
            builder: (context, constraints) {
              final compact = constraints.maxWidth < 800;
              final scanCard = SectionCard(
                title: '1 · Scan source',
                subtitle: 'Index image files from the project source/ folder.',
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('Supported source images are added to the project index. Existing records are kept on repeat scans.'),
                    const SizedBox(height: 18),
                    FilledButton.icon(
                      onPressed: busy || _scanning ? null : _scan,
                      icon: _scanning
                          ? const SizedBox(
                              width: 16,
                              height: 16,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const Icon(Icons.manage_search_rounded),
                      label: Text(_scanning ? 'Starting…' : 'Scan source folder'),
                    ),
                  ],
                ),
              );
              final options = SectionCard(
                title: '2 · Normalization options',
                subtitle: 'Choose how normalized PNG files are written to dataset/.',
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    TextField(
                      controller: _startNumber,
                      keyboardType: TextInputType.number,
                      decoration: const InputDecoration(
                        labelText: 'First output number',
                        prefixIcon: Icon(Icons.numbers_rounded),
                        helperText: 'For example, 1 creates 00001.png.',
                      ),
                    ),
                    const SizedBox(height: 14),
                    DropdownButtonFormField<String>(
                      initialValue: _alphaMode,
                      decoration: const InputDecoration(
                        labelText: 'Transparency handling',
                        prefixIcon: Icon(Icons.layers_outlined),
                      ),
                      items: const [
                        DropdownMenuItem(value: 'preserve', child: Text('Preserve transparency')),
                        DropdownMenuItem(value: 'white', child: Text('Composite on white')),
                        DropdownMenuItem(value: 'black', child: Text('Composite on black')),
                      ],
                      onChanged: busy ? null : (value) {
                        if (value != null) setState(() => _alphaMode = value);
                      },
                    ),
                    const SizedBox(height: 14),
                    DropdownButtonFormField<String>(
                      initialValue: _sortMode,
                      decoration: const InputDecoration(
                        labelText: 'Image order',
                        prefixIcon: Icon(Icons.sort_rounded),
                      ),
                      items: const [
                        DropdownMenuItem(value: 'filename_asc', child: Text('Filename · A to Z')),
                        DropdownMenuItem(value: 'filename_desc', child: Text('Filename · Z to A')),
                        DropdownMenuItem(value: 'largest_first', child: Text('Largest first')),
                        DropdownMenuItem(value: 'smallest_first', child: Text('Smallest first')),
                      ],
                      onChanged: busy ? null : (value) {
                        if (value != null) setState(() => _sortMode = value);
                      },
                    ),
                    const SizedBox(height: 6),
                    SwitchListTile(
                      contentPadding: EdgeInsets.zero,
                      title: const Text('Skip exact duplicates'),
                      subtitle: const Text('Avoid writing images with identical pixel content twice.'),
                      value: _skipDuplicates,
                      onChanged: busy ? null : (value) => setState(() => _skipDuplicates = value),
                    ),
                    const SizedBox(height: 12),
                    FilledButton.icon(
                      onPressed: busy || _normalizing ? null : _normalize,
                      icon: _normalizing
                          ? const SizedBox(
                              width: 16,
                              height: 16,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const Icon(Icons.auto_fix_high_rounded),
                      label: Text(_normalizing ? 'Starting…' : 'Start normalization'),
                    ),
                  ],
                ),
              );
              if (compact) {
                return Column(
                  children: [
                    scanCard,
                    const SizedBox(height: 14),
                    options,
                  ],
                );
              }
              return Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(child: scanCard),
                  const SizedBox(width: 14),
                  Expanded(child: options),
                ],
              );
            },
          ),
          const SizedBox(height: 16),
          JobProgressCard(controller: widget.controller),
          const SizedBox(height: 22),
        ],
      ),
    );
  }
}
