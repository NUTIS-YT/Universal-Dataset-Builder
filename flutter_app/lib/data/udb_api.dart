import 'dart:convert';

import 'package:http/http.dart' as http;

import 'models.dart';

class ApiException implements Exception {
  const ApiException(this.message, {this.statusCode});

  final String message;
  final int? statusCode;

  @override
  String toString() => message;
}

class UdbApi {
  UdbApi(String baseUrl, {http.Client? client})
      : _baseUrl = _normaliseBaseUrl(baseUrl),
        _client = client ?? http.Client();

  final http.Client _client;
  String _baseUrl;

  String get baseUrl => _baseUrl;

  static String _normaliseBaseUrl(String value) {
    final trimmed = value.trim();
    if (trimmed.isEmpty) {
      return 'http://127.0.0.1:17891';
    }
    return trimmed.replaceFirst(RegExp(r'/+$'), '');
  }

  void updateBaseUrl(String value) {
    _baseUrl = _normaliseBaseUrl(value);
  }

  Uri _uri(String path, [Map<String, String>? query]) {
    final uri = Uri.parse(_baseUrl).resolve(path);
    return query == null ? uri : uri.replace(queryParameters: query);
  }

  Future<dynamic> _request(
    String method,
    String path, {
    Object? body,
    Map<String, String>? query,
    Duration timeout = const Duration(seconds: 45),
  }) async {
    final request = http.Request(method, _uri(path, query))
      ..headers['Accept'] = 'application/json';
    if (body != null) {
      request.headers['Content-Type'] = 'application/json';
      request.body = jsonEncode(body);
    }

    final streamed = await _client.send(request).timeout(timeout);
    final response = await http.Response.fromStream(streamed).timeout(timeout);
    if (response.statusCode < 200 || response.statusCode >= 300) {
      var message = 'Request failed (status ${response.statusCode}).';
      try {
        final decoded = jsonDecode(response.body);
        if (decoded is Map && decoded['detail'] != null) {
          message = decoded['detail'].toString();
        }
      } on FormatException {
        if (response.body.isNotEmpty) {
          message = response.body;
        }
      }
      throw ApiException(message, statusCode: response.statusCode);
    }
    if (response.statusCode == 204 || response.body.isEmpty) {
      return null;
    }
    return jsonDecode(response.body);
  }

  Future<bool> health() async {
    final data = await _request('GET', '/api/v1/health') as JsonMap;
    return data['status'] == 'ok';
  }

  Future<ProjectInfo> getProject() async =>
      ProjectInfo.fromJson(await _request('GET', '/api/v1/project') as JsonMap);

  Future<ProjectInfo> createProject(String directory, String name) async =>
      ProjectInfo.fromJson(
        await _request(
          'POST',
          '/api/v1/project/create',
          body: {'directory': directory, 'name': name},
        ) as JsonMap,
      );

  Future<ProjectInfo> openProject(String databasePath) async =>
      ProjectInfo.fromJson(
        await _request(
          'POST',
          '/api/v1/project/open',
          body: {'database_path': databasePath},
        ) as JsonMap,
      );

  Future<void> closeProject() async {
    await _request('DELETE', '/api/v1/project');
  }

  Future<DatasetImagePage> getImagesPage({
    String search = '',
    String? status,
    int offset = 0,
    int limit = 100,
  }) async {
    final query = <String, String>{
      'search': search,
      'offset': '$offset',
      'limit': '$limit',
    };
    if (status != null && status != 'All') {
      query['status'] = status;
    }
    final data = await _request(
      'GET',
      '/api/v1/project/images',
      query: query,
    ) as JsonMap;
    return DatasetImagePage.fromJson(data);
  }

  Future<List<DatasetImage>> getImages({
    String search = '',
    String? status,
    int offset = 0,
    int limit = 100,
  }) async =>
      (await getImagesPage(
        search: search,
        status: status,
        offset: offset,
        limit: limit,
      )).items;

  Uri imageUri(String fileUrl) => _uri(fileUrl);

  Future<void> updateCaption(int imageId, String caption) async {
    await _request(
      'PATCH',
      '/api/v1/project/images/$imageId/caption',
      body: {'caption': caption},
    );
  }

  Future<void> updateStatus(int imageId, String status) async {
    await _request(
      'PATCH',
      '/api/v1/project/images/$imageId/status',
      body: {'status': status},
    );
  }

  Future<JobSnapshot> scan({bool recursive = true}) async =>
      JobSnapshot.fromJson(
        await _request(
          'POST',
          '/api/v1/project/scan',
          body: {'recursive': recursive},
        ) as JsonMap,
      );

  Future<JobSnapshot> normalize({
    int startNumber = 1,
    String alphaMode = 'preserve',
    bool skipDuplicates = true,
    String sortMode = 'filename_asc',
  }) async =>
      JobSnapshot.fromJson(
        await _request(
          'POST',
          '/api/v1/project/normalize',
          body: {
            'start_number': startNumber,
            'alpha_mode': alphaMode,
            'skip_duplicates': skipDuplicates,
            'sort_mode': sortMode,
          },
        ) as JsonMap,
      );

  Future<JobSnapshot> generateCaptions({
    required String selectionMode,
    required int limit,
    required String prompt,
  }) async =>
      JobSnapshot.fromJson(
        await _request(
          'POST',
          '/api/v1/project/captions/generate',
          body: {
            'selection_mode': selectionMode,
            'limit': limit,
            'prompt': prompt,
          },
        ) as JsonMap,
      );

  Future<JobSnapshot> getJob(String jobId) async =>
      JobSnapshot.fromJson(
        await _request('GET', '/api/v1/jobs/$jobId') as JsonMap,
      );

  Future<void> cancelJob(String jobId) async {
    await _request('DELETE', '/api/v1/jobs/$jobId');
  }

  Future<VlmSettings> getSettings() async =>
      VlmSettings.fromJson(
        await _request('GET', '/api/v1/settings') as JsonMap,
      );

  Future<VlmSettings> updateSettings(JsonMap values) async =>
      VlmSettings.fromJson(
        await _request('PUT', '/api/v1/settings', body: values) as JsonMap,
      );

  Future<JsonMap> testVlm({
    required String baseUrl,
    required String apiKey,
    required int timeoutSeconds,
  }) async =>
      Map<String, dynamic>.from(
        await _request(
          'POST',
          '/api/v1/vlm/test',
          body: {
            'base_url': baseUrl,
            'api_key': apiKey,
            'timeout_seconds': timeoutSeconds,
          },
          timeout: Duration(seconds: timeoutSeconds + 15),
        ) as Map,
      );

  Future<List<String>> getVlmModels() async {
    final data = await _request('GET', '/api/v1/vlm/models') as JsonMap;
    return (data['models'] as List<dynamic>? ?? const []).whereType<String>().toList();
  }

  Future<CharacterSettings> getCharacterSettings() async =>
      CharacterSettings.fromJson(
        await _request('GET', '/api/v1/project/caption-settings') as JsonMap,
      );

  Future<CharacterSettings> updateCharacterSettings(
    CharacterSettings settings,
  ) async =>
      CharacterSettings.fromJson(
        await _request(
          'PUT',
          '/api/v1/project/caption-settings',
          body: settings.toJson(),
        ) as JsonMap,
      );

  void close() => _client.close();
}
