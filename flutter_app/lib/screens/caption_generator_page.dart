import 'package:material_ui/material_ui.dart';

import '../data/models.dart';
import '../state/app_controller.dart';
import '../widgets/common.dart';

class CaptionGeneratorPage extends StatefulWidget {
  const CaptionGeneratorPage({super.key, required this.controller});

  final AppController controller;

  @override
  State<CaptionGeneratorPage> createState() => _CaptionGeneratorPageState();
}

class _CaptionGeneratorPageState extends State<CaptionGeneratorPage> {
  late final TextEditingController _prompt;
  late final TextEditingController _characterDescription;
  late final TextEditingController _triggerWord;
  final _limit = TextEditingController(text: '0');

  String _selectionMode = 'missing';
  bool _characterEnabled = false;
  bool _saving = false;
  bool _starting = false;
  String? _loadedProjectPath;

  @override
  void initState() {
    super.initState();
    _prompt = TextEditingController(text: widget.controller.vlmSettings.captionPrompt);
    _characterDescription = TextEditingController(
      text: widget.controller.characterSettings.description,
    );
    _triggerWord = TextEditingController(
      text: widget.controller.characterSettings.triggerWord,
    );
    _characterEnabled = widget.controller.characterSettings.enabled;
    _loadedProjectPath = widget.controller.project?.databasePath;
    widget.controller.addListener(_syncProjectSettings);
  }

  @override
  void dispose() {
    widget.controller.removeListener(_syncProjectSettings);
    _prompt.dispose();
    _characterDescription.dispose();
    _triggerWord.dispose();
    _limit.dispose();
    super.dispose();
  }

