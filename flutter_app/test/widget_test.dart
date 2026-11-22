import 'package:material_ui/material_ui.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:universal_dataset_builder_expressive/widgets/common.dart';

void main() {
  testWidgets('PageHeader shows its title and description', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: PageHeader(
            eyebrow: 'Workspace',
            title: 'Your dataset space',
            subtitle: 'Prepare your images and captions.',
          ),
        ),
      ),
    );

    expect(find.text('Your dataset space'), findsOneWidget);
    expect(find.text('Prepare your images and captions.'), findsOneWidget);
    expect(find.text('WORKSPACE'), findsOneWidget);
  });
}
