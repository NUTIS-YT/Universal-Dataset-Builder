import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:universal_dataset_builder_expressive/data/models.dart';
import 'package:universal_dataset_builder_expressive/data/udb_api.dart';

void main() {
  group('API models', () {
    test('project statistics are parsed as integer counters', () {
      final project = ProjectInfo.fromJson({
        'name': 'Character set',
        'database_path': '/data/Character set/project.fdb',
        'root_path': '/data/Character set',
        'source_path': '/data/Character set/source',
        'dataset_path': '/data/Character set/dataset',
        'metadata_path': '/data/Character set/dataset/metadata.jsonl',
        'metadata_format': 'jsonl',
        'statistics': {
          'images': 23,
          'captions': 18,
          'reviewed': 9,
          'failed': 1,
        },
      });

      expect(project.name, 'Character set');
      expect(project.statistics['images'], 23);
      expect(project.statistics['captions'], 18);
      expect(project.statistics['reviewed'], 9);
      expect(project.statistics['failed'], 1);
    });

    test('character settings preserve the enabled state and trigger word', () {
      final settings = CharacterSettings.fromJson({
        'enabled': true,
        'description': 'A character with silver hair and green eyes.',
        'trigger_word': 'silver_character',
      });

      expect(settings.enabled, isTrue);
      expect(settings.triggerWord, 'silver_character');
      expect(settings.toJson()['description'],
          'A character with silver hair and green eyes.');
    });

    test('dataset image pages retain total count and pagination offsets', () {
      final page = DatasetImagePage.fromJson({
        'items': [
          {
            'image_id': 7,
            'filename': '00007.png',
            'original_filename': 'portrait.png',
            'status': 'Captioned',
            'caption_text': 'A character portrait.',
            'caption_reviewed': false,
            'file_url': '/api/v1/project/images/7/file',
            'width': 1024,
            'height': 1024,
            'format': 'PNG',
          },
        ],
        'total': 245,
        'offset': 100,
        'limit': 100,
      });

      expect(page.items, hasLength(1));
      expect(page.items.single.id, 7);
      expect(page.total, 245);
      expect(page.offset, 100);
      expect(page.limit, 100);
    });

    test('job snapshots expose progress and terminal state', () {
      final job = JobSnapshot.fromJson({
        'job_id': 'abc123',
        'kind': 'caption_generation',
        'status': 'completed',
        'cancellable': false,
        'progress': {
          'current': 12,
          'total': 12,
          'percent': 100,
          'item': '012.png',
        },
        'result': {'generated': 12, 'failed': 0},
      });

      expect(job.isTerminal, isTrue);
      expect(job.isActive, isFalse);
      expect(job.percent, 100);
      expect(job.item, '012.png');
      expect(job.result?['generated'], 12);
    });
  });

  test('API client sends project creation to the shared backend', () async {
    final client = MockClient((request) async {
      expect(request.method, 'POST');
      expect(request.url.path, '/api/v1/project/create');
      final body = jsonDecode(request.body) as Map<String, dynamic>;
      expect(body['directory'], '/datasets');
      expect(body['name'], 'New set');

      return http.Response(
        jsonEncode({
          'name': 'New set',
          'database_path': '/datasets/New set/project.fdb',
          'root_path': '/datasets/New set',
          'source_path': '/datasets/New set/source',
          'dataset_path': '/datasets/New set/dataset',
          'metadata_path': '/datasets/New set/dataset/metadata.jsonl',
          'metadata_format': 'jsonl',
          'statistics': {'images': 0, 'captions': 0, 'reviewed': 0, 'failed': 0},
        }),
        201,
        headers: {'content-type': 'application/json'},
      );
    });

    final api = UdbApi('http://127.0.0.1:17891', client: client);
    final project = await api.createProject('/datasets', 'New set');

    expect(project.name, 'New set');
    expect(project.statistics['images'], 0);
    api.close();
  });

  test('API client surfaces backend error details', () async {
    final api = UdbApi(
      'http://127.0.0.1:17891',
      client: MockClient(
        (_) async => http.Response(
          jsonEncode({'detail': 'No project is currently open.'}),
          409,
          headers: {'content-type': 'application/json'},
        ),
      ),
    );

    await expectLater(
      api.getProject(),
      throwsA(
        isA<ApiException>().having(
          (error) => error.statusCode,
          'statusCode',
          409,
        ),
      ),
    );
    api.close();
  });
}
