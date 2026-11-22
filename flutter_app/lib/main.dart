import 'package:material_ui/material_ui.dart';

import 'app.dart';
import 'state/app_controller.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(UdbExpressiveApp(controller: AppController()));
}
