import 'package:flutter/material.dart';

import '../state/app_controller.dart';
import '../widgets/common.dart';

class ConnectionPage extends StatefulWidget {
  const ConnectionPage({super.key, required this.controller});

  final AppController controller;

  @override
  State<ConnectionPage> createState() => _ConnectionPageState();
}

class _ConnectionPageState extends State<ConnectionPage> {
  late final TextEditingController _apiUrl;
  late final TextEditingController _vlmUrl;
  late final TextEditingController _apiKey;
  late final TextEditingController _timeout;
  bool _savingApi = false;
  bool _testingVlm = false;
  String? _connectionMessage;

  AppController get controller => widget.controller;

  @override
  void initState() {
    super.initState();
    _apiUrl = TextEditingController(text: controller.apiBaseUrl);
    _vlmUrl = TextEditingController(text: controller.vlmSettings.baseUrl);
    _apiKey = TextEditingController();
    _timeout = TextEditingController(text: '${controller.vlmSettings.timeout}');
  }

  @override
  void dispose() {
    _apiUrl.dispose();
    _vlmUrl.dispose();
    _apiKey.dispose();
    _timeout.dispose();
    super.dispose();
  }

  Future<void> _saveApiUrl() async {
    setState(() => _savingApi = true);
    try {
      await controller.setApiBaseUrl(_apiUrl.text);
      if (!mounted) return;
      setState(() => _connectionMessage = controller.apiOnline
          ? 'The local API is responding.'
          : 'Could not reach the local API.');
    } catch (error) {
      if (!mounted) return;
      setState(() => _connectionMessage = error.toString());
    } finally {
      if (mounted) setState(() => _savingApi = false);
    }
  }

