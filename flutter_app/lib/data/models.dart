typedef JsonMap = Map<String, dynamic>;

class ProjectInfo {
  const ProjectInfo({
    required this.name,
    required this.databasePath,
    required this.rootPath,
    required this.sourcePath,
    required this.datasetPath,
    required this.metadataPath,
    required this.metadataFormat,
    required this.statistics,
  });

  final String name;
  final String databasePath;
  final String rootPath;
  final String sourcePath;
  final String datasetPath;
  final String metadataPath;
  final String metadataFormat;
  final Map<String, int> statistics;

  factory ProjectInfo.fromJson(JsonMap json) {
    final rawStats = json['statistics'];
    final stats = <String, int>{};
    if (rawStats is Map) {
      for (final entry in rawStats.entries) {
        stats[entry.key.toString()] = (entry.value as num?)?.toInt() ?? 0;
      }
    }
    return ProjectInfo(
      name: json['name'] as String? ?? 'Untitled project',
      databasePath: json['database_path'] as String? ?? '',
      rootPath: json['root_path'] as String? ?? '',
      sourcePath: json['source_path'] as String? ?? '',
      datasetPath: json['dataset_path'] as String? ?? '',
      metadataPath: json['metadata_path'] as String? ?? '',
      metadataFormat: json['metadata_format'] as String? ?? 'jsonl',
      statistics: stats,
    );
  }
}

class DatasetImage {
  const DatasetImage({
    required this.id,
    required this.filename,
    required this.originalFilename,
    required this.status,
    required this.caption,
    required this.captionReviewed,
    required this.fileUrl,
    this.width,
    this.height,
    this.format,
  });

  final int id;
  final String filename;
  final String originalFilename;
  final String status;
  final String caption;
  final bool captionReviewed;
  final String fileUrl;
  final int? width;
  final int? height;
  final String? format;

  factory DatasetImage.fromJson(JsonMap json) => DatasetImage(
        id: (json['image_id'] as num?)?.toInt() ?? 0,
        filename: json['filename'] as String? ?? '',
        originalFilename: json['original_filename'] as String? ?? '',
        status: json['status'] as String? ?? 'Pending',
        caption: json['caption_text'] as String? ?? '',
        captionReviewed: json['caption_reviewed'] as bool? ?? false,
        fileUrl: json['file_url'] as String? ?? '',
        width: (json['width'] as num?)?.toInt(),
        height: (json['height'] as num?)?.toInt(),
        format: json['format'] as String?,
      );
}

class JobSnapshot {
  const JobSnapshot({
    required this.id,
    required this.kind,
    required this.status,
    required this.cancellable,
    required this.current,
    required this.total,
    required this.percent,
    required this.item,
    this.error,
    this.result,
  });

  final String id;
  final String kind;
  final String status;
  final bool cancellable;
  final int current;
  final int total;
  final int percent;
  final String item;
  final String? error;
  final JsonMap? result;

  bool get isTerminal =>
      status == 'completed' || status == 'cancelled' || status == 'failed';

  bool get isActive =>
      status == 'queued' || status == 'running' || status == 'cancelling';

  factory JobSnapshot.fromJson(JsonMap json) {
    final progress = json['progress'] is Map
        ? Map<String, dynamic>.from(json['progress'] as Map)
        : <String, dynamic>{};
    final result = json['result'] is Map
        ? Map<String, dynamic>.from(json['result'] as Map)
        : null;
    return JobSnapshot(
      id: json['job_id'] as String? ?? '',
      kind: json['kind'] as String? ?? 'operation',
      status: json['status'] as String? ?? 'queued',
      cancellable: json['cancellable'] as bool? ?? false,
      current: (progress['current'] as num?)?.toInt() ?? 0,
      total: (progress['total'] as num?)?.toInt() ?? 0,
      percent: (progress['percent'] as num?)?.toInt() ?? 0,
      item: progress['item'] as String? ?? '',
      error: json['error'] as String?,
      result: result,
    );
  }
}

class CharacterSettings {
  const CharacterSettings({
    this.enabled = false,
    this.description = '',
    this.triggerWord = '',
  });

  final bool enabled;
  final String description;
  final String triggerWord;

  factory CharacterSettings.fromJson(JsonMap json) => CharacterSettings(
        enabled: json['enabled'] as bool? ?? false,
        description: json['description'] as String? ?? '',
        triggerWord: json['trigger_word'] as String? ?? '',
      );

  JsonMap toJson() => {
        'enabled': enabled,
        'description': description,
        'trigger_word': triggerWord,
      };
}

class VlmSettings {
  const VlmSettings({
    this.baseUrl = '',
    this.apiKeyConfigured = false,
    this.timeout = 120,
    this.model = '',
    this.models = const [],
    this.captionPrompt = '',
  });

  final String baseUrl;
  final bool apiKeyConfigured;
  final int timeout;
  final String model;
  final List<String> models;
  final String captionPrompt;

  factory VlmSettings.fromJson(JsonMap json) => VlmSettings(
        baseUrl: json['vlm_base_url'] as String? ?? '',
        apiKeyConfigured: json['vlm_api_key_configured'] as bool? ?? false,
        timeout: (json['vlm_timeout'] as num?)?.toInt() ?? 120,
        model: json['vlm_model'] as String? ?? '',
        models: (json['vlm_models'] as List<dynamic>? ?? const [])
            .whereType<String>()
            .toList(),
        captionPrompt: json['caption_prompt'] as String? ?? '',
      );
}
