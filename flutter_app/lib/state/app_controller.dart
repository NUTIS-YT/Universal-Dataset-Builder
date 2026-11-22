import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../data/models.dart';
import '../data/udb_api.dart';

enum MotionPreset { gentle, expressive }

class AppController extends ChangeNotifier {
  static const _defaultApiUrl = 'http://127.0.0.1:17891';

  final SharedPreferencesAsync _preferences = SharedPreferencesAsync();
  late UdbApi api;

  String apiBaseUrl = _defaultApiUrl;
  String themeMode = 'dark';
  bool animationsEnabled = true;
  MotionPreset motionPreset = MotionPreset.expressive;
  bool initialized = false;
  bool apiOnline = false;
  bool loading = false;
  String? lastError;

  ProjectInfo? project;
  List<DatasetImage> images = [];
  VlmSettings vlmSettings = const VlmSettings();
  CharacterSettings characterSettings = const CharacterSettings();
  JobSnapshot? job;

  bool get hasProject => project != null;
  bool get jobActive => job?.isActive ?? false;
  bool get isDark => themeMode == 'dark';

  Duration motionDuration(
    int milliseconds, {
    bool systemReduced = false,
  }) {
    if (!animationsEnabled || systemReduced) {
      return Duration.zero;
    }
    final multiplier = motionPreset == MotionPreset.expressive ? 1.0 : 0.55;
    return Duration(milliseconds: (milliseconds * multiplier).round());
  }

  Future<void> initialize() async {
    apiBaseUrl = await _preferences.getString('api_base_url') ?? _defaultApiUrl;
    themeMode = await _preferences.getString('theme_mode') ?? 'dark';
    animationsEnabled = await _preferences.getBool('animations_enabled') ?? true;
    final preset = await _preferences.getString('motion_preset') ?? 'expressive';
    motionPreset =
        preset == 'gentle' ? MotionPreset.gentle : MotionPreset.expressive;
    api = UdbApi(apiBaseUrl);
    await refreshConnection();
    initialized = true;
    notifyListeners();
  }

  Future<void> refreshConnection() async {
    try {
      apiOnline = await api.health();
      lastError = null;
      if (apiOnline) {
        vlmSettings = await api.getSettings();
        try {
          project = await api.getProject();
          await _refreshProjectData();
        } on ApiException catch (error) {
          if (error.statusCode == 409) {
            project = null;
            images = [];
            characterSettings = const CharacterSettings();
          } else {
            rethrow;
          }
        }
      }
    } catch (error) {
      apiOnline = false;
      lastError = error.toString();
    }
    notifyListeners();
  }

  Future<void> setApiBaseUrl(String value) async {
    final cleaned = value.trim().replaceFirst(RegExp(r'/+$'), '');
    if (cleaned.isEmpty) {
      throw const ApiException('Enter the local API address.');
    }
    apiBaseUrl = cleaned;
    api.updateBaseUrl(cleaned);
    await _preferences.setString('api_base_url', cleaned);
    notifyListeners();
    await refreshConnection();
  }

  Future<void> createProject(String directory, String name) async {
    _ensureIdle();
    project = await api.createProject(directory, name);
    await _refreshProjectData();
    notifyListeners();
  }

  Future<void> openProject(String databasePath) async {
    _ensureIdle();
    project = await api.openProject(databasePath);
    await _refreshProjectData();
    notifyListeners();
  }

  Future<void> closeProject() async {
    _ensureIdle();
    await api.closeProject();
    project = null;
    images = [];
    characterSettings = const CharacterSettings();
    notifyListeners();
  }

  Future<void> _refreshProjectData() async {
    project = await api.getProject();
    images = await api.getImages();
    characterSettings = await api.getCharacterSettings();
  }

  Future<void> refreshProject() async {
    if (!apiOnline || project == null) return;
    await _refreshProjectData();
    notifyListeners();
  }

  Future<void> refreshImages({
    String search = '',
    String? status,
  }) async {
    if (project == null) return;
    images = await api.getImages(search: search, status: status);
    notifyListeners();
  }