  Future<void> _testVlm() async {
    final timeout = int.tryParse(_timeout.text.trim()) ?? 120;
    if (timeout < 5 || timeout > 600) {
      _showMessage('Timeout must be between 5 and 600 seconds.', error: true);
      return;
    }
    setState(() {
      _testingVlm = true;
      _connectionMessage = null;
    });
    try {
      final result = await controller.testVlmConnection(
        baseUrl: _vlmUrl.text.trim(),
        apiKey: _apiKey.text,
        timeoutSeconds: timeout,
      );
      if (!mounted) return;
      setState(() {
        _connectionMessage =
            'Connected · ${(result['models'] as List<dynamic>? ?? const []).length} model(s) found.';
      });
      _apiKey.clear();
    } catch (error) {
      if (!mounted) return;
      setState(() => _connectionMessage = error.toString());
    } finally {
      if (mounted) setState(() => _testingVlm = false);
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
    final scheme = Theme.of(context).colorScheme;
    final settings = controller.vlmSettings;

    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          PageHeader(
            eyebrow: 'Connect',
            title: 'VLM connection',
            subtitle: 'Connect UDB to a running OpenAI-compatible vision-language API.',
            trailing: Icon(Icons.hub_rounded, size: 36, color: scheme.primary),
          ),
          LayoutBuilder(
            builder: (context, constraints) {
              final compact = constraints.maxWidth < 820;
              final localApi = SectionCard(
                title: 'UDB local API',
                subtitle: 'The Expressive interface communicates with the shared Python backend.',
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    TextField(
                      controller: _apiUrl,
                      decoration: const InputDecoration(
                        labelText: 'API base address',
                        hintText: 'http://127.0.0.1:17891',
                        prefixIcon: Icon(Icons.dns_outlined),
                      ),
                    ),
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        Icon(
                          controller.apiOnline ? Icons.check_circle_rounded : Icons.error_outline_rounded,
                          color: controller.apiOnline ? scheme.primary : scheme.error,
                        ),
                        const SizedBox(width: 9),
                        Expanded(
                          child: Text(
                            controller.apiOnline ? 'Connected to local UDB API' : 'API is offline',
                            style: Theme.of(context).textTheme.labelLarge,
                          ),
                        ),
                        FilledButton.tonal(
                          onPressed: _savingApi ? null : _saveApiUrl,
                          child: Text(_savingApi ? 'Checking…' : 'Connect'),
                        ),
                      ],
                    ),
                    if (_connectionMessage != null) ...[
                      const SizedBox(height: 10),
                      Text(
                        _connectionMessage!,
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(color: scheme.onSurfaceVariant),
                      ),
                    ],
                  ],
                ),
              );
              final vlmCard = SectionCard(
                title: 'Vision-language model',
                subtitle: 'These details are stored by the local backend. The API key is never returned to the UI.',
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    TextField(
                      controller: _vlmUrl,
                      decoration: const InputDecoration(
                        labelText: 'OpenAI-compatible base URL',
                        hintText: 'http://127.0.0.1:10809/v1',
                        prefixIcon: Icon(Icons.link_rounded),
                      ),
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _apiKey,
                      obscureText: true,
                      enableSuggestions: false,
                      autocorrect: false,
                      decoration: InputDecoration(
                        labelText: 'API key',
                        hintText: settings.apiKeyConfigured ? 'A key is already configured · blank input clears it' : 'Optional for local endpoints',
                        prefixIcon: const Icon(Icons.key_rounded),
                      ),
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _timeout,
                      keyboardType: TextInputType.number,
                      decoration: const InputDecoration(
                        labelText: 'Request timeout (seconds)',
                        prefixIcon: Icon(Icons.timer_outlined),
                      ),
                    ),
                    const SizedBox(height: 16),
                    FilledButton.icon(
                      onPressed: _testingVlm || !controller.apiOnline ? null : _testVlm,
                      icon: _testingVlm
                          ? const SizedBox(width: 17, height: 17, child: CircularProgressIndicator(strokeWidth: 2))
                          : const Icon(Icons.network_check_rounded),
                      label: Text(_testingVlm ? 'Testing endpoint…' : 'Test VLM connection'),
                    ),
                    if (_connectionMessage != null) ...[
                      const SizedBox(height: 12),
                      Text(
                        _connectionMessage!,
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(color: scheme.onSurfaceVariant),
                      ),
                    ],
                    if (settings.models.isNotEmpty) ...[
                      const SizedBox(height: 18),
                      DropdownButtonFormField<String>(
                        value: settings.models.contains(settings.model)
                            ? settings.model
                            : settings.models.first,
                        decoration: const InputDecoration(
                          labelText: 'Selected model',
                          prefixIcon: Icon(Icons.memory_rounded),
                        ),
                        items: [
                          for (final model in settings.models)
                            DropdownMenuItem(value: model, child: Text(model, overflow: TextOverflow.ellipsis)),
                        ],
                        onChanged: (value) async {
                          if (value == null) return;
                          try {
                            await controller.saveVlmModel(value);
                          } catch (error) {
                            _showMessage(error.toString(), error: true);
                          }
                        },
                      ),
                    ],
                  ],
                ),
              );

              if (compact) {
                return Column(
                  children: [localApi, const SizedBox(height: 14), vlmCard],
                );
              }
              return Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(child: localApi),
                  const SizedBox(width: 14),
                  Expanded(child: vlmCard),
                ],
              );
            },
          ),
          const SizedBox(height: 16),
          SectionCard(
            title: 'Connection notes',
            child: Column(
              children: const [
                _ConnectionNote(
                  icon: Icons.lock_outline_rounded,
                  title: 'Local by default',
                  text: 'The UDB API listens on loopback (127.0.0.1). It is not intended to be exposed to a network.',
                ),
                SizedBox(height: 14),
                _ConnectionNote(
                  icon: Icons.visibility_outlined,
                  title: 'VLM is external',
                  text: 'The model runtime stays independent. UDB sends image-plus-prompt requests to the configured API.',
                ),
                SizedBox(height: 14),
                _ConnectionNote(
                  icon: Icons.password_rounded,
                  title: 'Key privacy',
                  text: 'The VLM key is stored by the backend and is only exposed to the interface as a configured/not-configured state.',
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),
        ],
      ),
    );
  }
}

class _ConnectionNote extends StatelessWidget {
  const _ConnectionNote({
    required this.icon,
    required this.title,
    required this.text,
  });

  final IconData icon;
  final String title;
  final String text;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, color: scheme.primary),
        const SizedBox(width: 14),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(title, style: Theme.of(context).textTheme.titleSmall),
              const SizedBox(height: 3),
              Text(text, style: Theme.of(context).textTheme.bodySmall?.copyWith(color: scheme.onSurfaceVariant)),
            ],
          ),
        ),
      ],
    );
  }
}