  void _syncProjectSettings() {
    final projectPath = widget.controller.project?.databasePath;
    final savedPrompt = widget.controller.vlmSettings.captionPrompt;
    if (_prompt.text.trim().isEmpty && savedPrompt.isNotEmpty) {
      _prompt.text = savedPrompt;
    }
    if (projectPath == _loadedProjectPath) return;
    _loadedProjectPath = projectPath;
    final settings = widget.controller.characterSettings;
    _characterEnabled = settings.enabled;
    _characterDescription.text = settings.description;
    _triggerWord.text = settings.triggerWord;
    if (mounted) setState(() {});
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

  Future<void> _saveCharacterSettings() async {
    setState(() => _saving = true);
    try {
      await widget.controller.saveCharacterSettings(
        CharacterSettings(
          enabled: _characterEnabled,
          description: _characterDescription.text,
          triggerWord: _triggerWord.text,
        ),
      );
      _showMessage('Character reference saved to project.fdb.');
    } catch (error) {
      _showMessage(error.toString(), error: true);
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Future<void> _generate() async {
    final prompt = _prompt.text.trim();
    final limit = int.tryParse(_limit.text.trim());
    if (prompt.isEmpty) {
      _showMessage('Enter a caption prompt first.', error: true);
      return;
    }
    if (limit == null || limit < 0) {
      _showMessage('Maximum images must be zero or a positive integer.', error: true);
      return;
    }
    if (widget.controller.vlmSettings.model.isEmpty) {
      _showMessage('Connect to a VLM and select a model first.', error: true);
      return;
    }

    setState(() => _starting = true);
    try {
      await widget.controller.saveCaptionPrompt(prompt);
      await widget.controller.saveCharacterSettings(
        CharacterSettings(
          enabled: _characterEnabled,
          description: _characterDescription.text,
          triggerWord: _triggerWord.text,
        ),
      );
      await widget.controller.startCaptionGeneration(
        selectionMode: _selectionMode,
        limit: limit,
        prompt: prompt,
      );
      _showMessage('Caption generation started.');
    } catch (error) {
      _showMessage(error.toString(), error: true);
    } finally {
      if (mounted) setState(() => _starting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final controller = widget.controller;
    if (controller.project == null) return buildProjectRequiredState(context);
    final scheme = Theme.of(context).colorScheme;
    final settings = controller.vlmSettings;

    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          PageHeader(
            eyebrow: 'Describe',
            title: 'Caption generator',
            subtitle: 'Generate image-specific captions while keeping recurring character traits consistent.',
            trailing: Icon(Icons.auto_awesome_rounded, size: 36, color: scheme.primary),
          ),
          if (settings.model.isEmpty)
            Card(
              color: scheme.tertiaryContainer,
              child: ListTile(
                leading: Icon(Icons.info_outline_rounded, color: scheme.onTertiaryContainer),
                title: Text('No VLM model selected', style: TextStyle(color: scheme.onTertiaryContainer)),
                subtitle: Text('Open VLM Connection and test your OpenAI-compatible endpoint.', style: TextStyle(color: scheme.onTertiaryContainer)),
              ),
            ),
          const SizedBox(height: 14),
          LayoutBuilder(
            builder: (context, constraints) {
              final compact = constraints.maxWidth < 830;
              final promptCard = SectionCard(
                title: 'Caption prompt',
                subtitle: 'Instructions sent to the vision-language model for each image.',
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    TextField(
                      controller: _prompt,
                      minLines: 8,
                      maxLines: 13,
                      decoration: const InputDecoration(
                        hintText: 'Describe the image accurately and concisely…',
                        alignLabelWithHint: true,
                      ),
                    ),
                    const SizedBox(height: 14),
                    DropdownButtonFormField<String>(
                      initialValue: _selectionMode,
                      decoration: const InputDecoration(
                        labelText: 'Images to process',
                        prefixIcon: Icon(Icons.filter_alt_outlined),
                      ),
                      items: const [
                        DropdownMenuItem(value: 'missing', child: Text('Only images without captions')),
                        DropdownMenuItem(value: 'unreviewed', child: Text('Regenerate unreviewed captions')),
                      ],
                      onChanged: controller.jobActive
                          ? null
                          : (value) {
                              if (value != null) setState(() => _selectionMode = value);
                            },
                    ),
                    const SizedBox(height: 14),
                    TextField(
                      controller: _limit,
                      keyboardType: TextInputType.number,
                      decoration: const InputDecoration(
                        labelText: 'Maximum images',
                        helperText: '0 means all eligible images.',
                        prefixIcon: Icon(Icons.numbers_rounded),
                      ),
                    ),
                  ],
                ),
              );

              final characterCard = SectionCard(
                title: 'Character consistency',
                subtitle: 'Project-specific guidance for one recurring character across multiple views.',
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    SwitchListTile(
                      contentPadding: EdgeInsets.zero,
                      title: const Text('Use character reference'),
                      subtitle: const Text('Add identity guidance to every VLM request and prepend the trigger word to its caption.'),
                      value: _characterEnabled,
                      onChanged: controller.jobActive
                          ? null
                          : (value) => setState(() => _characterEnabled = value),
                    ),
                    AnimatedSize(
                      duration: context.readMotionDuration(320),
                      curve: Curves.easeInOutCubic,
                      child: _characterEnabled
                          ? Column(
                              children: [
                                const SizedBox(height: 10),
                                TextField(
                                  controller: _characterDescription,
                                  minLines: 4,
                                  maxLines: 8,
                                  decoration: const InputDecoration(
                                    labelText: 'Character information',
                                    hintText: 'Describe stable traits: colors, markings, hair, face, accessories, and other identifying details…',
                                    alignLabelWithHint: true,
                                  ),
                                ),
                                const SizedBox(height: 12),
                                TextField(
                                  controller: _triggerWord,
                                  decoration: const InputDecoration(
                                    labelText: 'Trigger word',
                                    hintText: 'e.g. my_character',
                                    prefixIcon: Icon(Icons.sell_outlined),
                                    helperText: 'Added automatically at the beginning of every generated caption.',
                                  ),
                                ),
                                const SizedBox(height: 14),
                              ],
                            )
                          : const SizedBox.shrink(),
                    ),
                    OutlinedButton.icon(
                      onPressed: _saving || controller.jobActive ? null : _saveCharacterSettings,
                      icon: _saving
                          ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                          : const Icon(Icons.save_outlined),
                      label: Text(_saving ? 'Saving…' : 'Save character settings'),
                    ),
                    const SizedBox(height: 12),
                    Container(
                      padding: const EdgeInsets.all(14),
                      decoration: BoxDecoration(
                        color: scheme.surfaceContainerHighest.withAlpha(110),
                        borderRadius: BorderRadius.circular(18),
                      ),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Icon(Icons.lightbulb_outline_rounded, color: scheme.primary),
                          const SizedBox(width: 10),
                          const Expanded(
                            child: Text('The character description guides the model, but the final caption still reflects the visible pose, angle, clothing, and scene in each individual image.'),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              );

              if (compact) {
                return Column(
                  children: [
                    promptCard,
                    const SizedBox(height: 14),
                    characterCard,
                  ],
                );
              }
              return Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(flex: 6, child: promptCard),
                  const SizedBox(width: 14),
                  Expanded(flex: 5, child: characterCard),
                ],
              );
            },
          ),
          const SizedBox(height: 16),
          SectionCard(
            title: 'Generate captions',
            subtitle: 'The prompt and project character settings are saved before the job starts.',
            trailing: Chip(
              avatar: const Icon(Icons.memory_rounded, size: 16),
              label: Text(settings.model.isEmpty ? 'No model' : settings.model),
            ),
            child: Wrap(
              spacing: 12,
              runSpacing: 12,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                FilledButton.icon(
                  onPressed: controller.jobActive || _starting ? null : _generate,
                  icon: _starting
                      ? const SizedBox(width: 17, height: 17, child: CircularProgressIndicator(strokeWidth: 2))
                      : const Icon(Icons.auto_awesome_rounded),
                  label: Text(_starting ? 'Starting…' : 'Generate captions'),
                ),
                Text(
                  _characterEnabled && _triggerWord.text.trim().isNotEmpty
                      ? 'Prefix: ${_triggerWord.text.trim()}'
                      : 'Character prefix disabled',
                  style: Theme.of(context).textTheme.labelMedium?.copyWith(color: scheme.onSurfaceVariant),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          JobProgressCard(controller: controller),
          const SizedBox(height: 22),
        ],
      ),
    );
  }
}