  Future<void> updateImageCaption(int imageId, String caption) async {
    await api.updateCaption(imageId, caption);
    await refreshProject();
  }

  Future<void> updateImageStatus(int imageId, String status) async {
    await api.updateStatus(imageId, status);
    await refreshProject();
  }

  Future<void> saveCharacterSettings(CharacterSettings settings) async {
    characterSettings = await api.updateCharacterSettings(settings);
    notifyListeners();
  }

  Future<void> saveCaptionPrompt(String prompt) async {
    vlmSettings = await api.updateSettings({'caption_prompt': prompt});
    notifyListeners();
  }

  Future<void> saveVlmModel(String model) async {
    vlmSettings = await api.updateSettings({'vlm_model': model});
    notifyListeners();
  }

  Future<JsonMap> testVlmConnection({
    required String baseUrl,
    required String apiKey,
    required int timeoutSeconds,
  }) async {
    final result = await api.testVlm(
      baseUrl: baseUrl,
      apiKey: apiKey,
      timeoutSeconds: timeoutSeconds,
    );
    vlmSettings = await api.getSettings();
    notifyListeners();
    return result;
  }

  Future<void> startScan() async {
    _ensureProjectAndIdle();
    final started = await api.scan();
    _beginJob(started);
  }

  Future<void> startNormalization({
    required int startNumber,
    required String alphaMode,
    required bool skipDuplicates,
    required String sortMode,
  }) async {
    _ensureProjectAndIdle();
    final started = await api.normalize(
      startNumber: startNumber,
      alphaMode: alphaMode,
      skipDuplicates: skipDuplicates,
      sortMode: sortMode,
    );
    _beginJob(started);
  }

  Future<void> startCaptionGeneration({
    required String selectionMode,
    required int limit,
    required String prompt,
  }) async {
    _ensureProjectAndIdle();
    final started = await api.generateCaptions(
      selectionMode: selectionMode,
      limit: limit,
      prompt: prompt,
    );
    _beginJob(started);
  }

  void _beginJob(JobSnapshot started) {
    job = started;
    lastError = null;
    notifyListeners();
    unawaited(_watchJob(started.id));
  }

  Future<void> _watchJob(String id) async {
    while (true) {
      await Future<void>.delayed(const Duration(milliseconds: 700));
      try {
        final latest = await api.getJob(id);
        job = latest;
        notifyListeners();
        if (latest.isTerminal) {
          if (latest.status == 'failed') {
            lastError = latest.error ?? 'The operation failed.';
          }
          await refreshProject();
          return;
        }
      } catch (error) {
        lastError = error.toString();
        notifyListeners();
        return;
      }
    }
  }

  Future<void> cancelCurrentJob() async {
    final active = job;
    if (active == null || !active.isActive || !active.cancellable) return;
    await api.cancelJob(active.id);
    job = await api.getJob(active.id);
    notifyListeners();
  }

  Future<void> setThemeMode(String value) async {
    themeMode = value;
    await _preferences.setString('theme_mode', value);
    notifyListeners();
  }

  Future<void> setAnimationsEnabled(bool value) async {
    animationsEnabled = value;
    await _preferences.setBool('animations_enabled', value);
    notifyListeners();
  }

  Future<void> setMotionPreset(MotionPreset value) async {
    motionPreset = value;
    await _preferences.setString(
      'motion_preset',
      value == MotionPreset.gentle ? 'gentle' : 'expressive',
    );
    notifyListeners();
  }

  void clearError() {
    lastError = null;
    notifyListeners();
  }

  void _ensureIdle() {
    if (jobActive) {
      throw const ApiException('Wait for the current dataset operation to finish.');
    }
  }

  void _ensureProjectAndIdle() {
    if (project == null) {
      throw const ApiException('Create or open a project first.');
    }
    _ensureIdle();
  }

  @override
  void dispose() {
    api.close();
    super.dispose();
  }
}
